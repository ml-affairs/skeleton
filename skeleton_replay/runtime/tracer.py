"""Runtime tracer built on ``sys.setprofile``."""

from __future__ import annotations

import inspect
import json
import runpy
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import TextIO

from skeleton_replay.runtime.events import Endpoint, TraceEvent
from skeleton_replay.runtime.filters import TraceFilter
from skeleton_replay.safety import ValueSummariser


@dataclass(frozen=True)
class TraceOptions:
    """Configuration for a single traced target run."""

    project_root: Path
    out_dir: Path
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    max_events: int | None = None


@dataclass(frozen=True)
class TraceResult:
    """Paths produced by the runtime trace phase."""

    trace_path: Path
    event_count: int


class RuntimeTracer:
    """Collect public project-local call and return events."""

    def __init__(self, options: TraceOptions, summariser: ValueSummariser | None = None) -> None:
        """Initialize a runtime tracer for one target execution."""
        self.options = options
        self.summariser = summariser or ValueSummariser()
        self.trace_filter = TraceFilter(
            project_root=options.project_root,
            include=options.include,
            exclude=options.exclude,
        )
        self.trace_path = options.out_dir / "trace.jsonl"
        self._event_count = 0
        self._stack: list[Endpoint] = []
        self._frames: dict[int, Endpoint] = {}
        self._writer: TextIO | None = None

    @property
    def event_count(self) -> int:
        """Return the number of events written by this tracer."""
        return self._event_count

    def __enter__(self) -> RuntimeTracer:
        """Open the trace writer and install the profile callback."""
        self.options.out_dir.mkdir(parents=True, exist_ok=True)
        self._writer = self.trace_path.open("w", encoding="utf-8")
        sys.setprofile(self._profile)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Remove the profile callback and close the trace writer."""
        sys.setprofile(None)
        if self._writer:
            self._writer.close()

    def _profile(self, frame: FrameType, event: str, arg: object) -> None:
        if event == "call":
            self._handle_call(frame)
        elif event == "return":
            self._handle_return(frame, arg)

    def _handle_call(self, frame: FrameType) -> None:
        endpoint = self._endpoint_from_frame(frame)
        if endpoint is None:
            return

        caller = self._stack[-1] if self._stack else None
        args = self.summariser.summarise_arguments(self._argument_values(frame))
        self._write_event(
            TraceEvent(
                event_type="call",
                order=self._event_count,
                timestamp=time.time(),
                depth=len(self._stack),
                caller=caller,
                callee=endpoint,
                args=args,
            )
        )
        self._frames[id(frame)] = endpoint
        self._stack.append(endpoint)

    def _handle_return(self, frame: FrameType, return_value: object) -> None:
        endpoint = self._frames.pop(id(frame), None)
        if endpoint is None:
            return

        self._pop_endpoint(endpoint)
        caller = self._stack[-1] if self._stack else None
        self._write_event(
            TraceEvent(
                event_type="return",
                order=self._event_count,
                timestamp=time.time(),
                depth=len(self._stack),
                caller=caller,
                callee=endpoint,
                return_value=self.summariser.summarise_value(return_value, name="return"),
            )
        )

    def _write_event(self, event: TraceEvent) -> None:
        if self.options.max_events is not None and self._event_count >= self.options.max_events:
            return
        if self._writer is None:
            raise RuntimeError("Trace writer is not open")
        self._writer.write(json.dumps(event.to_json(), sort_keys=True) + "\n")
        self._event_count += 1

    def _endpoint_from_frame(self, frame: FrameType) -> Endpoint | None:
        code = frame.f_code
        filename = code.co_filename
        function = code.co_name
        if self._is_class_body(frame):
            return None
        if not self.trace_filter.allows_function(function):
            return None
        if not self.trace_filter.allows_file(filename):
            return None

        file_path = str(Path(filename).resolve())
        module = self._module_name(frame, Path(filename))
        class_name, instance_id = self._class_and_instance(frame, module)
        qualified_name = self._qualified_name(module=module, class_name=class_name, function=function)
        return Endpoint(
            module=module,
            class_name=class_name,
            function=function,
            qualified_name=qualified_name,
            file=file_path,
            line=code.co_firstlineno,
            node_id=f"function:{qualified_name}",
            instance_id=instance_id,
        )

    def _module_name(self, frame: FrameType, filename: Path) -> str:
        module = frame.f_globals.get("__name__")
        if isinstance(module, str) and module not in {"__main__", "<run_path>"}:
            return module
        return self.trace_filter.module_from_path(filename)

    @staticmethod
    def _class_and_instance(frame: FrameType, module: str) -> tuple[str | None, str | None]:
        if "self" in frame.f_locals:
            instance = frame.f_locals["self"]
            class_name = type(instance).__name__
            return class_name, f"{module}.{class_name}@0x{id(instance):x}"
        if "cls" in frame.f_locals and inspect.isclass(frame.f_locals["cls"]):
            cls = frame.f_locals["cls"]
            return str(cls.__name__), None
        return None, None

    @staticmethod
    def _is_class_body(frame: FrameType) -> bool:
        qualified_name = frame.f_locals.get("__qualname__")
        has_class_locals = isinstance(qualified_name, str) and frame.f_code.co_name == qualified_name and "__module__" in frame.f_locals
        has_class_code_flags = (frame.f_code.co_flags & inspect.CO_NEWLOCALS) == 0
        return has_class_locals or has_class_code_flags

    @staticmethod
    def _argument_values(frame: FrameType) -> dict[str, object]:
        try:
            arg_info = inspect.getargvalues(frame)
        except Exception:
            return {}
        values: dict[str, object] = {}
        for name in arg_info.args:
            if name not in {"self", "cls"}:
                values[name] = arg_info.locals.get(name)
        if arg_info.varargs:
            values[arg_info.varargs] = arg_info.locals.get(arg_info.varargs, ())
        if arg_info.keywords:
            values[arg_info.keywords] = arg_info.locals.get(arg_info.keywords, {})
        return values

    @staticmethod
    def _qualified_name(*, module: str, class_name: str | None, function: str) -> str:
        parts = [module]
        if class_name:
            parts.append(class_name)
        parts.append(function)
        return ".".join(part for part in parts if part)

    def _pop_endpoint(self, endpoint: Endpoint) -> None:
        if self._stack and self._stack[-1] == endpoint:
            self._stack.pop()
            return
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index] == endpoint:
                del self._stack[index]
                return


@dataclass(frozen=True)
class TargetScriptRunner:
    """Runs a target script under a runtime tracer."""

    summariser: ValueSummariser = field(default_factory=ValueSummariser)

    def run(self, script: Path, script_args: list[str], options: TraceOptions) -> TraceResult:
        """Run a Python script under the runtime tracer."""
        script = script.resolve()
        project_root = options.project_root.resolve()
        old_argv = sys.argv[:]
        old_path = sys.path[:]
        sys.argv = [str(script), *script_args]
        sys.path.insert(0, str(script.parent))
        if str(project_root) not in sys.path:
            sys.path.insert(1, str(project_root))
        try:
            with RuntimeTracer(options, summariser=self.summariser) as tracer:
                runpy.run_path(str(script), run_name="__main__")
                return TraceResult(trace_path=tracer.trace_path, event_count=tracer.event_count)
        finally:
            sys.argv = old_argv
            sys.path = old_path

"""Pytest target runner for tracing existing test scenarios."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from skeleton_replay.runtime.tracer import RuntimeTracer, TraceOptions, TraceResult
from skeleton_replay.safety import ValueSummariser


@dataclass(frozen=True)
class TargetPytestRunner:
    """Runs pytest under a runtime tracer."""

    summariser: ValueSummariser = field(default_factory=ValueSummariser)

    def run(self, pytest_args: list[str], options: TraceOptions) -> TraceResult:
        """Run pytest under the runtime tracer and preserve pytest's exit code."""
        try:
            import pytest
        except ModuleNotFoundError as exc:
            raise RuntimeError("pytest is required for `skeleton pytest`; install Skeleton with the dev/test environment that provides pytest.") from exc

        project_root = options.project_root.resolve()
        old_argv = sys.argv[:]
        old_path = sys.path[:]
        old_cwd = Path.cwd()
        sys.argv = ["pytest", *pytest_args]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        try:
            os.chdir(project_root)
            with RuntimeTracer(options, summariser=self.summariser) as tracer:
                exit_code = self._exit_code(pytest.main(pytest_args))
                return TraceResult(trace_path=tracer.trace_path, event_count=tracer.event_count, target_exit_code=exit_code)
        finally:
            os.chdir(old_cwd)
            sys.argv = old_argv
            sys.path = old_path

    @staticmethod
    def _exit_code(value: object) -> int:
        """Normalize pytest's ``ExitCode`` enum or integer-like return value."""
        if isinstance(value, int):
            return value
        return int(value) if hasattr(value, "__int__") else 1

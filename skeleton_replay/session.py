"""Public Python API for running Skeleton trace sessions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Literal, Self

from skeleton_replay.analysis import ArchitectureQualityAnalyzer, ArchitectureQualityWriter
from skeleton_replay.interface import ArtifactGenerationPipeline, ArtifactPaths, HtmlReportOpener, OutputPathResolver, PytestOutputPathResolver, SessionArtifactSet, SessionManifestWriter, SessionTarget
from skeleton_replay.reporting import HtmlReportWriter, WorkflowNarrativeWriter
from skeleton_replay.runtime import RuntimeTracer, TargetPytestRunner, TargetScriptRunner, TraceOptions, TraceResult


@dataclass(frozen=True)
class TraceSessionResult:
    """Artifacts and metrics produced by one Skeleton trace session."""

    trace_path: Path
    snapshot_path: Path
    workflow_path: Path
    quality_path: Path
    quality_markdown_path: Path
    session_path: Path
    report_path: Path | None
    report_opened: bool
    event_count: int
    node_count: int
    edge_count: int
    target_exit_code: int
    target_error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether the traced target completed with exit code zero."""
        return self.target_exit_code == 0


@dataclass
class InProcessTraceSession:
    """Context manager that traces already-running Python code and writes Skeleton artifacts."""

    trace_session: TraceSession
    label: str
    project_root: Path
    out_dir: Path
    _tracer: RuntimeTracer | None = field(default=None, init=False, repr=False)
    _result: TraceSessionResult | None = field(default=None, init=False, repr=False)

    @property
    def result(self) -> TraceSessionResult:
        """Return generated artifacts after the context exits."""
        if self._result is None:
            raise RuntimeError("Skeleton trace result is available after the trace context exits")
        return self._result

    def __enter__(self) -> Self:
        """Start tracing the current process."""
        trace_options = TraceOptions(
            project_root=self.project_root,
            out_dir=self.out_dir,
            include=self.trace_session.include,
            exclude=self.trace_session.exclude,
            max_events=self.trace_session.max_events,
        )
        tracer = RuntimeTracer(trace_options)
        self._tracer = tracer.__enter__()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> Literal[False]:
        """Stop tracing, write artifacts, and preserve any target exception."""
        if self._tracer is None:
            raise RuntimeError("Skeleton trace context was not entered")
        self._tracer.__exit__(exc_type, exc, traceback)
        target_exit_code = self._target_exit_code(exc)
        target_error = None if exc is None or isinstance(exc, SystemExit) else f"{type(exc).__name__}: {exc}"
        trace_result = TraceResult(trace_path=self._tracer.trace_path, event_count=self._tracer.event_count, target_exit_code=target_exit_code)
        self._result = self.trace_session._result_from_trace(
            command="trace",
            invocation=("skeleton_replay.trace", self.label),
            project_root=self.project_root,
            out_dir=self.out_dir,
            target=SessionTarget(kind="callable", label=self.label),
            trace_result=trace_result,
            target_exit_code=target_exit_code,
            target_error=target_error,
        )
        return False

    @staticmethod
    def _target_exit_code(exc: BaseException | None) -> int:
        if exc is None:
            return 0
        if isinstance(exc, SystemExit):
            return TraceSession._system_exit_code(exc)
        return 1


@dataclass(frozen=True)
class TraceSession:
    """Run Python code under Skeleton and produce replayable architecture artifacts."""

    project_root: Path | str
    out_dir: Path | str | None = None
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    max_events: int | None = None
    html_enabled: bool = True
    open_report: bool = False
    pytest_runner: TargetPytestRunner = field(default_factory=TargetPytestRunner)
    runner: TargetScriptRunner = field(default_factory=TargetScriptRunner)
    report_writer: HtmlReportWriter = field(default_factory=HtmlReportWriter)
    workflow_writer: WorkflowNarrativeWriter = field(default_factory=WorkflowNarrativeWriter)
    quality_analyzer: ArchitectureQualityAnalyzer = field(default_factory=ArchitectureQualityAnalyzer)
    quality_writer: ArchitectureQualityWriter = field(default_factory=ArchitectureQualityWriter)
    output_paths: OutputPathResolver = field(default_factory=OutputPathResolver)
    pytest_output_paths: PytestOutputPathResolver = field(default_factory=PytestOutputPathResolver)
    report_opener: HtmlReportOpener = field(default_factory=HtmlReportOpener)
    session_manifest_writer: SessionManifestWriter = field(default_factory=SessionManifestWriter)

    def trace(self, label: str) -> InProcessTraceSession:
        """Return a context manager for tracing already-running Python code."""
        clean_label = self._resolved_label(label)
        project_root = self._resolved_project_root()
        out_dir = self.output_paths.resolve_callable(project_root=project_root, requested_out_dir=self._requested_out_dir(), label=clean_label)
        return InProcessTraceSession(trace_session=self, label=clean_label, project_root=project_root, out_dir=out_dir)

    def run_script(self, script: Path | str, script_args: Sequence[str] = ()) -> TraceSessionResult:
        """Trace a Python script and return generated artifact paths and metrics."""
        project_root = self._resolved_project_root()
        script_path = self._resolved_script(script)
        out_dir = self.output_paths.resolve(project_root=project_root, requested_out_dir=self._requested_out_dir(), target_path=script_path)
        trace_options = TraceOptions(
            project_root=project_root,
            out_dir=out_dir,
            include=self.include,
            exclude=self.exclude,
            max_events=self.max_events,
        )

        trace_result: TraceResult | None = None
        target_exit_code = 0
        target_error: str | None = None
        try:
            trace_result = self.runner.run(script_path, list(script_args), trace_options)
        except SystemExit as exc:
            target_exit_code = self._system_exit_code(exc)
        except Exception as exc:
            target_exit_code = 1
            target_error = f"{type(exc).__name__}: {exc}"

        return self._result_from_trace(
            command="run_script",
            invocation=("TraceSession.run_script", str(script_path), *script_args),
            project_root=project_root,
            out_dir=out_dir,
            target=SessionTarget(kind="script", path=script_path, args=tuple(script_args)),
            trace_result=trace_result,
            target_exit_code=target_exit_code,
            target_error=target_error,
        )

    def run_pytest(self, pytest_args: Sequence[str] = ()) -> TraceSessionResult:
        """Trace a pytest invocation and return generated artifact paths and metrics."""
        project_root = self._resolved_project_root()
        pytest_arguments = list(pytest_args)
        out_dir = self.pytest_output_paths.resolve(project_root=project_root, requested_out_dir=self._requested_out_dir(), pytest_args=pytest_arguments)
        trace_options = TraceOptions(
            project_root=project_root,
            out_dir=out_dir,
            include=self.include,
            exclude=self.exclude,
            max_events=self.max_events,
        )

        trace_result: TraceResult | None = None
        target_exit_code = 0
        target_error: str | None = None
        try:
            trace_result = self.pytest_runner.run(list(pytest_arguments), trace_options)
            target_exit_code = trace_result.target_exit_code
        except SystemExit as exc:
            target_exit_code = self._system_exit_code(exc)
        except Exception as exc:
            target_exit_code = 1
            target_error = f"{type(exc).__name__}: {exc}"

        return self._result_from_trace(
            command="run_pytest",
            invocation=("TraceSession.run_pytest", *pytest_arguments),
            project_root=project_root,
            out_dir=out_dir,
            target=SessionTarget(kind="pytest", args=tuple(pytest_arguments)),
            trace_result=trace_result,
            target_exit_code=target_exit_code,
            target_error=target_error,
        )

    def _result_from_trace(
        self,
        *,
        command: str,
        invocation: tuple[str, ...],
        project_root: Path,
        out_dir: Path,
        target: SessionTarget,
        trace_result: TraceResult | None,
        target_exit_code: int,
        target_error: str | None,
    ) -> TraceSessionResult:
        """Generate artifacts from a trace result and return public session metadata."""
        trace_path = trace_result.trace_path if trace_result else out_dir / "trace.jsonl"
        snapshot_path = out_dir / "snapshot.json"
        workflow_path = out_dir / "workflow.md"
        quality_path = out_dir / "quality.json"
        quality_markdown_path = out_dir / "architecture_quality.md"
        session_path = out_dir / "session.json"
        report_path = out_dir / "report.html" if self.html_enabled else None
        artifact_result = ArtifactGenerationPipeline(
            report_writer=self.report_writer,
            workflow_writer=self.workflow_writer,
            quality_analyzer=self.quality_analyzer,
            quality_writer=self.quality_writer,
        ).generate(
            project_root=project_root,
            paths=ArtifactPaths(
                trace_path=trace_path,
                snapshot_path=snapshot_path,
                workflow_path=workflow_path,
                quality_path=quality_path,
                quality_markdown_path=quality_markdown_path,
                report_path=report_path,
            ),
        )
        report_opened = False
        if report_path is not None and self.open_report:
            report_opened = self.report_opener.open(report_path)

        event_count = trace_result.event_count if trace_result else artifact_result.metrics.event_count
        self.session_manifest_writer.write(
            session_path=session_path,
            command=command,
            invocation=invocation,
            project_root=project_root,
            target=target,
            artifacts=SessionArtifactSet(
                trace_path=trace_path,
                snapshot_path=snapshot_path,
                workflow_path=workflow_path,
                quality_path=quality_path,
                quality_markdown_path=quality_markdown_path,
                report_path=report_path,
                session_path=session_path,
            ),
            event_count=event_count,
            node_count=artifact_result.metrics.node_count,
            edge_count=artifact_result.metrics.edge_count,
            target_exit_code=target_exit_code,
            target_error=target_error,
            report_opened=report_opened,
        )
        return TraceSessionResult(
            trace_path=trace_path,
            snapshot_path=snapshot_path,
            workflow_path=workflow_path,
            quality_path=quality_path,
            quality_markdown_path=quality_markdown_path,
            session_path=session_path,
            report_path=report_path,
            report_opened=report_opened,
            event_count=event_count,
            node_count=artifact_result.metrics.node_count,
            edge_count=artifact_result.metrics.edge_count,
            target_exit_code=target_exit_code,
            target_error=target_error,
        )

    def _resolved_project_root(self) -> Path:
        project_root = Path(self.project_root).expanduser().resolve()
        if not project_root.exists():
            raise FileNotFoundError(f"Project root not found: {project_root}")
        if not project_root.is_dir():
            raise NotADirectoryError(f"Project root is not a directory: {project_root}")
        return project_root

    def _resolved_script(self, script: Path | str) -> Path:
        script_path = Path(script).expanduser().resolve()
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        if not script_path.is_file():
            raise ValueError(f"Script is not a file: {script_path}")
        return script_path

    def _requested_out_dir(self) -> Path | None:
        if self.out_dir is None:
            return None
        return Path(self.out_dir).expanduser().resolve()

    @staticmethod
    def _resolved_label(label: str) -> str:
        clean_label = label.strip()
        if not clean_label:
            raise ValueError("Trace label must not be empty")
        return clean_label

    @staticmethod
    def _system_exit_code(exc: SystemExit) -> int:
        return exc.code if isinstance(exc.code, int) else 1


def trace(
    *,
    project_root: Path | str,
    label: str,
    out_dir: Path | str | None = None,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    max_events: int | None = None,
    html_enabled: bool = True,
    open_report: bool = False,
) -> InProcessTraceSession:
    """Return a context manager that traces code running in the current Python process."""
    return TraceSession(
        project_root=project_root,
        out_dir=out_dir,
        include=include,
        exclude=exclude,
        max_events=max_events,
        html_enabled=html_enabled,
        open_report=open_report,
    ).trace(label)

"""Public Python API for running Skeleton trace sessions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from skeleton_replay.analysis import SnapshotBuilder, SnapshotMetrics
from skeleton_replay.interface import HtmlReportOpener, OutputPathResolver
from skeleton_replay.reporting import HtmlReportWriter, WorkflowNarrativeWriter
from skeleton_replay.runtime import TargetScriptRunner, TraceOptions, TraceResult


@dataclass(frozen=True)
class TraceSessionResult:
    """Artifacts and metrics produced by one Skeleton trace session."""

    trace_path: Path
    snapshot_path: Path
    workflow_path: Path
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
    runner: TargetScriptRunner = field(default_factory=TargetScriptRunner)
    report_writer: HtmlReportWriter = field(default_factory=HtmlReportWriter)
    workflow_writer: WorkflowNarrativeWriter = field(default_factory=WorkflowNarrativeWriter)
    output_paths: OutputPathResolver = field(default_factory=OutputPathResolver)
    report_opener: HtmlReportOpener = field(default_factory=HtmlReportOpener)

    def run_script(self, script: Path | str, script_args: Sequence[str] = ()) -> TraceSessionResult:
        """Trace a Python script and return generated artifact paths and metrics."""
        project_root = self._resolved_project_root()
        script_path = self._resolved_script(script)
        out_dir = self.output_paths.resolve(project_root=project_root, requested_out_dir=self._requested_out_dir())
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

        trace_path = trace_result.trace_path if trace_result else out_dir / "trace.jsonl"
        snapshot_path = out_dir / "snapshot.json"
        workflow_path = out_dir / "workflow.md"
        snapshot = SnapshotBuilder(project_root).build(trace_path, snapshot_path)
        metrics = SnapshotMetrics.from_snapshot(snapshot)
        self.workflow_writer.write(snapshot, workflow_path)

        report_path: Path | None = None
        report_opened = False
        if self.html_enabled:
            report_path = out_dir / "report.html"
            self.report_writer.write(snapshot, report_path)
            if self.open_report:
                report_opened = self.report_opener.open(report_path)

        event_count = trace_result.event_count if trace_result else metrics.event_count
        return TraceSessionResult(
            trace_path=trace_path,
            snapshot_path=snapshot_path,
            workflow_path=workflow_path,
            report_path=report_path,
            report_opened=report_opened,
            event_count=event_count,
            node_count=metrics.node_count,
            edge_count=metrics.edge_count,
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
    def _system_exit_code(exc: SystemExit) -> int:
        return exc.code if isinstance(exc.code, int) else 1

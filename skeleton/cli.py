"""Command line interface for Skeleton."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from skeleton.analysis import SnapshotBuilder, SnapshotMetrics
from skeleton.interface import ColorMode, SkeletonConsole
from skeleton.reporting import HtmlReportWriter, WorkflowNarrativeWriter
from skeleton.runtime import TargetScriptRunner, TraceOptions, TraceResult


@dataclass(frozen=True)
class RunConfiguration:
    """Validated configuration for one ``skeleton run`` invocation."""

    script: Path
    script_args: list[str]
    project_root: Path
    out_dir: Path
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    max_events: int | None
    html_enabled: bool

    @property
    def trace_path(self) -> Path:
        """Return the trace output path."""
        return self.out_dir / "trace.jsonl"

    @property
    def snapshot_path(self) -> Path:
        """Return the snapshot output path."""
        return self.out_dir / "snapshot.json"

    @property
    def report_path(self) -> Path:
        """Return the HTML report output path."""
        return self.out_dir / "report.html"

    @property
    def workflow_path(self) -> Path:
        """Return the workflow narrative output path."""
        return self.out_dir / "workflow.md"

    def trace_options(self) -> TraceOptions:
        """Return runtime tracing options for this command."""
        return TraceOptions(
            project_root=self.project_root,
            out_dir=self.out_dir,
            include=self.include,
            exclude=self.exclude,
            max_events=self.max_events,
        )


@dataclass(frozen=True)
class RunCommand:
    """Executes ``skeleton run`` as a coordinated architecture replay pipeline."""

    console: SkeletonConsole
    runner: TargetScriptRunner = field(default_factory=TargetScriptRunner)
    report_writer: HtmlReportWriter = field(default_factory=HtmlReportWriter)
    workflow_writer: WorkflowNarrativeWriter = field(default_factory=WorkflowNarrativeWriter)

    def execute(self, args: argparse.Namespace) -> int:
        """Run the target script and generate Skeleton artifacts."""
        config = self._configuration_from_args(args)
        self.console.banner(project_root=config.project_root, out_dir=config.out_dir)
        self._warn_if_script_is_outside_project(config)

        result: TraceResult | None = None
        target_exit_code = 0
        target_error: Exception | None = None

        self.console.step("Tracing project-local public calls")
        try:
            result = self.runner.run(config.script, config.script_args, config.trace_options())
        except SystemExit as exc:
            target_exit_code = self._system_exit_code(exc)
            self.console.warning(f"Target exited with status {target_exit_code}; writing artifacts from captured events.")
        except Exception as exc:
            target_exit_code = 1
            target_error = exc
            self.console.error(f"Target raised {type(exc).__name__}: {exc}")

        self.console.step("Building architecture snapshot")
        snapshot = SnapshotBuilder(config.project_root).build(config.trace_path, config.snapshot_path)
        metrics = SnapshotMetrics.from_snapshot(snapshot)

        self.console.step("Writing LLM-readable workflow narrative")
        self.workflow_writer.write(snapshot, config.workflow_path)

        report_path = None
        if config.html_enabled:
            self.console.step("Rendering interactive HTML replay")
            self.report_writer.write(snapshot, config.report_path)
            report_path = config.report_path

        event_count = result.event_count if result else metrics.event_count
        self.console.summary(
            event_count=event_count,
            node_count=metrics.node_count,
            edge_count=metrics.edge_count,
            trace_path=config.trace_path,
            snapshot_path=config.snapshot_path,
            workflow_path=config.workflow_path,
            report_path=report_path,
        )
        if target_error:
            self.console.warning("Skeleton completed artifact generation, but the target script failed.")
        else:
            self.console.success("Replay artifacts ready.")
        return target_exit_code

    def _configuration_from_args(self, args: argparse.Namespace) -> RunConfiguration:
        script = Path(args.script).resolve()
        if not script.exists():
            raise SystemExit(f"Script not found: {script}")
        if not script.is_file():
            raise SystemExit(f"Script is not a file: {script}")

        project_root = self._project_root(script=script, raw_project_root=args.project_root)
        if not project_root.exists():
            raise SystemExit(f"Project root not found: {project_root}")
        if not project_root.is_dir():
            raise SystemExit(f"Project root is not a directory: {project_root}")

        out_dir = (Path(args.out_dir) if args.out_dir else project_root / ".skeleton").resolve()
        return RunConfiguration(
            script=script,
            script_args=list(args.script_args),
            project_root=project_root,
            out_dir=out_dir,
            include=tuple(args.include or ()),
            exclude=tuple(args.exclude or ()),
            max_events=args.max_events,
            html_enabled=not args.no_html,
        )

    def _warn_if_script_is_outside_project(self, config: RunConfiguration) -> None:
        try:
            config.script.relative_to(config.project_root)
        except ValueError:
            self.console.warning("Target script is outside the project root; only project-root files will be traced.")

    @staticmethod
    def _project_root(*, script: Path, raw_project_root: Path | None) -> Path:
        if raw_project_root:
            return raw_project_root.resolve()
        cwd = Path.cwd().resolve()
        try:
            script.relative_to(cwd)
        except ValueError:
            return script.parent.resolve()
        return cwd

    @staticmethod
    def _system_exit_code(exc: SystemExit) -> int:
        return exc.code if isinstance(exc.code, int) else 1


@dataclass(frozen=True)
class CliApplication:
    """Owns parsing and command dispatch for the Skeleton CLI."""

    def build_parser(self) -> argparse.ArgumentParser:
        """Build the command line parser for Skeleton."""
        parser = argparse.ArgumentParser(
            prog="skeleton",
            description="Replay and visualise the living architecture of a Python application.",
        )
        parser.add_argument(
            "--color",
            choices=("auto", "always", "never"),
            default="auto",
            help="Control ANSI color output.",
        )
        subparsers = parser.add_subparsers(dest="command", required=True)
        run_parser = subparsers.add_parser("run", help="Run a Python script under Skeleton tracing")
        run_parser.add_argument("--project-root", type=Path, default=None)
        run_parser.add_argument("--out-dir", type=Path, default=None)
        run_parser.add_argument("--include", action="append", default=[])
        run_parser.add_argument("--exclude", action="append", default=[])
        run_parser.add_argument("--max-events", type=int, default=None)
        run_parser.add_argument("--no-html", action="store_true")
        run_parser.add_argument(
            "--color",
            choices=("auto", "always", "never"),
            default=argparse.SUPPRESS,
            help="Control ANSI color output.",
        )
        run_parser.add_argument("script", type=Path)
        run_parser.add_argument("script_args", nargs=argparse.REMAINDER)
        return parser

    def run(self, argv: list[str] | None = None) -> int:
        """Parse arguments and execute the requested command."""
        parser = self.build_parser()
        args = parser.parse_args(argv)
        console = SkeletonConsole(color_mode=self._color_mode(args.color))
        if args.command == "run":
            return RunCommand(console=console).execute(args)
        parser.error(f"Unknown command: {args.command}")
        return 2

    @staticmethod
    def _color_mode(value: str) -> ColorMode:
        if value in {"auto", "always", "never"}:
            return cast(ColorMode, value)
        return "auto"


def main(argv: list[str] | None = None) -> int:
    """Run the Skeleton command line interface."""
    return CliApplication().run(argv)

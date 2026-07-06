"""Command line interface for Skeleton."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, cast

from skeleton_replay.analysis import ArchitectureQualityAnalyzer, ArchitectureQualityWriter
from skeleton_replay.interface import ArtifactGenerationPipeline, ArtifactPaths, ColorMode, HtmlReportOpener, OutputPathResolver, PytestOutputPathResolver, SkeletonConsole
from skeleton_replay.reporting import HtmlReportWriter, WorkflowNarrativeWriter
from skeleton_replay.runtime import TargetPytestRunner, TargetScriptRunner, TraceOptions, TraceResult


class ReportOpener(Protocol):
    """Boundary for opening generated HTML reports."""

    def open(self, report_path: Path) -> bool:
        """Open a generated HTML report."""


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
    open_report: bool

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

    @property
    def quality_path(self) -> Path:
        """Return the machine-readable quality report path."""
        return self.out_dir / "quality.json"

    @property
    def quality_markdown_path(self) -> Path:
        """Return the human-readable quality report path."""
        return self.out_dir / "architecture_quality.md"

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
class PytestConfiguration:
    """Validated configuration for one ``skeleton pytest`` invocation."""

    pytest_args: list[str]
    project_root: Path
    out_dir: Path
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    max_events: int | None
    html_enabled: bool
    open_report: bool

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

    @property
    def quality_path(self) -> Path:
        """Return the machine-readable quality report path."""
        return self.out_dir / "quality.json"

    @property
    def quality_markdown_path(self) -> Path:
        """Return the human-readable quality report path."""
        return self.out_dir / "architecture_quality.md"

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
    quality_analyzer: ArchitectureQualityAnalyzer = field(default_factory=ArchitectureQualityAnalyzer)
    quality_writer: ArchitectureQualityWriter = field(default_factory=ArchitectureQualityWriter)
    output_paths: OutputPathResolver = field(default_factory=OutputPathResolver)
    report_opener: ReportOpener = field(default_factory=HtmlReportOpener)

    def execute(self, args: argparse.Namespace) -> int:
        """Run the target script and generate Skeleton artifacts."""
        config = self._configuration_from_args(args)
        self.console.banner(project_root=config.project_root, out_dir=config.out_dir)
        self._warn_if_script_is_outside_project(config)

        result: TraceResult | None = None
        target_exit_code = 0
        target_error: Exception | None = None

        self.console.step("Tracing project-local calls")
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
        self.console.step("Analyzing design-quality signals")
        self.console.step("Writing LLM-readable workflow narrative")
        if config.html_enabled:
            self.console.step("Rendering interactive HTML replay")
        artifact_result = ArtifactGenerationPipeline(
            report_writer=self.report_writer,
            workflow_writer=self.workflow_writer,
            quality_analyzer=self.quality_analyzer,
            quality_writer=self.quality_writer,
        ).generate(
            project_root=config.project_root,
            paths=ArtifactPaths(
                trace_path=config.trace_path,
                snapshot_path=config.snapshot_path,
                workflow_path=config.workflow_path,
                quality_path=config.quality_path,
                quality_markdown_path=config.quality_markdown_path,
                report_path=config.report_path if config.html_enabled else None,
            ),
        )

        report_path = artifact_result.report_path
        report_opened = False
        if report_path is not None and config.open_report:
            self.console.step("Opening HTML replay")
            report_opened = self.report_opener.open(report_path)
            if not report_opened:
                self.console.warning(f"Could not open report automatically: {report_path}")

        event_count = result.event_count if result else artifact_result.metrics.event_count
        self.console.summary(
            event_count=event_count,
            node_count=artifact_result.metrics.node_count,
            edge_count=artifact_result.metrics.edge_count,
            trace_path=config.trace_path,
            snapshot_path=config.snapshot_path,
            workflow_path=config.workflow_path,
            quality_path=config.quality_path,
            quality_markdown_path=config.quality_markdown_path,
            report_path=report_path,
            report_opened=report_opened,
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

        out_dir = self.output_paths.resolve(project_root=project_root, requested_out_dir=args.out_dir, target_path=script)
        return RunConfiguration(
            script=script,
            script_args=list(args.script_args),
            project_root=project_root,
            out_dir=out_dir,
            include=tuple(args.include or ()),
            exclude=tuple(args.exclude or ()),
            max_events=args.max_events,
            html_enabled=not args.no_html,
            open_report=not args.no_open and not args.no_html,
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
class PytestCommand:
    """Executes ``skeleton pytest`` as a traced pytest session."""

    console: SkeletonConsole
    runner: TargetPytestRunner = field(default_factory=TargetPytestRunner)
    report_writer: HtmlReportWriter = field(default_factory=HtmlReportWriter)
    workflow_writer: WorkflowNarrativeWriter = field(default_factory=WorkflowNarrativeWriter)
    quality_analyzer: ArchitectureQualityAnalyzer = field(default_factory=ArchitectureQualityAnalyzer)
    quality_writer: ArchitectureQualityWriter = field(default_factory=ArchitectureQualityWriter)
    output_paths: PytestOutputPathResolver = field(default_factory=PytestOutputPathResolver)
    report_opener: ReportOpener = field(default_factory=HtmlReportOpener)

    def execute(self, args: argparse.Namespace) -> int:
        """Run pytest and generate Skeleton artifacts."""
        config = self._configuration_from_args(args)
        self.console.banner(project_root=config.project_root, out_dir=config.out_dir)

        result: TraceResult | None = None
        target_exit_code = 0
        target_error: Exception | None = None

        self.console.step("Tracing pytest session")
        try:
            result = self.runner.run(config.pytest_args, config.trace_options())
            target_exit_code = result.target_exit_code
            if target_exit_code != 0:
                self.console.warning(f"Pytest exited with status {target_exit_code}; writing artifacts from captured events.")
        except SystemExit as exc:
            target_exit_code = self._system_exit_code(exc)
            self.console.warning(f"Pytest exited with status {target_exit_code}; writing artifacts from captured events.")
        except Exception as exc:
            target_exit_code = 1
            target_error = exc
            self.console.error(f"Pytest tracing raised {type(exc).__name__}: {exc}")

        trace_path = result.trace_path if result else config.trace_path
        self.console.step("Building architecture snapshot")
        self.console.step("Analyzing design-quality signals")
        self.console.step("Writing LLM-readable workflow narrative")
        if config.html_enabled:
            self.console.step("Rendering interactive HTML replay")
        artifact_result = ArtifactGenerationPipeline(
            report_writer=self.report_writer,
            workflow_writer=self.workflow_writer,
            quality_analyzer=self.quality_analyzer,
            quality_writer=self.quality_writer,
        ).generate(
            project_root=config.project_root,
            paths=ArtifactPaths(
                trace_path=trace_path,
                snapshot_path=config.snapshot_path,
                workflow_path=config.workflow_path,
                quality_path=config.quality_path,
                quality_markdown_path=config.quality_markdown_path,
                report_path=config.report_path if config.html_enabled else None,
            ),
        )

        report_path = artifact_result.report_path
        report_opened = False
        if report_path is not None and config.open_report:
            self.console.step("Opening HTML replay")
            report_opened = self.report_opener.open(report_path)
            if not report_opened:
                self.console.warning(f"Could not open report automatically: {report_path}")

        event_count = result.event_count if result else artifact_result.metrics.event_count
        self.console.summary(
            event_count=event_count,
            node_count=artifact_result.metrics.node_count,
            edge_count=artifact_result.metrics.edge_count,
            trace_path=trace_path,
            snapshot_path=config.snapshot_path,
            workflow_path=config.workflow_path,
            quality_path=config.quality_path,
            quality_markdown_path=config.quality_markdown_path,
            report_path=report_path,
            report_opened=report_opened,
        )
        if target_error:
            self.console.warning("Skeleton completed artifact generation, but pytest tracing failed.")
        else:
            self.console.success("Replay artifacts ready.")
        return target_exit_code

    def _configuration_from_args(self, args: argparse.Namespace) -> PytestConfiguration:
        project_root = self._project_root(args.project_root)
        if not project_root.exists():
            raise SystemExit(f"Project root not found: {project_root}")
        if not project_root.is_dir():
            raise SystemExit(f"Project root is not a directory: {project_root}")

        pytest_args = self._pytest_args(args.pytest_args)
        out_dir = self.output_paths.resolve(project_root=project_root, requested_out_dir=args.out_dir, pytest_args=pytest_args)
        return PytestConfiguration(
            pytest_args=pytest_args,
            project_root=project_root,
            out_dir=out_dir,
            include=tuple(args.include or ()),
            exclude=tuple(args.exclude or ()),
            max_events=args.max_events,
            html_enabled=not args.no_html,
            open_report=not args.no_open and not args.no_html,
        )

    @staticmethod
    def _project_root(raw_project_root: Path | None) -> Path:
        if raw_project_root:
            return raw_project_root.resolve()
        return Path.cwd().resolve()

    @staticmethod
    def _pytest_args(pytest_args: list[str]) -> list[str]:
        if pytest_args and pytest_args[0] == "--":
            return pytest_args[1:]
        return pytest_args

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
        run_parser.add_argument("--no-open", action="store_true", help="Do not open report.html after generation.")
        run_parser.add_argument(
            "--color",
            choices=("auto", "always", "never"),
            default=argparse.SUPPRESS,
            help="Control ANSI color output.",
        )
        run_parser.add_argument("script", type=Path)
        run_parser.add_argument("script_args", nargs=argparse.REMAINDER)
        pytest_parser = subparsers.add_parser("pytest", help="Run pytest under Skeleton tracing")
        pytest_parser.add_argument("--project-root", type=Path, default=None)
        pytest_parser.add_argument("--out-dir", type=Path, default=None)
        pytest_parser.add_argument("--include", action="append", default=[])
        pytest_parser.add_argument("--exclude", action="append", default=[])
        pytest_parser.add_argument("--max-events", type=int, default=None)
        pytest_parser.add_argument("--no-html", action="store_true")
        pytest_parser.add_argument("--no-open", action="store_true", help="Do not open report.html after generation.")
        pytest_parser.add_argument(
            "--color",
            choices=("auto", "always", "never"),
            default=argparse.SUPPRESS,
            help="Control ANSI color output.",
        )
        pytest_parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
        return parser

    def run(self, argv: list[str] | None = None) -> int:
        """Parse arguments and execute the requested command."""
        parser = self.build_parser()
        args = parser.parse_args(argv)
        console = SkeletonConsole(color_mode=self._color_mode(args.color))
        if args.command == "run":
            return RunCommand(console=console).execute(args)
        if args.command == "pytest":
            return PytestCommand(console=console).execute(args)
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

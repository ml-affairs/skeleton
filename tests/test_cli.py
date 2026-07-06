import json
from argparse import Namespace
from io import StringIO
from pathlib import Path

import pytest

from skeleton_replay.cli import CliApplication, PytestCommand, RunCommand
from skeleton_replay.interface import OutputPathResolver, SkeletonConsole


class RecordingReportOpener:
    """Test double for report-opening behavior."""

    def __init__(self) -> None:
        """Initialize an empty list of opened report paths."""
        self.opened: list[Path] = []

    def open(self, report_path: Path) -> bool:
        """Record the report path instead of opening a browser."""
        self.opened.append(report_path)
        return True


class TestRunCommand:
    """CLI run command behavior."""

    @pytest.mark.parametrize(
        "project_name",
        [
            "sample_project",
            "sample_supply_chain",
            "sample_orchestrated",
            "sample_io_boundaries",
        ],
    )
    def test_writes_trace_snapshot_workflow_report_for_fixtures(self, project_name: str) -> None:
        # Given
        project_root = Path(f"tests/fixtures/{project_name}").resolve()
        out_dir = project_root / ".skeleton"
        opener = RecordingReportOpener()
        command = RunCommand(
            console=SkeletonConsole(stream=StringIO(), color_mode="never"),
            report_opener=opener,
        )
        args = Namespace(
            script=project_root / "app.py",
            script_args=[],
            project_root=project_root,
            out_dir=out_dir,
            include=[],
            exclude=[],
            max_events=None,
            no_html=False,
            no_open=False,
        )

        # When
        exit_code = command.execute(args)

        # Then
        assert exit_code == 0
        assert (out_dir / "trace.jsonl").exists()
        assert (out_dir / "snapshot.json").exists()
        assert (out_dir / "workflow.md").exists()
        assert (out_dir / "quality.json").exists()
        assert (out_dir / "architecture_quality.md").exists()
        assert (out_dir / "report.html").exists()
        assert (out_dir / "trace.jsonl").stat().st_size > 0
        assert (out_dir / "report.html").stat().st_size > 0
        assert opener.opened == [out_dir / "report.html"]

    def test_writes_trace_snapshot_workflow_report_and_opens_html(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        out_dir = tmp_path / ".skeleton"
        opener = RecordingReportOpener()
        command = RunCommand(
            console=SkeletonConsole(stream=StringIO(), color_mode="never"),
            report_opener=opener,
        )
        args = Namespace(
            script=project_root / "app.py",
            script_args=[],
            project_root=project_root,
            out_dir=out_dir,
            include=[],
            exclude=[],
            max_events=None,
            no_html=False,
            no_open=False,
        )

        # When
        exit_code = command.execute(args)

        # Then
        assert exit_code == 0
        assert (out_dir / "trace.jsonl").exists()
        assert (out_dir / "snapshot.json").exists()
        assert (out_dir / "workflow.md").exists()
        assert (out_dir / "quality.json").exists()
        assert (out_dir / "architecture_quality.md").exists()
        assert (out_dir / "report.html").exists()

        snapshot = json.loads((out_dir / "snapshot.json").read_text(encoding="utf-8"))
        assert snapshot["event_count"] > 0
        assert snapshot["quality"]["summary"]["events"] == snapshot["event_count"]
        assert any(node["id"] == "function:app.main" for node in snapshot["nodes"])
        assert any(node["id"] == "function:service.Greeter.greet" for node in snapshot["nodes"])
        assert not any(node["id"] == "function:service.Greeter" for node in snapshot["nodes"])
        private_node = next(node for node in snapshot["nodes"] if node["id"] == "function:service.Greeter._format")
        assert private_node["is_private"] is True
        assert private_node["visibility"] == "private"
        assert opener.opened == [out_dir / "report.html"]

    def test_opens_html_report_by_default(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        out_dir = tmp_path / "reports"
        opener = RecordingReportOpener()
        command = RunCommand(
            console=SkeletonConsole(stream=StringIO(), color_mode="never"),
            report_opener=opener,
        )
        args = Namespace(
            script=project_root / "app.py",
            script_args=[],
            project_root=project_root,
            out_dir=out_dir,
            include=[],
            exclude=[],
            max_events=None,
            no_html=False,
            no_open=False,
        )

        # When
        exit_code = command.execute(args)

        # Then
        assert exit_code == 0
        assert opener.opened == [out_dir / "report.html"]


class TestPytestCommand:
    """CLI pytest command behavior."""

    def test_writes_artifacts_and_preserves_pytest_exit_code(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_pytest_project").resolve()
        out_dir = tmp_path / "pytest-command-artifacts"
        opener = RecordingReportOpener()
        command = PytestCommand(
            console=SkeletonConsole(stream=StringIO(), color_mode="never"),
            report_opener=opener,
        )
        args = Namespace(
            pytest_args=["-q", "-p", "no:cov", str(project_root / "test_checkout.py::test_builds_receipt_total")],
            project_root=project_root,
            out_dir=out_dir,
            include=[],
            exclude=[],
            max_events=None,
            no_html=False,
            no_open=True,
        )

        # When
        exit_code = command.execute(args)

        # Then
        assert exit_code == 0
        assert (out_dir / "trace.jsonl").exists()
        assert (out_dir / "snapshot.json").exists()
        assert (out_dir / "workflow.md").exists()
        assert (out_dir / "quality.json").exists()
        assert (out_dir / "architecture_quality.md").exists()
        assert (out_dir / "report.html").exists()
        assert opener.opened == []


class TestOutputPathResolver:
    """Output directory resolution behavior."""

    def test_defaults_to_skeleton_home_application_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        skeleton_home = tmp_path / "home" / ".skeleton"
        project_root = Path("tests/fixtures/sample_project").resolve()
        monkeypatch.setenv("SKELETON_HOME", str(skeleton_home))

        # When
        out_dir = OutputPathResolver().resolve(project_root=project_root, requested_out_dir=None)

        # Then
        assert out_dir == skeleton_home / "sample_project"

    def test_uses_preconfigured_output_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        configured_out_dir = tmp_path / "configured-reports"
        project_root = Path("tests/fixtures/sample_project").resolve()
        monkeypatch.setenv("SKELETON_HOME", str(tmp_path / "home" / ".skeleton"))
        monkeypatch.setenv("SKELETON_OUT_DIR", str(configured_out_dir))

        # When
        out_dir = OutputPathResolver().resolve(project_root=project_root, requested_out_dir=None)

        # Then
        assert out_dir == configured_out_dir


class TestCliApplication:
    """Top-level CLI parser behavior."""

    def test_parses_run_command_without_opening(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        out_dir = tmp_path / "cli-reports"

        # When
        exit_code = CliApplication().run(
            [
                "run",
                "--color",
                "never",
                "--no-open",
                "--project-root",
                str(project_root),
                "--out-dir",
                str(out_dir),
                str(project_root / "app.py"),
            ]
        )

        # Then
        assert exit_code == 0
        assert (out_dir / "report.html").exists()

    def test_parses_pytest_command_without_opening(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_pytest_project").resolve()
        out_dir = tmp_path / "cli-pytest-reports"

        # When
        exit_code = CliApplication().run(
            [
                "pytest",
                "--color",
                "never",
                "--no-open",
                "--project-root",
                str(project_root),
                "--out-dir",
                str(out_dir),
                "--",
                "-q",
                "-p",
                "no:cov",
                str(project_root / "test_checkout.py::test_builds_receipt_total"),
            ]
        )

        # Then
        assert exit_code == 0
        assert (out_dir / "report.html").exists()

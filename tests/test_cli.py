import json
import shutil
from argparse import Namespace
from io import StringIO
from pathlib import Path

import pytest

from skeleton_replay.cli import CliApplication, PytestCommand, RunCommand
from skeleton_replay.interface import OutputPathResolver, PytestOutputPathResolver, SkeletonConsole
from skeleton_replay.runtime import TargetPytestRunner, TraceOptions, TraceResult


class RecordingReportOpener:
    """Test double for report-opening behavior."""

    def __init__(self) -> None:
        """Initialize an empty list of opened report paths."""
        self.opened: list[Path] = []

    def open(self, report_path: Path) -> bool:
        """Record the report path instead of opening a browser."""
        self.opened.append(report_path)
        return True


class FailingBeforeTracePytestRunner(TargetPytestRunner):
    """Test double that fails before creating a trace file."""

    def run(self, pytest_args: list[str], options: TraceOptions) -> TraceResult:
        """Raise before delegating to ``RuntimeTracer``."""
        del pytest_args, options
        raise RuntimeError("pytest is unavailable")


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
        assert (out_dir / "session.json").exists()
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
        assert (out_dir / "session.json").exists()
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

        session_manifest = json.loads((out_dir / "session.json").read_text(encoding="utf-8"))
        assert session_manifest["schema_version"] == 1
        assert session_manifest["command"] == "run"
        assert session_manifest["invocation"] == [
            "skeleton",
            "run",
            "--project-root",
            str(project_root),
            "--out-dir",
            str(out_dir),
            str(project_root / "app.py"),
        ]
        assert session_manifest["target"] == {"args": [], "kind": "script", "path": str(project_root / "app.py")}
        assert session_manifest["artifacts"]["session"] == str(out_dir / "session.json")
        assert session_manifest["metrics"]["events"] == snapshot["event_count"]
        assert session_manifest["target_exit_code"] == 0
        assert session_manifest["target_error"] is None
        assert session_manifest["report_opened"] is True

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

    def test_defaults_artifacts_to_selected_test_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_pytest_project").resolve()
        out_dir = project_root / ".skeleton" / "test_checkout" / "test_builds_receipt_total" / "latest"
        opener = RecordingReportOpener()
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)
        command = PytestCommand(
            console=SkeletonConsole(stream=StringIO(), color_mode="never"),
            report_opener=opener,
        )
        args = Namespace(
            pytest_args=["-q", "-p", "no:cov", "test_checkout.py::test_builds_receipt_total"],
            project_root=project_root,
            out_dir=None,
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
        assert (out_dir / "session.json").exists()
        assert (out_dir / "report.html").exists()
        assert opener.opened == []

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
        assert (out_dir / "session.json").exists()
        assert (out_dir / "report.html").exists()
        assert opener.opened == []

        session_manifest = json.loads((out_dir / "session.json").read_text(encoding="utf-8"))
        assert session_manifest["command"] == "pytest"
        assert session_manifest["invocation"] == [
            "skeleton",
            "pytest",
            "--project-root",
            str(project_root),
            "--out-dir",
            str(out_dir),
            "--no-open",
            "--",
            "-q",
            "-p",
            "no:cov",
            str(project_root / "test_checkout.py::test_builds_receipt_total"),
        ]
        assert session_manifest["target"]["kind"] == "pytest"
        assert session_manifest["target_exit_code"] == 0

    def test_writes_empty_trace_artifacts_when_pytest_fails_before_tracing(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_pytest_project").resolve()
        out_dir = tmp_path / "pytest-import-failure-artifacts"
        command = PytestCommand(
            console=SkeletonConsole(stream=StringIO(), color_mode="never"),
            runner=FailingBeforeTracePytestRunner(),
        )
        args = Namespace(
            pytest_args=["-q"],
            project_root=project_root,
            out_dir=out_dir,
            include=[],
            exclude=[],
            max_events=None,
            no_html=True,
            no_open=True,
        )

        # When
        exit_code = command.execute(args)

        # Then
        assert exit_code == 1
        assert (out_dir / "trace.jsonl").exists()
        assert (out_dir / "trace.jsonl").read_text(encoding="utf-8") == ""
        assert (out_dir / "snapshot.json").exists()
        assert (out_dir / "workflow.md").exists()
        assert (out_dir / "quality.json").exists()
        assert (out_dir / "architecture_quality.md").exists()
        assert (out_dir / "session.json").exists()
        assert not (out_dir / "report.html").exists()

        snapshot = json.loads((out_dir / "snapshot.json").read_text(encoding="utf-8"))
        assert snapshot["event_count"] == 0

        session_manifest = json.loads((out_dir / "session.json").read_text(encoding="utf-8"))
        assert "report" not in session_manifest["artifacts"]
        assert session_manifest["target_exit_code"] == 1
        assert session_manifest["target_error"] == "RuntimeError: pytest is unavailable"


class TestOutputPathResolver:
    """Output directory resolution behavior."""

    def test_defaults_to_target_local_script_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        script = project_root / "app.py"
        monkeypatch.delenv("SKELETON_HOME", raising=False)
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)

        # When
        out_dir = OutputPathResolver().resolve(project_root=project_root, requested_out_dir=None, target_path=script)

        # Then
        assert out_dir == project_root / ".skeleton" / "app" / "latest"

    def test_skeleton_home_overrides_target_local_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        skeleton_home = tmp_path / "home" / ".skeleton"
        project_root = Path("tests/fixtures/sample_project").resolve()
        script = project_root / "app.py"
        monkeypatch.setenv("SKELETON_HOME", str(skeleton_home))
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)

        # When
        out_dir = OutputPathResolver().resolve(project_root=project_root, requested_out_dir=None, target_path=script)

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


class TestPytestOutputPathResolver:
    """Pytest output directory resolution behavior."""

    def test_defaults_to_selected_test_node_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "sample_pytest_project"
        shutil.copytree(Path("tests/fixtures/sample_pytest_project"), project_root, ignore=shutil.ignore_patterns("__pycache__", ".skeleton"))
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)

        # When
        out_dir = PytestOutputPathResolver().resolve(
            project_root=project_root,
            requested_out_dir=None,
            pytest_args=["-q", "test_checkout.py::test_builds_receipt_total"],
        )

        # Then
        assert out_dir == project_root / ".skeleton" / "test_checkout" / "test_builds_receipt_total" / "latest"

    def test_defaults_parametrized_test_node_to_safe_deterministic_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "sample_pytest_project"
        shutil.copytree(Path("tests/fixtures/sample_pytest_project"), project_root, ignore=shutil.ignore_patterns("__pycache__", ".skeleton"))
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)

        # When
        first_out_dir = PytestOutputPathResolver().resolve(
            project_root=project_root,
            requested_out_dir=None,
            pytest_args=["test_checkout.py::test_builds_receipt_total[guest/cart]"],
        )
        second_out_dir = PytestOutputPathResolver().resolve(
            project_root=project_root,
            requested_out_dir=None,
            pytest_args=["test_checkout.py::test_builds_receipt_total[guest/cart]"],
        )

        # Then
        assert first_out_dir == second_out_dir
        assert first_out_dir.parent.name.startswith("test_builds_receipt_total_guest_cart")
        assert "[" not in first_out_dir.parent.name
        assert "/" not in first_out_dir.parent.name
        assert first_out_dir == project_root / ".skeleton" / "test_checkout" / first_out_dir.parent.name / "latest"

    def test_defaults_whole_file_invocation_to_file_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "sample_pytest_project"
        shutil.copytree(Path("tests/fixtures/sample_pytest_project"), project_root, ignore=shutil.ignore_patterns("__pycache__", ".skeleton"))
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)

        # When
        out_dir = PytestOutputPathResolver().resolve(
            project_root=project_root,
            requested_out_dir=None,
            pytest_args=["test_checkout.py"],
        )

        # Then
        assert out_dir == project_root / ".skeleton" / "test_checkout" / "file" / "latest"

    def test_reserved_single_test_names_do_not_collide_with_whole_file_sentinel(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "sample_pytest_project"
        shutil.copytree(Path("tests/fixtures/sample_pytest_project"), project_root, ignore=shutil.ignore_patterns("__pycache__", ".skeleton"))
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)

        # When
        file_out_dir = PytestOutputPathResolver().resolve(
            project_root=project_root,
            requested_out_dir=None,
            pytest_args=["test_checkout.py"],
        )
        node_out_dir = PytestOutputPathResolver().resolve(
            project_root=project_root,
            requested_out_dir=None,
            pytest_args=["test_checkout.py::file"],
        )

        # Then
        assert file_out_dir == project_root / ".skeleton" / "test_checkout" / "file" / "latest"
        assert node_out_dir == project_root / ".skeleton" / "test_checkout" / "node-file" / "latest"

    def test_defaults_to_selected_test_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "sample_pytest_project"
        shutil.copytree(Path("tests/fixtures/sample_pytest_project"), project_root, ignore=shutil.ignore_patterns("__pycache__", ".skeleton"))
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)

        # When
        out_dir = PytestOutputPathResolver().resolve(
            project_root=project_root,
            requested_out_dir=None,
            pytest_args=[str(project_root)],
        )

        # Then
        assert out_dir == project_root / ".skeleton" / "directory" / "latest"

    def test_uses_preconfigured_output_directory_before_selected_test(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "sample_pytest_project"
        configured_out_dir = tmp_path / "configured-pytest-reports"
        shutil.copytree(Path("tests/fixtures/sample_pytest_project"), project_root, ignore=shutil.ignore_patterns("__pycache__", ".skeleton"))
        monkeypatch.setenv("SKELETON_OUT_DIR", str(configured_out_dir))

        # When
        out_dir = PytestOutputPathResolver().resolve(
            project_root=project_root,
            requested_out_dir=None,
            pytest_args=["test_checkout.py::test_builds_receipt_total"],
        )

        # Then
        assert out_dir == configured_out_dir

    def test_skeleton_home_overrides_target_local_pytest_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "sample_pytest_project"
        skeleton_home = tmp_path / "home" / ".skeleton"
        shutil.copytree(Path("tests/fixtures/sample_pytest_project"), project_root, ignore=shutil.ignore_patterns("__pycache__", ".skeleton"))
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.setenv("SKELETON_HOME", str(skeleton_home))

        # When
        out_dir = PytestOutputPathResolver().resolve(
            project_root=project_root,
            requested_out_dir=None,
            pytest_args=["test_checkout.py::test_builds_receipt_total"],
        )

        # Then
        assert out_dir == skeleton_home / "sample_pytest_project"


class TestCliApplication:
    """Top-level CLI parser behavior."""

    def test_parses_run_command_with_target_local_default_without_opening(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "sample_project"
        shutil.copytree(Path("tests/fixtures/sample_project"), project_root, ignore=shutil.ignore_patterns("__pycache__", ".skeleton"))
        out_dir = project_root / ".skeleton" / "app" / "latest"
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)

        # When
        exit_code = CliApplication().run(
            [
                "run",
                "--color",
                "never",
                "--no-open",
                "--project-root",
                str(project_root),
                str(project_root / "app.py"),
            ]
        )

        # Then
        assert exit_code == 0
        assert (out_dir / "trace.jsonl").exists()
        assert (out_dir / "report.html").exists()

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

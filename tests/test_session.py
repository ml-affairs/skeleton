import json
import shutil
import sys
from importlib import util
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

import pytest

from skeleton_replay import InProcessTraceSession, TraceSession, trace


class _Monitor(Protocol):
    def run(self) -> int: ...


class _MonitorFactory(Protocol):
    def __call__(self, config: dict[str, int]) -> _Monitor: ...


def _load_module(module_path: Path) -> ModuleType:
    spec = util.spec_from_file_location(module_path.stem, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    previous_module = sys.modules.get(module_path.stem)
    sys.modules[module_path.stem] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous_module is None:
            sys.modules.pop(module_path.stem, None)
        else:
            sys.modules[module_path.stem] = previous_module
    return module


def _write_callable_project(project_root: Path) -> ModuleType:
    project_root.mkdir()
    module_path = project_root / "app.py"
    module_path.write_text(
        """
class Monitor:
    def __init__(self, config):
        self.config = config

    def run(self):
        return self._tick(self.config["count"])

    def _tick(self, count):
        return count + 1
""".lstrip(),
        encoding="utf-8",
    )
    return _load_module(module_path)


class TestTraceSession:
    """Public Python API behavior."""

    @pytest.mark.parametrize(
        ("project_name", "expected_min_calls"),
        [
            ("sample_project", {"function:app.main", "function:service.Greeter.greet"}),
            ("sample_supply_chain", {"function:app.main", "function:supply_service.ShipmentService.fulfill"}),
            ("sample_orchestrated", {"function:app.main", "function:orchestrator.WorkflowOrchestrator.run"}),
        ],
    )
    def test_run_script_writes_reports_for_fixture_projects(
        self,
        project_name: str,
        expected_min_calls: set[str],
    ) -> None:
        # Given
        project_root = Path(f"tests/fixtures/{project_name}").resolve()
        out_dir = project_root / ".skeleton"
        session = TraceSession(project_root=project_root, out_dir=out_dir)

        # When
        result = session.run_script(project_root / "app.py")

        # Then
        assert result.succeeded
        assert result.target_exit_code == 0
        assert not result.report_opened
        assert result.report_path == out_dir / "report.html"
        assert result.trace_path.exists()
        assert result.snapshot_path.exists()
        assert result.workflow_path.exists()
        assert result.quality_path.exists()
        assert result.quality_markdown_path.exists()
        assert result.session_path.exists()
        assert result.report_path is not None
        assert result.report_path.exists()
        assert result.trace_path.stat().st_size > 0
        assert result.snapshot_path.stat().st_size > 0
        assert result.workflow_path.stat().st_size > 0
        assert result.quality_path.stat().st_size > 0
        assert result.quality_markdown_path.stat().st_size > 0
        assert result.report_path.stat().st_size > 0
        assert result.event_count > 0
        assert result.node_count > 0
        assert result.edge_count > 0
        assert result.event_count == sum(1 for _ in result.trace_path.read_text(encoding="utf-8").splitlines() if _.strip())

        snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
        observed_nodes = {node["id"] for node in snapshot["nodes"]}
        assert expected_min_calls.issubset(observed_nodes)

    def test_run_script_writes_artifacts_without_opening_report_by_default(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        out_dir = tmp_path / "api-artifacts"
        session = TraceSession(project_root=project_root, out_dir=out_dir)

        # When
        result = session.run_script(project_root / "app.py")

        # Then
        assert result.succeeded
        assert result.target_exit_code == 0
        assert result.target_error is None
        assert result.trace_path == out_dir / "trace.jsonl"
        assert result.snapshot_path == out_dir / "snapshot.json"
        assert result.workflow_path == out_dir / "workflow.md"
        assert result.quality_path == out_dir / "quality.json"
        assert result.quality_markdown_path == out_dir / "architecture_quality.md"
        assert result.session_path == out_dir / "session.json"
        assert result.report_path == out_dir / "report.html"
        assert not result.report_opened
        assert result.event_count > 0
        assert result.node_count > 0
        assert result.edge_count > 0
        assert result.trace_path.exists()
        assert result.snapshot_path.exists()
        assert result.workflow_path.exists()
        assert result.quality_path.exists()
        assert result.quality_markdown_path.exists()
        assert result.session_path.exists()
        assert result.report_path.exists()

        snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
        assert snapshot["event_count"] == result.event_count
        assert snapshot["quality"]["summary"]["events"] == result.event_count

        session_manifest = json.loads(result.session_path.read_text(encoding="utf-8"))
        assert session_manifest["schema_version"] == 1
        assert session_manifest["command"] == "run_script"
        assert session_manifest["invocation"] == ["TraceSession.run_script", str(project_root / "app.py")]
        assert session_manifest["project_root"] == str(project_root)
        assert session_manifest["target"] == {"args": [], "kind": "script", "path": str(project_root / "app.py")}
        assert session_manifest["artifacts"]["trace"] == str(result.trace_path)
        assert session_manifest["artifacts"]["snapshot"] == str(result.snapshot_path)
        assert session_manifest["artifacts"]["workflow"] == str(result.workflow_path)
        assert session_manifest["artifacts"]["quality"] == str(result.quality_path)
        assert session_manifest["artifacts"]["quality_markdown"] == str(result.quality_markdown_path)
        assert session_manifest["artifacts"]["report"] == str(result.report_path)
        assert session_manifest["artifacts"]["session"] == str(result.session_path)
        assert session_manifest["metrics"] == {"edges": result.edge_count, "events": result.event_count, "nodes": result.node_count}
        assert session_manifest["target_exit_code"] == 0
        assert session_manifest["target_error"] is None
        assert session_manifest["report_opened"] is False

    def test_run_script_defaults_artifacts_to_target_local_latest_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "sample_project"
        shutil.copytree(Path("tests/fixtures/sample_project"), project_root, ignore=shutil.ignore_patterns("__pycache__", ".skeleton"))
        out_dir = project_root / ".skeleton" / "app" / "latest"
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)
        session = TraceSession(project_root=project_root)

        # When
        result = session.run_script(project_root / "app.py")

        # Then
        assert result.succeeded
        assert result.trace_path == out_dir / "trace.jsonl"
        assert result.snapshot_path == out_dir / "snapshot.json"
        assert result.workflow_path == out_dir / "workflow.md"
        assert result.quality_path == out_dir / "quality.json"
        assert result.quality_markdown_path == out_dir / "architecture_quality.md"
        assert result.session_path == out_dir / "session.json"
        assert result.report_path == out_dir / "report.html"
        assert result.trace_path.exists()
        assert result.report_path is not None
        assert result.report_path.exists()

    def test_run_script_can_skip_html_report(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        out_dir = tmp_path / "api-artifacts"
        session = TraceSession(project_root=project_root, out_dir=out_dir, html_enabled=False)

        # When
        result = session.run_script(project_root / "app.py")

        # Then
        assert result.succeeded
        assert result.report_path is None
        assert not result.report_opened
        assert result.trace_path.exists()
        assert result.snapshot_path.exists()
        assert result.workflow_path.exists()
        assert result.quality_path.exists()
        assert result.quality_markdown_path.exists()
        assert result.session_path.exists()
        assert not (out_dir / "report.html").exists()

        session_manifest = json.loads(result.session_path.read_text(encoding="utf-8"))
        assert "report" not in session_manifest["artifacts"]

    def test_trace_context_writes_full_artifacts_for_live_callable(self, tmp_path: Path) -> None:
        # Given
        project_root = tmp_path / "callable_project"
        module = _write_callable_project(project_root)
        monitor_factory = cast(_MonitorFactory, module.__dict__["Monitor"])
        out_dir = tmp_path / "callable-artifacts"

        # When
        with trace(project_root=project_root, out_dir=out_dir, label="Monitor", html_enabled=False) as skeleton_session:
            with pytest.raises(RuntimeError, match="available after the trace context exits"):
                _ = skeleton_session.result
            monitor = monitor_factory({"count": 2})
            assert monitor.run() == 3

        # Then
        result = skeleton_session.result
        assert result.succeeded
        assert result.target_exit_code == 0
        assert result.target_error is None
        assert result.report_path is None
        assert result.trace_path == out_dir / "trace.jsonl"
        assert result.snapshot_path.exists()
        assert result.workflow_path.exists()
        assert result.quality_path.exists()
        assert result.quality_markdown_path.exists()
        assert result.session_path.exists()
        assert result.event_count > 0
        assert result.node_count > 0

        snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
        observed_nodes = {node["id"] for node in snapshot["nodes"]}
        assert "function:app.Monitor.run" in observed_nodes
        assert "function:app.Monitor._tick" in observed_nodes

        session_manifest = json.loads(result.session_path.read_text(encoding="utf-8"))
        assert session_manifest["command"] == "trace"
        assert session_manifest["invocation"] == ["skeleton_replay.trace", "Monitor"]
        assert session_manifest["target"] == {"args": [], "kind": "callable", "label": "Monitor"}
        assert session_manifest["metrics"] == {"edges": result.edge_count, "events": result.event_count, "nodes": result.node_count}

    def test_trace_context_defaults_artifacts_to_project_local_label_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = tmp_path / "callable_project"
        module = _write_callable_project(project_root)
        monitor_factory = cast(_MonitorFactory, module.__dict__["Monitor"])
        out_dir = project_root / ".skeleton" / "Monitor" / "latest"
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)

        # When
        with trace(project_root=project_root, label="Monitor", html_enabled=False) as skeleton_session:
            monitor_factory({"count": 1}).run()

        # Then
        result = skeleton_session.result
        assert result.succeeded
        assert result.trace_path == out_dir / "trace.jsonl"
        assert result.session_path == out_dir / "session.json"
        assert result.report_path is None
        assert result.trace_path.exists()
        assert result.session_path.exists()

    def test_trace_context_preserves_exception_and_writes_partial_artifacts(self, tmp_path: Path) -> None:
        # Given
        project_root = tmp_path / "callable_project"
        module = _write_callable_project(project_root)
        monitor_factory = cast(_MonitorFactory, module.__dict__["Monitor"])
        out_dir = tmp_path / "callable-failure-artifacts"
        skeleton_session = TraceSession(project_root=project_root, out_dir=out_dir, html_enabled=False).trace("Monitor")

        def run_failing_trace(session: InProcessTraceSession) -> None:
            with session:
                monitor_factory({"count": 1}).run()
                raise ValueError("boom")

        # When
        with pytest.raises(ValueError, match="boom"):
            run_failing_trace(skeleton_session)

        # Then
        result = skeleton_session.result
        assert not result.succeeded
        assert result.target_exit_code == 1
        assert result.target_error == "ValueError: boom"
        assert result.trace_path.exists()
        assert result.snapshot_path.exists()
        assert result.session_path.exists()

        session_manifest = json.loads(result.session_path.read_text(encoding="utf-8"))
        assert session_manifest["target_exit_code"] == 1
        assert session_manifest["target_error"] == "ValueError: boom"

    def test_run_pytest_writes_artifacts_for_selected_test(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_pytest_project").resolve()
        out_dir = tmp_path / "pytest-artifacts"
        session = TraceSession(project_root=project_root, out_dir=out_dir)

        # When
        result = session.run_pytest(["-q", "-p", "no:cov", str(project_root / "test_checkout.py::test_builds_receipt_total")])

        # Then
        assert result.succeeded
        assert result.target_exit_code == 0
        assert result.target_error is None
        assert result.trace_path.exists()
        assert result.snapshot_path.exists()
        assert result.workflow_path.exists()
        assert result.quality_path.exists()
        assert result.quality_markdown_path.exists()
        assert result.session_path.exists()
        assert result.report_path is not None
        assert result.report_path.exists()

        snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
        observed_nodes = {node["id"] for node in snapshot["nodes"]}
        assert "function:test_checkout.test_builds_receipt_total" in observed_nodes
        assert "function:calculator.build_receipt" in observed_nodes
        assert "function:calculator.PriceCalculator.total" in observed_nodes

        session_manifest = json.loads(result.session_path.read_text(encoding="utf-8"))
        assert session_manifest["command"] == "run_pytest"
        assert session_manifest["target"]["kind"] == "pytest"
        assert session_manifest["target"]["args"] == ["-q", "-p", "no:cov", str(project_root / "test_checkout.py::test_builds_receipt_total")]

    def test_run_pytest_defaults_artifacts_to_selected_test_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_pytest_project").resolve()
        out_dir = project_root / ".skeleton" / "test_checkout" / "test_builds_receipt_total" / "latest"
        monkeypatch.delenv("SKELETON_OUT_DIR", raising=False)
        monkeypatch.delenv("SKELETON_HOME", raising=False)
        session = TraceSession(project_root=project_root)

        # When
        result = session.run_pytest(["-q", "-p", "no:cov", "test_checkout.py::test_builds_receipt_total"])

        # Then
        assert result.succeeded
        assert result.trace_path == out_dir / "trace.jsonl"
        assert result.snapshot_path == out_dir / "snapshot.json"
        assert result.workflow_path == out_dir / "workflow.md"
        assert result.quality_path == out_dir / "quality.json"
        assert result.quality_markdown_path == out_dir / "architecture_quality.md"
        assert result.session_path == out_dir / "session.json"
        assert result.report_path == out_dir / "report.html"
        assert result.trace_path.exists()
        assert result.report_path is not None
        assert result.report_path.exists()

    def test_run_pytest_preserves_failure_exit_code_and_partial_artifacts(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_pytest_project").resolve()
        out_dir = tmp_path / "pytest-failure-artifacts"
        session = TraceSession(project_root=project_root, out_dir=out_dir, html_enabled=False)

        # When
        result = session.run_pytest(["-q", "-p", "no:cov", str(project_root / "failure_scenario.py::test_failing_receipt_total")])

        # Then
        assert not result.succeeded
        assert result.target_exit_code == 1
        assert result.target_error is None
        assert result.trace_path.exists()
        assert result.snapshot_path.exists()
        assert result.workflow_path.exists()
        assert result.quality_path.exists()
        assert result.quality_markdown_path.exists()
        assert result.session_path.exists()
        assert result.report_path is None

        snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
        assert snapshot["event_count"] == result.event_count
        assert snapshot["event_count"] > 0

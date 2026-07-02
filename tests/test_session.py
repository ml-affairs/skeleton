import json
from pathlib import Path

import pytest

from skeleton_replay import TraceSession


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
        assert result.report_path.exists()

        snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
        assert snapshot["event_count"] == result.event_count
        assert snapshot["quality"]["summary"]["events"] == result.event_count

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
        assert not (out_dir / "report.html").exists()

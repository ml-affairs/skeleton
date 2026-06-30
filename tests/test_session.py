import json
from pathlib import Path

from skeleton_replay import TraceSession


class TestTraceSession:
    """Public Python API behavior."""

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
        assert result.report_path == out_dir / "report.html"
        assert not result.report_opened
        assert result.event_count > 0
        assert result.node_count > 0
        assert result.edge_count > 0
        assert result.trace_path.exists()
        assert result.snapshot_path.exists()
        assert result.workflow_path.exists()
        assert result.report_path.exists()

        snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
        assert snapshot["event_count"] == result.event_count

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
        assert not (out_dir / "report.html").exists()

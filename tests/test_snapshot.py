from pathlib import Path

from skeleton.analysis import SnapshotBuilder
from skeleton.runtime import TargetScriptRunner, TraceOptions


class TestSnapshotBuilder:
    """Runtime snapshot generation behavior."""

    def test_builds_runtime_call_edges(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        out_dir = tmp_path / ".skeleton"
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )

        # When
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")
        edges = {(edge["source"], edge["target"]): edge for edge in snapshot["edges"]}

        # Then
        assert ("entrypoint", "function:app.main") in edges
        assert ("function:app.main", "function:service.Greeter.greet") in edges
        greet = next(node for node in snapshot["nodes"] if node["id"] == "function:service.Greeter.greet")
        assert greet["call_count"] == 1
        assert greet["fan_in"] == 1
        assert greet["return_examples"]

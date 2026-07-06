import json
from pathlib import Path

from skeleton_replay.analysis import SnapshotBuilder
from skeleton_replay.runtime import Endpoint, TargetScriptRunner, TraceEvent, TraceOptions


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

    def test_builds_snapshot_for_supply_chain_fixtures(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_supply_chain").resolve()
        out_dir = tmp_path / ".skeleton" / "sample_supply_chain"
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )

        # When
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")
        nodes = {node["id"] for node in snapshot["nodes"]}
        edges = {(edge["source"], edge["target"]) for edge in snapshot["edges"]}

        # Then
        assert "function:app.main" in nodes
        assert "function:app.bootstrap" in nodes
        assert "function:app.read_seed" in nodes
        assert "function:supply_telemetry.read_text" in nodes
        assert "function:supply_telemetry.write_text" in nodes
        assert "function:supply_telemetry.post" in nodes
        assert "function:supply_service.ShipmentService.fulfill" in nodes
        assert "function:supply_repository.ShipmentRepository.create_shipment" in nodes
        assert "function:supply_repository.ShipmentRepository.load_destination" in nodes
        assert ("function:app.main", "function:supply_telemetry.write_text") in edges
        assert ("function:app.main", "function:app.bootstrap") in edges
        assert ("function:supply_service.ShipmentService.fulfill", "function:supply_repository.ShipmentRepository.load_destination") in edges

    def test_builds_snapshot_for_orchestrated_fixture(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_orchestrated").resolve()
        out_dir = tmp_path / ".skeleton" / "sample_orchestrated"
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )

        # When
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")
        nodes = {node["id"]: node for node in snapshot["nodes"]}
        edges = {(edge["source"], edge["target"]) for edge in snapshot["edges"]}

        # Then
        assert "function:app.main" in nodes
        assert "function:orchestrator.WorkflowOrchestrator.run" in nodes
        assert "function:workers.Worker.execute" in nodes
        assert "function:workers.Worker._run_step" in nodes
        assert "function:pipeline.build_plan" in nodes
        assert "function:queueing.stage_one" in nodes
        assert "function:orchestrated_telemetry.get" in nodes
        assert "function:orchestrated_telemetry.write_text" in nodes
        assert nodes["function:workers.Worker._run_step"]["is_private"] is True
        assert nodes["function:workers.Worker._run_step"]["visibility"] == "private"
        assert ("function:orchestrator.WorkflowOrchestrator.run", "function:pipeline.build_plan") in edges
        assert ("function:workers.Worker.execute", "function:workers.Worker._run_step") in edges
        assert ("function:workers.Worker._run_step", "function:queueing.stage_one") in edges
        assert ("function:orchestrator.WorkflowOrchestrator.run", "function:orchestrated_telemetry.write_text") in edges

    def test_builds_resource_nodes_for_io_boundary_fixture(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_io_boundaries").resolve()
        out_dir = tmp_path / ".skeleton" / "sample_io_boundaries"
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )

        # When
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")
        nodes = {node["id"]: node for node in snapshot["nodes"]}
        edges = {(edge["source"], edge["target"]) for edge in snapshot["edges"]}

        # Then
        assert nodes["resource:stdout:resource.stdout"]["type"] == "io"
        assert nodes["resource:stdout:resource.stdout"]["resource_category"] == "stdout"
        assert nodes["resource:db:resource.database"]["type"] == "io"
        assert nodes["resource:db:resource.database"]["resource_category"] == "db"
        assert any(node["type"] == "io" and node["resource_category"] == "file" for node in nodes.values())
        assert ("function:notification_adapter.ConsoleNotifier.announce", "resource:stdout:resource.stdout") in edges
        assert ("function:order_repository.SqliteOrderRepository.save", "resource:db:resource.database") in edges

    def test_builds_external_service_node_for_network_boundary(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        trace_path = tmp_path / "trace.jsonl"
        out_path = tmp_path / "snapshot.json"
        caller = Endpoint(
            module="client",
            function="send",
            qualified_name="client.ApiClient.send",
            file=str((project_root / "client.py").resolve()),
            line=1,
            node_id="function:client.ApiClient.send",
            class_name="ApiClient",
            instance_id="client.ApiClient@0xabc",
        )
        callee = Endpoint(
            module="external",
            function="service",
            qualified_name="external.service",
            file="",
            line=0,
            node_id="external_service:network:external.service",
            endpoint_type="external_service",
            resource_category="network",
        )
        event = TraceEvent(event_type="call", order=0, timestamp=1.0, depth=1, caller=caller, callee=callee)
        trace_path.write_text(json.dumps(event.to_json()) + "\n", encoding="utf-8")

        # When
        snapshot = SnapshotBuilder(project_root).build(trace_path, out_path)
        nodes = {node["id"]: node for node in snapshot["nodes"]}

        # Then
        assert nodes["external_service:network:external.service"]["type"] == "external_service"
        assert nodes["external_service:network:external.service"]["endpoint_type"] == "external_service"
        assert nodes["external_service:network:external.service"]["resource_category"] == "network"

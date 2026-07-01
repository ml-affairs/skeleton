import inspect
import json
import sqlite3
from pathlib import Path
from types import FrameType

import pytest

from skeleton_replay.runtime import RuntimeTracer, TargetScriptRunner, TraceOptions
from skeleton_replay.runtime.events import Endpoint, TraceEvent
from skeleton_replay.runtime.resources import RuntimeResourceClassifier


class SampleFrames:
    """Frame factory used to exercise tracer endpoint inference."""

    def instance_method(self, subject: str) -> FrameType:
        """Return a live frame from an instance method."""
        del subject
        frame = inspect.currentframe()
        assert frame is not None
        return frame

    @classmethod
    def class_method(cls) -> FrameType:
        """Return a live frame from a class method."""
        frame = inspect.currentframe()
        assert frame is not None
        return frame


def public_frame(subject: str, *items: object, **metadata: object) -> FrameType:
    frame = inspect.currentframe()
    assert frame is not None
    assert subject
    assert items
    assert metadata
    return frame


def _private_frame() -> FrameType:
    frame = inspect.currentframe()
    assert frame is not None
    return frame


def endpoint_for_tests() -> Endpoint:
    return Endpoint(
        module="tests.test_tracer",
        class_name=None,
        function="public_frame",
        qualified_name="tests.test_tracer.public_frame",
        file=str(Path(__file__).resolve()),
        line=1,
        node_id="function:tests.test_tracer.public_frame",
        instance_id=None,
    )


class TestTargetScriptRunner:
    """Runtime tracing through the target-script runner."""

    def test_records_public_project_calls_and_redacts_args(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        out_dir = tmp_path / ".skeleton"

        # When
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )

        events = [json.loads(line) for line in result.trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        calls = [event for event in events if event["event_type"] == "call"]
        qualified = [event["callee"]["qualified_name"] for event in calls]

        # Then
        assert "app.main" in qualified
        assert "service.Greeter.greet" in qualified
        assert "service.Greeter" not in qualified
        assert all("._format" not in name for name in qualified)

        greet_call = next(event for event in calls if event["callee"]["qualified_name"] == "service.Greeter.greet")
        assert greet_call["callee"]["class_name"] == "Greeter"
        assert greet_call["callee"]["instance_id"].startswith("service.Greeter@0x")
        assert greet_call["args"]["token"]["type"] == "redacted"

    def test_respects_max_events(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        out_dir = tmp_path / ".skeleton"

        # When
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir, max_events=1),
        )

        # Then
        assert result.event_count == 1
        assert len(result.trace_path.read_text(encoding="utf-8").splitlines()) == 1


class TestRuntimeTracer:
    """Low-level runtime tracer behavior."""

    def test_writes_call_and_return_events_from_frames(self, tmp_path: Path) -> None:
        # Given
        tracer = RuntimeTracer(TraceOptions(project_root=Path.cwd(), out_dir=tmp_path))
        frame = public_frame("Ada", "workflow", token="secret-value")
        tmp_path.mkdir(parents=True, exist_ok=True)

        # When
        with tracer.trace_path.open("w", encoding="utf-8") as writer:
            tracer._writer = writer
            tracer._handle_call(frame)
            tracer._handle_return(frame, {"status": "ok"})

        # Then
        events = [json.loads(line) for line in tracer.trace_path.read_text(encoding="utf-8").splitlines()]
        assert [event["event_type"] for event in events] == ["call", "return"]
        assert events[0]["callee"]["qualified_name"] == "test_tracer.public_frame"
        assert events[0]["args"]["subject"]["value"] == "Ada"
        assert events[0]["args"]["items"]["len"] == 1
        assert events[0]["args"]["metadata"]["preview"][0]["value"]["type"] == "redacted"
        assert events[1]["return_value"]["type"] == "dict"

    def test_infers_instance_and_class_endpoints(self, tmp_path: Path) -> None:
        # Given
        tracer = RuntimeTracer(TraceOptions(project_root=Path.cwd(), out_dir=tmp_path))
        sample = SampleFrames()

        # When
        instance_endpoint = tracer._endpoint_from_frame(sample.instance_method("Ada"))
        class_endpoint = tracer._endpoint_from_frame(SampleFrames.class_method())

        # Then
        assert instance_endpoint is not None
        assert instance_endpoint.class_name == "SampleFrames"
        assert instance_endpoint.instance_id is not None
        assert instance_endpoint.instance_id.startswith("test_tracer.SampleFrames@0x")
        assert class_endpoint is not None
        assert class_endpoint.class_name == "SampleFrames"
        assert class_endpoint.instance_id is None

    def test_ignores_private_frames(self, tmp_path: Path) -> None:
        # Given
        tracer = RuntimeTracer(TraceOptions(project_root=Path.cwd(), out_dir=tmp_path))

        # When
        endpoint = tracer._endpoint_from_frame(_private_frame())

        # Then
        assert endpoint is None

    def test_requires_open_writer(self, tmp_path: Path) -> None:
        # Given
        tracer = RuntimeTracer(TraceOptions(project_root=Path.cwd(), out_dir=tmp_path))
        event = TraceEvent(
            event_type="call",
            order=0,
            timestamp=1.0,
            depth=0,
            caller=None,
            callee=endpoint_for_tests(),
        )

        # When / Then
        with pytest.raises(RuntimeError, match="Trace writer is not open"):
            tracer._write_event(event)


class TestRuntimeResourceClassifier:
    """Selected standard-library C-call resource classification."""

    def test_classifies_stdout_filesystem_and_sqlite_boundaries(self) -> None:
        # Given
        classifier = RuntimeResourceClassifier()

        # When
        stdout_call = classifier.classify(print)
        file_call = classifier.classify(open)
        database_call = classifier.classify(sqlite3.connect)

        # Then
        assert stdout_call is not None
        assert stdout_call.endpoint.endpoint_type == "resource"
        assert stdout_call.endpoint.resource_category == "stdout"
        assert stdout_call.endpoint.qualified_name == "resource.stdout"
        assert file_call is not None
        assert file_call.endpoint.resource_category == "file"
        assert database_call is not None
        assert database_call.endpoint.resource_category == "db"


class TestFixtureProjects:
    """Target-script fixture regression for richer architecture traces."""

    @pytest.mark.parametrize(
        ("project_name", "required_calls"),
        [
            (
                "sample_supply_chain",
                {
                    "app.main",
                    "app.bootstrap",
                    "app.read_seed",
                    "supply_service.ShipmentService.fulfill",
                    "supply_repository.ShipmentRepository.create_shipment",
                    "supply_repository.ShipmentRepository.load_destination",
                    "supply_telemetry.read_text",
                    "supply_telemetry.write_text",
                    "supply_telemetry.post",
                },
            ),
            (
                "sample_orchestrated",
                {
                    "app.main",
                    "app.bootstrap",
                    "orchestrated_telemetry.read_text",
                    "orchestrator.WorkflowOrchestrator.run",
                    "pipeline.build_plan",
                    "workers.Worker.execute",
                    "queueing.stage_one",
                    "queueing.stage_two",
                    "queueing.stage_three",
                    "orchestrated_telemetry.get",
                    "orchestrated_telemetry.write_text",
                },
            ),
            (
                "sample_io_boundaries",
                {
                    "app.main",
                    "app.bootstrap",
                    "order_service.OrderService.register_order",
                    "order_repository.SqliteOrderRepository.save",
                    "order_repository.SqliteOrderRepository.load",
                    "notification_adapter.ConsoleNotifier.announce",
                    "order_domain.Order.display_label",
                },
            ),
        ],
    )
    def test_project_traces_expected_public_calls(self, tmp_path: Path, project_name: str, required_calls: set[str]) -> None:
        # Given
        project_root = Path(f"tests/fixtures/{project_name}").resolve()
        out_dir = tmp_path / ".skeleton" / project_name

        # When
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        events = [json.loads(line) for line in result.trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        calls = [event for event in events if event["event_type"] == "call"]

        # Then
        assert events
        observed = {event["callee"]["qualified_name"] for event in calls}
        for expected in required_calls:
            assert any(qualified.endswith(f".{expected}") or qualified == expected for qualified in observed)

    def test_project_traces_io_resource_boundaries(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_io_boundaries").resolve()
        out_dir = tmp_path / ".skeleton" / "sample_io_boundaries"

        # When
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        events = [json.loads(line) for line in result.trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        resource_calls = [event["callee"] for event in events if event["event_type"] == "call" and event["callee"].get("endpoint_type") == "resource"]

        # Then
        resource_categories = {call["resource_category"] for call in resource_calls}
        resource_names = {call["qualified_name"] for call in resource_calls}
        assert {"stdout", "file", "db"}.issubset(resource_categories)
        assert "resource.stdout" in resource_names
        assert "resource.database" in resource_names
        assert all(call["node_id"].startswith("resource:") for call in resource_calls)

    def test_private_methods_are_not_traced_in_fixtures(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_supply_chain").resolve()
        out_dir = tmp_path / ".skeleton" / "sample_supply_chain"

        # When
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        events = [json.loads(line) for line in result.trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]

        # Then
        qualified = [event["callee"]["qualified_name"] for event in events if event["event_type"] == "call"]
        assert "sample_supply_chain.supply_service.ShipmentService._resolve_tracking" not in qualified
        assert "sample_supply_chain.workers.Worker._run_step" not in qualified

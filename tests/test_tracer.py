import inspect
import json
from pathlib import Path
from types import FrameType

import pytest

from skeleton.runtime import RuntimeTracer, TargetScriptRunner, TraceOptions
from skeleton.runtime.events import Endpoint, TraceEvent


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


def test_tracer_records_public_project_calls_and_redacts_args(tmp_path: Path) -> None:
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


def test_tracer_respects_max_events(tmp_path: Path) -> None:
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


def test_runtime_tracer_writes_call_and_return_events_from_frames(tmp_path: Path) -> None:
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


def test_runtime_tracer_infers_instance_and_class_endpoints(tmp_path: Path) -> None:
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


def test_runtime_tracer_ignores_private_frames(tmp_path: Path) -> None:
    # Given
    tracer = RuntimeTracer(TraceOptions(project_root=Path.cwd(), out_dir=tmp_path))

    # When
    endpoint = tracer._endpoint_from_frame(_private_frame())

    # Then
    assert endpoint is None


def test_runtime_tracer_requires_open_writer(tmp_path: Path) -> None:
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

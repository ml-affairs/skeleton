import json
from pathlib import Path

from skeleton.runtime import TargetScriptRunner, TraceOptions


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

import json
from pathlib import Path

from skeleton_replay.analysis import SnapshotBuilder
from skeleton_replay.reporting import HtmlReportWriter, WorkflowNarrativeWriter
from skeleton_replay.runtime import Endpoint, TargetScriptRunner, TraceEvent, TraceOptions


class TestTraceRoles:
    """Trace-role classification behavior."""

    def test_classifies_setup_entrypoint_test_utility_and_system_under_test(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_trace_roles").resolve()
        out_dir = tmp_path / ".skeleton"
        result = TargetScriptRunner().run(
            project_root / "tests" / "scenarios" / "tool_flow.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        raw_events = [json.loads(line) for line in result.trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]

        # When
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")

        # Then
        assert snapshot["events"] == raw_events
        trace_roles = snapshot["trace_roles"]
        role_by_order = {event_role["order"]: event_role for event_role in trace_roles["events"]}
        nodes = {node["id"]: node for node in snapshot["nodes"]}

        entrypoint_order = trace_roles["entrypoint_event_order"]
        assert entrypoint_order == next(event["order"] for event in raw_events if event["event_type"] == "call" and event["callee"]["function"] == "run_scenario")
        assert role_by_order[0]["trace_role"] == "import_setup"
        assert role_by_order[1]["trace_role"] == "import_setup"
        assert role_by_order[entrypoint_order]["trace_role"] == "entrypoint"
        assert role_by_order[entrypoint_order]["root_context"] == "root_inside_selected_trace_boundary"

        assert nodes["function:tests.scenarios.tool_flow.run_scenario"]["trace_role"] == "entrypoint"
        assert nodes["function:tests.helpers.factory.build_service"]["trace_role"] == "test_utility"
        assert nodes["module:tests.helpers.factory"]["trace_role"] == "test_utility"
        assert nodes["function:app.service.Service.run"]["trace_role"] == "system_under_test"
        assert nodes["function:app.service.Service.render"]["trace_role"] == "system_under_test"
        assert nodes["function:tests.scenarios.tool_flow.compute_import_payload"]["trace_role"] == "import_setup"

        setup_group = trace_roles["setup_event_groups"][0]
        assert setup_group["label"] == "Setup before entrypoint"
        assert setup_group["trace_role"] == "import_setup"
        assert setup_group["collapsed_by_default"] is True
        assert setup_group["event_orders"] == [0, 1]

    def test_workflow_narrative_includes_collapsed_setup_group_and_roles(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_trace_roles").resolve()
        out_dir = tmp_path / ".skeleton"
        result = TargetScriptRunner().run(
            project_root / "tests" / "scenarios" / "tool_flow.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")

        # When
        markdown = WorkflowNarrativeWriter().render(snapshot)

        # Then
        assert "## Setup Before Entrypoint" in markdown
        assert "- `Setup before entrypoint` role=`import_setup` events=`0, 1` collapsed_by_default=`true`" in markdown
        assert "`function:tests.helpers.factory.build_service` (function) `build_service` role=test_utility" in markdown
        assert "`function:app.service.Service.run` (function) `run` role=system_under_test" in markdown
        assert "root_context=root_inside_selected_trace_boundary" in markdown

    def test_html_report_surfaces_trace_roles_without_extra_hide_button(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_trace_roles").resolve()
        out_dir = tmp_path / ".skeleton"
        result = TargetScriptRunner().run(
            project_root / "tests" / "scenarios" / "tool_flow.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")
        report_path = out_dir / "report.html"

        # When
        HtmlReportWriter().write(snapshot, report_path)

        # Then
        html = report_path.read_text(encoding="utf-8")
        assert "Setup before entrypoint" in html
        assert "setup-event-group" in html
        assert "role-test-utility" in html
        assert "role-test-harness" in html
        assert "role-import-setup" in html
        assert "trace-role-pill" in html
        assert "root inside selected trace boundary" in html
        assert "caller outside trace boundary" in html
        assert "Hide private" in html
        assert "hide test" not in html.lower()
        assert "hide utility" not in html.lower()

    def test_classifies_later_boundary_roots_as_filtered_external(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        trace_path = tmp_path / "trace.jsonl"
        out_path = tmp_path / "snapshot.json"
        main = _endpoint(project_root, "app.main", function="main")
        callback = _endpoint(project_root, "callbacks.on_event", function="on_event")
        events = [
            TraceEvent(event_type="call", order=0, timestamp=0.0, depth=0, caller=None, callee=main, args={}),
            TraceEvent(event_type="return", order=1, timestamp=0.1, depth=0, caller=None, callee=main, return_value={"type": "none", "value": None}),
            TraceEvent(event_type="call", order=2, timestamp=0.2, depth=0, caller=None, callee=callback, args={}),
        ]
        trace_path.write_text("\n".join(json.dumps(event.to_json()) for event in events) + "\n", encoding="utf-8")

        # When
        snapshot = SnapshotBuilder(project_root).build(trace_path, out_path)

        # Then
        role_by_order = {event_role["order"]: event_role for event_role in snapshot["trace_roles"]["events"]}
        nodes = {node["id"]: node for node in snapshot["nodes"]}
        assert role_by_order[2]["trace_role"] == "filtered_external"
        assert role_by_order[2]["root_context"] == "caller_outside_trace_boundary"
        assert nodes["function:callbacks.on_event"]["trace_role"] == "filtered_external"


def _endpoint(project_root: Path, qualified_name: str, *, function: str) -> Endpoint:
    module = qualified_name.removesuffix(f".{function}")
    return Endpoint(
        module=module,
        function=function,
        qualified_name=qualified_name,
        file=str((project_root / f"{module.replace('.', '/')}.py").resolve()),
        line=1,
        node_id=f"function:{qualified_name}",
    )

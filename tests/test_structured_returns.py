import json
from pathlib import Path
from textwrap import dedent

from skeleton_replay.analysis import SnapshotBuilder
from skeleton_replay.reporting import HtmlReportWriter, WorkflowNarrativeWriter
from skeleton_replay.runtime import Endpoint, TargetScriptRunner, TraceEvent, TraceOptions


class TestStructuredReturnGroups:
    """Structured return aggregation behavior."""

    def test_builds_structured_return_group_from_compatible_payload_returns(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_structured_returns").resolve()
        out_dir = tmp_path / ".skeleton"
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        raw_lines = result.trace_path.read_text(encoding="utf-8").splitlines()

        # When
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")

        # Then
        assert [json.loads(line) for line in raw_lines if line.strip()] == snapshot["events"]
        groups = snapshot["structured_return_groups"]
        assert len(groups) == 1
        group = groups[0]
        assert group["id"].startswith("structured_return:boundaries.ContextLaneBoundary.payload:")
        assert group["label"] == "ContextLaneBoundary payload records"
        assert group["qualified_name"] == "boundaries.ContextLaneBoundary.payload"
        assert group["class_name"] == "ContextLaneBoundary"
        assert group["function"] == "payload"
        assert group["record_count"] == 6
        assert group["key_overlap"] == 1.0
        assert group["label_field"] == "name"
        assert group["active_count"] == 5
        assert group["inactive_count"] == 1
        assert len(group["event_orders"]) == 6
        assert len(group["raw_event_orders"]) == 12
        assert group["columns"] == ["name", "id", "kind", "lane", "owner", "role", "stage", "event_type", "active"]
        assert group["records"][0]["label"] == "memory"
        assert group["records"][0]["values"]["lane"] == "summary"
        assert group["records"][0]["return_event_order"] in group["raw_event_orders"]
        assert "projection_clusters" not in snapshot

    def test_groups_arbitrary_function_name_when_returns_match_structured_record_pattern(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        trace_path = tmp_path / "trace.jsonl"
        out_path = tmp_path / "snapshot.json"
        caller = _endpoint("app.main", function="main")
        callee = _endpoint("catalog.emit_record", function="emit_record", class_name=None)
        events: list[TraceEvent] = []
        for index, name in enumerate(("alpha", "beta", "gamma")):
            call_order = index * 2
            events.append(TraceEvent(event_type="call", order=call_order, timestamp=float(call_order), depth=1, caller=caller, callee=callee))
            events.append(
                TraceEvent(
                    event_type="return",
                    order=call_order + 1,
                    timestamp=float(call_order) + 0.1,
                    depth=1,
                    caller=caller,
                    callee=callee,
                    return_value=_dict_summary({"name": name, "kind": "manifest", "active": index != 1}),
                )
            )
        _write_events(trace_path, events)

        # When
        snapshot = SnapshotBuilder(project_root).build(trace_path, out_path)

        # Then
        groups = snapshot["structured_return_groups"]
        assert len(groups) == 1
        assert groups[0]["function"] == "emit_record"
        assert groups[0]["record_count"] == 3
        assert groups[0]["records"][1]["label"] == "beta"

    def test_does_not_group_payload_calls_with_observed_workflow_children(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_project").resolve()
        trace_path = tmp_path / "trace.jsonl"
        out_path = tmp_path / "snapshot.json"
        caller = _endpoint("app.main", function="main")
        payload = _endpoint("records.Record.payload", function="payload", class_name="Record", instance_id="records.Record@0xabc")
        helper = _endpoint("records.Record.load", function="load", class_name="Record", instance_id="records.Record@0xabc")
        events: list[TraceEvent] = []
        for index, name in enumerate(("alpha", "beta", "gamma")):
            base = index * 4
            events.extend(
                [
                    TraceEvent(event_type="call", order=base, timestamp=float(base), depth=1, caller=caller, callee=payload),
                    TraceEvent(event_type="call", order=base + 1, timestamp=float(base) + 0.1, depth=2, caller=payload, callee=helper),
                    TraceEvent(event_type="return", order=base + 2, timestamp=float(base) + 0.2, depth=2, caller=payload, callee=helper, return_value={"type": "str", "value": name}),
                    TraceEvent(
                        event_type="return",
                        order=base + 3,
                        timestamp=float(base) + 0.3,
                        depth=1,
                        caller=caller,
                        callee=payload,
                        return_value=_dict_summary({"name": name, "kind": "workflow", "active": True}),
                    ),
                ]
            )
        _write_events(trace_path, events)

        # When
        snapshot = SnapshotBuilder(project_root).build(trace_path, out_path)

        # Then
        assert snapshot["structured_return_groups"] == []

    def test_project_config_tunes_min_records_group_labels_and_record_labels(self, tmp_path: Path) -> None:
        # Given
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text(
            dedent(
                """
                [tool.skeleton.structured_returns]
                min_records = 2
                label_fields = ["lane", "name"]

                [tool.skeleton.structured_returns.groups]
                "*.Boundary.emit" = "Prompt context lane catalog"

                [tool.skeleton.display_labels]
                "*.Boundary" = "{lane}"
                """
            ),
            encoding="utf-8",
        )
        trace_path = tmp_path / "trace.jsonl"
        out_path = tmp_path / "snapshot.json"
        caller = _endpoint("app.main", function="main")
        emit = _endpoint("catalog.Boundary.emit", function="emit", class_name="Boundary", instance_id="catalog.Boundary@0xabc")
        events = [
            TraceEvent(event_type="call", order=0, timestamp=0.0, depth=1, caller=caller, callee=emit),
            TraceEvent(event_type="return", order=1, timestamp=0.1, depth=1, caller=caller, callee=emit, return_value=_dict_summary({"name": "memory", "lane": "summary"})),
            TraceEvent(event_type="call", order=2, timestamp=0.2, depth=1, caller=caller, callee=emit),
            TraceEvent(event_type="return", order=3, timestamp=0.3, depth=1, caller=caller, callee=emit, return_value=_dict_summary({"name": "tools", "lane": "tooling"})),
        ]
        _write_events(trace_path, events)

        # When
        snapshot = SnapshotBuilder(project_root).build(trace_path, out_path)

        # Then
        group = snapshot["structured_return_groups"][0]
        assert group["label"] == "Prompt context lane catalog"
        assert group["label_field"] == "lane"
        assert group["columns"] == ["lane", "name"]
        assert [record["label"] for record in group["records"]] == ["summary", "tooling"]


class TestStructuredReturnRendering:
    """Structured return group presentation behavior."""

    def test_workflow_narrative_includes_structured_return_section(self) -> None:
        # Given
        snapshot = _snapshot_with_group()

        # When
        markdown = WorkflowNarrativeWriter().render(snapshot)

        # Then
        assert "## Structured Return Groups" in markdown
        assert "These records were derived from repeated structured return values. Raw events remain available below." in markdown
        assert "`Prompt context lane catalog` from `boundaries.ContextLaneBoundary.payload` records=2 key_overlap=1.0 raw_events=`4, 5, 8, 9`" in markdown
        assert "| lane | owner | active |" in markdown
        assert "| summary | memory | True |" in markdown

    def test_html_report_renders_structured_groups_collapses_matching_events_and_exports_groups(self, tmp_path: Path) -> None:
        # Given
        out_path = tmp_path / "report.html"

        # When
        HtmlReportWriter().write(_snapshot_with_group(), out_path)

        # Then
        html = out_path.read_text(encoding="utf-8")
        assert "Structured Return Groups" in html
        assert "These records were derived from repeated structured return values. Raw events remain available below." in html
        assert "structured-return-group-card" in html
        assert "structured-return-raw-events" in html
        assert "Prompt context lane catalog" in html
        assert "summary" in html
        assert "memory" in html
        assert "structuredReturnEventOrders" in html
        assert "isStructuredReturnEvent" in html
        assert "if (isStructuredReturnEvent(event)) continue;" in html
        assert "structuredReturnGroupsForWindow" in html
        assert "structured_return_groups: selectedStructuredReturnGroups" in html


def _snapshot_with_group() -> dict[str, object]:
    return {
        "project_root": "/example",
        "event_count": 2,
        "nodes": [
            {"id": "entrypoint", "type": "entrypoint", "label": "entrypoint"},
            {"id": "module:boundaries", "type": "module", "label": "boundaries", "module": "boundaries"},
            {
                "id": "instance:boundaries.ContextLaneBoundary@0xabc",
                "type": "instance",
                "label": "ContextLaneBoundary",
                "module": "boundaries",
                "class_name": "ContextLaneBoundary",
                "object_id": "boundaries.ContextLaneBoundary@0xabc",
            },
            {
                "id": "function:boundaries.ContextLaneBoundary.payload",
                "type": "function",
                "label": "payload",
                "module": "boundaries",
                "class_name": "ContextLaneBoundary",
                "function": "payload",
                "qualified_name": "boundaries.ContextLaneBoundary.payload",
            },
        ],
        "edges": [],
        "events": [
            {
                "event_type": "call",
                "order": 4,
                "timestamp": 1.0,
                "depth": 1,
                "caller": None,
                "callee": _endpoint_json(),
                "args": {},
            },
            {
                "event_type": "return",
                "order": 5,
                "timestamp": 1.1,
                "depth": 1,
                "caller": None,
                "callee": _endpoint_json(),
                "return_value": _dict_summary({"lane": "summary", "owner": "memory", "active": True}),
            },
        ],
        "structured_return_groups": [
            {
                "id": "structured_return:boundaries.ContextLaneBoundary.payload:abc123",
                "label": "Prompt context lane catalog",
                "qualified_name": "boundaries.ContextLaneBoundary.payload",
                "class_name": "ContextLaneBoundary",
                "function": "payload",
                "record_count": 2,
                "first_event": 4,
                "last_event": 9,
                "event_orders": [5, 9],
                "raw_event_orders": [4, 5, 8, 9],
                "key_overlap": 1.0,
                "label_field": "lane",
                "columns": ["lane", "owner", "active"],
                "collapse_by_default": True,
                "active_count": 1,
                "inactive_count": 1,
                "records": [
                    {"event_order": 5, "call_event_order": 4, "return_event_order": 5, "label": "summary", "values": {"lane": "summary", "owner": "memory", "active": True}},
                    {"event_order": 9, "call_event_order": 8, "return_event_order": 9, "label": "tooling", "values": {"lane": "tooling", "owner": "tools", "active": False}},
                ],
                "raw_events": [
                    {
                        "order": 4,
                        "event_type": "call",
                        "timestamp": 1.0,
                        "caller": "entrypoint",
                        "callee": "boundaries.ContextLaneBoundary.payload",
                        "callee_object_id": "boundaries.ContextLaneBoundary@0xabc",
                        "args": {},
                        "return_value": None,
                    },
                    {
                        "order": 5,
                        "event_type": "return",
                        "timestamp": 1.1,
                        "caller": "entrypoint",
                        "callee": "boundaries.ContextLaneBoundary.payload",
                        "callee_object_id": "boundaries.ContextLaneBoundary@0xabc",
                        "args": None,
                        "return_value": _dict_summary({"lane": "summary", "owner": "memory", "active": True}),
                    },
                ],
            }
        ],
    }


def _endpoint_json() -> dict[str, object]:
    return {
        "module": "boundaries",
        "class_name": "ContextLaneBoundary",
        "instance_id": "boundaries.ContextLaneBoundary@0xabc",
        "function": "payload",
        "qualified_name": "boundaries.ContextLaneBoundary.payload",
        "node_id": "function:boundaries.ContextLaneBoundary.payload",
        "file": "",
        "line": 1,
        "endpoint_type": "function",
        "resource_category": None,
    }


def _endpoint(qualified_name: str, *, function: str, class_name: str | None = None, instance_id: str | None = None) -> Endpoint:
    suffix = f".{class_name}.{function}" if class_name else f".{function}"
    module = qualified_name.removesuffix(suffix)
    return Endpoint(
        module=module,
        class_name=class_name,
        function=function,
        qualified_name=qualified_name,
        file=f"/example/{module.replace('.', '/')}.py",
        line=1,
        node_id=f"function:{qualified_name}",
        instance_id=instance_id,
    )


def _dict_summary(values: dict[str, object]) -> dict[str, object]:
    return {
        "type": "dict",
        "len": len(values),
        "preview": [{"key": {"type": "str", "value": key}, "value": _value_summary(value)} for key, value in values.items()],
    }


def _value_summary(value: object) -> dict[str, object]:
    if value is None:
        return {"type": "NoneType", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int | float):
        return {"type": type(value).__name__, "value": value}
    return {"type": "str", "value": str(value)}


def _write_events(trace_path: Path, events: list[TraceEvent]) -> None:
    trace_path.write_text("".join(f"{json.dumps(event.to_json(), sort_keys=True)}\n" for event in events), encoding="utf-8")

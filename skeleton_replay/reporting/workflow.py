"""LLM-readable workflow narration for Skeleton snapshots."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skeleton_replay.analysis.structured_returns import STRUCTURED_RETURN_NOTE

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class WorkflowNarrativeWriter:
    """Writes a compact workflow explanation from a generated snapshot."""

    max_events: int = 80

    def write(self, snapshot: JsonObject, out_path: Path) -> None:
        """Write an LLM-readable workflow narrative."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(self.render(snapshot), encoding="utf-8")

    def render(self, snapshot: JsonObject) -> str:
        """Render a markdown workflow narrative from snapshot data."""
        nodes = list(snapshot.get("nodes", []))
        edges = list(snapshot.get("edges", []))
        events = list(snapshot.get("events", []))
        structured_return_groups = [group for group in list(snapshot.get("structured_return_groups", [])) if isinstance(group, dict)]
        lines = [
            "# Skeleton Workflow",
            "",
            "This file is generated evidence from one runtime trace. It is designed for humans and LLMs to read without inferring architecture from source code alone.",
            "",
            "## Run Summary",
            "",
            f"- Project root: `{snapshot.get('project_root', '')}`",
            f"- Events observed: `{snapshot.get('event_count', 0)}`",
            f"- Nodes observed: `{len(nodes)}`",
            f"- Runtime edges observed: `{len(edges)}`",
            "",
            "## Actors",
            "",
            *self._actor_lines(nodes),
            "",
            "## Runtime Calls",
            "",
            *self._edge_lines(edges),
            "",
            *self._structured_return_section(structured_return_groups),
            "## Event Timeline",
            "",
            *self._event_lines(events),
            "",
            "## LLM Notes",
            "",
            "- Treat event ids, node ids, and edge ids as evidence references.",
            "- Argument and return examples are safe summaries, not full object contents.",
            "- Private methods and excluded files may be absent from this workflow by design.",
        ]
        return "\n".join(lines) + "\n"

    def _actor_lines(self, nodes: list[object]) -> list[str]:
        actor_nodes = [node for node in nodes if isinstance(node, dict) and node.get("type") in {"module", "class", "function", "instance", "io", "external_service"}]
        if not actor_nodes:
            return ["- No actors observed."]
        return [self._actor_line(node) for node in actor_nodes[: self.max_events]]

    def _actor_line(self, node: JsonObject) -> str:
        node_id = str(node.get("id", ""))
        label = str(node.get("label", node_id))
        node_type = str(node.get("type", "node"))
        fan_in = int(node.get("fan_in", 0))
        fan_out = int(node.get("fan_out", 0))
        call_count = int(node.get("call_count", 0))
        file_path = str(node.get("file", ""))
        location = f" `{file_path}`" if file_path else ""
        return f"- `{node_id}` ({node_type}) `{label}` calls={call_count} fan_in={fan_in} fan_out={fan_out}{location}"

    def _edge_lines(self, edges: list[object]) -> list[str]:
        if not edges:
            return ["- No runtime call edges observed."]
        edge_objects = [edge for edge in edges if isinstance(edge, dict)]
        edge_objects.sort(key=lambda edge: int(edge.get("first_seen", 0)))
        return [self._edge_line(edge) for edge in edge_objects[: self.max_events]]

    def _edge_line(self, edge: JsonObject) -> str:
        return f"- `{edge.get('id', '')}`: `{edge.get('source', '')}` -> `{edge.get('target', '')}` calls={edge.get('call_count', 0)} first_seen={edge.get('first_seen', '')} last_seen={edge.get('last_seen', '')}"

    def _structured_return_section(self, groups: list[JsonObject]) -> list[str]:
        if not groups:
            return []
        lines = [
            "## Structured Return Groups",
            "",
            STRUCTURED_RETURN_NOTE,
            "",
        ]
        for group in groups[: self.max_events]:
            lines.extend(self._structured_return_group_lines(group))
            lines.append("")
        return lines

    def _structured_return_group_lines(self, group: JsonObject) -> list[str]:
        raw_event_orders = ", ".join(str(order) for order in list(group.get("raw_event_orders", [])))
        label = group.get("label", group.get("qualified_name", ""))
        qualified_name = group.get("qualified_name", "")
        record_count = group.get("record_count", 0)
        key_overlap = group.get("key_overlap", "")
        lines = [
            f"- `{label}` from `{qualified_name}` records={record_count} key_overlap={key_overlap} raw_events=`{raw_event_orders}`",
        ]
        table_columns = [str(column) for column in list(group.get("columns", []))]
        records = [record for record in list(group.get("records", [])) if isinstance(record, dict)]
        if table_columns and records:
            lines.extend(self._structured_return_table_lines(table_columns, records[: self.max_events]))
        return lines

    def _structured_return_table_lines(self, table_columns: list[str], records: list[JsonObject]) -> list[str]:
        header = "| " + " | ".join(table_columns) + " |"
        separator = "| " + " | ".join("---" for _column in table_columns) + " |"
        rows = [header, separator]
        for record in records:
            values = record.get("values", {})
            value_map = values if isinstance(values, dict) else {}
            rows.append("| " + " | ".join(self._cell_text(value_map.get(column, "")) for column in table_columns) + " |")
        return rows

    @staticmethod
    def _cell_text(value: object) -> str:
        text = str(value)
        return text.replace("|", "\\|").replace("\n", " ")

    def _event_lines(self, events: list[object]) -> list[str]:
        if not events:
            return ["- No events observed."]
        event_objects = [event for event in events if isinstance(event, dict)]
        return [self._event_line(event) for event in event_objects[: self.max_events]]

    def _event_line(self, event: JsonObject) -> str:
        callee = event.get("callee", {})
        caller = event.get("caller") or {"node_id": "entrypoint"}
        caller_id = str(caller.get("node_id", "entrypoint")) if isinstance(caller, dict) else "entrypoint"
        callee_id = str(callee.get("node_id", "")) if isinstance(callee, dict) else ""
        details = event.get("args") if event.get("event_type") == "call" else event.get("return_value")
        safe_details = json.dumps(details, sort_keys=True) if details else "{}"
        return f"- event `{event.get('order', '')}` {event.get('event_type', '')}: `{caller_id}` -> `{callee_id}` depth={event.get('depth', 0)} evidence={safe_details}"

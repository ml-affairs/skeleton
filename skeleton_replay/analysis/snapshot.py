"""Build architecture snapshots from trace events."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skeleton_replay.analysis.static import StaticProjectScanner
from skeleton_replay.analysis.structured_returns import StructuredReturnConfig, StructuredReturnGroupAnalyzer
from skeleton_replay.analysis.trace_roles import TraceRoleAnalyzer
from skeleton_replay.runtime.events import Endpoint, TraceEvent
from skeleton_replay.runtime.filters import TraceFilter

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class TraceReader:
    """Reads runtime trace files."""

    trace_path: Path

    def read(self) -> list[TraceEvent]:
        """Read trace events from JSONL."""
        events: list[TraceEvent] = []
        if not self.trace_path.exists():
            return events
        with self.trace_path.open("r", encoding="utf-8") as reader:
            for line in reader:
                if line.strip():
                    events.append(TraceEvent.from_json(json.loads(line)))
        return events


@dataclass(frozen=True)
class SnapshotMetrics:
    """Compact counts for a generated architecture snapshot."""

    event_count: int
    node_count: int
    edge_count: int

    @classmethod
    def from_snapshot(cls, snapshot: JsonObject) -> SnapshotMetrics:
        """Create compact metrics from a snapshot JSON object."""
        nodes = snapshot.get("nodes", [])
        edges = snapshot.get("edges", [])
        return cls(
            event_count=int(snapshot.get("event_count", 0)),
            node_count=len(nodes),
            edge_count=len(edges),
        )


@dataclass(frozen=True)
class SnapshotBuilder:
    """Converts trace events and static facts into a graph-oriented snapshot."""

    project_root: Path

    def build(self, trace_path: Path, out_path: Path) -> JsonObject:
        """Convert a JSONL trace into a graph-oriented snapshot."""
        events = TraceReader(trace_path).read()
        static_index = StaticProjectScanner(self.project_root).scan()
        structured_return_config = StructuredReturnConfig.from_project(self.project_root)
        nodes: dict[str, JsonObject] = {}
        edges: dict[str, JsonObject] = {}

        for module in static_index.modules.values():
            nodes[module.id] = {
                "id": module.id,
                "type": "module",
                "label": module.module,
                "module": module.module,
                "file": module.file,
                "loc": module.loc,
                "classes": module.classes,
                "functions": module.functions,
                "imports": module.imports,
                "fan_in": 0,
                "fan_out": 0,
                "call_count": 0,
            }
        for symbol in static_index.symbols.values():
            symbol_node = {
                "id": symbol.id,
                "type": symbol.kind,
                "label": symbol.name,
                "module": symbol.module,
                "file": symbol.file,
                "line": symbol.line,
                "loc": symbol.loc,
                "fan_in": 0,
                "fan_out": 0,
                "call_count": 0,
                "arg_examples": [],
                "return_examples": [],
                "is_private": symbol.is_private,
                "visibility": "private" if symbol.is_private else "public",
            }
            if symbol.kind == "function":
                symbol_node["callable_kind"] = "module_function"
            nodes[symbol.id] = symbol_node

        nodes["entrypoint"] = {
            "id": "entrypoint",
            "type": "entrypoint",
            "label": "entrypoint",
            "fan_in": 0,
            "fan_out": 0,
            "call_count": 0,
        }

        for event in events:
            self._add_event(nodes=nodes, edges=edges, event=event)

        trace_role_analysis = TraceRoleAnalyzer(self.project_root).analyze(events)
        self._apply_trace_roles(nodes=nodes, trace_node_roles=trace_role_analysis.node_roles)
        self._compute_fan_metrics(nodes, edges)
        snapshot = {
            "schema_version": 1,
            "generated_at": time.time(),
            "project_root": str(self.project_root.resolve()),
            "event_count": len(events),
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
            "events": [event.to_json() for event in events],
            "trace_roles": trace_role_analysis.to_json(),
            "structured_return_groups": StructuredReturnGroupAnalyzer(config=structured_return_config).analyze(events),
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
        return snapshot

    def _add_event(self, *, nodes: dict[str, JsonObject], edges: dict[str, JsonObject], event: TraceEvent) -> None:
        self._ensure_endpoint_nodes(nodes, event.callee)
        if event.caller:
            self._ensure_endpoint_nodes(nodes, event.caller)
        if event.event_type == "call":
            self._add_call_event(nodes=nodes, edges=edges, event=event)
        elif event.return_value:
            self._add_return_event(nodes=nodes, event=event)

        if event.event_type == "call" and event.callee.instance_id:
            instance_id = f"instance:{event.callee.instance_id}"
            instance_node = nodes.setdefault(
                instance_id,
                {
                    "id": instance_id,
                    "type": "instance",
                    "label": event.callee.class_name or "instance",
                    "module": event.callee.module,
                    "class_name": event.callee.class_name,
                    "object_id": event.callee.instance_id,
                    "fan_in": 0,
                    "fan_out": 0,
                    "call_count": 0,
                },
            )
            instance_node["call_count"] = int(instance_node.get("call_count", 0)) + 1
            self._touch_node(instance_node, event.order)

    def _add_call_event(self, *, nodes: dict[str, JsonObject], edges: dict[str, JsonObject], event: TraceEvent) -> None:
        source = event.caller.node_id if event.caller else "entrypoint"
        target = event.callee.node_id
        edge_id = f"{source}->{target}"
        edge = edges.setdefault(
            edge_id,
            {
                "id": edge_id,
                "source": source,
                "target": target,
                "kind": "runtime_call",
                "call_count": 0,
                "first_seen": event.order,
                "last_seen": event.order,
            },
        )
        edge["call_count"] += 1
        edge["last_seen"] = event.order
        self._touch_node(nodes[target], event.order)
        nodes[target]["call_count"] = int(nodes[target].get("call_count", 0)) + 1
        if event.args and len(nodes[target].setdefault("arg_examples", [])) < 3:
            nodes[target]["arg_examples"].append({"event": event.order, "args": event.args})

    def _add_return_event(self, *, nodes: dict[str, JsonObject], event: TraceEvent) -> None:
        target_node = nodes[event.callee.node_id]
        if len(target_node.setdefault("return_examples", [])) < 3:
            target_node["return_examples"].append({"event": event.order, "return_value": event.return_value})
        self._touch_node(target_node, event.order)

    def _ensure_endpoint_nodes(self, nodes: dict[str, JsonObject], endpoint: Endpoint) -> None:
        if endpoint.endpoint_type == "resource":
            nodes.setdefault(
                endpoint.node_id,
                {
                    "id": endpoint.node_id,
                    "type": "io",
                    "label": endpoint.function,
                    "module": endpoint.module,
                    "function": endpoint.function,
                    "qualified_name": endpoint.qualified_name,
                    "resource_category": endpoint.resource_category,
                    "endpoint_type": endpoint.endpoint_type,
                    "fan_in": 0,
                    "fan_out": 0,
                    "call_count": 0,
                    "arg_examples": [],
                    "return_examples": [],
                },
            )
            return
        if endpoint.endpoint_type == "external_service":
            nodes.setdefault(
                endpoint.node_id,
                {
                    "id": endpoint.node_id,
                    "type": "external_service",
                    "label": endpoint.function,
                    "module": endpoint.module,
                    "function": endpoint.function,
                    "qualified_name": endpoint.qualified_name,
                    "resource_category": endpoint.resource_category,
                    "endpoint_type": endpoint.endpoint_type,
                    "fan_in": 0,
                    "fan_out": 0,
                    "call_count": 0,
                    "arg_examples": [],
                    "return_examples": [],
                },
            )
            return
        module_id = f"module:{endpoint.module}"
        nodes.setdefault(
            module_id,
            {
                "id": module_id,
                "type": "module",
                "label": endpoint.module,
                "module": endpoint.module,
                "file": endpoint.file,
                "fan_in": 0,
                "fan_out": 0,
                "call_count": 0,
            },
        )
        if endpoint.class_name:
            class_id = f"class:{endpoint.module}.{endpoint.class_name}"
            nodes.setdefault(
                class_id,
                {
                    "id": class_id,
                    "type": "class",
                    "label": endpoint.class_name,
                    "module": endpoint.module,
                    "class_name": endpoint.class_name,
                    "file": endpoint.file,
                    "fan_in": 0,
                    "fan_out": 0,
                    "call_count": 0,
                },
            )
        nodes.setdefault(
            endpoint.node_id,
            {
                "id": endpoint.node_id,
                "type": "function",
                "label": endpoint.function,
                "module": endpoint.module,
                "class_name": endpoint.class_name,
                "function": endpoint.function,
                "qualified_name": endpoint.qualified_name,
                "file": endpoint.file,
                "line": endpoint.line,
                "fan_in": 0,
                "fan_out": 0,
                "call_count": 0,
                "arg_examples": [],
                "return_examples": [],
                "is_private": self._is_private_endpoint(endpoint),
                "visibility": "private" if self._is_private_endpoint(endpoint) else "public",
                "callable_kind": endpoint.callable_kind,
            },
        )
        if endpoint.callable_kind:
            nodes[endpoint.node_id]["callable_kind"] = endpoint.callable_kind

    @staticmethod
    def _touch_node(node: JsonObject, order: int) -> None:
        node["first_seen"] = min(int(node.get("first_seen", order)), order)
        node["last_seen"] = max(int(node.get("last_seen", order)), order)

    @staticmethod
    def _compute_fan_metrics(nodes: dict[str, JsonObject], edges: dict[str, JsonObject]) -> None:
        incoming: dict[str, set[str]] = {node_id: set() for node_id in nodes}
        outgoing: dict[str, set[str]] = {node_id: set() for node_id in nodes}
        for edge in edges.values():
            source = str(edge["source"])
            target = str(edge["target"])
            outgoing.setdefault(source, set()).add(target)
            incoming.setdefault(target, set()).add(source)
        for node_id, node in nodes.items():
            node["fan_in"] = len(incoming.get(node_id, set()))
            node["fan_out"] = len(outgoing.get(node_id, set()))

    @staticmethod
    def _apply_trace_roles(*, nodes: dict[str, JsonObject], trace_node_roles: dict[str, JsonObject]) -> None:
        for node_id, role_payload in trace_node_roles.items():
            node = nodes.get(node_id)
            if node is None:
                continue
            node["trace_role"] = role_payload["trace_role"]
            node["trace_roles"] = role_payload["trace_roles"]

    @staticmethod
    def _is_private_endpoint(endpoint: Endpoint) -> bool:
        return endpoint.endpoint_type == "function" and TraceFilter.is_private_function(endpoint.function)

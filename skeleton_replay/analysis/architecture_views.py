"""Derived high-level architecture views for Skeleton snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from skeleton_replay.runtime.events import Endpoint, TraceEvent

JsonObject = dict[str, Any]
ArchitectureViewMode = Literal["actor", "module", "package", "detail"]
DrilldownViewMode = Literal["actor", "module", "package"]


@dataclass
class _AggregateNode:
    """Mutable aggregate node while deriving an architecture view."""

    id: str
    label: str
    scope_type: str
    scope: str
    endpoint: Endpoint | None = None
    call_count: int = 0
    internal_call_count: int = 0
    raw_event_orders: list[int] = field(default_factory=list)
    first_seen: int | None = None
    last_seen: int | None = None
    collapsed_calls: dict[str, JsonObject] = field(default_factory=dict)

    def touch(self, order: int) -> None:
        """Record that this aggregate appeared at an event order."""
        self.raw_event_orders.append(order)
        self.first_seen = order if self.first_seen is None else min(self.first_seen, order)
        self.last_seen = order if self.last_seen is None else max(self.last_seen, order)

    def add_internal_call(self, event: TraceEvent) -> None:
        """Record an internal call collapsed into this aggregate."""
        self.internal_call_count += 1
        self.touch(event.order)
        qualified_name = event.callee.qualified_name
        record = self.collapsed_calls.setdefault(
            qualified_name,
            {
                "qualified_name": qualified_name,
                "function": event.callee.function,
                "call_count": 0,
                "first_seen": event.order,
                "last_seen": event.order,
                "raw_event_orders": [],
            },
        )
        record["call_count"] = int(record["call_count"]) + 1
        record["first_seen"] = min(int(record["first_seen"]), event.order)
        record["last_seen"] = max(int(record["last_seen"]), event.order)
        raw_orders = record["raw_event_orders"]
        if isinstance(raw_orders, list):
            raw_orders.append(event.order)

    def to_json(self) -> JsonObject:
        """Return a JSON-compatible aggregate node."""
        payload: JsonObject = {
            "id": self.id,
            "label": self.label,
            "scope_type": self.scope_type,
            "scope": self.scope,
            "call_count": self.call_count,
            "internal_call_count": self.internal_call_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "raw_event_orders": self.raw_event_orders,
            "top_collapsed_internal_calls": sorted(
                self.collapsed_calls.values(),
                key=lambda record: (-int(record.get("call_count", 0)), int(record.get("first_seen", 0)), str(record.get("qualified_name", ""))),
            )[:8],
        }
        if self.endpoint is not None:
            payload["representative_endpoint"] = _endpoint_json(self.endpoint)
            payload["file"] = self.endpoint.file
            payload["line"] = self.endpoint.line
            payload["module"] = self.endpoint.module
            payload["class_name"] = self.endpoint.class_name
        return payload


@dataclass
class _AggregateEdge:
    """Mutable aggregate edge while deriving an architecture view."""

    source: str
    target: str
    call_count: int = 0
    first_seen: int | None = None
    last_seen: int | None = None
    raw_event_orders: list[int] = field(default_factory=list)
    representative_event_order: int | None = None
    representative_caller: Endpoint | None = None
    representative_callee: Endpoint | None = None

    @property
    def id(self) -> str:
        """Return the aggregate edge id."""
        return f"{self.source}->{self.target}"

    def add_call(self, event: TraceEvent) -> None:
        """Record one raw call event on this aggregate edge."""
        self.call_count += 1
        self.raw_event_orders.append(event.order)
        self.first_seen = event.order if self.first_seen is None else min(self.first_seen, event.order)
        self.last_seen = event.order if self.last_seen is None else max(self.last_seen, event.order)
        if self.representative_event_order is None:
            self.representative_event_order = event.order
            self.representative_caller = event.caller
            self.representative_callee = event.callee

    def to_json(self) -> JsonObject:
        """Return a JSON-compatible aggregate edge."""
        payload: JsonObject = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "kind": "aggregate_call",
            "call_count": self.call_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "representative_event_order": self.representative_event_order,
            "raw_event_orders": self.raw_event_orders,
        }
        if self.representative_caller is not None:
            payload["representative_caller"] = _endpoint_json(self.representative_caller)
        if self.representative_callee is not None:
            payload["representative_callee"] = _endpoint_json(self.representative_callee)
        return payload


@dataclass
class _DrilldownGraph:
    """Mutable one-level child graph for one aggregate parent node."""

    mode: DrilldownViewMode
    parent_id: str
    parent_label: str
    parent_scope_type: str
    child_scope_type: str
    nodes: dict[str, _AggregateNode] = field(default_factory=dict)
    edges: dict[str, _AggregateEdge] = field(default_factory=dict)

    def node_for(self, *, node_id: str, label: str, scope_type: str, scope: str, endpoint: Endpoint) -> _AggregateNode:
        """Return or create a child drilldown node."""
        node = self.nodes.get(node_id)
        if node is None:
            node = _AggregateNode(id=node_id, label=label, scope_type=scope_type, scope=scope, endpoint=endpoint)
            self.nodes[node_id] = node
        return node

    def edge_for(self, *, source: str, target: str) -> _AggregateEdge:
        """Return or create a child drilldown edge."""
        edge_id = f"{source}->{target}"
        edge = self.edges.get(edge_id)
        if edge is None:
            edge = _AggregateEdge(source=source, target=target)
            self.edges[edge_id] = edge
        return edge

    def to_json(self) -> JsonObject:
        """Return a JSON-compatible drilldown graph."""
        return {
            "mode": self.mode,
            "parent_id": self.parent_id,
            "parent_label": self.parent_label,
            "parent_scope_type": self.parent_scope_type,
            "child_scope_type": self.child_scope_type,
            "nodes": [node.to_json() for node in sorted(self.nodes.values(), key=lambda item: (-item.call_count, item.id))],
            "edges": [edge.to_json() for edge in sorted(self.edges.values(), key=lambda item: (item.first_seen if item.first_seen is not None else -1, item.id))],
            "summary": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "internal_call_count": sum(node.internal_call_count for node in self.nodes.values()),
                "cross_boundary_call_count": sum(edge.call_count for edge in self.edges.values()),
            },
        }


@dataclass(frozen=True)
class ArchitectureViewBuilder:
    """Build architecture-level views from raw trace events without changing the raw trace."""

    package_depth: int = 1

    def build(self, events: list[TraceEvent]) -> JsonObject:
        """Return all supported architecture views."""
        modes: tuple[ArchitectureViewMode, ...] = ("actor", "module", "package", "detail")
        views = {mode: self._build_view(events=events, mode=mode) for mode in modes}
        public_events = [event for event in events if not self._touches_private_endpoint(event)]
        public_views = {mode: self._build_view(events=public_events, mode=mode) for mode in modes}
        return {
            "schema_version": 1,
            "default_view": "actor",
            "views": views,
            "public_views": public_views,
            "drilldowns": self._build_drilldowns(events),
            "public_drilldowns": self._build_drilldowns(public_events),
        }

    def _build_view(self, *, events: list[TraceEvent], mode: ArchitectureViewMode) -> JsonObject:
        nodes: dict[str, _AggregateNode] = {}
        edges: dict[str, _AggregateEdge] = {}
        for event in events:
            if event.event_type != "call":
                continue
            if mode != "detail" and self._is_stdout_event(event):
                continue
            target = self._node_for_endpoint(nodes=nodes, endpoint=event.callee, mode=mode)
            target.call_count += 1
            target.touch(event.order)
            if event.caller is None:
                source = nodes.setdefault("entrypoint", _AggregateNode(id="entrypoint", label="entrypoint", scope_type="entrypoint", scope="entrypoint"))
                source.touch(event.order)
            else:
                source = self._node_for_endpoint(nodes=nodes, endpoint=event.caller, mode=mode)
                source.touch(event.order)
            if source.id == target.id:
                target.add_internal_call(event)
                continue
            edge = edges.setdefault(f"{source.id}->{target.id}", _AggregateEdge(source=source.id, target=target.id))
            edge.add_call(event)

        return {
            "mode": mode,
            "label": self._view_label(mode),
            "nodes": [node.to_json() for node in sorted(nodes.values(), key=lambda item: (-item.call_count, item.id))],
            "edges": [edge.to_json() for edge in sorted(edges.values(), key=lambda item: (item.first_seen if item.first_seen is not None else -1, item.id))],
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "internal_call_count": sum(node.internal_call_count for node in nodes.values()),
                "cross_boundary_call_count": sum(edge.call_count for edge in edges.values()),
            },
        }

    def _build_drilldowns(self, events: list[TraceEvent]) -> dict[str, dict[str, JsonObject]]:
        drilldowns: dict[DrilldownViewMode, dict[str, _DrilldownGraph]] = {
            "actor": {},
            "module": {},
            "package": {},
        }
        for event in events:
            if event.event_type != "call":
                continue
            if self._is_stdout_event(event):
                continue
            for mode in ("package", "module", "actor"):
                self._add_drilldown_event(drilldowns=drilldowns, event=event, mode=mode)
        return {mode: {parent_id: graph.to_json() for parent_id, graph in sorted(graphs.items()) if graph.nodes} for mode, graphs in drilldowns.items()}

    def _add_drilldown_event(self, *, drilldowns: dict[DrilldownViewMode, dict[str, _DrilldownGraph]], event: TraceEvent, mode: DrilldownViewMode) -> None:
        source_parent = self._drilldown_parent_id_for_endpoint(event.caller, mode)
        target_parent = self._drilldown_parent_id_for_endpoint(event.callee, mode)
        parent_ids = {parent_id for parent_id in (source_parent, target_parent) if parent_id is not None}
        if not parent_ids:
            return
        for parent_id in parent_ids:
            source_node = None
            target_node = None
            if source_parent == parent_id and event.caller is not None:
                source_node = self._touch_drilldown_node(drilldowns=drilldowns, parent_id=parent_id, endpoint=event.caller, event=event, mode=mode, increment_call_count=False)
            if target_parent == parent_id or (source_parent == parent_id and self._included_drilldown_resource(event.callee)):
                target_node = self._touch_drilldown_node(drilldowns=drilldowns, parent_id=parent_id, endpoint=event.callee, event=event, mode=mode, increment_call_count=True)
            if source_node is None or target_node is None:
                continue
            if source_node.id == target_node.id:
                target_node.add_internal_call(event)
                continue
            drilldowns[mode][parent_id].edge_for(source=source_node.id, target=target_node.id).add_call(event)

    def _touch_drilldown_node(
        self,
        *,
        drilldowns: dict[DrilldownViewMode, dict[str, _DrilldownGraph]],
        parent_id: str,
        endpoint: Endpoint,
        event: TraceEvent,
        mode: DrilldownViewMode,
        increment_call_count: bool,
    ) -> _AggregateNode | None:
        child_scope = self._drilldown_child_scope_for_endpoint(endpoint=endpoint, mode=mode)
        if child_scope is None:
            return None
        node_id, label, scope_type, scope = child_scope
        graph = drilldowns[mode].setdefault(parent_id, self._drilldown_graph(mode=mode, parent_id=parent_id))
        node = graph.node_for(node_id=node_id, label=label, scope_type=scope_type, scope=scope, endpoint=endpoint)
        if increment_call_count:
            node.call_count += 1
        node.touch(event.order)
        return node

    def _drilldown_child_scope_for_endpoint(self, *, endpoint: Endpoint, mode: DrilldownViewMode) -> tuple[str, str, str, str] | None:
        if self._included_drilldown_resource(endpoint):
            label = endpoint.resource_category or endpoint.function
            return endpoint.node_id, label, "resource", endpoint.node_id
        if endpoint.endpoint_type != "function":
            return None
        if mode == "package":
            return f"module:{endpoint.module}", endpoint.module, "module", endpoint.module
        if mode == "module":
            if endpoint.class_name is not None:
                class_scope = f"{endpoint.module}.{endpoint.class_name}"
                return f"class:{class_scope}", endpoint.class_name, "class", class_scope
            return endpoint.node_id, endpoint.function, "function", endpoint.qualified_name
        if endpoint.class_name is None:
            return None
        return endpoint.node_id, endpoint.function, "method", endpoint.qualified_name

    def _drilldown_parent_id_for_endpoint(self, endpoint: Endpoint | None, mode: DrilldownViewMode) -> str | None:
        if endpoint is None or endpoint.endpoint_type != "function":
            return None
        if mode == "package":
            return f"package:{self._package_scope(endpoint.module)}"
        if mode == "module":
            return f"module:{endpoint.module}"
        if endpoint.class_name is None:
            return None
        return f"class:{endpoint.module}.{endpoint.class_name}"

    def _drilldown_graph(self, *, mode: DrilldownViewMode, parent_id: str) -> _DrilldownGraph:
        parent_scope_type = "class" if mode == "actor" else mode
        return _DrilldownGraph(
            mode=mode,
            parent_id=parent_id,
            parent_label=self._drilldown_parent_label(parent_id),
            parent_scope_type=parent_scope_type,
            child_scope_type={"package": "module", "module": "actor", "actor": "method"}[mode],
        )

    @staticmethod
    def _drilldown_parent_label(parent_id: str) -> str:
        if parent_id.startswith("class:"):
            return parent_id.replace("class:", "", 1).split(".")[-1]
        if ":" in parent_id:
            return parent_id.split(":", 1)[1]
        return parent_id

    def _node_for_endpoint(self, *, nodes: dict[str, _AggregateNode], endpoint: Endpoint, mode: ArchitectureViewMode) -> _AggregateNode:
        node_id, label, scope_type, scope = self._scope_for_endpoint(endpoint=endpoint, mode=mode)
        node = nodes.get(node_id)
        if node is None:
            node = _AggregateNode(id=node_id, label=label, scope_type=scope_type, scope=scope, endpoint=endpoint)
            nodes[node_id] = node
        return node

    def _scope_for_endpoint(self, *, endpoint: Endpoint, mode: ArchitectureViewMode) -> tuple[str, str, str, str]:
        if endpoint.endpoint_type in {"resource", "external_service"}:
            label = endpoint.resource_category or endpoint.function
            return endpoint.node_id, label, endpoint.endpoint_type, endpoint.node_id
        if mode == "detail":
            return endpoint.node_id, endpoint.function, "callable", endpoint.qualified_name
        if mode == "package":
            package_name = self._package_scope(endpoint.module)
            return f"package:{package_name}", package_name, "package", package_name
        if mode == "module" or endpoint.class_name is None:
            return f"module:{endpoint.module}", endpoint.module, "module", endpoint.module
        return f"class:{endpoint.module}.{endpoint.class_name}", endpoint.class_name, "class", f"{endpoint.module}.{endpoint.class_name}"

    def _package_scope(self, module_name: str) -> str:
        parts = [part for part in module_name.split(".") if part]
        if not parts:
            return module_name or "application"
        if len(parts) > 1:
            return ".".join(parts[:-1])
        return ".".join(parts[: max(1, self.package_depth)])

    @staticmethod
    def _is_stdout_event(event: TraceEvent) -> bool:
        return event.callee.endpoint_type == "resource" and event.callee.resource_category == "stdout"

    @staticmethod
    def _included_drilldown_resource(endpoint: Endpoint) -> bool:
        return endpoint.endpoint_type == "resource" and endpoint.resource_category in {"file", "db"}

    @classmethod
    def _touches_private_endpoint(cls, event: TraceEvent) -> bool:
        return cls._is_private_endpoint(event.callee) or cls._is_private_endpoint(event.caller)

    @staticmethod
    def _is_private_endpoint(endpoint: Endpoint | None) -> bool:
        if endpoint is None or endpoint.endpoint_type != "function":
            return False
        function = endpoint.function
        return function.startswith("_") and not (function.startswith("__") and function.endswith("__"))

    @staticmethod
    def _view_label(mode: ArchitectureViewMode) -> str:
        return {
            "actor": "Actor/Class",
            "module": "Module",
            "package": "Package",
            "detail": "Detail",
        }[mode]


def _endpoint_json(endpoint: Endpoint) -> JsonObject:
    """Return a JSON-compatible endpoint payload for aggregate evidence."""
    return {
        "module": endpoint.module,
        "function": endpoint.function,
        "qualified_name": endpoint.qualified_name,
        "file": endpoint.file,
        "line": endpoint.line,
        "node_id": endpoint.node_id,
        "class_name": endpoint.class_name,
        "instance_id": endpoint.instance_id,
        "endpoint_type": endpoint.endpoint_type,
        "resource_category": endpoint.resource_category,
        "callable_kind": endpoint.callable_kind,
    }

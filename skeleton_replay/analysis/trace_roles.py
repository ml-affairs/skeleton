"""Classify traced frames into narrative roles for presentation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from skeleton_replay.runtime.events import Endpoint, TraceEvent

JsonObject = dict[str, Any]
TraceRole = Literal["entrypoint", "system_under_test", "test_harness", "test_utility", "import_setup", "filtered_external"]

ROLE_PRIORITY: dict[TraceRole, int] = {
    "entrypoint": 0,
    "system_under_test": 1,
    "test_utility": 2,
    "test_harness": 3,
    "import_setup": 4,
    "filtered_external": 5,
}


@dataclass(frozen=True)
class TraceRoleAnalysis:
    """Derived trace-role data for one snapshot."""

    events: list[JsonObject]
    node_roles: dict[str, JsonObject]
    setup_event_groups: list[JsonObject]
    entrypoint_event_order: int | None
    entrypoint_node_id: str | None

    def to_json(self) -> JsonObject:
        """Return a JSON-safe representation."""
        return {
            "entrypoint_event_order": self.entrypoint_event_order,
            "entrypoint_node_id": self.entrypoint_node_id,
            "events": self.events,
            "nodes": self.node_roles,
            "setup_event_groups": self.setup_event_groups,
        }


@dataclass(frozen=True)
class TraceRoleAnalyzer:
    """Derives semantic frame roles from observed trace events."""

    project_root: Path

    def analyze(self, events: list[TraceEvent]) -> TraceRoleAnalysis:
        """Classify event and node roles without mutating raw trace events."""
        entrypoint = self._entrypoint_event(events)
        entrypoint_order = entrypoint.order if entrypoint else None
        entrypoint_node_id = entrypoint.callee.node_id if entrypoint else None
        event_roles: list[JsonObject] = []
        node_role_sets: dict[str, set[TraceRole]] = {}

        for event in events:
            trace_role = self._event_role(event=event, entrypoint_order=entrypoint_order, entrypoint_node_id=entrypoint_node_id)
            root_context = self._root_context(event=event, trace_role=trace_role)
            event_roles.append(
                {
                    "order": event.order,
                    "trace_role": trace_role,
                    "callee_node_id": event.callee.node_id,
                    "caller_node_id": event.caller.node_id if event.caller else None,
                    "root_context": root_context,
                }
            )
            self._record_endpoint_role(node_role_sets, event.callee, trace_role)
            if event.caller is not None:
                self._record_endpoint_role(node_role_sets, event.caller, self._endpoint_role(event.caller, entrypoint_node_id=entrypoint_node_id))

        node_roles = {node_id: self._node_role_payload(roles) for node_id, roles in node_role_sets.items()}
        setup_groups = self._setup_event_groups(event_roles=event_roles, entrypoint_order=entrypoint_order, entrypoint_node_id=entrypoint_node_id)
        return TraceRoleAnalysis(
            events=event_roles,
            node_roles=node_roles,
            setup_event_groups=setup_groups,
            entrypoint_event_order=entrypoint_order,
            entrypoint_node_id=entrypoint_node_id,
        )

    def _entrypoint_event(self, events: list[TraceEvent]) -> TraceEvent | None:
        root_calls = [event for event in events if event.event_type == "call" and event.caller is None and event.callee.endpoint_type == "function"]
        for event in root_calls:
            if self._is_named_entrypoint(event.callee):
                return event
        return root_calls[0] if root_calls else None

    def _event_role(self, *, event: TraceEvent, entrypoint_order: int | None, entrypoint_node_id: str | None) -> TraceRole:
        if entrypoint_order is not None and event.order < entrypoint_order:
            return "import_setup"
        if event.callee.node_id == entrypoint_node_id:
            return "entrypoint"
        if event.caller is None and entrypoint_order is not None and event.order > entrypoint_order:
            return "filtered_external"
        return self._endpoint_role(event.callee, entrypoint_node_id=entrypoint_node_id)

    def _endpoint_role(self, endpoint: Endpoint, *, entrypoint_node_id: str | None) -> TraceRole:
        if endpoint.node_id == entrypoint_node_id:
            return "entrypoint"
        if self._is_test_utility(endpoint):
            return "test_utility"
        if self._is_test_harness(endpoint):
            return "test_harness"
        return "system_under_test"

    def _record_endpoint_role(self, node_role_sets: dict[str, set[TraceRole]], endpoint: Endpoint, trace_role: TraceRole) -> None:
        node_ids = [endpoint.node_id, f"module:{endpoint.module}"]
        if endpoint.class_name:
            node_ids.append(f"class:{endpoint.module}.{endpoint.class_name}")
        if endpoint.instance_id:
            node_ids.append(f"instance:{endpoint.instance_id}")
        for node_id in node_ids:
            node_role_sets.setdefault(node_id, set()).add(trace_role)

    @staticmethod
    def _node_role_payload(roles: set[TraceRole]) -> JsonObject:
        ordered_roles = sorted(roles, key=lambda role: ROLE_PRIORITY[role])
        return {
            "trace_role": ordered_roles[0] if ordered_roles else "system_under_test",
            "trace_roles": ordered_roles,
        }

    @staticmethod
    def _setup_event_groups(*, event_roles: list[JsonObject], entrypoint_order: int | None, entrypoint_node_id: str | None) -> list[JsonObject]:
        setup_orders = [int(record["order"]) for record in event_roles if record.get("trace_role") == "import_setup"]
        if not setup_orders:
            return []
        return [
            {
                "id": "setup-before-entrypoint",
                "label": "Setup before entrypoint",
                "trace_role": "import_setup",
                "collapsed_by_default": True,
                "event_orders": setup_orders,
                "first_event": min(setup_orders),
                "last_event": max(setup_orders),
                "entrypoint_event_order": entrypoint_order,
                "entrypoint_node_id": entrypoint_node_id,
            }
        ]

    @staticmethod
    def _root_context(*, event: TraceEvent, trace_role: TraceRole) -> str | None:
        if event.caller is not None:
            return None
        if trace_role == "filtered_external" or event.callee.function.startswith("test_"):
            return "caller_outside_trace_boundary"
        return "root_inside_selected_trace_boundary"

    @staticmethod
    def _is_named_entrypoint(endpoint: Endpoint) -> bool:
        return endpoint.function in {"main", "run", "run_scenario", "scenario"} or endpoint.function.startswith("test_")

    def _is_test_utility(self, endpoint: Endpoint) -> bool:
        relative_parts = self._relative_file_parts(endpoint)
        module = endpoint.module
        return ("tests" in relative_parts and "helpers" in relative_parts) or module == "conftest" or module.startswith("tests.helpers") or ".tests.helpers." in f".{module}."

    def _is_test_harness(self, endpoint: Endpoint) -> bool:
        relative_parts = self._relative_file_parts(endpoint)
        module = endpoint.module
        return endpoint.function.startswith("test_") or "tests" in relative_parts or module.startswith("test_") or module.startswith("tests.") or ".tests." in f".{module}."

    def _relative_file_parts(self, endpoint: Endpoint) -> tuple[str, ...]:
        if not endpoint.file:
            return ()
        try:
            return Path(endpoint.file).resolve().relative_to(self.project_root.resolve()).parts
        except (OSError, ValueError):
            return ()

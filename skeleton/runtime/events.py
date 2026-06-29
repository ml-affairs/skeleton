"""Typed event schema for Skeleton trace files."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

SCHEMA_VERSION = 1
JsonObject = dict[str, Any]
EventType = Literal["call", "return"]


@dataclass(frozen=True)
class Endpoint:
    """A callable observed at runtime."""

    module: str
    function: str
    qualified_name: str
    file: str
    line: int
    node_id: str
    class_name: str | None = None
    instance_id: str | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> Endpoint:
        """Create an endpoint from a decoded trace object."""
        return cls(
            module=str(data["module"]),
            function=str(data["function"]),
            qualified_name=str(data["qualified_name"]),
            file=str(data["file"]),
            line=int(data["line"]),
            node_id=str(data["node_id"]),
            class_name=str(data["class_name"]) if data.get("class_name") is not None else None,
            instance_id=str(data["instance_id"]) if data.get("instance_id") is not None else None,
        )


@dataclass(frozen=True)
class TraceEvent:
    """A single public project-local call or return event."""

    event_type: EventType
    order: int
    timestamp: float
    depth: int
    callee: Endpoint
    caller: Endpoint | None = None
    args: JsonObject | None = None
    return_value: JsonObject | None = None
    schema_version: int = SCHEMA_VERSION

    def to_json(self) -> JsonObject:
        """Return a JSON-serializable representation of the event."""
        return asdict(self)

    @classmethod
    def from_json(cls, data: JsonObject) -> TraceEvent:
        """Create a trace event from a decoded trace object."""
        caller_data = data.get("caller")
        event_type = data["event_type"]
        if event_type not in {"call", "return"}:
            raise ValueError(f"Unknown event type: {event_type}")
        return cls(
            event_type=event_type,
            order=int(data["order"]),
            timestamp=float(data["timestamp"]),
            depth=int(data["depth"]),
            callee=Endpoint.from_json(data["callee"]),
            caller=Endpoint.from_json(caller_data) if caller_data else None,
            args=data.get("args"),
            return_value=data.get("return_value"),
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
        )

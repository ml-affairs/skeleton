"""Context boundary records for structured-return tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextLaneBoundary:
    """Small runtime record that exposes a structured dictionary return."""

    name: str
    id: str
    kind: str
    lane: str
    owner: str
    role: str
    stage: str
    event_type: str
    active: bool

    def payload(self) -> dict[str, object]:
        """Return a safe metadata dictionary for traceability."""
        return {
            "name": self.name,
            "id": self.id,
            "kind": self.kind,
            "lane": self.lane,
            "owner": self.owner,
            "role": self.role,
            "stage": self.stage,
            "event_type": self.event_type,
            "active": self.active,
        }

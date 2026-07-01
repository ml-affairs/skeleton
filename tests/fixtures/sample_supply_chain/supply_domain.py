"""Domain data model for the supply-chain fixture."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Shipment:
    """Simple shipment aggregate used by the sample service."""

    order_id: str
    recipient: str
    destination: str = "main-warehouse"

    def label(self) -> str:
        """Return a human-readable label for display in demo traces."""
        return f"{self.order_id}:{self.recipient}"

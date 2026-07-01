"""Service orchestration for the supply-chain sample fixture."""

from __future__ import annotations

from supply_domain import Shipment
from supply_repository import ShipmentRepository


class ShipmentService:
    """Demonstrate class-method calls and delegation into repositories."""

    def __init__(self, repository: ShipmentRepository) -> None:
        self.repository = repository

    def fulfill(self, shipment: Shipment) -> str:
        """Run one fulfillment workflow and return a tracking label."""
        destination = self.repository.load_destination(shipment.order_id)
        return self._resolve_tracking(destination)

    def _resolve_tracking(self, destination: str) -> str:
        """Private helper to keep noise low in runtime traces."""
        if destination:
            return f"trk-{destination[:4].lower()}"
        return "trk-fallback"

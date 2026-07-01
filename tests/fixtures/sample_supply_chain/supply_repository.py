"""Repository helpers for the supply-chain sample fixture."""

from __future__ import annotations

from supply_domain import Shipment
from supply_telemetry import read_text, write_text


class ShipmentRepository:
    """Persist and reload lightweight shipment projections."""

    def create_shipment(self, order_id: str, recipient: str) -> Shipment:
        """Create a new Shipment and persist an audit checkpoint."""
        shipment = Shipment(order_id=order_id, recipient=recipient)
        write_text(f"shipment-{order_id}.json", shipment.__dict__)
        return shipment

    def load_destination(self, order_id: str) -> str:
        """Load destination metadata for a shipment from local traceable storage."""
        payload = read_text(f"destination-{order_id}.json")
        return payload.get("destination", "main-warehouse")

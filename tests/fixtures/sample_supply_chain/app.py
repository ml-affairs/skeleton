"""Demo script for supply-chain-like module and instance collaboration."""

from supply_repository import ShipmentRepository
from supply_service import ShipmentService
from supply_telemetry import post, read_text, write_text


def bootstrap(order_id: str) -> dict[str, str]:
    """Prepare a small workflow payload for the demo run."""
    repository = ShipmentRepository()
    seed_data = read_seed()
    shipment = repository.create_shipment(order_id=order_id, recipient=seed_data["recipient"])
    service = ShipmentService(repository=repository)
    tracking = service.fulfill(shipment)
    acknowledgement = post({"shipment": shipment.order_id, "tracking": tracking})
    return {
        "tracking": tracking,
        "ack": acknowledgement,
        "destination": shipment.destination,
    }


def read_seed() -> dict[str, str]:
    """Read a fixture-like configuration blob and emit traceable file I/O."""
    payload = read_text("seed-destination.json")
    return {"recipient": payload.get("recipient", "Ada Lovelace"), "method": payload.get("method", "standard")}


def main() -> str:
    """Entry point used by the CLI smoke tests."""
    result = bootstrap("ORD-007")
    write_text(
        "shipping-result.log",
        {
            "tracking": result["tracking"],
            "ack": result["ack"],
        },
    )
    return result["tracking"]


if __name__ == "__main__":
    print(main())

"""Script entrypoint for the I/O boundary sample project."""

from __future__ import annotations

from pathlib import Path

from notification_adapter import ConsoleNotifier
from order_repository import SqliteOrderRepository
from order_service import OrderService


def bootstrap(database_path: Path) -> OrderService:
    """Compose the application service with its persistence and output adapters."""
    repository = SqliteOrderRepository(database_path)
    notifier = ConsoleNotifier()
    return OrderService(repository=repository, notifier=notifier)


def main() -> None:
    """Run a small order-registration workflow."""
    runtime_dir = Path(__file__).resolve().parent / ".skeleton" / "runtime"
    service = bootstrap(runtime_dir / "orders.sqlite3")
    service.register_order(order_id="ORD-1001", customer_name="Ada Lovelace", total=42.5)


if __name__ == "__main__":
    main()

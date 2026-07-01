"""Application service for the I/O boundary sample."""

from __future__ import annotations

from typing import Protocol

from order_domain import Order


class OrderRepository(Protocol):
    """Persistence port used by the order service."""

    def save(self, order: Order) -> str:
        """Persist an order and return its storage reference."""
        ...

    def load(self, order_id: str) -> Order:
        """Load an order from persistence."""
        ...


class OrderNotifier(Protocol):
    """Output port used by the order service."""

    def announce(self, order: Order) -> None:
        """Publish order status to an external output."""
        ...


class OrderService:
    """Coordinates order registration without owning persistence or stdout."""

    def __init__(self, repository: OrderRepository, notifier: OrderNotifier) -> None:
        """Initialize the service with explicit I/O ports."""
        self.repository = repository
        self.notifier = notifier

    def register_order(self, order_id: str, customer_name: str, total: float) -> Order:
        """Register, persist, reload, and announce an order."""
        order = Order(order_id=order_id, customer_name=customer_name, total=total)
        stored_reference = self.repository.save(order)
        stored_order = self.repository.load(stored_reference)
        self.notifier.announce(stored_order)
        return stored_order

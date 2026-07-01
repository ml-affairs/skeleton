"""Console notification adapter for the I/O boundary sample."""

from __future__ import annotations

from order_domain import Order


class ConsoleNotifier:
    """Publishes order status to standard output."""

    def announce(self, order: Order) -> None:
        """Write a concise order notification to stdout."""
        print(f"registered {order.display_label()} total={order.total:.2f}")

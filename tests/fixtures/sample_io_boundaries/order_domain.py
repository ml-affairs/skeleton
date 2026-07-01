"""Domain model for the I/O boundary sample."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    """A customer order handled by the application service."""

    order_id: str
    customer_name: str
    total: float

    def display_label(self) -> str:
        """Return a concise human-facing order label."""
        return f"{self.order_id} for {self.customer_name}"

"""Deterministic plan construction and summary helpers."""

from __future__ import annotations


def build_plan(order_id: str, strategy: str) -> list[str]:
    """Build a deterministic execution plan for an order."""
    prefix = "fast" if strategy == "standard" else "careful"
    return [f"{prefix}:{order_id}:collect", f"{prefix}:{order_id}:validate", f"{prefix}:{order_id}:ship"]


def summarize(*, order_id: str, status: str, response: dict[str, str]) -> dict[str, str]:
    """Summarise workflow outcome in a single return payload."""
    return {
        "order_id": order_id,
        "result": f"{status}:{response['status']}",
    }

"""Pytest scenarios that encode application behavior."""

from calculator import build_receipt


def test_builds_receipt_total() -> None:
    """Exercise the checkout calculation path."""
    receipt = build_receipt(10.0, 0.2)

    assert receipt == {"kind": "receipt", "subtotal": 10.0, "total": 12.0}

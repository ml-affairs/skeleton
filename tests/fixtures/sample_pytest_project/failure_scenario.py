"""Failure scenario selected explicitly by Skeleton tests."""

from calculator import build_receipt


def test_failing_receipt_total() -> None:
    """Provide a failure scenario for exit-code preservation tests."""
    receipt = build_receipt(10.0, 0.2)

    assert receipt["total"] == 13.0

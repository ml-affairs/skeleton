"""Small project used to verify pytest tracing."""


class PriceCalculator:
    """Calculates totals for checkout-like test scenarios."""

    def total(self, subtotal: float, tax_rate: float) -> float:
        """Return the subtotal plus tax."""
        return round(subtotal + self.tax(subtotal, tax_rate), 2)

    def tax(self, subtotal: float, tax_rate: float) -> float:
        """Return the tax portion for a subtotal."""
        return subtotal * tax_rate


def build_receipt(subtotal: float, tax_rate: float) -> dict[str, float | str]:
    """Build a receipt record for tests to assert against."""
    calculator = PriceCalculator()
    return {"kind": "receipt", "subtotal": subtotal, "total": calculator.total(subtotal, tax_rate)}

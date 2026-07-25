"""Transformation rules for the noisy ETL fixture."""


class CustomerRules:
    """Score and label customer records."""

    def __init__(self) -> None:
        self.multiplier = 1.0
        self.adjustments: dict[str, int] = {}

    def configure(self, settings: dict[str, object]) -> None:
        """Configure rule weighting."""
        self.multiplier = max(1.0, float(settings.get("source_count", 1))) * max(1.0, float(settings.get("score_multiplier", 1)))
        adjustments = settings.get("adjustments", {})
        self.adjustments = adjustments if isinstance(adjustments, dict) else {}

    def score(self, spend: float) -> int:
        """Score one customer."""
        return int(self._weighted(spend) / 10)

    def segment(self, score: int) -> str:
        """Assign a segment."""
        segment = "vip" if score > 20 else "standard"
        _ = self.adjustments.get(segment, 0)
        return segment

    def title(self, value: str) -> str:
        """Format a display title."""
        return value.title()

    def _weighted(self, spend: float) -> float:
        return spend * self.multiplier

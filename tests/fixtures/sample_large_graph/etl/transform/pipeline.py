"""Transformation stage for the noisy ETL fixture."""

from warehouse.data.files import LocalDataCatalog

from etl.transform.rules import CustomerRules


class CustomerTransformer:
    """Transform raw rows into warehouse records."""

    def __init__(self, data_catalog: LocalDataCatalog) -> None:
        self.data_catalog = data_catalog
        self.rules = CustomerRules()
        self.source_count = 0

    def configure(self, settings: dict[str, object]) -> None:
        """Configure transformation context."""
        file_settings = self.data_catalog.load_rules()
        adjustments = self.data_catalog.load_adjustments()
        self.source_count = int(settings.get("source_count", 0))
        self.rules.configure({**settings, **file_settings, "adjustments": adjustments})

    def transform(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        """Transform raw rows."""
        return [self._build_record(row) for row in rows]

    def _build_record(self, row: dict[str, object]) -> dict[str, object]:
        score = self.rules.score(float(row["spend"]))
        return {
            "id": row["id"],
            "display_name": self.rules.title(str(row["name"])),
            "score": score,
            "segment": self.rules.segment(score),
            "source_count": self.source_count,
        }

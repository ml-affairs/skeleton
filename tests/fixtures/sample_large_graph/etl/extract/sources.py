"""Source adapters for the noisy ETL fixture."""


class SourceReader:
    """Pretend to read customer rows from source systems."""

    def count_sources(self) -> int:
        """Return the number of source systems."""
        return len(self._source_names())

    def read_rows(self) -> list[dict[str, object]]:
        """Read raw customer rows."""
        return [self._row("c-1", "Ada", 150.0), self._row("c-2", "Grace", 260.0)]

    def _source_names(self) -> list[str]:
        return ["crm", "billing"]

    def _row(self, customer_id: str, name: str, spend: float) -> dict[str, object]:
        return {"id": customer_id, "name": name, "spend": spend}

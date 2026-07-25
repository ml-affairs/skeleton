"""Extraction stage for the noisy ETL fixture."""

from etl.extract.sources import SourceReader


class CustomerExtractor:
    """Read and normalize customer source rows."""

    def __init__(self) -> None:
        self.reader = SourceReader()

    def source_count(self) -> int:
        """Return the number of configured sources."""
        return self.reader.count_sources()

    def extract(self) -> list[dict[str, object]]:
        """Extract raw customer rows."""
        rows = self.reader.read_rows()
        return [self._normalize(row) for row in rows]

    def _normalize(self, row: dict[str, object]) -> dict[str, object]:
        return {
            "id": self._text(row["id"]),
            "name": self._text(row["name"]),
            "spend": float(row["spend"]),
        }

    def _text(self, value: object) -> str:
        return str(value).strip()

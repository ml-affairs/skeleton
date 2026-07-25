"""Audit boundary for the noisy ETL fixture."""


class AuditAdapter:
    """Record audit metadata for loaded batches."""

    def record_batch(self, inserted: int) -> None:
        """Record the inserted row count."""
        _ = self._format("inserted", inserted)

    def record_checksum(self, checksum: str) -> None:
        """Record a checksum."""
        _ = self._format("checksum", checksum)
        print("audit checksum recorded")

    def _format(self, key: str, value: object) -> str:
        return f"{key}={value}"

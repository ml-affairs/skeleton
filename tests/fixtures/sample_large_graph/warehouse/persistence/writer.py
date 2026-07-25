"""Persistence writer for the noisy ETL fixture."""


class BatchWriter:
    """Pretend to write transformed records to a warehouse."""

    def __init__(self) -> None:
        self.keys: list[str] = []

    def prepare(self) -> None:
        """Prepare the writer."""
        self.keys.clear()

    def write(self, record: dict[str, object]) -> None:
        """Write one record."""
        self.keys.append(self._warehouse_key(record))

    def last_checksum(self) -> str:
        """Return a simple checksum for the batch."""
        return str(sum(len(key) for key in self.keys))

    def _warehouse_key(self, record: dict[str, object]) -> str:
        return f"customer:{record['id']}"

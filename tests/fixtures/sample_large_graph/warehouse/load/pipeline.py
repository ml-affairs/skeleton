"""Loading stage for the noisy ETL fixture."""

from warehouse.audit.adapter import AuditAdapter
from warehouse.data.files import LocalDataCatalog
from warehouse.persistence.writer import BatchWriter


class WarehouseLoader:
    """Persist transformed rows and notify an audit boundary."""

    def __init__(self, data_catalog: LocalDataCatalog) -> None:
        self.data_catalog = data_catalog
        self.writer = BatchWriter()
        self.audit = AuditAdapter()

    def prepare(self) -> None:
        """Prepare the warehouse writer."""
        self.writer.prepare()

    def load(self, records: list[dict[str, object]]) -> int:
        """Load records and return the inserted count."""
        inserted = 0
        for record in records:
            if self._validate(record):
                self.writer.write(record)
                inserted += 1
        self.data_catalog.persist_records(records)
        self.audit.record_batch(inserted)
        self.audit.record_checksum(self.writer.last_checksum())
        return inserted

    def _validate(self, record: dict[str, object]) -> bool:
        return bool(record.get("id")) and bool(record.get("display_name"))

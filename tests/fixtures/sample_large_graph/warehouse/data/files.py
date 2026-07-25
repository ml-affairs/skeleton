"""Local file and database resources for the noisy ETL fixture."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path


class LocalDataCatalog:
    """Reads fixture data files and writes a tiny local warehouse database."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def load_rules(self) -> dict[str, object]:
        """Load JSON rule metadata."""
        return json.loads((self.base_dir / "rules.json").read_text(encoding="utf-8"))

    def load_adjustments(self) -> dict[str, int]:
        """Load CSV adjustment metadata."""
        with (self.base_dir / "adjustments.csv").open(encoding="utf-8") as csv_file:
            return {row["segment"]: int(row["bonus"]) for row in csv.DictReader(csv_file)}

    def persist_records(self, records: list[dict[str, object]]) -> int:
        """Persist records to a local SQLite file."""
        database_path = self.base_dir / "warehouse.sqlite3"
        with sqlite3.connect(database_path) as connection:
            connection.execute("create table if not exists customers (id text primary key, display_name text not null, segment text not null)")
            for record in records:
                connection.execute(
                    "insert or replace into customers (id, display_name, segment) values (?, ?, ?)",
                    (str(record["id"]), str(record["display_name"]), str(record["segment"])),
                )
            connection.commit()
        return len(records)

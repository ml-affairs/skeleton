"""SQLite persistence adapter for the I/O boundary sample."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from order_domain import Order


class SqliteOrderRepository:
    """Stores and loads orders through an explicit SQLite persistence boundary."""

    def __init__(self, database_path: Path) -> None:
        """Initialize the repository with its database file path."""
        self.database_path = database_path

    def save(self, order: Order) -> str:
        """Persist an order and return its storage reference."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("create table if not exists orders (order_id text primary key, customer_name text not null, total real not null)")
            connection.execute(
                "insert or replace into orders (order_id, customer_name, total) values (?, ?, ?)",
                (order.order_id, order.customer_name, order.total),
            )
            connection.commit()
        return order.order_id

    def load(self, order_id: str) -> Order:
        """Load an order from SQLite by storage reference."""
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "select order_id, customer_name, total from orders where order_id = ?",
                (order_id,),
            ).fetchone()
        if row is None:
            raise LookupError(order_id)
        return Order(order_id=str(row[0]), customer_name=str(row[1]), total=float(row[2]))

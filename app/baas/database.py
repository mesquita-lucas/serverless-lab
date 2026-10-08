import sqlite3
from pathlib import Path

from app.models.order import ProcessedOrder

class Database:
    def __init__(self, path="data/serverless_lab.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.initialize()

    def connect(self):
        return sqlite3.connect(self.path)

    def initialize(self):
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    product TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    original_total REAL NOT NULL,
                    discount REAL NOT NULL,
                    final_total REAL NOT NULL
                )
                """
            )

    def save_order(self, order: ProcessedOrder):
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO orders (
                    id,
                    workspace_id,
                    product,
                    quantity,
                    original_total,
                    discount,
                    final_total
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.order_id,
                    order.workspace_id,
                    order.product,
                    order.quantity,
                    order.original_total,
                    order.discount,
                    order.final_total,
                ),
            )

    def list_orders(self, workspace_id: str):
        with self.connect() as connection:
            cursor = connection.execute(
                """
                SELECT
                    id,
                    product,
                    quantity,
                    original_total,
                    discount,
                    final_total
                FROM orders
                WHERE workspace_id = ?
                """,
                (workspace_id,),
            )

            return cursor.fetchall()

    def clear_workspace(self, workspace_id: str):
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM orders WHERE workspace_id = ?",
                (workspace_id,),
            )
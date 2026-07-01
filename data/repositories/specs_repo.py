"""
InventoryPro - Computer Specs Repository
CRUD for the computer_specs table + performance scoring integration.
"""
import uuid
import sqlite3
from datetime import datetime
from typing import Optional

from data.database import get_connection
from data.models import ComputerSpecs
from utils.performance_scorer import calculate_score

# Categories that qualify as "computer" items
COMPUTER_CATEGORIES = {"laptop", "desktop", "computer"}


def is_computer_category(category_name: Optional[str]) -> bool:
    """Return True if this category should have computer specs."""
    if not category_name:
        return False
    return category_name.strip().lower() in COMPUTER_CATEGORIES


class SpecsRepository:

    def get_by_item(self, item_id: str) -> Optional[ComputerSpecs]:
        """Fetch specs for one item. Returns None if not a computer or no specs yet."""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM computer_specs WHERE item_id = ?", (item_id,))
        row = c.fetchone()
        conn.close()
        return self._row_to_model(row) if row else None

    def upsert(self, item_id: str, data: dict) -> ComputerSpecs:
        """
        Insert or update specs for a computer item.
        Automatically recalculates the performance score.
        """
        conn = get_connection()
        now = datetime.utcnow().isoformat()

        # Build a temporary model to score it
        temp = ComputerSpecs(
            id="", item_id=item_id,
            cpu=data.get("cpu"),
            cpu_cores=self._int(data.get("cpu_cores")),
            cpu_ghz=self._float(data.get("cpu_ghz")),
            ram_gb=self._int(data.get("ram_gb")),
            storage_gb=self._int(data.get("storage_gb")),
            storage_type=data.get("storage_type", "SSD"),
            gpu=data.get("gpu"),
            purchase_year=self._int(data.get("purchase_year")),
        )
        score = calculate_score(temp)

        # Check if row exists
        c = conn.cursor()
        c.execute("SELECT id FROM computer_specs WHERE item_id = ?", (item_id,))
        existing = c.fetchone()

        if existing:
            c.execute("""
                UPDATE computer_specs SET
                    cpu=?, cpu_cores=?, cpu_ghz=?, ram_gb=?,
                    storage_gb=?, storage_type=?, gpu=?, purchase_year=?,
                    perf_score=?, updated_at=?
                WHERE item_id=?
            """, (
                data.get("cpu"), self._int(data.get("cpu_cores")),
                self._float(data.get("cpu_ghz")), self._int(data.get("ram_gb")),
                self._int(data.get("storage_gb")), data.get("storage_type", "SSD"),
                data.get("gpu"), self._int(data.get("purchase_year")),
                score, now, item_id
            ))
        else:
            spec_id = str(uuid.uuid4())
            c.execute("""
                INSERT INTO computer_specs
                    (id, item_id, cpu, cpu_cores, cpu_ghz, ram_gb,
                     storage_gb, storage_type, gpu, purchase_year, perf_score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                spec_id, item_id,
                data.get("cpu"), self._int(data.get("cpu_cores")),
                self._float(data.get("cpu_ghz")), self._int(data.get("ram_gb")),
                self._int(data.get("storage_gb")), data.get("storage_type", "SSD"),
                data.get("gpu"), self._int(data.get("purchase_year")),
                score, now
            ))

        conn.commit()
        conn.close()
        return self.get_by_item(item_id)

    def delete(self, item_id: str):
        conn = get_connection()
        conn.execute("DELETE FROM computer_specs WHERE item_id = ?", (item_id,))
        conn.commit()
        conn.close()

    def get_all_scored(self) -> list[ComputerSpecs]:
        """
        Return all computer specs joined with item name/brand/model/assigned_to,
        sorted best → worst score.
        """
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT
                cs.*,
                i.name as item_name,
                i.brand as item_brand,
                i.model as item_model,
                i.serial_number,
                e.full_name as assigned_to
            FROM computer_specs cs
            JOIN items i ON cs.item_id = i.id
            LEFT JOIN assignments a ON a.item_id = i.id AND a.is_active = 1
            LEFT JOIN employees e ON a.employee_id = e.id
            ORDER BY cs.perf_score DESC NULLS LAST
        """)
        rows = c.fetchall()
        conn.close()
        return [self._row_to_model(r) for r in rows]

    def recalculate_all(self):
        """Recalculate scores for every computer in the DB."""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM computer_specs")
        rows = c.fetchall()
        for row in rows:
            specs = self._row_to_model(row)
            score = calculate_score(specs)
            conn.execute(
                "UPDATE computer_specs SET perf_score=? WHERE id=?",
                (score, specs.id)
            )
        conn.commit()
        conn.close()

    def _row_to_model(self, row: sqlite3.Row) -> ComputerSpecs:
        d = dict(row)
        specs = ComputerSpecs(
            id=d["id"],
            item_id=d["item_id"],
            cpu=d.get("cpu"),
            cpu_cores=d.get("cpu_cores"),
            cpu_ghz=d.get("cpu_ghz"),
            ram_gb=d.get("ram_gb"),
            storage_gb=d.get("storage_gb"),
            storage_type=d.get("storage_type", "SSD"),
            gpu=d.get("gpu"),
            purchase_year=d.get("purchase_year"),
            perf_score=d.get("perf_score"),
            updated_at=d.get("updated_at", ""),
        )
        # Attach joined fields as plain attributes (not in dataclass)
        specs.__dict__.update({
            "item_name":   d.get("item_name"),
            "item_brand":  d.get("item_brand"),
            "item_model":  d.get("item_model"),
            "serial_number": d.get("serial_number"),
            "assigned_to": d.get("assigned_to"),
        })
        return specs

    @staticmethod
    def _int(v) -> Optional[int]:
        try:
            return int(v) if v not in (None, "", "None") else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _float(v) -> Optional[float]:
        try:
            return float(v) if v not in (None, "", "None") else None
        except (ValueError, TypeError):
            return None

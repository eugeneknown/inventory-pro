"""
InventoryPro - Item Repository
All DB queries for the items (equipment) table.
"""
import uuid
from datetime import datetime
from typing import Optional
import sqlite3

from data.database import get_connection
from data.models import Item


class ItemRepository:

    def next_item_id(self) -> str:
        """Generate the next available ITM-XXX string."""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT item_id FROM items WHERE item_id LIKE 'ITM-%' ORDER BY CAST(SUBSTR(item_id, 5) AS INTEGER) DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if not row:
            return "ITM-001"
        try:
            last_num = int(row[0].split("-")[1])
            return f"ITM-{last_num + 1:03d}"
        except Exception:
            return "ITM-001"

    def get_all(self, category_id: Optional[str] = None,
                status_id: Optional[str] = None,
                search: Optional[str] = None,
                assigned_to: Optional[str] = None) -> list[Item]:
        conn = get_connection()
        c = conn.cursor()
        query = """
            SELECT i.*,
                   cat.name as category_name,
                   s.name as status_name,
                   s.color_hex as status_color,
                   e.full_name as assigned_to,
                   a.employee_id as assigned_employee_id
            FROM items i
            LEFT JOIN categories cat ON i.category_id = cat.id
            LEFT JOIN statuses s ON i.status_id = s.id
            LEFT JOIN assignments a ON a.item_id = i.id AND a.is_active = 1
            LEFT JOIN employees e ON a.employee_id = e.id
            WHERE 1=1
        """
        params = []
        if category_id:
            query += " AND i.category_id = ?"
            params.append(category_id)
        if status_id:
            query += " AND i.status_id = ?"
            params.append(status_id)
        if assigned_to:
            query += " AND a.employee_id = ?"
            params.append(assigned_to)
        if search:
            query += """ AND (i.name LIKE ? OR i.serial_number LIKE ?
                         OR i.brand LIKE ? OR i.model LIKE ?)"""
            s = f"%{search}%"
            params.extend([s, s, s, s])
        query += " ORDER BY i.created_at DESC"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [self._row_to_model(r) for r in rows]

    def get_by_id(self, item_id: str) -> Optional[Item]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT i.*,
                   cat.name as category_name,
                   s.name as status_name,
                   s.color_hex as status_color,
                   e.full_name as assigned_to,
                   a.employee_id as assigned_employee_id
            FROM items i
            LEFT JOIN categories cat ON i.category_id = cat.id
            LEFT JOIN statuses s ON i.status_id = s.id
            LEFT JOIN assignments a ON a.item_id = i.id AND a.is_active = 1
            LEFT JOIN employees e ON a.employee_id = e.id
            WHERE i.id = ?
        """, (item_id,))
        row = c.fetchone()
        conn.close()
        return self._row_to_model(row) if row else None

    def get_by_serial(self, serial: str) -> Optional[Item]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM items WHERE serial_number = ?", (serial,))
        row = c.fetchone()
        conn.close()
        if row:
            return self.get_by_id(row["id"])
        return None

    def create(self, data: dict) -> Item:
        conn = get_connection()
        c = conn.cursor()
        item_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        c.execute("""
            INSERT INTO items
                (id, item_id, serial_number, serial_source, name, brand, model,
                 category_id, description, purchase_date, purchase_price,
                 status_id, image_path, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id,
            data.get("item_id") or self.next_item_id(),
            data.get("serial_number"),
            data.get("serial_source", "manual"),
            data["name"],
            data.get("brand"),
            data.get("model"),
            data.get("category_id"),
            data.get("description"),
            data.get("purchase_date"),
            data.get("purchase_price"),
            data.get("status_id") or self._get_default_status_id(conn),
            data.get("image_path"),
            data.get("notes"),
            now, now
        ))
        conn.commit()
        conn.close()
        return self.get_by_id(item_id)

    def create_many(self, data_list: list[dict]) -> list[Item]:
        if not data_list: return []
        conn = get_connection()
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        # Pre-fetch the next ID so we can increment it in memory
        current_next_id = self.next_item_id()
        if current_next_id.startswith("ITM-"):
            try:
                next_num = int(current_next_id.split("-")[1])
            except:
                next_num = 1
        else:
            next_num = 1
        
        insert_records = []
        created_items = []
        for data in data_list:
            item_id = str(uuid.uuid4())
            
            assigned_item_id = data.get("item_id")
            if not assigned_item_id:
                assigned_item_id = f"ITM-{next_num:03d}"
                next_num += 1
                
            insert_records.append((
                item_id,
                assigned_item_id,
                data.get("serial_number"),
                data.get("serial_source", "manual"),
                data["name"],
                data.get("brand"),
                data.get("model"),
                data.get("category_id"),
                data.get("description"),
                data.get("purchase_date"),
                data.get("purchase_price"),
                data.get("status_id") or self._get_default_status_id(conn),
                data.get("image_path"),
                data.get("notes"),
                now, now
            ))
            created_items.append(Item(
                id=item_id, item_id=assigned_item_id, name=data["name"],
                serial_number=data.get("serial_number"), serial_source=data.get("serial_source", "manual"),
                brand=data.get("brand"), model=data.get("model"), category_id=data.get("category_id"),
                description=data.get("description"), purchase_date=data.get("purchase_date"),
                purchase_price=data.get("purchase_price"), status_id=data.get("status_id"),
                image_path=data.get("image_path"), notes=data.get("notes"),
                created_at=now, updated_at=now
            ))

        c.executemany("""
            INSERT INTO items
                (id, item_id, serial_number, serial_source, name, brand, model,
                 category_id, description, purchase_date, purchase_price,
                 status_id, image_path, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, insert_records)
        conn.commit()
        conn.close()
        return created_items

    def update(self, item_id: str, data: dict) -> Optional[Item]:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        c.execute("""
            UPDATE items SET
                name = ?, brand = ?, model = ?, category_id = ?,
                description = ?, purchase_date = ?, purchase_price = ?,
                status_id = ?, image_path = ?, notes = ?,
                updated_at = ?, sync_status = 'pending'
            WHERE id = ?
        """, (
            data["name"], data.get("brand"), data.get("model"),
            data.get("category_id"), data.get("description"),
            data.get("purchase_date"), data.get("purchase_price"),
            data.get("status_id"), data.get("image_path"),
            data.get("notes"), now, item_id
        ))
        conn.commit()
        conn.close()
        return self.get_by_id(item_id)

    def update_status(self, item_id: str, status_id: str, notes: Optional[str] = None) -> Optional[Item]:
        conn = get_connection()
        now = datetime.utcnow().isoformat()
        if notes is not None:
            conn.execute(
                "UPDATE items SET status_id=?, notes=?, updated_at=?, sync_status='pending' WHERE id=?",
                (status_id, notes, now, item_id)
            )
        else:
            conn.execute(
                "UPDATE items SET status_id=?, updated_at=?, sync_status='pending' WHERE id=?",
                (status_id, now, item_id)
            )
        conn.commit()
        conn.close()
        return self.get_by_id(item_id)

    def delete(self, item_id: str) -> bool:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM assignments WHERE item_id = ? AND is_active = 1", (item_id,))
        if c.fetchone()[0] > 0:
            conn.close()
            raise ValueError("Cannot delete item with an active assignment.")
        
        # Delete historical assignments to satisfy foreign key constraints
        c.execute("DELETE FROM assignments WHERE item_id = ?", (item_id,))
        c.execute("DELETE FROM computer_specs WHERE item_id = ?", (item_id,))
        c.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        return True

    def get_categories(self) -> list[dict]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM categories ORDER BY name")
        rows = [{"id": r["id"], "name": r["name"]} for r in c.fetchall()]
        conn.close()
        return rows

    def get_statuses(self) -> list[dict]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, color_hex FROM statuses ORDER BY name")
        rows = [{"id": r["id"], "name": r["name"], "color_hex": r["color_hex"]}
                for r in c.fetchall()]
        conn.close()
        return rows

    def _get_default_status_id(self, conn: sqlite3.Connection) -> Optional[str]:
        c = conn.cursor()
        c.execute("SELECT id FROM statuses WHERE is_default = 1 LIMIT 1")
        row = c.fetchone()
        return row["id"] if row else None

    def _row_to_model(self, row: sqlite3.Row) -> Item:
        d = dict(row)
        return Item(
            id=d["id"],
            name=d["name"],
            item_id=d.get("item_id", ""),
            serial_number=d.get("serial_number"),
            serial_source=d.get("serial_source", "manual"),
            brand=d.get("brand"),
            model=d.get("model"),
            category_id=d.get("category_id"),
            description=d.get("description"),
            purchase_date=d.get("purchase_date"),
            purchase_price=d.get("purchase_price"),
            status_id=d.get("status_id"),
            image_path=d.get("image_path"),
            notes=d.get("notes"),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            sync_status=d.get("sync_status", "pending"),
            category_name=d.get("category_name"),
            status_name=d.get("status_name"),
            status_color=d.get("status_color"),
            assigned_to=d.get("assigned_to"),
            assigned_employee_id=d.get("assigned_employee_id"),
        )

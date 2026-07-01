"""
InventoryPro - Assignment Repository
"""
import uuid
from datetime import datetime
from typing import Optional
import sqlite3

from data.database import get_connection
from data.models import Assignment


class AssignmentRepository:

    def get_active_for_item(self, item_id: str) -> Optional[Assignment]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT a.*, i.name as item_name, i.serial_number as item_serial,
                   e.full_name as employee_name, d.name as employee_dept
            FROM assignments a
            JOIN items i ON a.item_id = i.id
            JOIN employees e ON a.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE a.item_id = ? AND a.is_active = 1
        """, (item_id,))
        row = c.fetchone()
        conn.close()
        return self._row_to_model(row) if row else None

    def get_for_employee(self, employee_id: str, active_only: bool = True) -> list[Assignment]:
        conn = get_connection()
        c = conn.cursor()
        query = """
            SELECT a.*, i.name as item_name, i.serial_number as item_serial,
                   e.full_name as employee_name, d.name as employee_dept
            FROM assignments a
            JOIN items i ON a.item_id = i.id
            JOIN employees e ON a.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE a.employee_id = ?
        """
        params = [employee_id]
        if active_only:
            query += " AND a.is_active = 1"
        query += " ORDER BY a.assigned_at DESC"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [self._row_to_model(r) for r in rows]

    def get_all(self, active_only: bool = False,
                employee_id: Optional[str] = None) -> list[Assignment]:
        conn = get_connection()
        c = conn.cursor()
        query = """
            SELECT a.*, i.name as item_name, i.serial_number as item_serial,
                   e.full_name as employee_name, d.name as employee_dept
            FROM assignments a
            JOIN items i ON a.item_id = i.id
            JOIN employees e ON a.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE 1=1
        """
        params = []
        if active_only:
            query += " AND a.is_active = 1"
        if employee_id:
            query += " AND a.employee_id = ?"
            params.append(employee_id)
        query += " ORDER BY a.assigned_at DESC"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [self._row_to_model(r) for r in rows]

    def assign(self, item_id: str, employee_id: str,
               assigned_by: str, notes: Optional[str] = None) -> Assignment:
        conn = get_connection()
        c = conn.cursor()
        # Deactivate any existing assignment for the item
        c.execute("""
            UPDATE assignments SET is_active=0, returned_at=?
            WHERE item_id=? AND is_active=1
        """, (datetime.utcnow().isoformat(), item_id))
        # Create new assignment
        assign_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        c.execute("""
            INSERT INTO assignments (id, item_id, employee_id, assigned_by, assigned_at, notes, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (assign_id, item_id, employee_id, assigned_by, now, notes))
        # Update item status to 'assigned'
        c.execute("""
            UPDATE items SET status_id = (
                SELECT id FROM statuses WHERE name='assigned' LIMIT 1
            ), updated_at=?, sync_status='pending'
            WHERE id=?
        """, (now, item_id))
        conn.commit()
        conn.close()
        return self.get_by_id(assign_id)

    def return_item(self, item_id: str, notes: Optional[str] = None) -> bool:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        c.execute("""
            UPDATE assignments SET is_active=0, returned_at=?, notes=?
            WHERE item_id=? AND is_active=1
        """, (now, notes, item_id))
        # Update item status to 'available'
        c.execute("""
            UPDATE items SET status_id = (
                SELECT id FROM statuses WHERE name='available' LIMIT 1
            ), updated_at=?, sync_status='pending'
            WHERE id=?
        """, (now, item_id))
        conn.commit()
        conn.close()
        return True

    def get_by_id(self, assignment_id: str) -> Optional[Assignment]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT a.*, i.name as item_name, i.serial_number as item_serial,
                   e.full_name as employee_name, d.name as employee_dept
            FROM assignments a
            JOIN items i ON a.item_id = i.id
            JOIN employees e ON a.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE a.id = ?
        """, (assignment_id,))
        row = c.fetchone()
        conn.close()
        return self._row_to_model(row) if row else None

    def _row_to_model(self, row: sqlite3.Row) -> Assignment:
        d = dict(row)
        return Assignment(
            id=d["id"],
            item_id=d["item_id"],
            employee_id=d["employee_id"],
            assigned_by=d["assigned_by"],
            assigned_at=d.get("assigned_at", ""),
            returned_at=d.get("returned_at"),
            notes=d.get("notes"),
            is_active=bool(d.get("is_active", 1)),
            sync_status=d.get("sync_status", "pending"),
            item_name=d.get("item_name"),
            item_serial=d.get("item_serial"),
            employee_name=d.get("employee_name"),
            employee_dept=d.get("employee_dept"),
        )

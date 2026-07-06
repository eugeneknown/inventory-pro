"""
InventoryPro - Employee Repository
All DB queries for the employees table.
"""
import uuid
import json
from datetime import datetime
from typing import Optional
import sqlite3

from data.database import get_connection
from data.models import Employee


class EmployeeRepository:

    def get_all(self, department_id: Optional[str] = None,
                status: Optional[str] = None,
                search: Optional[str] = None) -> list[Employee]:
        conn = get_connection()
        c = conn.cursor()
        query = """
            SELECT e.*, d.name as department_name,
                   COUNT(a.id) as assigned_count
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            LEFT JOIN assignments a ON a.employee_id = e.id AND a.is_active = 1
            WHERE 1=1
        """
        params = []
        if department_id:
            query += " AND e.department_id = ?"
            params.append(department_id)
        if status:
            query += " AND e.status = ?"
            params.append(status)
        if search:
            query += " AND (e.full_name LIKE ? OR e.employee_id LIKE ? OR e.email LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        query += " GROUP BY e.id ORDER BY e.created_at DESC"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [self._row_to_model(r) for r in rows]

    def get_by_id(self, employee_id: str) -> Optional[Employee]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT e.*, d.name as department_name,
                   COUNT(a.id) as assigned_count
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            LEFT JOIN assignments a ON a.employee_id = e.id AND a.is_active = 1
            WHERE e.id = ?
            GROUP BY e.id
        """, (employee_id,))
        row = c.fetchone()
        conn.close()
        return self._row_to_model(row) if row else None

    def create(self, data: dict) -> Employee:
        conn = get_connection()
        c = conn.cursor()
        emp_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        c.execute("""
            INSERT INTO employees
                (id, employee_id, full_name, department_id, position, email, phone, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            emp_id, data["employee_id"], data["full_name"],
            data.get("department_id"), data.get("position"),
            data.get("email"), data.get("phone"),
            data.get("status", "active"), data.get("notes"),
            now, now
        ))
        conn.commit()
        conn.close()
        return self.get_by_id(emp_id)

    def create_many(self, data_list: list[dict]) -> list[Employee]:
        if not data_list: return []
        conn = get_connection()
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        current_next_id = self.next_employee_id()
        if current_next_id.startswith("EMP-"):
            try:
                next_num = int(current_next_id.split("-")[1])
            except:
                next_num = 1
        else:
            next_num = 1
        
        insert_records = []
        created_emps = []
        for data in data_list:
            emp_id = str(uuid.uuid4())
            
            assigned_emp_id = data.get("employee_id")
            if not assigned_emp_id:
                assigned_emp_id = f"EMP-{next_num:03d}"
                next_num += 1
                
            insert_records.append((
                emp_id, assigned_emp_id, data["full_name"],
                data.get("department_id"), data.get("position"),
                data.get("email"), data.get("phone"),
                data.get("status", "active"), data.get("notes"),
                now, now
            ))
            created_emps.append(Employee(
                id=emp_id, employee_id=assigned_emp_id, full_name=data["full_name"],
                department_id=data.get("department_id"), position=data.get("position"),
                email=data.get("email"), phone=data.get("phone"),
                status=data.get("status", "active"), notes=data.get("notes"),
                created_at=now, updated_at=now
            ))
            
        c.executemany("""
            INSERT INTO employees
                (id, employee_id, full_name, department_id, position, email, phone, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, insert_records)
        conn.commit()
        conn.close()
        return created_emps

    def update(self, employee_id: str, data: dict) -> Optional[Employee]:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        c.execute("""
            UPDATE employees SET
                full_name = ?, department_id = ?, position = ?,
                email = ?, phone = ?, status = ?, notes = ?,
                updated_at = ?, sync_status = 'pending'
            WHERE id = ?
        """, (
            data["full_name"], data.get("department_id"),
            data.get("position"), data.get("email"),
            data.get("phone"), data.get("status", "active"),
            data.get("notes"), now, employee_id
        ))
        conn.commit()
        conn.close()
        return self.get_by_id(employee_id)

    def delete(self, employee_id: str) -> bool:
        conn = get_connection()
        c = conn.cursor()
        # Check for active assignments
        c.execute("SELECT COUNT(*) FROM assignments WHERE employee_id = ? AND is_active = 1", (employee_id,))
        if c.fetchone()[0] > 0:
            conn.close()
            raise ValueError("Cannot delete employee with active assignments.")
        
        # Delete historical assignments to satisfy foreign key constraints
        c.execute("DELETE FROM assignments WHERE employee_id = ?", (employee_id,))
        c.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        conn.commit()
        conn.close()
        return True

    def get_departments(self) -> list[dict]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM departments ORDER BY name")
        rows = [{"id": r["id"], "name": r["name"]} for r in c.fetchall()]
        conn.close()
        return rows

    def next_employee_id(self) -> str:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM employees")
        count = c.fetchone()[0]
        conn.close()
        return f"EMP-{str(count + 1).zfill(4)}"

    def _row_to_model(self, row: sqlite3.Row) -> Employee:
        d = dict(row)
        return Employee(
            id=d["id"],
            employee_id=d["employee_id"],
            full_name=d["full_name"],
            department_id=d.get("department_id"),
            position=d.get("position"),
            email=d.get("email"),
            phone=d.get("phone"),
            status=d.get("status", "active"),
            notes=d.get("notes"),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            sync_status=d.get("sync_status", "pending"),
            department_name=d.get("department_name"),
            assigned_count=d.get("assigned_count", 0),
        )

"""
InventoryPro - CSV Import/Export
Bulk import items or employees from CSV, and export any table to CSV.
"""
import csv
import uuid
import os
from datetime import datetime
from typing import Optional
from tkinter import filedialog, messagebox

from data.database import get_connection
from data.repositories.item_repo import ItemRepository
from data.repositories.employee_repo import EmployeeRepository
from data.repositories.audit_repo import AuditRepository
from barcodes.generator import generate_serial


# ── Export ────────────────────────────────────────────────────────────────────

def export_employees_csv(performed_by: str = "admin") -> Optional[str]:
    """Export all employees to CSV. Returns file path or None if cancelled."""
    path = filedialog.asksaveasfilename(
        title="Export Employees",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialfile=f"employees_{datetime.now().strftime('%Y%m%d')}.csv"
    )
    if not path:
        return None

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT e.employee_id, e.full_name, d.name as department,
               e.position, e.email, e.phone, e.status, e.notes, e.created_at
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        ORDER BY e.full_name
    """)
    rows = c.fetchall()
    conn.close()

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["employee_id", "full_name", "department",
                          "position", "email", "phone", "status", "notes", "created_at"])
        for row in rows:
            writer.writerow(list(row))

    print(f"[Export] Employees exported: {path}")
    return path


def export_items_csv(performed_by: str = "admin") -> Optional[str]:
    """Export all items to CSV."""
    path = filedialog.asksaveasfilename(
        title="Export Inventory",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialfile=f"inventory_{datetime.now().strftime('%Y%m%d')}.csv"
    )
    if not path:
        return None

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT i.serial_number, i.name, i.brand, i.model,
               cat.name as category, s.name as status,
               e.full_name as assigned_to,
               i.purchase_date, i.purchase_price, i.description, i.notes, i.created_at
        FROM items i
        LEFT JOIN categories cat ON i.category_id = cat.id
        LEFT JOIN statuses s ON i.status_id = s.id
        LEFT JOIN assignments a ON a.item_id = i.id AND a.is_active = 1
        LEFT JOIN employees e ON a.employee_id = e.id
        ORDER BY i.name
    """)
    rows = c.fetchall()
    conn.close()

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["serial_number", "name", "brand", "model", "category",
                          "status", "assigned_to", "purchase_date",
                          "purchase_price", "description", "notes", "created_at"])
        for row in rows:
            writer.writerow(list(row))

    print(f"[Export] Items exported: {path}")
    return path


def export_assignments_csv() -> Optional[str]:
    """Export all assignment history to CSV."""
    path = filedialog.asksaveasfilename(
        title="Export Assignments",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        initialfile=f"assignments_{datetime.now().strftime('%Y%m%d')}.csv"
    )
    if not path:
        return None

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT i.serial_number, i.name as item_name,
               e.employee_id, e.full_name as employee_name,
               a.assigned_by, a.assigned_at, a.returned_at,
               CASE WHEN a.is_active=1 THEN 'Active' ELSE 'Returned' END as status,
               a.notes
        FROM assignments a
        JOIN items i ON a.item_id = i.id
        JOIN employees e ON a.employee_id = e.id
        ORDER BY a.assigned_at DESC
    """)
    rows = c.fetchall()
    conn.close()

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["serial_number", "item_name", "employee_id",
                          "employee_name", "assigned_by", "assigned_at",
                          "returned_at", "status", "notes"])
        for row in rows:
            writer.writerow(list(row))

    print(f"[Export] Assignments exported: {path}")
    return path


# ── Import ────────────────────────────────────────────────────────────────────

def import_items_csv(performed_by: str = "admin") -> dict:
    """
    Import items from CSV.
    Expected columns (required): name
    Optional: serial_number, brand, model, category, description, notes, purchase_date, purchase_price

    Returns: {"imported": int, "skipped": int, "errors": list[str]}
    """
    path = filedialog.askopenfilename(
        title="Import Items from CSV",
        filetypes=[("CSV files", "*.csv")]
    )
    if not path:
        return {"imported": 0, "skipped": 0, "errors": []}

    repo = ItemRepository()
    audit = AuditRepository()
    imported = 0
    skipped = 0
    errors = []

    # Get category map
    categories = repo.get_categories()
    cat_map = {c["name"].lower(): c["id"] for c in categories}

    # Get default status
    statuses = repo.get_statuses()
    default_status_id = next(
        (s["id"] for s in statuses if s["name"] == "available"), None
    )

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            try:
                name = (row.get("name") or row.get("Name") or "").strip()
                if not name:
                    errors.append(f"Row {i}: Missing item name — skipped.")
                    skipped += 1
                    continue

                serial = (row.get("serial_number") or row.get("Serial Number") or "").strip()
                if not serial:
                    serial = generate_serial()
                    serial_source = "generated"
                else:
                    serial_source = "manual"

                # Skip if serial already exists
                existing = repo.get_by_serial(serial)
                if existing:
                    errors.append(f"Row {i}: Serial '{serial}' already exists — skipped.")
                    skipped += 1
                    continue

                cat_name = (row.get("category") or row.get("Category") or "").strip().lower()
                cat_id = cat_map.get(cat_name)

                price_str = (row.get("purchase_price") or "").strip()
                price = None
                if price_str:
                    try:
                        price = float(price_str.replace("$", "").replace(",", ""))
                    except ValueError:
                        pass

                data = {
                    "serial_number":  serial,
                    "serial_source":  serial_source,
                    "name":           name,
                    "brand":          (row.get("brand") or row.get("Brand") or "").strip() or None,
                    "model":          (row.get("model") or row.get("Model") or "").strip() or None,
                    "category_id":    cat_id,
                    "description":    (row.get("description") or "").strip() or None,
                    "purchase_date":  (row.get("purchase_date") or "").strip() or None,
                    "purchase_price": price,
                    "status_id":      default_status_id,
                    "notes":          (row.get("notes") or "").strip() or None,
                }
                item = repo.create(data)
                audit.log("create", "item", item.id,
                          before=None, after=data, performed_by=performed_by)
                imported += 1

            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")
                skipped += 1

    return {"imported": imported, "skipped": skipped, "errors": errors}


def import_employees_csv(performed_by: str = "admin") -> dict:
    """
    Import employees from CSV.
    Required: full_name
    Optional: employee_id, department, position, email, phone, notes
    """
    path = filedialog.askopenfilename(
        title="Import Employees from CSV",
        filetypes=[("CSV files", "*.csv")]
    )
    if not path:
        return {"imported": 0, "skipped": 0, "errors": []}

    repo = EmployeeRepository()
    audit = AuditRepository()
    imported = 0
    skipped = 0
    errors = []

    depts = repo.get_departments()
    dept_map = {d["name"].lower(): d["id"] for d in depts}

    conn = get_connection()

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            try:
                full_name = (row.get("full_name") or row.get("Full Name") or "").strip()
                if not full_name:
                    errors.append(f"Row {i}: Missing full_name — skipped.")
                    skipped += 1
                    continue

                emp_id_raw = (row.get("employee_id") or row.get("Employee ID") or "").strip()
                if not emp_id_raw:
                    emp_id_raw = repo.next_employee_id()

                # Skip duplicates
                c = conn.cursor()
                c.execute("SELECT id FROM employees WHERE employee_id=?", (emp_id_raw,))
                if c.fetchone():
                    errors.append(f"Row {i}: Employee ID '{emp_id_raw}' already exists — skipped.")
                    skipped += 1
                    continue

                dept_name = (row.get("department") or row.get("Department") or "").strip().lower()
                dept_id = dept_map.get(dept_name)

                data = {
                    "employee_id":   emp_id_raw,
                    "full_name":     full_name,
                    "department_id": dept_id,
                    "position":      (row.get("position") or "").strip() or None,
                    "email":         (row.get("email") or "").strip() or None,
                    "phone":         (row.get("phone") or "").strip() or None,
                    "notes":         (row.get("notes") or "").strip() or None,
                    "status":        "active",
                }
                emp = repo.create(data)
                audit.log("create", "employee", emp.id,
                          before=None, after=data, performed_by=performed_by)
                imported += 1

            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")
                skipped += 1

    conn.close()
    return {"imported": imported, "skipped": skipped, "errors": errors}

"""
InventoryPro - Sync Manager
Background thread that pushes/pulls data to Google Sheets.
"""
import threading
import json
from typing import Optional, Callable
from enum import Enum

from config import SYNC_INTERVAL_SECONDS, CREDENTIALS_PATH, MACHINE_ID
import os

# ── Module-level singleton ─────────────────────────────────
_instance: Optional["SyncManager"] = None

def get_instance() -> Optional["SyncManager"]:
    """Return the active SyncManager, or None if not started."""
    return _instance

def wake_sync():
    """Trigger an immediate sync cycle if the manager is running."""
    if _instance and _instance.state not in (SyncState.NOT_CONFIGURED,):
        _instance.force_sync()


class SyncState(Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    NOT_CONFIGURED = "not_configured"


class SyncManager:
    """
    Background sync manager. Runs as a daemon thread.
    Pushes pending changes to Google Sheets and pulls remote changes.
    """

    def __init__(self, on_state_change: Optional[Callable] = None,
                 on_conflict: Optional[Callable] = None):
        self._state = SyncState.NOT_CONFIGURED
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()  # signals early wake from wait
        self._on_state_change = on_state_change
        self._on_conflict = on_conflict
        self._client = None
        self._lock = threading.Lock()
        self._last_sync: Optional[str] = None

    @property
    def state(self) -> SyncState:
        return self._state

    def _set_state(self, state: SyncState):
        self._state = state
        if self._on_state_change:
            self._on_state_change(state)

    def start(self):
        """Start the background sync thread."""
        global _instance
        _instance = self  # register singleton
        if not os.path.exists(CREDENTIALS_PATH):
            self._set_state(SyncState.NOT_CONFIGURED)
            print("[Sync] No credentials found. Sync disabled.")
            return
        self._stop_event.clear()
        self._wake_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[Sync] Background sync started.")

    def stop(self):
        """Stop the background sync thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        """Main sync loop."""
        while not self._stop_event.is_set():
            self._sync_cycle()
            # Wait for interval or an early wake signal
            self._wake_event.wait(timeout=SYNC_INTERVAL_SECONDS)
            self._wake_event.clear()

    def _sync_cycle(self):
        """One full sync cycle: check online → push → pull."""
        if not self._check_online():
            self._set_state(SyncState.OFFLINE)
            return

        self._set_state(SyncState.SYNCING)
        try:
            client = self._get_client()
            if not client:
                self._set_state(SyncState.NOT_CONFIGURED)
                return
            self._push_pending(client)
            self._push_computer_scores(client)
            self._pull_remote(client)
            from datetime import datetime
            self._last_sync = datetime.utcnow().isoformat()
            self._set_state(SyncState.ONLINE)
        except Exception as e:
            print(f"[Sync] Cycle error: {e}")
            self._set_state(SyncState.OFFLINE)

    def _check_online(self) -> bool:
        """Quick connectivity check."""
        try:
            import socket
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
                ("8.8.8.8", 53)
            )
            return True
        except Exception:
            return False

    def _get_client(self):
        """Initialize or return cached gspread client."""
        if self._client:
            return self._client
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(
                CREDENTIALS_PATH, scopes=scopes
            )
            self._client = gspread.authorize(creds)
            return self._client
        except Exception as e:
            print(f"[Sync] Auth error: {e}")
            return None

    def _push_pending(self, client):
        """Push all pending queue items to Google Sheets."""
        from data.repositories.audit_repo import AuditRepository
        audit_repo = AuditRepository()
        pending = audit_repo.get_pending_sync()

        for item in pending:
            try:
                self._push_one(client, item)
                audit_repo.mark_synced(item["id"])
            except ConflictError as ce:
                if self._on_conflict:
                    self._on_conflict(item, ce.remote_data)
                audit_repo.mark_conflict(item["id"], ce.remote_data)
                self._set_state(SyncState.CONFLICT)
            except Exception as e:
                print(f"[Sync] Push error for {item['id']}: {e}")

    def _transform_payload(self, table: str, payload: dict) -> dict:
        if not payload:
            return payload
            
        data = payload.copy()
        from data.database import get_connection
        conn = get_connection()
        c = conn.cursor()
        
        try:
            if table == "employee":
                if "department_id" in data:
                    dept_id = data.pop("department_id")
                    if dept_id:
                        c.execute("SELECT name FROM departments WHERE id=?", (dept_id,))
                        row = c.fetchone()
                        data["department"] = row[0] if row else None
                    else:
                        data["department"] = None
            elif table == "item":
                if "category_id" in data:
                    cat_id = data.pop("category_id")
                    if cat_id:
                        c.execute("SELECT name FROM categories WHERE id=?", (cat_id,))
                        row = c.fetchone()
                        data["category"] = row[0] if row else None
                    else:
                        data["category"] = None
                if "status_id" in data:
                    stat_id = data.pop("status_id")
                    if stat_id:
                        c.execute("SELECT name FROM statuses WHERE id=?", (stat_id,))
                        row = c.fetchone()
                        data["status"] = row[0].replace("_", " ").title() if row else None
                    else:
                        data["status"] = None
            elif table == "assignment":
                if "item_id" in data:
                    item_id = data.pop("item_id")
                    if item_id:
                        c.execute("SELECT name, serial_number FROM items WHERE id=?", (item_id,))
                        row = c.fetchone()
                        data["item"] = f"{row[0]} ({row[1]})" if row else None
                    else:
                        data["item"] = None
                if "employee_id" in data:
                    emp_id = data.pop("employee_id")
                    if emp_id:
                        c.execute("SELECT full_name FROM employees WHERE id=?", (emp_id,))
                        row = c.fetchone()
                        data["employee"] = row[0] if row else None
                    else:
                        data["employee"] = None
        except Exception as e:
            print(f"[Sync] Error transforming payload: {e}")
        finally:
            conn.close()
            
        return data

    def _push_one(self, client, queue_item: dict):
        """Push a single change to the appropriate Sheets tab."""
        from config import SHEETS_CORE_NAME, SHEETS_AUDIT_NAME
        payload = json.loads(queue_item["payload"])
        table = queue_item["table_name"]
        action = queue_item["action_type"]
        record_id = queue_item["record_id"]

        # Get or open the spreadsheet
        try:
            sh = client.open(SHEETS_CORE_NAME)
        except Exception:
            sh = client.create(SHEETS_CORE_NAME)

        sheet_map = {
            "employee": "Employees",
            "item": "Items",
            "assignment": "Assignments",
        }
        sheet_name = sheet_map.get(table, table.capitalize())

        try:
            ws = sh.worksheet(sheet_name)
        except Exception:
            ws = sh.add_worksheet(sheet_name, rows=1000, cols=30)
            # Add headers
            after_preview = self._transform_payload(table, payload.get("after"))
            if after_preview:
                headers = list(after_preview.keys())
                ws.append_row(["id"] + [h for h in headers if h != "id"])

        # Check for conflicts (remote row has different updated_at)
        if action in ("update", "status_change", "return"):
            remote_row = self._find_remote_row(ws, record_id)
            local_ts = (payload.get("after") or {}).get("updated_at", "")
            if remote_row:
                remote_ts = remote_row.get("updated_at", "")
                if remote_ts and remote_ts > queue_item["timestamp"] and remote_ts != local_ts:
                    raise ConflictError(remote_row)

        after = payload.get("after")
        if after:
            after = self._transform_payload(table, after)

        if action == "create" and after:
            self._upsert_row(ws, record_id, after)
        elif action in ("update", "status_change") and after:
            self._upsert_row(ws, record_id, after)
        elif action == "delete":
            self._delete_row(ws, record_id)
        elif action in ("assign", "return") and after:
            try:
                assign_ws = sh.worksheet("Assignments")
            except Exception:
                assign_ws = sh.add_worksheet("Assignments", rows=1000, cols=20)
                headers = list(after.keys())
                assign_ws.append_row(["id"] + [h for h in headers if h != "id"])
            self._upsert_row(assign_ws, record_id, after)

    def _push_computer_scores(self, client):
        """Dump the ordered list of computers to the 'Computers' sheet."""
        from data.repositories.specs_repo import SpecsRepository
        from config import SHEETS_CORE_NAME
        
        try:
            sh = client.open(SHEETS_CORE_NAME)
        except Exception:
            return  # No sheet yet

        repo = SpecsRepository()
        scored = repo.get_all_scored()
        
        try:
            ws = sh.worksheet("Computers")
        except Exception:
            ws = sh.add_worksheet("Computers", rows=1000, cols=15)
        
        # We will just clear it and rewrite it since it's a generated ranked view
        ws.clear()
        
        headers = [
            "Rank", "Score", "Tier", "Item Name", "Serial Number",
            "Brand", "Model", "CPU", "RAM (GB)", "Storage", "GPU",
            "Purchase Year", "Assigned To"
        ]
        
        rows = [headers]
        for idx, s in enumerate(scored, start=1):
            storage = f"{s.storage_gb}GB {s.storage_type}" if s.storage_gb else ""
            rows.append([
                idx,
                s.perf_score or 0,
                s.tier,
                getattr(s, "item_name", ""),
                getattr(s, "serial_number", ""),
                getattr(s, "item_brand", ""),
                getattr(s, "item_model", ""),
                f"{s.cpu or ''} ({s.cpu_cores or '?'}c/{s.cpu_ghz or '?'}GHz)".strip(" ()"),
                s.ram_gb or "",
                storage,
                s.gpu or "",
                s.purchase_year or "",
                getattr(s, "assigned_to", "") or "Available"
            ])
            
        if len(rows) > 1:
            # update the entire range at once
            end_col = chr(ord('A') + len(headers) - 1)
            ws.update(values=rows, range_name=f"A1:{end_col}{len(rows)}")

    def _pull_remote(self, client):
        """Pull new rows from Google Sheets into local SQLite (bidirectional sync)."""
        from config import SHEETS_CORE_NAME
        try:
            sh = client.open(SHEETS_CORE_NAME)
        except Exception:
            return  # Sheet doesn't exist yet — nothing to pull

        self._pull_employees(sh)
        self._pull_items(sh)
        self._pull_assignments(sh)

    def _pull_employees(self, sh):
        """Import any employee rows from the sheet that aren't in local DB."""
        try:
            ws = sh.worksheet("Employees")
        except Exception:
            return

        try:
            records = ws.get_all_records()
        except Exception as e:
            print(f"[Sync] Failed to read Employees sheet: {e}")
            return

        from data.database import get_connection
        from data.repositories.employee_repo import EmployeeRepository
        from data.repositories.audit_repo import AuditRepository
        repo = EmployeeRepository()
        audit = AuditRepository()
        conn = get_connection()
        c = conn.cursor()

        # Build local lookup sets
        c.execute("SELECT id FROM employees")
        local_ids = {r[0] for r in c.fetchall()}
        c.execute("SELECT employee_id FROM employees")
        local_emp_ids = {r[0] for r in c.fetchall()}

        # Department name → id map
        depts = repo.get_departments()
        dept_map = {d["name"].lower(): d["id"] for d in depts}

        rows_to_update = []  # (row_index, new_uuid) for writing back to sheet

        for i, row in enumerate(records, start=2):  # row 1 = header
            uid = str(row.get("id", "")).strip()
            full_name = str(row.get("full_name", "")).strip()
            if not full_name:
                continue  # skip blank rows

            # Already known locally by UUID
            if uid and uid in local_ids:
                continue

            # Already known by employee_id code
            emp_id_raw = str(row.get("employee_id", "")).strip()
            if emp_id_raw and emp_id_raw in local_emp_ids:
                continue

            # New record from the sheet → import locally
            if not emp_id_raw:
                emp_id_raw = repo.next_employee_id()

            dept_name = str(row.get("department", "")).strip().lower()
            dept_id = dept_map.get(dept_name)

            data = {
                "employee_id":   emp_id_raw,
                "full_name":     full_name,
                "department_id": dept_id,
                "position":      str(row.get("position", "")).strip() or None,
                "email":         str(row.get("email", "")).strip() or None,
                "phone":         str(row.get("phone", "")).strip() or None,
                "notes":         str(row.get("notes", "")).strip() or None,
                "status":        str(row.get("status", "active")).strip() or "active",
            }
            try:
                emp = repo.create(data)
                # Don't call audit.log here to avoid triggering another push cycle
                print(f"[Sync] Pulled new employee from sheet: {full_name}")
                rows_to_update.append((i, emp.id))
                local_ids.add(emp.id)
                local_emp_ids.add(emp_id_raw)
            except Exception as e:
                print(f"[Sync] Failed to import employee row {i}: {e}")

        conn.close()

        # Write generated UUIDs back to the sheet so future syncs can track by id
        if rows_to_update:
            try:
                headers = ws.row_values(1)
                if "id" in headers:
                    id_col = headers.index("id") + 1  # 1-indexed
                    for row_num, new_id in rows_to_update:
                        ws.update_cell(row_num, id_col, new_id)
                        
                        # Log to audit so the sync engine pushes the fully-formatted row back to the sheet
                        from data.repositories.audit_repo import AuditRepository
                        AuditRepository().log("create", "employee", new_id, None, {"id": new_id}, "sync_pull")
            except Exception as e:
                print(f"[Sync] Failed to write back employee IDs to sheet: {e}")

    def _pull_items(self, sh):
        """Import any item rows from the sheet that aren't in local DB."""
        try:
            ws = sh.worksheet("Items")
        except Exception:
            return

        try:
            records = ws.get_all_records()
        except Exception as e:
            print(f"[Sync] Failed to read Items sheet: {e}")
            return

        from data.database import get_connection
        from data.repositories.item_repo import ItemRepository
        from barcodes.generator import generate_serial
        repo = ItemRepository()
        conn = get_connection()
        c = conn.cursor()

        # Build local lookup sets
        c.execute("SELECT id FROM items")
        local_ids = {r[0] for r in c.fetchall()}
        c.execute("SELECT serial_number FROM items")
        local_serials = {r[0] for r in c.fetchall()}

        # Category name → id map
        categories = repo.get_categories()
        cat_map = {cat["name"].lower(): cat["id"] for cat in categories}

        # Status name → id map (handle "Under Repair" → "under_repair" etc.)
        statuses = repo.get_statuses()
        stat_map = {}
        for s in statuses:
            stat_map[s["name"].lower()] = s["id"]
            stat_map[s["name"].replace("_", " ").lower()] = s["id"]

        default_status_id = next(
            (s["id"] for s in statuses if s["name"] == "available"), None
        )

        rows_to_update = []

        for i, row in enumerate(records, start=2):
            uid = str(row.get("id", "")).strip()
            name = str(row.get("name", "")).strip()
            if not name:
                continue

            # Already known locally by UUID
            if uid and uid in local_ids:
                continue

            # Already known by serial number
            serial = str(row.get("serial_number", "")).strip()
            if serial and serial in local_serials:
                continue

            if not serial:
                serial = generate_serial()

            cat_name = str(row.get("category", "")).strip().lower()
            cat_id = cat_map.get(cat_name)

            status_raw = str(row.get("status", "")).strip().lower()
            status_id = stat_map.get(status_raw, default_status_id)

            price_str = str(row.get("purchase_price", "")).strip()
            price = None
            if price_str:
                try:
                    price = float(price_str.replace("$", "").replace(",", ""))
                except ValueError:
                    pass

            data = {
                "serial_number":  serial,
                "serial_source":  "manual",
                "name":           name,
                "brand":          str(row.get("brand", "")).strip() or None,
                "model":          str(row.get("model", "")).strip() or None,
                "category_id":    cat_id,
                "description":    str(row.get("description", "")).strip() or None,
                "purchase_date":  str(row.get("purchase_date", "")).strip() or None,
                "purchase_price": price,
                "status_id":      status_id,
                "notes":          str(row.get("notes", "")).strip() or None,
            }
            try:
                item = repo.create(data)
                print(f"[Sync] Pulled new item from sheet: {name}")
                rows_to_update.append((i, item.id))
                local_ids.add(item.id)
                local_serials.add(serial)
            except Exception as e:
                print(f"[Sync] Failed to import item row {i}: {e}")

        conn.close()

        # Write generated UUIDs back to the sheet
        if rows_to_update:
            try:
                headers = ws.row_values(1)
                if "id" in headers:
                    id_col = headers.index("id") + 1
                    for row_num, new_id in rows_to_update:
                        ws.update_cell(row_num, id_col, new_id)
                        
                        from data.repositories.audit_repo import AuditRepository
                        AuditRepository().log("create", "item", new_id, None, {"id": new_id}, "sync_pull")
            except Exception as e:
                print(f"[Sync] Failed to write back item IDs to sheet: {e}")

    def _pull_assignments(self, sh):
        """Import any assignment rows from the sheet that aren't in local DB."""
        try:
            ws = sh.worksheet("Assignments")
        except Exception:
            return

        try:
            records = ws.get_all_records()
        except Exception as e:
            print(f"[Sync] Failed to read Assignments sheet: {e}")
            return

        from data.database import get_connection
        import uuid
        from datetime import datetime
        conn = get_connection()
        c = conn.cursor()

        # Build local UUID set for assignments
        c.execute("SELECT id FROM assignments")
        local_ids = {r[0] for r in c.fetchall()}

        # Build lookup maps: serial → item_id, employee_id code → employee uuid
        c.execute("SELECT id, serial_number, name FROM items")
        item_rows = c.fetchall()
        serial_to_item = {r[1]: r[0] for r in item_rows}
        name_to_item  = {r[2].lower(): r[0] for r in item_rows}

        c.execute("SELECT id, employee_id, full_name FROM employees")
        emp_rows = c.fetchall()
        empcode_to_id = {r[1]: r[0] for r in emp_rows}
        empname_to_id = {r[2].lower(): r[0] for r in emp_rows}

        rows_to_update = []

        for i, row in enumerate(records, start=2):
            uid = str(row.get("id", "")).strip()

            # Already known locally by UUID
            if uid and uid in local_ids:
                continue

            # Resolve item
            item_raw = str(row.get("item", "")).strip()
            # Sheet format is "Name (SERIAL)" — try to extract serial first
            item_id = None
            if "(" in item_raw and item_raw.endswith(")"):
                serial_part = item_raw.split("(")[-1].rstrip(")")
                item_id = serial_to_item.get(serial_part)
            if not item_id:
                # Fall back to matching by name prefix
                name_part = item_raw.split("(")[0].strip().lower()
                item_id = name_to_item.get(name_part)
            if not item_id:
                print(f"[Sync] Assignment row {i}: could not resolve item '{item_raw}' — skipped.")
                continue

            # Resolve employee
            emp_raw = str(row.get("employee", "")).strip()
            emp_id = empcode_to_id.get(emp_raw) or empname_to_id.get(emp_raw.lower())
            if not emp_id:
                print(f"[Sync] Assignment row {i}: could not resolve employee '{emp_raw}' — skipped.")
                continue

            # Skip if this item already has an active assignment to this employee
            c.execute(
                "SELECT id FROM assignments WHERE item_id=? AND employee_id=? AND is_active=1",
                (item_id, emp_id)
            )
            if c.fetchone():
                continue

            # Create the assignment
            new_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            assigned_by = str(row.get("assigned_by", "sheet-import")).strip() or "sheet-import"
            notes = str(row.get("notes", "")).strip() or None
            try:
                c.execute("""
                    INSERT INTO assignments
                        (id, item_id, employee_id, assigned_at, assigned_by, notes, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (new_id, item_id, emp_id, now, assigned_by, notes))
                # Mark item as assigned
                c.execute(
                    "UPDATE items SET status_id=("
                    "  SELECT id FROM statuses WHERE name='assigned' LIMIT 1"
                    "), updated_at=? WHERE id=?",
                    (now, item_id)
                )
                conn.commit()
                local_ids.add(new_id)
                rows_to_update.append((i, new_id))
                print(f"[Sync] Pulled new assignment from sheet: row {i}")
            except Exception as e:
                print(f"[Sync] Failed to import assignment row {i}: {e}")

        conn.close()

        # Write generated UUIDs back to the sheet
        if rows_to_update:
            try:
                headers = ws.row_values(1)
                if "id" in headers:
                    id_col = headers.index("id") + 1
                    for row_num, new_id in rows_to_update:
                        ws.update_cell(row_num, id_col, new_id)
                        
                        from data.repositories.audit_repo import AuditRepository
                        AuditRepository().log("create", "assignment", new_id, None, {"id": new_id}, "sync_pull")
            except Exception as e:
                print(f"[Sync] Failed to write back assignment IDs to sheet: {e}")

    def _find_remote_row(self, ws, record_id: str) -> Optional[dict]:
        try:
            records = ws.get_all_records()
            for r in records:
                if str(r.get("id")) == record_id:
                    return r
        except Exception:
            pass
        return None

    def _upsert_row(self, ws, record_id: str, data: dict):
        """Insert or update a row in the worksheet."""
        # Ensure 'id' is in the data payload so the spreadsheet has a primary key
        if "id" not in data:
            data["id"] = record_id

        try:
            records = ws.get_all_records()
            headers = ws.row_values(1)
            if not headers:
                headers = list(data.keys())
                # Enforce 'id' as the first column
                if "id" in headers:
                    headers.remove("id")
                    headers = ["id"] + headers
                ws.append_row(headers)

            # Find existing row
            for i, rec in enumerate(records):
                if str(rec.get("id")) == record_id:
                    row_num = i + 2  # 1-indexed + header
                    values = [str(data.get(h, "")) for h in headers]
                    ws.update(f"A{row_num}", [values])
                    return

            # Insert new row
            values = [str(data.get(h, "")) for h in headers]
            ws.append_row(values)
        except Exception as e:
            print(f"[Sync] Upsert error: {e}")

    def _delete_row(self, ws, record_id: str):
        try:
            cell = ws.find(record_id)
            if cell:
                ws.delete_rows(cell.row)
        except Exception as e:
            print(f"[Sync] Delete row error: {e}")

    def force_sync(self):
        """Trigger an immediate sync cycle (call from UI or after any save)."""
        self._wake_event.set()  # interrupt the sleep early
        threading.Thread(target=self._sync_cycle, daemon=True).start()


class ConflictError(Exception):
    def __init__(self, remote_data: dict):
        self.remote_data = remote_data
        super().__init__("Sync conflict detected")

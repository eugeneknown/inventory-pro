"""
InventoryPro - Assignment Panel
Assign items to employees, view and return assignments.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font
from data.repositories.assignment_repo import AssignmentRepository
from data.repositories.employee_repo import EmployeeRepository
from data.repositories.item_repo import ItemRepository
from data.repositories.audit_repo import AuditRepository
from ui.components import (SectionHeader, DataTable, ConfirmDialog,
                            Toast, EmptyState, FilterDropdown, SearchBar)
import threading


class AssignmentPanel(ctk.CTkFrame):

    def __init__(self, parent, user: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._user = user
        self._assign_repo = AssignmentRepository()
        self._emp_repo = EmployeeRepository()
        self._item_repo = ItemRepository()
        self._audit = AuditRepository()
        self._show_active_only = True
        self._search_query = ""
        self._fetch_id = 0
        self._build()
        self._load()

    def _build(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header_frame, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(left, text="Assignments", font=get_font(22, "bold"),
                     text_color=COLORS["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(left, text="Assign and return equipment to employees",
                     font=get_font(12), text_color=COLORS["text_secondary"]).pack(anchor="w")

        right = ctk.CTkFrame(header_frame, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            right, text="+ New Assignment",
            font=get_font(13, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=36,
            command=self._open_assign_dialog
        ).pack(side="right")

        # Toggle active/all
        toggle_frame = ctk.CTkFrame(self, fg_color="transparent")
        toggle_frame.pack(fill="x", pady=(0, 16))

        self._toggle_var = ctk.StringVar(value="Active")
        ctk.CTkSegmentedButton(
            toggle_frame,
            values=["Active", "All History"],
            variable=self._toggle_var,
            fg_color=COLORS["bg_surface"],
            selected_color=COLORS["primary"],
            unselected_color=COLORS["bg_surface"],
            font=get_font(12),
            command=self._on_toggle
        ).pack(side="left")

        from ui.components import SearchBar
        SearchBar(
            toggle_frame, placeholder="Search assignments...",
            on_change=self._on_search
        ).pack(side="right", fill="x", expand=False, padx=(16, 0))

        # Table
        self._table_container = ctk.CTkFrame(self, fg_color="transparent")
        self._table_container.pack(fill="both", expand=True)

    def _on_toggle(self, value: str):
        self._show_active_only = (value == "Active")
        self._load()

    def _on_search(self, q: str):
        self._search_query = q
        self._load()

    def _load(self):
        self._fetch_id += 1
        current_fetch = self._fetch_id

        for w in self._table_container.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self._table_container,
            text="Loading...",
            font=get_font(14),
            text_color=COLORS["text_secondary"]
        ).pack(expand=True)

        active_only = self._show_active_only
        search_query = self._search_query

        def fetch():
            assignments = self._assign_repo.get_all(
                active_only=active_only,
                search=search_query or None
            )
            self.after(0, lambda: self._render(assignments, current_fetch))

        threading.Thread(target=fetch, daemon=True).start()

    def _render(self, assignments, fetch_id=None):
        if fetch_id is not None and fetch_id != self._fetch_id:
            return

        for w in self._table_container.winfo_children():
            w.destroy()

        if not assignments:
            EmptyState(
                self._table_container,
                icon="🔗",
                title="No assignments found",
                subtitle="Assign an item to an employee to get started."
            ).pack(fill="both", expand=True)
            return

        columns = [
            ("item_id",        "Item ID",       100),
            ("item_serial",    "Serial Number", 130),
            ("item_name",      "Item",          150),
            ("employee_name",  "Employee",      150),
            ("employee_dept",  "Department",    120),
            ("assigned_by",    "Assigned By",   110),
            ("assigned_at",    "Date Assigned", 130),
            ("returned_at",    "Returned",      110),
        ]

        rows = []
        for a in assignments:
            assigned_ts = a.assigned_at[:10] if a.assigned_at else "—"
            returned_ts = a.returned_at[:10] if a.returned_at else "—"
            rows.append({
                "item_id":       a.item_item_id or "—",
                "item_serial":   a.item_serial or "—",
                "item_name":     a.item_name or "—",
                "employee_name": a.employee_name or "—",
                "employee_dept": a.employee_dept or "—",
                "assigned_by":   a.assigned_by,
                "assigned_at":   assigned_ts,
                "returned_at":   returned_ts,
                "status":        "assigned" if a.is_active else "available",
                "status_name":   "Active" if a.is_active else "Returned",
                "_id":           a.id,
                "_obj":          a,
            })

        action_list = []
        if self._show_active_only:
            action_list.append(("Return", COLORS["warning"], self._return_item))

        table = DataTable(
            self._table_container,
            columns=columns,
            actions=action_list
        )
        table.pack(fill="both", expand=True)
        table.load(rows)

    def _open_assign_dialog(self):
        AssignDialog(self, user=self._user, on_save=self._load)

    def _return_item(self, row: dict):
        a = row["_obj"]
        def do_return():
            before = {"item_id": a.item_id, "employee_id": a.employee_id, "is_active": True}
            self._assign_repo.return_item(a.item_id)
            after = {"item_id": a.item_id, "employee_id": a.employee_id, "is_active": False}
            self._audit.log(
                "return", "assignment", a.id,
                before=before, after=after,
                performed_by=self._user.get("display_name", "admin")
            )
            Toast.show(self, f"Item '{a.item_name}' returned from {a.employee_name}.", "success")
            self._load()

        ConfirmDialog(
            self,
            title="Return Item",
            message=f"Mark '{a.item_name}' as returned from {a.employee_name}?",
            on_confirm=do_return
        )


class AssignDialog(ctk.CTkToplevel):
    """Dialog to assign an available item to an employee."""

    def __init__(self, parent, user: dict, on_save=None):
        super().__init__(parent)
        self._user = user
        self._on_save = on_save
        self._emp_repo = EmployeeRepository()
        self._item_repo = ItemRepository()
        self._assign_repo = AssignmentRepository()
        self._audit = AuditRepository()

        self.title("New Assignment")
        self.geometry("500x500")
        self.minsize(440, 460)
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_card"])
        self.grab_set()
        self.lift()
        self._build()

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_surface"],
                               corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="New Assignment", font=get_font(16, "bold"),
                     text_color=COLORS["text_primary"]).pack(side="left", padx=24, pady=16)

        # ── Bottom buttons (packed BEFORE form so they stay visible) ──────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", padx=24, pady=(0, 20))

        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color=COLORS["bg_input"], hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"], font=get_font(12),
            corner_radius=8, height=42, command=self.destroy
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="✔  Assign Item",
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            font=get_font(13, "bold"), corner_radius=8, height=42,
            command=self._save
        ).pack(side="left", expand=True, fill="x")

        # ── Error label ───────────────────────────────────────────────────────
        self._error = ctk.CTkLabel(self, text="", font=get_font(11),
                                   text_color=COLORS["danger"])
        self._error.pack(side="bottom", pady=(0, 4))

        # ── Form (fills remaining space between header and buttons) ───────────
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24, pady=20)

        # Employee selection
        ctk.CTkLabel(form, text="Employee *", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        employees = self._emp_repo.get_all(status="active")
        self._emp_map = {f"{e.full_name} ({e.employee_id})": e.id for e in employees}
        emp_names = list(self._emp_map.keys()) or ["No employees"]

        self._emp_combo = ctk.CTkComboBox(
            form, values=emp_names,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            button_color=COLORS["border"], button_hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"], font=get_font(12),
            corner_radius=8, height=40, state="readonly"
        )
        if emp_names:
            self._emp_combo.set(emp_names[0])
        self._emp_combo.pack(fill="x", pady=(4, 16))

        from ui.components.ctk_scrollable_dropdown import CTkScrollableDropdown
        CTkScrollableDropdown(
            self._emp_combo, values=emp_names,
            command=self._emp_combo.set,
            autocomplete=True, justify="left",
            height=220,
            fg_color=COLORS["bg_card"],
            button_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            frame_border_color=COLORS["border"],
            scrollbar_button_color=COLORS["border"],
            font=get_font(12),
        )

        # Item selection (available only)
        ctk.CTkLabel(form, text="Item (Available only) *", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        avail_statuses = self._item_repo.get_statuses()
        avail_id = next(
            (s["id"] for s in avail_statuses if s["name"] == "available"), None
        )
        items = self._item_repo.get_all(status_id=avail_id)
        self._item_map = {f"{i.name} — {i.serial_number}": i.id for i in items}
        item_names = list(self._item_map.keys()) or ["No available items"]

        self._item_combo = ctk.CTkComboBox(
            form, values=item_names,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            button_color=COLORS["border"], button_hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"], font=get_font(12),
            corner_radius=8, height=40, state="readonly"
        )
        if item_names:
            self._item_combo.set(item_names[0])
        self._item_combo.pack(fill="x", pady=(4, 16))

        CTkScrollableDropdown(
            self._item_combo, values=item_names,
            command=self._item_combo.set,
            autocomplete=True, justify="left",
            height=220,
            fg_color=COLORS["bg_card"],
            button_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            frame_border_color=COLORS["border"],
            scrollbar_button_color=COLORS["border"],
            font=get_font(12),
        )

        # Notes
        ctk.CTkLabel(form, text="Notes (optional)", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        self._notes = ctk.CTkTextbox(
            form, height=70,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8
        )
        self._notes.pack(fill="x", pady=(4, 0))

    def _save(self):
        emp_key = self._emp_combo.get()
        item_key = self._item_combo.get()
        emp_id = self._emp_map.get(emp_key)
        item_id = self._item_map.get(item_key)

        if not emp_id or not item_id:
            self._error.configure(text="Please select both an employee and an item.")
            return

        notes = self._notes.get("1.0", "end").strip() or None
        assigned_by = self._user.get("display_name", "admin")

        try:
            assignment = self._assign_repo.assign(item_id, emp_id, assigned_by, notes)
            self._audit.log(
                "assign", "assignment", assignment.id,
                before=None,
                after={"item_id": item_id, "employee_id": emp_id,
                       "assigned_by": assigned_by, "is_active": True},
                performed_by=assigned_by
            )
            Toast.show(self.master, f"Item assigned to {emp_key.split('(')[0].strip()}.", "success")
            if self._on_save:
                self._on_save()
            self.after(10, self.destroy)
        except Exception as e:
            self._error.configure(text=str(e))

"""
InventoryPro - Employee List Page
Filterable employee table with add/edit/delete.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font
from data.repositories.employee_repo import EmployeeRepository
from data.repositories.audit_repo import AuditRepository
from ui.components import (SearchBar, FilterDropdown,
                            DataTable, ConfirmDialog, Toast, EmptyState)
from config import MACHINE_ID
import json
import os
import threading


class EmployeeListPage(ctk.CTkFrame):

    def __init__(self, parent, user: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._user = user
        self._repo = EmployeeRepository()
        self._audit = AuditRepository()
        self._search_query = ""
        self._dept_filter = "All"
        self._status_filter = "All"
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
        ctk.CTkLabel(left, text="Employees", font=get_font(22, "bold"),
                     text_color=COLORS["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(left, text="Manage your team members",
                     font=get_font(12), text_color=COLORS["text_secondary"]).pack(anchor="w")

        right = ctk.CTkFrame(header_frame, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            right, text="↑ Import CSV",
            font=get_font(12), fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"], text_color=COLORS["text_secondary"],
            corner_radius=8, height=36, command=self._import_csv
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right, text="↓ Export CSV",
            font=get_font(12), fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"], text_color=COLORS["text_secondary"],
            corner_radius=8, height=36, command=self._export_csv
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right, text="+ Add Employee",
            font=get_font(13, "bold"), fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            corner_radius=8, height=36, command=self._open_add_form
        ).pack(side="left")

        # Filter row
        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", pady=(0, 16))

        SearchBar(
            filters, placeholder="Search by name, ID, or email...",
            on_change=self._on_search
        ).pack(side="left", fill="x", expand=True, padx=(0, 16))

        self._dept_filter_widget = FilterDropdown(
            filters, label="Department:",
            options=["All"] + [d["name"] for d in self._repo.get_departments()],
            on_change=self._on_dept_filter
        )
        self._dept_filter_widget.pack(side="left", padx=(0, 12))

        FilterDropdown(
            filters, label="Status:",
            options=["All", "Active", "Inactive"],
            on_change=self._on_status_filter
        ).pack(side="left")

        # Table
        self._table_container = ctk.CTkFrame(self, fg_color="transparent")
        self._table_container.pack(fill="both", expand=True)

    def _load(self):
        # Clear and show a loading indicator immediately
        self._fetch_id += 1
        current_fetch = self._fetch_id

        for w in self._table_container.winfo_children():
            w.destroy()

        loading_label = ctk.CTkLabel(
            self._table_container,
            text="Loading...",
            font=get_font(14),
            text_color=COLORS["text_secondary"]
        )
        loading_label.pack(expand=True)

        dept_filter = self._dept_filter
        status_filter = self._status_filter
        search_query = self._search_query

        def fetch():
            dept_id = None
            if dept_filter != "All":
                depts = self._repo.get_departments()
                dept_id = next((d["id"] for d in depts if d["name"] == dept_filter), None)

            status = None if status_filter == "All" else status_filter.lower()
            employees = self._repo.get_all(
                department_id=dept_id,
                status=status,
                search=search_query or None
            )
            self.after(0, lambda: self._render(employees, current_fetch))

        threading.Thread(target=fetch, daemon=True).start()

    def _render(self, employees, fetch_id=None):
        if fetch_id is not None and fetch_id != self._fetch_id:
            return

        for w in self._table_container.winfo_children():
            w.destroy()

        if not employees:
            EmptyState(
                self._table_container,
                icon="👥",
                title="No employees found",
                subtitle="Add your first employee or adjust the filters."
            ).pack(fill="both", expand=True)
            return

        columns = [
            ("employee_id",     "Employee ID",  110),
            ("full_name",       "Full Name",    180),
            ("department_name", "Department",   130),
            ("position",        "Position",     140),
            ("email",           "Email",        180),
            ("status",          "Status",       100),
            ("assigned_count",  "Items",         60),
        ]

        rows = [
            {
                "employee_id":     e.employee_id,
                "full_name":       e.full_name,
                "department_name": e.department_name or "—",
                "position":        e.position or "—",
                "email":           e.email or "—",
                "status":          e.status,
                "status_name":     e.status,
                "assigned_count":  e.assigned_count,
                "_id":             e.id,
                "_obj":            e,
            }
            for e in employees
        ]

        table = DataTable(
            self._table_container,
            columns=columns,
            on_row_click=self._open_detail,
            actions=[
                ("Edit",   COLORS["primary"], self._edit_row),
                ("Delete", COLORS["danger"],  self._delete_row),
            ]
        )
        table.pack(fill="both", expand=True)
        table.load(rows)

    def _on_search(self, query: str):
        self._search_query = query
        self._load()

    def _on_dept_filter(self, value: str):
        self._dept_filter = value
        self._load()

    def _on_status_filter(self, value: str):
        self._status_filter = value
        self._load()

    def _open_add_form(self):
        from ui.employees.employee_form import EmployeeFormDialog
        EmployeeFormDialog(self, user=self._user, on_save=self._load)

    def _open_detail(self, row: dict):
        from ui.employees.employee_detail import EmployeeDetailDialog
        EmployeeDetailDialog(self, employee=row["_obj"],
                             current_user=self._user, on_change=self._load)

    def _edit_row(self, row: dict):
        from ui.employees.employee_form import EmployeeFormDialog
        EmployeeFormDialog(self, user=self._user, employee=row["_obj"], on_save=self._load)

    def _delete_row(self, row: dict):
        def do_delete():
            try:
                before = {"full_name": row["full_name"], "employee_id": row["employee_id"]}
                self._repo.delete(row["_id"])
                self._audit.log(
                    "delete", "employee", row["_id"],
                    before=before, after=None,
                    performed_by=self._user.get("display_name", "admin")
                )
                Toast.show(self, f"Employee '{row['full_name']}' deleted.", "success")
                self._load()
            except ValueError as e:
                Toast.show(self, str(e), "error")

        ConfirmDialog(
            self,
            title="Delete Employee",
            message=f"Are you sure you want to delete '{row['full_name']}'?\nThis action is logged.",
            on_confirm=do_delete,
            danger=True
        )

    def _export_csv(self):
        from utils.csv_io import export_employees_csv
        path = export_employees_csv(self._user.get("display_name", "admin"))
        if path:
            Toast.show(self, f"Exported to {os.path.basename(path)}", "success")
            import subprocess
            subprocess.Popen(["explorer", "/select,", path])

    def _import_csv(self):
        from utils.csv_io import import_employees_csv
        result = import_employees_csv(self._user.get("display_name", "admin"))
        if result["imported"] > 0 or result["skipped"] > 0:
            msg = f"Imported: {result['imported']}  Skipped: {result['skipped']}"
            kind = "success" if result["imported"] > 0 else "warning"
            Toast.show(self, msg, kind)
            if result["errors"]:
                print("[Import] Errors:\n" + "\n".join(result["errors"]))
            self._load()

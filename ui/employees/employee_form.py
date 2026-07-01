"""
InventoryPro - Employee Form Dialog
Add / Edit employee modal.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font
from data.repositories.employee_repo import EmployeeRepository
from data.repositories.audit_repo import AuditRepository
from data.models import Employee
from ui.components import Toast
from typing import Optional, Callable
import json


class EmployeeFormDialog(ctk.CTkToplevel):

    def __init__(self, parent, user: dict,
                 employee: Optional[Employee] = None,
                 on_save: Optional[Callable] = None, **kwargs):
        super().__init__(parent)
        self._user = user
        self._employee = employee
        self._on_save = on_save
        self._repo = EmployeeRepository()
        self._audit = AuditRepository()
        self._is_edit = employee is not None

        title = "Edit Employee" if self._is_edit else "Add Employee"
        self.title(title)
        self.geometry("480x560")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_card"])
        self.grab_set()
        self.lift()

        self._build(title)
        if self._is_edit:
            self._populate()

    def _build(self, title: str):
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_surface"], corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text=title,
            font=get_font(16, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left", padx=24, pady=16)

        # Scrollable form
        form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24, pady=16)

        depts = self._repo.get_departments()
        dept_options = ["(None)"] + [d["name"] for d in depts]
        self._dept_ids = {d["name"]: d["id"] for d in depts}

        self._fields = {}
        field_defs = [
            ("employee_id",  "Employee ID *",    False),
            ("full_name",    "Full Name *",       False),
            ("position",     "Position",          False),
            ("email",        "Email",             False),
            ("phone",        "Phone",             False),
            ("notes",        "Notes",             True),
        ]

        for key, label, multiline in field_defs:
            ctk.CTkLabel(form, text=label, font=get_font(11),
                         text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 2))
            if multiline:
                widget = ctk.CTkTextbox(
                    form, height=70,
                    fg_color=COLORS["bg_input"],
                    border_color=COLORS["border"],
                    text_color=COLORS["text_primary"],
                    font=get_font(12), corner_radius=8
                )
            else:
                widget = ctk.CTkEntry(
                    form,
                    fg_color=COLORS["bg_input"],
                    border_color=COLORS["border"],
                    text_color=COLORS["text_primary"],
                    font=get_font(13), corner_radius=8, height=38
                )
            widget.pack(fill="x")
            self._fields[key] = widget

        # Department dropdown
        ctk.CTkLabel(form, text="Department", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 2))
        self._dept_var = ctk.StringVar(value="(None)")
        ctk.CTkOptionMenu(
            form, values=dept_options, variable=self._dept_var,
            fg_color=COLORS["bg_input"], button_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12),
            corner_radius=8, height=38
        ).pack(fill="x")

        # Status
        ctk.CTkLabel(form, text="Status", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 2))
        self._status_var = ctk.StringVar(value="active")
        ctk.CTkOptionMenu(
            form, values=["active", "inactive"], variable=self._status_var,
            fg_color=COLORS["bg_input"], button_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12),
            corner_radius=8, height=38
        ).pack(fill="x")

        # Error
        self._error = ctk.CTkLabel(self, text="", font=get_font(11),
                                   text_color=COLORS["danger"])
        self._error.pack(pady=(0, 4))

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 20))

        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color=COLORS["bg_input"], hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"], font=get_font(12),
            corner_radius=8, height=40,
            command=self.destroy
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Save Employee",
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            font=get_font(12, "bold"), corner_radius=8, height=40,
            command=self._save
        ).pack(side="left", expand=True, fill="x")

        # Auto employee ID for new
        if not self._is_edit:
            self._fields["employee_id"].insert(0, self._repo.next_employee_id())

    def _populate(self):
        e = self._employee
        field_vals = {
            "employee_id": e.employee_id,
            "full_name":   e.full_name,
            "position":    e.position or "",
            "email":       e.email or "",
            "phone":       e.phone or "",
            "notes":       e.notes or "",
        }
        for key, val in field_vals.items():
            widget = self._fields[key]
            if isinstance(widget, ctk.CTkTextbox):
                widget.insert("1.0", val)
            else:
                widget.insert(0, val)

        if e.department_name:
            self._dept_var.set(e.department_name)
        self._status_var.set(e.status)

    def _save(self):
        def get_val(key):
            w = self._fields[key]
            if isinstance(w, ctk.CTkTextbox):
                return w.get("1.0", "end").strip()
            return w.get().strip()

        employee_id = get_val("employee_id")
        full_name = get_val("full_name")

        if not employee_id or not full_name:
            self._error.configure(text="Employee ID and Full Name are required.")
            return

        dept_name = self._dept_var.get()
        dept_id = self._dept_ids.get(dept_name)

        data = {
            "employee_id":   employee_id,
            "full_name":     full_name,
            "department_id": dept_id,
            "position":      get_val("position") or None,
            "email":         get_val("email") or None,
            "phone":         get_val("phone") or None,
            "notes":         get_val("notes") or None,
            "status":        self._status_var.get(),
        }

        try:
            if self._is_edit:
                before = {"full_name": self._employee.full_name, "email": self._employee.email}
                result = self._repo.update(self._employee.id, data)
                self._audit.log(
                    "update", "employee", self._employee.id,
                    before=before, after=data,
                    performed_by=self._user.get("display_name", "admin")
                )
                Toast.show(self.master, f"Employee '{full_name}' updated.", "success")
            else:
                result = self._repo.create(data)
                self._audit.log(
                    "create", "employee", result.id,
                    before=None, after=data,
                    performed_by=self._user.get("display_name", "admin")
                )
                Toast.show(self.master, f"Employee '{full_name}' added.", "success")

            if self._on_save:
                self._on_save()
            self.after(10, self.destroy)
        except Exception as e:
            self._error.configure(text=str(e))

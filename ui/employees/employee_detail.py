"""
InventoryPro - Employee Detail Dialog
Full profile view: info, active assignments, and full assignment history.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font
from data.repositories.employee_repo import EmployeeRepository
from data.repositories.assignment_repo import AssignmentRepository
from data.repositories.audit_repo import AuditRepository
from data.repositories.item_repo import ItemRepository
from data.models import Employee
from ui.components import StatusBadge, Toast, ConfirmDialog
from typing import Optional, Callable


class EmployeeDetailDialog(ctk.CTkToplevel):
    """Full employee profile with assigned items and history."""

    def __init__(self, parent, employee: Employee,
                 current_user: dict,
                 on_change: Optional[Callable] = None):
        super().__init__(parent)
        self._employee = employee
        self._user = current_user
        self._on_change = on_change
        self._emp_repo = EmployeeRepository()
        self._assign_repo = AssignmentRepository()
        self._item_repo = ItemRepository()
        self._audit = AuditRepository()

        self.title(f"Employee — {employee.full_name}")
        self.geometry("800x640")
        self.minsize(700, 500)
        self.configure(fg_color=COLORS["bg_app"])
        self.grab_set()
        self.lift()
        self._build()

    def _build(self):
        # Top profile bar
        profile_bar = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0, height=120)
        profile_bar.pack(fill="x")
        profile_bar.pack_propagate(False)

        inner = ctk.CTkFrame(profile_bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=28, pady=18)

        # Avatar circle
        avatar = ctk.CTkFrame(inner, fg_color=COLORS["primary_dim"],
                              width=68, height=68, corner_radius=34)
        avatar.pack(side="left", padx=(0, 20))
        avatar.pack_propagate(False)
        initials = "".join(n[0].upper() for n in self._employee.full_name.split()[:2])
        ctk.CTkLabel(avatar, text=initials, font=get_font(22, "bold"),
                     text_color=COLORS["primary"]).place(relx=0.5, rely=0.5, anchor="center")

        # Info
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            info, text=self._employee.full_name,
            font=get_font(20, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w")

        meta_row = ctk.CTkFrame(info, fg_color="transparent")
        meta_row.pack(anchor="w", pady=(4, 0))
        for text, color in [
            (self._employee.employee_id,                   COLORS["text_muted"]),
            ("•",                                          COLORS["border"]),
            (self._employee.department_name or "No Dept",  COLORS["text_secondary"]),
            ("•",                                          COLORS["border"]),
            (self._employee.position or "No Position",     COLORS["text_secondary"]),
        ]:
            ctk.CTkLabel(meta_row, text=text, font=get_font(12),
                         text_color=color).pack(side="left", padx=3)

        email_row = ctk.CTkFrame(info, fg_color="transparent")
        email_row.pack(anchor="w", pady=(4, 0))
        if self._employee.email:
            ctk.CTkLabel(email_row, text=self._employee.email,
                         font=get_font(11), text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 12))
        if self._employee.phone:
            ctk.CTkLabel(email_row, text=self._employee.phone,
                         font=get_font(11), text_color=COLORS["text_muted"]).pack(side="left")

        # Right side: status badge + buttons (vertical stack)
        right_col = ctk.CTkFrame(inner, fg_color="transparent")
        right_col.pack(side="right", anchor="n")

        # Status + count row
        top_row = ctk.CTkFrame(right_col, fg_color="transparent")
        top_row.pack(anchor="e")
        StatusBadge(top_row, self._employee.status).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            top_row,
            text=f"{self._employee.assigned_count} item(s)",
            font=get_font(11), text_color=COLORS["text_secondary"]
        ).pack(side="left")

        # Edit button — full width, clearly visible
        ctk.CTkButton(
            right_col, text="✏   Edit Profile",
            font=get_font(12, "bold"),
            fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=8, height=36, width=150,
            command=self._edit_employee
        ).pack(anchor="e", pady=(8, 0))

        # Tab view
        tabs = ctk.CTkTabview(
            self,
            fg_color=COLORS["bg_surface"],
            segmented_button_fg_color=COLORS["bg_card"],
            segmented_button_selected_color=COLORS["primary"],
            segmented_button_unselected_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
            corner_radius=0
        )
        tabs.pack(fill="both", expand=True)
        tabs.add("Current Items")
        tabs.add("Assignment History")
        tabs.add("Activity Log")

        self._build_current_items(tabs.tab("Current Items"))
        self._build_history(tabs.tab("Assignment History"))
        self._build_activity(tabs.tab("Activity Log"))

    def _build_current_items(self, parent):
        """Show currently assigned items with return button."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=12)

        # Quick assign button - Always visible at top right
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(
            btn_frame, text="+ Assign Item",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=36,
            command=self._assign_item
        ).pack(side="right")

        assignments = self._assign_repo.get_for_employee(self._employee.id, active_only=True)

        if not assignments:
            ctk.CTkLabel(
                frame, text="No items currently assigned.",
                font=get_font(13), text_color=COLORS["text_muted"]
            ).pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(frame, fg_color=COLORS["bg_card"], corner_radius=10)
        scroll.pack(fill="both", expand=True)

        for a in assignments:
            self._build_assignment_card(scroll, a, show_return=True)

    def _build_assignment_card(self, parent, assignment, show_return: bool = False):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_surface"], corner_radius=10)
        card.pack(fill="x", padx=10, pady=5)

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=14, pady=12)

        ctk.CTkLabel(
            left, text=assignment.item_name or "Unknown Item",
            font=get_font(13, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text=f"S/N: {assignment.item_serial or '—'}  •  "
                 f"Assigned: {(assignment.assigned_at or '')[:10]}  •  "
                 f"By: {assignment.assigned_by}",
            font=get_font(10), text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(2, 0))

        if show_return:
            def return_item(a=assignment):
                def do():
                    self._assign_repo.return_item(a.item_id, notes="Returned via employee profile")
                    self._audit.log(
                        "return", "assignment", a.id,
                        before={"item_id": a.item_id, "employee_id": a.employee_id, "is_active": True},
                        after={"item_id": a.item_id, "employee_id": a.employee_id, "is_active": False},
                        performed_by=self._user.get("display_name", "admin")
                    )
                    Toast.show(self, f"'{a.item_name}' returned.", "success")
                    if self._on_change:
                        self._on_change()
                    # Reload tabs
                    self._refresh()

                ConfirmDialog(
                    self, title="Return Item",
                    message=f"Mark '{a.item_name}' as returned from {self._employee.full_name}?",
                    on_confirm=do
                )

            ctk.CTkButton(
                card, text="Return",
                font=get_font(10, "bold"),
                fg_color=COLORS["warning_dim"], hover_color=COLORS["warning"],
                text_color=COLORS["warning"],
                corner_radius=6, height=28, width=70,
                command=return_item
            ).pack(side="right", padx=14, pady=12)

    def _build_history(self, parent):
        """All past assignments (returned)."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=12)

        assignments = self._assign_repo.get_for_employee(self._employee.id, active_only=False)
        past = [a for a in assignments if not a.is_active]

        if not past:
            ctk.CTkLabel(
                frame, text="No past assignment history.",
                font=get_font(13), text_color=COLORS["text_muted"]
            ).pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        for a in past:
            card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_surface"], corner_radius=8)
            card.pack(fill="x", pady=3)

            ctk.CTkFrame(card, fg_color=COLORS["text_muted"], width=3,
                         corner_radius=0).pack(side="left", fill="y")

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(side="left", fill="both", expand=True, padx=12, pady=10)

            ctk.CTkLabel(inner, text=a.item_name or "—",
                         font=get_font(12, "bold"),
                         text_color=COLORS["text_primary"]).pack(anchor="w")
            ctk.CTkLabel(
                inner,
                text=f"S/N: {a.item_serial or '—'}  |  "
                     f"{(a.assigned_at or '')[:10]} → {(a.returned_at or 'Not returned')[:10]}",
                font=get_font(10), text_color=COLORS["text_muted"]
            ).pack(anchor="w")

    def _build_activity(self, parent):
        """Audit log entries for this employee."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=12)

        entries = self._audit.get_all(entity_id=self._employee.id, limit=50)

        if not entries:
            ctk.CTkLabel(frame, text="No activity recorded.",
                         font=get_font(13), text_color=COLORS["text_muted"]).pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        action_colors = {
            "create": COLORS["success"], "update": COLORS["primary"],
            "delete": COLORS["danger"],  "assign": COLORS["info"],
            "return": COLORS["warning"], "status_change": COLORS["secondary"],
        }
        for entry in entries:
            row = ctk.CTkFrame(scroll, fg_color=COLORS["bg_surface"], corner_radius=8, height=40)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            color = action_colors.get(entry.action_type, COLORS["text_muted"])
            ctk.CTkLabel(row, text="●", font=get_font(10),
                         text_color=color).pack(side="left", padx=(12, 8))
            ctk.CTkLabel(
                row, text=entry.action_type.replace("_", " ").upper(),
                font=get_font(10, "bold"), text_color=color, width=100
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=entry.performed_by,
                font=get_font(10), text_color=COLORS["text_secondary"]
            ).pack(side="left", padx=8)
            ts = (entry.timestamp or "")[:16].replace("T", " ")
            ctk.CTkLabel(row, text=ts, font=get_font(10),
                         text_color=COLORS["text_muted"]).pack(side="right", padx=12)

    def _assign_item(self):
        """Quick-assign an item to this employee."""
        from ui.assignments.assignment_panel import AssignDialog

        class QuickAssignDialog(AssignDialog):
            def __init__(self_, parent_, user_, emp_id, on_save=None):
                super().__init__(parent_, user_, on_save)
                # Pre-select this employee
                for key, eid in self_._emp_map.items():
                    if eid == emp_id:
                        self_._emp_combo.set(key)
                        break

        QuickAssignDialog(self, self._user, self._employee.id,
                          on_save=lambda: (self._refresh(), self._on_change and self._on_change()))

    def _edit_employee(self):
        from ui.employees.employee_form import EmployeeFormDialog

        def _on_edit_saved():
            self._refresh()
            if self._on_change:
                self._on_change()

        EmployeeFormDialog(self, user=self._user, employee=self._employee,
                           on_save=_on_edit_saved)

    def _refresh(self):
        """Reload employee data and rebuild all content."""
        refreshed = self._emp_repo.get_by_id(self._employee.id)
        if refreshed:
            self._employee = refreshed
        for w in self.winfo_children():
            w.destroy()
        self._build()

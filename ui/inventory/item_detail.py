"""
InventoryPro - Item Detail Dialog
Full item profile: info, current assignment, history, and status change.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font
from data.repositories.item_repo import ItemRepository
from data.repositories.assignment_repo import AssignmentRepository
from data.repositories.audit_repo import AuditRepository
from data.models import Item
from ui.components import StatusBadge, Toast, ConfirmDialog
from typing import Optional, Callable


class ItemDetailDialog(ctk.CTkToplevel):

    def __init__(self, parent, item: Item,
                 current_user: dict,
                 on_change: Optional[Callable] = None):
        super().__init__(parent)
        self._item = item
        self._user = current_user
        self._on_change = on_change
        self._item_repo = ItemRepository()
        self._assign_repo = AssignmentRepository()
        self._audit = AuditRepository()

        self.title(f"Item — {item.name}")
        self.geometry("780x620")
        self.minsize(680, 480)
        self.configure(fg_color=COLORS["bg_app"])
        self.grab_set()
        self.lift()
        self._build()

    def _build(self):
        # Header bar
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0, height=100)
        header.pack(fill="x")
        header.pack_propagate(False)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=12)

        # Category icon / color block
        cat_color = COLORS["primary_dim"]
        icon_frame = ctk.CTkFrame(inner, fg_color=cat_color, width=56, height=56, corner_radius=10)
        icon_frame.pack(side="left", padx=(0, 18))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text="📦", font=ctk.CTkFont(size=26)).place(
            relx=0.5, rely=0.5, anchor="center"
        )

        # Name / serial / meta
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            info, text=self._item.name,
            font=get_font(20, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w")

        serial_row = ctk.CTkFrame(info, fg_color="transparent")
        serial_row.pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(
            serial_row, text="S/N:",
            font=get_font(11), text_color=COLORS["text_muted"]
        ).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            serial_row, text=self._item.serial_number,
            font=ctk.CTkFont(family="Fira Code", size=13, weight="bold"),
            text_color=COLORS["primary"]
        ).pack(side="left")

        meta = ctk.CTkFrame(info, fg_color="transparent")
        meta.pack(anchor="w", pady=(4, 0))
        for text, color in [
            (self._item.brand or "—",         COLORS["text_secondary"]),
            ("•",                              COLORS["border"]),
            (self._item.model or "—",          COLORS["text_secondary"]),
            ("•",                              COLORS["border"]),
            (self._item.category_name or "—", COLORS["text_muted"]),
        ]:
            ctk.CTkLabel(meta, text=text, font=get_font(11),
                         text_color=color).pack(side="left", padx=3)

        # Right side: status badge + action buttons
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right", anchor="n")

        # Status badge
        StatusBadge(right, self._item.status_name or "available").pack(anchor="e", pady=(0, 8))

        # Buttons row
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(anchor="e")

        ctk.CTkButton(
            btn_row, text="✏  Edit",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=36, width=90,
            command=self._edit_item
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="🖨  Label",
            font=get_font(12),
            fg_color=COLORS["bg_surface"], hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=8, height=36, width=90,
            command=self._print_label
        ).pack(side="left")

        # Tabs
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
        tabs.add("Details")
        tabs.add("Assignment")
        tabs.add("History")
        tabs.add("Change Status")

        self._build_details_tab(tabs.tab("Details"))
        self._build_assignment_tab(tabs.tab("Assignment"))
        self._build_history_tab(tabs.tab("History"))
        self._build_status_tab(tabs.tab("Change Status"))

    def _build_details_tab(self, parent):
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=12)

        fields = [
            ("Item Name",       self._item.name),
            ("Serial Number",   self._item.serial_number),
            ("Serial Source",   self._item.serial_source.title()),
            ("Brand",           self._item.brand or "—"),
            ("Model",           self._item.model or "—"),
            ("Category",        self._item.category_name or "—"),
            ("Status",          (self._item.status_name or "—").replace("_", " ").title()),
            ("Purchase Date",   self._item.purchase_date or "—"),
            ("Purchase Price",  f"${self._item.purchase_price:,.2f}" if self._item.purchase_price else "—"),
            ("Description",     self._item.description or "—"),
            ("Notes",           self._item.notes or "—"),
            ("Added",           (self._item.created_at or "")[:10]),
            ("Last Updated",    (self._item.updated_at or "")[:10]),
        ]

        for label, value in fields:
            row = ctk.CTkFrame(frame, fg_color=COLORS["bg_surface"], corner_radius=8)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row, text=label,
                font=get_font(11), text_color=COLORS["text_muted"],
                width=140, anchor="w"
            ).pack(side="left", padx=14, pady=10)
            ctk.CTkLabel(
                row, text=str(value),
                font=get_font(12),
                text_color=COLORS["text_primary"] if value != "—" else COLORS["text_muted"],
                anchor="w", wraplength=440
            ).pack(side="left", padx=(0, 14))

    def _build_assignment_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=12)

        active = self._assign_repo.get_active_for_item(self._item.id)

        if active:
            # Currently assigned card
            card = ctk.CTkFrame(frame, fg_color=COLORS["primary_dim"], corner_radius=12)
            card.pack(fill="x", pady=(0, 16))

            ctk.CTkLabel(
                card, text="Currently Assigned To",
                font=get_font(11), text_color=COLORS["secondary"]
            ).pack(anchor="w", padx=16, pady=(14, 2))
            ctk.CTkLabel(
                card, text=active.employee_name or "—",
                font=get_font(18, "bold"), text_color=COLORS["text_primary"]
            ).pack(anchor="w", padx=16)
            ctk.CTkLabel(
                card,
                text=f"Dept: {active.employee_dept or '—'}  •  Since: {(active.assigned_at or '')[:10]}  •  By: {active.assigned_by}",
                font=get_font(11), text_color=COLORS["text_secondary"]
            ).pack(anchor="w", padx=16, pady=(2, 14))

            def return_item():
                def do():
                    self._assign_repo.return_item(self._item.id, notes="Returned via item profile")
                    self._audit.log(
                        "return", "assignment", active.id,
                        before={"item_id": active.item_id, "employee_id": active.employee_id, "is_active": True},
                        after={"item_id": active.item_id, "employee_id": active.employee_id, "is_active": False},
                        performed_by=self._user.get("display_name", "admin")
                    )
                    Toast.show(self, "Item returned.", "success")
                    if self._on_change:
                        self._on_change()
                    self._refresh()

                ConfirmDialog(self, title="Return Item",
                              message=f"Mark this item as returned from {active.employee_name}?",
                              on_confirm=do)

            ctk.CTkButton(
                frame, text="↩  Return Item",
                font=get_font(12, "bold"),
                fg_color=COLORS["warning_dim"], hover_color=COLORS["warning"],
                text_color=COLORS["warning"],
                corner_radius=8, height=38,
                command=return_item
            ).pack(anchor="w")

        else:
            ctk.CTkLabel(
                frame, text="This item is not currently assigned.",
                font=get_font(13), text_color=COLORS["text_muted"]
            ).pack(pady=(20, 12))

            ctk.CTkButton(
                frame, text="+ Assign to Employee",
                font=get_font(12, "bold"),
                fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                corner_radius=8, height=38,
                command=self._assign_item
            ).pack(anchor="w")

    def _build_history_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=12)

        all_assignments = self._assign_repo.get_all(active_only=False,
                                                     employee_id=None)
        item_history = [a for a in all_assignments if a.item_id == self._item.id]

        if not item_history:
            ctk.CTkLabel(frame, text="No assignment history for this item.",
                         font=get_font(13), text_color=COLORS["text_muted"]).pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        for a in item_history:
            card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_surface"], corner_radius=8)
            card.pack(fill="x", pady=3)

            dot_color = COLORS["primary"] if a.is_active else COLORS["text_muted"]
            ctk.CTkFrame(card, fg_color=dot_color, width=3,
                         corner_radius=0).pack(side="left", fill="y")

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(side="left", fill="both", expand=True, padx=12, pady=10)

            ctk.CTkLabel(inner, text=a.employee_name or "—",
                         font=get_font(12, "bold"),
                         text_color=COLORS["text_primary"]).pack(anchor="w")
            period = f"{(a.assigned_at or '')[:10]} → {(a.returned_at or 'Present')[:10]}"
            ctk.CTkLabel(inner, text=f"{period}  •  By: {a.assigned_by}",
                         font=get_font(10),
                         text_color=COLORS["text_muted"]).pack(anchor="w")

            if a.is_active:
                ctk.CTkLabel(card, text="ACTIVE", font=get_font(9, "bold"),
                             text_color=COLORS["primary"]).pack(side="right", padx=14)

    def _build_status_tab(self, parent):
        """Let the user change the item status directly from the detail view."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            frame, text="Change Item Status",
            font=get_font(15, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            frame,
            text="This action will be recorded in the audit log and can be reverted.",
            font=get_font(11), text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(0, 20))

        statuses = self._item_repo.get_statuses()
        current_name = self._item.status_name or "available"

        # Current status display
        cur_row = ctk.CTkFrame(frame, fg_color=COLORS["bg_surface"], corner_radius=8)
        cur_row.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(cur_row, text="Current Status:", font=get_font(11),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=14, pady=12)
        StatusBadge(cur_row, current_name).pack(side="left", padx=8)

        # Status picker
        ctk.CTkLabel(frame, text="Change To:", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 8))

        status_map = {s["name"].replace("_", " ").title(): s["id"] for s in statuses}
        self._new_status_var = ctk.StringVar(value=current_name.replace("_", " ").title())

        ctk.CTkOptionMenu(
            frame,
            values=list(status_map.keys()),
            variable=self._new_status_var,
            fg_color=COLORS["bg_input"], button_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(13),
            corner_radius=8, height=42
        ).pack(fill="x", pady=(0, 16))

        # Notes
        ctk.CTkLabel(frame, text="Reason / Notes (optional)", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 4))
        self._status_notes = ctk.CTkTextbox(
            frame, height=70,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8
        )
        self._status_notes.pack(fill="x", pady=(0, 16))

        def apply_status():
            new_name_display = self._new_status_var.get()
            new_id = status_map.get(new_name_display)
            if not new_id:
                return
            before = {"status_id": self._item.status_id, "status": current_name}
            self._item_repo.update_status(self._item.id, new_id)
            self._audit.log(
                "status_change", "item", self._item.id,
                before=before,
                after={"status_id": new_id,
                       "status": new_name_display.lower().replace(" ", "_"),
                       "notes": self._status_notes.get("1.0", "end").strip()},
                performed_by=self._user.get("display_name", "admin")
            )
            Toast.show(self, f"Status changed to '{new_name_display}'.", "success")
            if self._on_change:
                self._on_change()
            self._refresh()

        ctk.CTkButton(
            frame, text="Apply Status Change",
            font=get_font(13, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=42,
            command=apply_status
        ).pack(anchor="w")

    def _assign_item(self):
        from ui.assignments.assignment_panel import AssignDialog
        AssignDialog(self, user=self._user,
                     on_save=lambda: (self._refresh(), self._on_change and self._on_change()))

    def _edit_item(self):
        from ui.inventory.item_form import ItemFormDialog

        def _on_edit_saved():
            self._refresh()
            if self._on_change:
                self._on_change()

        ItemFormDialog(self, user=self._user, item=self._item,
                       on_save=_on_edit_saved)

    def _print_label(self):
        from barcodes.label_printer import generate_label_pdf
        import subprocess
        label_items = [{
            "serial_number": self._item.serial_number,
            "name":          self._item.name,
            "brand":         self._item.brand,
            "model":         self._item.model,
        }]
        pdf_path = generate_label_pdf(label_items)
        Toast.show(self, f"Label saved: {pdf_path}", "success")
        subprocess.Popen(["start", "", pdf_path], shell=True)

    def _refresh(self):
        refreshed = self._item_repo.get_by_id(self._item.id)
        if refreshed:
            self._item = refreshed
        for w in self.winfo_children():
            w.destroy()
        self._build()

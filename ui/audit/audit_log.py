"""
InventoryPro - Audit Log Page
Full history of all actions with selective revert capability.
"""
import customtkinter as ctk
import json
from utils.theme import COLORS, get_font
from data.repositories.audit_repo import AuditRepository
from data.repositories.assignment_repo import AssignmentRepository
from data.repositories.item_repo import ItemRepository
from ui.components import SectionHeader, FilterDropdown, ConfirmDialog, Toast


class AuditLogPage(ctk.CTkFrame):

    def __init__(self, parent, user: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._user = user
        self._audit = AuditRepository()
        self._assign_repo = AssignmentRepository()
        self._item_repo = ItemRepository()
        self._action_filter = "All"
        self._entity_filter = "All"
        self._build()
        self._load()

    def _build(self):
        # Header
        ctk.CTkLabel(
            self, text="Audit Log",
            font=get_font(22, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            self,
            text="Full history of all system actions. Revertible actions are highlighted.",
            font=get_font(12),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(0, 20))

        # Filters
        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", pady=(0, 16))

        FilterDropdown(
            filters, label="Action:",
            options=["All", "create", "update", "delete", "assign", "return", "status_change"],
            on_change=self._on_action_filter
        ).pack(side="left", padx=(0, 16))

        FilterDropdown(
            filters, label="Entity:",
            options=["All", "employee", "item", "assignment"],
            on_change=self._on_entity_filter
        ).pack(side="left", padx=(0, 16))

        ctk.CTkButton(
            filters, text="↻ Refresh",
            font=get_font(12),
            fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=8, height=36, width=90,
            command=self._load
        ).pack(side="right")

        # Legend
        legend = ctk.CTkFrame(self, fg_color=COLORS["bg_surface"], corner_radius=8)
        legend.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            legend,
            text="  ↩ Revertible  ●  Actions that can be undone: assign, return, status_change",
            font=get_font(10),
            text_color=COLORS["text_muted"]
        ).pack(side="left", padx=12, pady=8)

        # Table header
        self._header = self._build_table_header()
        self._header.pack(fill="x")

        # Scrollable rows
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["bg_surface"],
            corner_radius=12
        )
        self._scroll.pack(fill="both", expand=True, pady=(0, 0))

    def _build_table_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=8, height=38)
        header.pack_propagate(False)
        cols = [
            ("Timestamp",   160),
            ("Action",       90),
            ("Entity",       90),
            ("Performed By", 130),
            ("Machine",      150),
            ("Details",      230),
            ("",              80),
        ]
        for label, width in cols:
            ctk.CTkLabel(
                header, text=label.upper(),
                font=get_font(9, "bold"),
                text_color=COLORS["text_muted"],
                width=width, anchor="w"
            ).pack(side="left", padx=(12, 0))
        return header

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        action = None if self._action_filter == "All" else self._action_filter
        entity = None if self._entity_filter == "All" else self._entity_filter

        entries = self._audit.get_all(
            entity_type=entity,
            action_type=action,
            limit=200
        )

        if not entries:
            ctk.CTkLabel(
                self._scroll,
                text="No audit entries found.",
                font=get_font(13),
                text_color=COLORS["text_muted"]
            ).pack(pady=40)
            return

        action_colors = {
            "create":        COLORS["success"],
            "update":        COLORS["primary"],
            "delete":        COLORS["danger"],
            "assign":        COLORS["info"],
            "return":        COLORS["warning"],
            "status_change": COLORS["secondary"],
        }

        for i, entry in enumerate(entries):
            bg = COLORS["bg_surface"] if i % 2 == 0 else COLORS["bg_card"]
            row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=0, height=46)
            row.pack(fill="x")
            row.pack_propagate(False)

            # Revert indicator
            indicator_color = COLORS["cta"] if (entry.revertible and not entry.is_reverted) else "transparent"
            ctk.CTkFrame(row, fg_color=indicator_color, width=3, corner_radius=0).pack(side="left", fill="y")

            # Timestamp
            ts = entry.timestamp[:16].replace("T", " ") if entry.timestamp else "—"
            ctk.CTkLabel(
                row, text=ts,
                font=ctk.CTkFont(family="Fira Code", size=11),
                text_color=COLORS["text_muted"],
                width=160, anchor="w"
            ).pack(side="left", padx=(10, 0))

            # Action badge
            action_color = action_colors.get(entry.action_type, COLORS["text_muted"])
            ctk.CTkLabel(
                row,
                text=f"  {entry.action_type.upper()}  ",
                font=get_font(9, "bold"),
                text_color=action_color,
                fg_color=COLORS["bg_input"],
                corner_radius=6,
                width=88
            ).pack(side="left", padx=(8, 0), pady=10)

            # Entity
            ctk.CTkLabel(
                row, text=entry.entity_type,
                font=get_font(11),
                text_color=COLORS["text_secondary"],
                width=88, anchor="w"
            ).pack(side="left", padx=(10, 0))

            # Performed by
            ctk.CTkLabel(
                row, text=entry.performed_by,
                font=get_font(11),
                text_color=COLORS["text_primary"],
                width=128, anchor="w"
            ).pack(side="left", padx=(10, 0))

            # Machine
            machine = entry.machine_id[:20] + "…" if len(entry.machine_id) > 20 else entry.machine_id
            ctk.CTkLabel(
                row, text=machine,
                font=ctk.CTkFont(family="Fira Code", size=9),
                text_color=COLORS["text_muted"],
                width=148, anchor="w"
            ).pack(side="left", padx=(10, 0))

            # Details (before → after summary)
            detail = self._summarize(entry.action_type, entry.before_state, entry.after_state)
            ctk.CTkLabel(
                row, text=detail,
                font=get_font(10),
                text_color=COLORS["text_secondary"],
                width=228, anchor="w",
                wraplength=220
            ).pack(side="left", padx=(10, 0))

            # Revert button or status
            if entry.is_reverted:
                ctk.CTkLabel(
                    row, text="Reverted",
                    font=get_font(9),
                    text_color=COLORS["text_muted"],
                    width=78
                ).pack(side="left", padx=(10, 0))
            elif entry.revertible:
                ctk.CTkButton(
                    row, text="↩ Revert",
                    font=get_font(9, "bold"),
                    fg_color=COLORS["bg_input"],
                    hover_color=COLORS["warning_dim"],
                    text_color=COLORS["warning"],
                    corner_radius=6, height=26, width=76,
                    command=lambda e=entry: self._confirm_revert(e)
                ).pack(side="left", padx=(10, 0), pady=8)
            else:
                ctk.CTkLabel(row, text="", width=78).pack(side="left")

    def _summarize(self, action: str, before_str: str, after_str: str) -> str:
        """Create a short human-readable summary of what changed."""
        try:
            before = json.loads(before_str) if before_str else {}
            after = json.loads(after_str) if after_str else {}
        except Exception:
            return "—"

        if action == "create":
            return f"Created: {after.get('name', after.get('full_name', ''))}"
        elif action == "delete":
            return f"Deleted: {before.get('name', before.get('full_name', ''))}"
        elif action == "assign":
            return f"Assigned item to employee"
        elif action == "return":
            return f"Item returned"
        elif action == "status_change":
            old = before.get("status", "?")
            new = after.get("status", "?")
            return f"Status: {old} → {new}"
        elif action == "update":
            changed = [k for k in after if before.get(k) != after.get(k)]
            return f"Updated: {', '.join(changed[:3])}" if changed else "Updated"
        return "—"

    def _confirm_revert(self, entry):
        """Show confirmation before reverting."""
        detail = self._summarize(entry.action_type, entry.before_state, entry.after_state)
        ConfirmDialog(
            self,
            title="Revert Action",
            message=f"Revert this action?\n{entry.action_type.upper()} on {entry.entity_type}\n{detail}\n\nThis will restore the previous state.",
            on_confirm=lambda: self._do_revert(entry),
            danger=False
        )

    def _do_revert(self, entry):
        """Execute the revert for supported action types."""
        try:
            if entry.action_type == "assign":
                # Revert by returning the item
                before = json.loads(entry.before_state or "{}")
                after = json.loads(entry.after_state or "{}")
                item_id = after.get("item_id")
                if item_id:
                    self._assign_repo.return_item(item_id, notes="Reverted via audit log")
                    self._audit.mark_reverted(entry.id)
                    # Log the revert itself
                    self._audit.log(
                        "return", "assignment", item_id,
                        before=after, after={"reverted_from": entry.id},
                        performed_by=self._user.get("display_name", "admin")
                    )
                    Toast.show(self, "Assignment reverted successfully.", "success")

            elif entry.action_type == "return":
                # Revert by re-assigning
                after = json.loads(entry.after_state or "{}")
                before = json.loads(entry.before_state or "{}")
                item_id = before.get("item_id") or after.get("item_id")
                emp_id = before.get("employee_id") or after.get("employee_id")
                if item_id and emp_id:
                    assigned_by = self._user.get("display_name", "admin")
                    assignment = self._assign_repo.assign(
                        item_id, emp_id, assigned_by,
                        notes="Re-assigned via audit log revert"
                    )
                    self._audit.mark_reverted(entry.id)
                    self._audit.log(
                        "assign", "assignment", assignment.id,
                        before=None, after={"reverted_from": entry.id},
                        performed_by=assigned_by
                    )
                    Toast.show(self, "Return reverted — item re-assigned.", "success")

            elif entry.action_type == "status_change":
                # Restore previous status
                before = json.loads(entry.before_state or "{}")
                item_id = entry.entity_id
                old_status_id = before.get("status_id")
                if item_id and old_status_id:
                    self._item_repo.update_status(item_id, old_status_id)
                    self._audit.mark_reverted(entry.id)
                    self._audit.log(
                        "status_change", "item", item_id,
                        before=json.loads(entry.after_state or "{}"),
                        after=before,
                        performed_by=self._user.get("display_name", "admin")
                    )
                    Toast.show(self, "Status change reverted.", "success")

            self._load()

        except Exception as e:
            Toast.show(self, f"Revert failed: {e}", "error")

    def _on_action_filter(self, v): self._action_filter = v; self._load()
    def _on_entity_filter(self, v): self._entity_filter = v; self._load()

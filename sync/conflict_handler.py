"""
InventoryPro - Conflict Resolution Dialog
Shown when two machines edited the same record offline.
User picks: keep local, keep server, or view details.
"""
import customtkinter as ctk
import json
from utils.theme import COLORS, get_font
from typing import Callable, Optional


class ConflictDialog(ctk.CTkToplevel):
    """
    Shows a side-by-side comparison of a conflict between the local
    pending change and the remote (server) version.

    on_resolve(winner): called with "local" or "remote"
    """

    def __init__(self, parent,
                 queue_item: dict,
                 remote_data: dict,
                 on_resolve: Callable):
        super().__init__(parent)
        self._queue_item = queue_item
        self._remote_data = remote_data
        self._on_resolve = on_resolve

        self.title("⚠  Sync Conflict Detected")
        self.geometry("720x540")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_card"])
        self.grab_set()
        self.lift()
        self.attributes("-topmost", True)
        self._build()

    def _build(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["warning_dim"], corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⚠  Sync Conflict",
            font=get_font(17, "bold"),
            text_color=COLORS["warning"]
        ).pack(side="left", padx=20, pady=16)

        ts = self._queue_item.get("timestamp", "")[:16].replace("T", " ")
        ctk.CTkLabel(
            header, text=f"Conflicting change from  {ts}",
            font=get_font(11),
            text_color=COLORS["text_secondary"]
        ).pack(side="left")

        # Explanation
        info = ctk.CTkFrame(self, fg_color=COLORS["bg_surface"], corner_radius=0)
        info.pack(fill="x", padx=0)
        ctk.CTkLabel(
            info,
            text="This record was edited on two different machines while offline.\n"
                 "Choose which version to keep. The other version will be discarded.",
            font=get_font(11),
            text_color=COLORS["text_secondary"],
            justify="left"
        ).pack(padx=20, pady=10, anchor="w")

        # Side-by-side comparison
        compare = ctk.CTkFrame(self, fg_color="transparent")
        compare.pack(fill="both", expand=True, padx=16, pady=12)
        compare.columnconfigure(0, weight=1)
        compare.columnconfigure(1, weight=1)

        # Local version
        local_card = ctk.CTkFrame(compare, fg_color=COLORS["bg_surface"], corner_radius=10)
        local_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(
            local_card, text="THIS MACHINE (Local)",
            font=get_font(11, "bold"),
            text_color=COLORS["primary"]
        ).pack(anchor="w", padx=14, pady=(14, 6))

        local_payload = json.loads(self._queue_item.get("payload", "{}"))
        local_after = local_payload.get("after", {}) or {}
        self._render_fields(local_card, local_after, remote=self._remote_data)

        ctk.CTkButton(
            local_card, text="✓ Keep My Version",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=38,
            command=lambda: self._resolve("local")
        ).pack(fill="x", padx=14, pady=14)

        # Remote version
        remote_card = ctk.CTkFrame(compare, fg_color=COLORS["bg_surface"], corner_radius=10)
        remote_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(
            remote_card, text="SERVER (Remote)",
            font=get_font(11, "bold"),
            text_color=COLORS["success"]
        ).pack(anchor="w", padx=14, pady=(14, 6))

        self._render_fields(remote_card, self._remote_data, remote=local_after)

        ctk.CTkButton(
            remote_card, text="✓ Keep Server Version",
            font=get_font(12, "bold"),
            fg_color=COLORS["success"], hover_color="#16A34A",
            corner_radius=8, height=38,
            command=lambda: self._resolve("remote")
        ).pack(fill="x", padx=14, pady=14)

        # Skip button
        ctk.CTkButton(
            self, text="Skip For Now (decide later)",
            font=get_font(11),
            fg_color="transparent",
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_muted"],
            corner_radius=8, height=32,
            command=self.destroy
        ).pack(pady=(0, 12))

    def _render_fields(self, parent, data: dict, remote: dict):
        """Render key-value pairs, highlighting differences in orange."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=280)
        scroll.pack(fill="both", expand=True, padx=14)

        important_keys = ["name", "full_name", "status", "status_id",
                          "employee_id", "serial_number", "updated_at",
                          "assigned_by", "returned_at", "is_active"]

        shown = {k: v for k, v in data.items()
                 if k in important_keys or k not in ["id", "sync_status"]}

        for key, val in shown.items():
            is_different = str(remote.get(key, "")) != str(val)
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=key.replace("_", " ").title() + ":",
                font=get_font(10),
                text_color=COLORS["text_muted"],
                width=120, anchor="w"
            ).pack(side="left")

            value_color = COLORS["warning"] if is_different else COLORS["text_primary"]
            ctk.CTkLabel(
                row, text=str(val)[:40] if val else "—",
                font=get_font(10, "bold" if is_different else "normal"),
                text_color=value_color,
                anchor="w"
            ).pack(side="left")

    def _resolve(self, winner: str):
        self._on_resolve(winner)
        self.destroy()

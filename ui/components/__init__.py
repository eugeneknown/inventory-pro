"""
InventoryPro - Shared UI Components
Reusable widgets: StatusBadge, DataTable, ConfirmDialog, Toast, SearchBar.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font, get_status_color
from typing import Callable, Optional


# ── Status Badge ──────────────────────────────────────────────────────────────
class StatusBadge(ctk.CTkLabel):
    """Colored pill badge for item/employee statuses."""

    def __init__(self, parent, status: str, **kwargs):
        fg, bg = get_status_color(status)
        display = status.replace("_", " ").title()
        super().__init__(
            parent,
            text=f"  {display}  ",
            font=get_font(10, "bold"),
            text_color=fg,
            fg_color=bg,
            corner_radius=10,
            **kwargs
        )


# ── Section Header ────────────────────────────────────────────────────────────
class SectionHeader(ctk.CTkFrame):
    """Page header with title, subtitle, and optional action button."""

    def __init__(self, parent, title: str, subtitle: str = "",
                 action_text: str = "", action_cmd: Callable = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.columnconfigure(0, weight=1)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            left, text=title,
            font=get_font(22, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                left, text=subtitle,
                font=get_font(12),
                text_color=COLORS["text_secondary"]
            ).pack(anchor="w")

        if action_text and action_cmd:
            ctk.CTkButton(
                self,
                text=f"+ {action_text}",
                font=get_font(13, "bold"),
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                corner_radius=8,
                height=36,
                command=action_cmd
            ).grid(row=0, column=1, sticky="e", padx=(0, 0))


# ── Search Bar ────────────────────────────────────────────────────────────────
class SearchBar(ctk.CTkFrame):
    """Search input with icon placeholder."""

    def __init__(self, parent, placeholder: str = "Search...",
                 on_change: Callable = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_change = on_change
        self._var = ctk.StringVar()
        self._var.trace_add("write", self._on_write)

        self._entry = ctk.CTkEntry(
            self,
            textvariable=self._var,
            placeholder_text=f"🔍  {placeholder}",
            font=get_font(13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_muted"],
            corner_radius=8,
            height=38,
        )
        self._entry.pack(fill="x", expand=True)

    def _on_write(self, *_):
        if self._on_change:
            self._on_change(self._var.get())

    def get(self) -> str:
        return self._var.get()

    def clear(self):
        self._var.set("")


# ── Filter Dropdown ───────────────────────────────────────────────────────────
class FilterDropdown(ctk.CTkFrame):
    """Label + OptionMenu combo for filtering."""

    def __init__(self, parent, label: str, options: list[str],
                 on_change: Callable = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_change = on_change

        ctk.CTkLabel(
            self, text=label,
            font=get_font(11),
            text_color=COLORS["text_secondary"]
        ).pack(side="left", padx=(0, 6))

        self._var = ctk.StringVar(value=options[0] if options else "All")
        self._menu = ctk.CTkOptionMenu(
            self,
            values=options,
            variable=self._var,
            command=self._changed,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            font=get_font(12),
            corner_radius=8,
            width=140,
            height=36,
        )
        self._menu.pack(side="left")

    def _changed(self, value):
        if self._on_change:
            self._on_change(value)

    def get(self) -> str:
        return self._var.get()

    def set_options(self, options: list[str]):
        self._menu.configure(values=options)
        if options:
            self._var.set(options[0])


# ── Data Table ────────────────────────────────────────────────────────────────
class DataTable(ctk.CTkScrollableFrame):
    """
    Generic scrollable data table with configurable columns.
    columns: list of (key, label, width) tuples
    rows: list of dicts
    on_row_click: called with the row dict
    actions: list of (label, color, callback) for action buttons per row
    """

    HEADER_H = 40
    ROW_H = 46

    def __init__(self, parent, columns: list[tuple],
                 on_row_click: Callable = None,
                 actions: list[tuple] = None, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["bg_surface"],
            corner_radius=12,
            **kwargs
        )
        self._columns = columns
        self._on_row_click = on_row_click
        self._actions = actions or []
        self._rows: list[dict] = []
        self._draw_header()

    def _draw_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0, height=self.HEADER_H)
        header.pack(fill="x", padx=0, pady=(0, 1))
        header.pack_propagate(False)

        for col_key, col_label, col_w in self._columns:
            ctk.CTkLabel(
                header,
                text=col_label.upper(),
                font=get_font(10, "bold"),
                text_color=COLORS["text_muted"],
                width=col_w,
                anchor="w"
            ).pack(side="left", padx=(12, 0))

        if self._actions:
            ctk.CTkLabel(
                header,
                text="ACTIONS",
                font=get_font(10, "bold"),
                text_color=COLORS["text_muted"],
                width=120,
                anchor="w"
            ).pack(side="left", padx=(12, 0))

    def load(self, rows: list[dict]):
        """Clear and reload the table with new row data."""
        self._rows = rows
        # Remove existing row frames (skip header)
        for widget in self.winfo_children():
            if hasattr(widget, "_is_data_row"):
                widget.destroy()
        for i, row in enumerate(rows):
            self._draw_row(row, i)

    def _draw_row(self, row: dict, idx: int):
        bg = COLORS["bg_surface"] if idx % 2 == 0 else COLORS["bg_card"]
        frame = ctk.CTkFrame(self, fg_color=bg, corner_radius=0, height=self.ROW_H)
        frame._is_data_row = True
        frame.pack(fill="x", padx=0, pady=0)
        frame.pack_propagate(False)

        # Store bg for hover reset
        frame._bg = bg

        def _is_hoverable(w) -> bool:
            """Only propagate hover to transparent wrapper frames, not buttons or badges."""
            return isinstance(w, ctk.CTkFrame) and not isinstance(w, ctk.CTkButton)

        def on_enter(e, f=frame):
            f.configure(fg_color=COLORS["bg_hover"])
            for child in f.winfo_children():
                if _is_hoverable(child):
                    try:
                        child.configure(fg_color=COLORS["bg_hover"])
                    except Exception:
                        pass

        def on_leave(e, f=frame):
            f.configure(fg_color=f._bg)
            for child in f.winfo_children():
                if _is_hoverable(child):
                    try:
                        child.configure(fg_color=f._bg)
                    except Exception:
                        pass

        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)

        def _bind_click(widget, r=row):
            if self._on_row_click:
                widget.bind("<Button-1>", lambda e, _r=r: self._on_row_click(_r))
                widget.configure(cursor="hand2")

        _bind_click(frame)

        for col_key, col_label, col_w in self._columns:
            value = row.get(col_key, "")
            if col_key in ("status", "status_name"):
                cell = ctk.CTkFrame(frame, fg_color="transparent", width=col_w)
                cell.pack(side="left", padx=(12, 0))
                cell.pack_propagate(False)
                badge = StatusBadge(cell, str(value))
                badge.pack(anchor="w", pady=8)
                # Bind click on cell frame and badge
                _bind_click(cell)
                _bind_click(badge)
                cell.bind("<Enter>", on_enter)
                cell.bind("<Leave>", on_leave)
            else:
                lbl = ctk.CTkLabel(
                    frame,
                    text=str(value) if value is not None else "—",
                    font=get_font(12),
                    text_color=COLORS["text_primary"],
                    width=col_w,
                    anchor="w",
                    wraplength=col_w - 10
                )
                lbl.pack(side="left", padx=(12, 0))
                _bind_click(lbl)
                lbl.bind("<Enter>", on_enter)
                lbl.bind("<Leave>", on_leave)

        # Action buttons — NOT clickable for row navigation (they have their own command)
        for action_label, action_color, action_cb in self._actions:
            hover = COLORS["primary_hover"] if action_color == COLORS["primary"] else action_color
            ctk.CTkButton(
                frame,
                text=action_label,
                font=get_font(11, "bold"),
                fg_color=action_color,
                hover_color=hover,
                corner_radius=6,
                height=30,
                width=68,
                command=lambda r=row, cb=action_cb: cb(r)
            ).pack(side="left", padx=4, pady=8)


# ── Confirm Dialog ────────────────────────────────────────────────────────────
class ConfirmDialog(ctk.CTkToplevel):
    """Simple confirmation modal dialog."""

    def __init__(self, parent, title: str, message: str,
                 on_confirm: Callable, danger: bool = False):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_card"])
        self.grab_set()
        self.lift()

        ctk.CTkLabel(
            self, text=title,
            font=get_font(16, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            self, text=message,
            font=get_font(12),
            text_color=COLORS["text_secondary"],
            wraplength=360
        ).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"],
            font=get_font(12),
            width=100,
            command=self.destroy
        ).pack(side="left", padx=8)

        confirm_color = COLORS["danger"] if danger else COLORS["primary"]
        ctk.CTkButton(
            btn_frame, text="Confirm",
            fg_color=confirm_color,
            hover_color=COLORS["primary_hover"],
            font=get_font(12, "bold"),
            width=100,
            command=lambda: (on_confirm(), self.after(10, self.destroy))
        ).pack(side="left", padx=8)


# ── Toast Notification ────────────────────────────────────────────────────────
class Toast:
    """Non-blocking toast notification."""

    @staticmethod
    def show(parent, message: str, kind: str = "success", duration: int = 3000):
        colors_map = {
            "success": (COLORS["success"], COLORS["success_dim"]),
            "error":   (COLORS["danger"],  COLORS["danger_dim"]),
            "warning": (COLORS["warning"], COLORS["warning_dim"]),
            "info":    (COLORS["info"],    COLORS["bg_surface"]),
        }
        fg, bg = colors_map.get(kind, colors_map["info"])

        toast = ctk.CTkToplevel(parent)
        toast.overrideredirect(True)
        toast.configure(fg_color=bg)
        toast.attributes("-topmost", True)

        # Position bottom-right of parent
        px = parent.winfo_rootx() + parent.winfo_width() - 320
        py = parent.winfo_rooty() + parent.winfo_height() - 80
        toast.geometry(f"300x50+{px}+{py}")

        ctk.CTkLabel(
            toast, text=message,
            font=get_font(12),
            text_color=fg,
        ).pack(expand=True, fill="both", padx=16)

        toast.after(duration, toast.destroy)


# ── Empty State ───────────────────────────────────────────────────────────────
class EmptyState(ctk.CTkFrame):
    """Shown when a table has no data."""

    def __init__(self, parent, icon: str = "📦", title: str = "No items",
                 subtitle: str = "", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        ctk.CTkLabel(self, text=icon, font=ctk.CTkFont(size=48)).pack(pady=(40, 8))
        ctk.CTkLabel(self, text=title, font=get_font(16, "bold"),
                     text_color=COLORS["text_primary"]).pack()
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=get_font(12),
                         text_color=COLORS["text_secondary"]).pack(pady=(4, 0))

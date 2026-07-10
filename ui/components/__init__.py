"""
InventoryPro - Shared UI Components
Reusable widgets: StatusBadge, DataTable, ConfirmDialog, Toast, SearchBar.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font, get_status_color
from typing import Callable, Optional
import tkinter as tk
from tkinter import ttk


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
        try:
            self._var.trace_add("write", self._on_write)
        except Exception:
            pass

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
        
        # Bind to multiple events to ensure it fires across all OS/CTK versions
        self._entry.bind("<KeyRelease>", self._on_write)
        self._entry.bind("<Return>", self._on_write)
        if hasattr(self._entry, "_entry"):
            self._entry._entry.bind("<KeyRelease>", self._on_write)

    def _on_write(self, *_args, **_kwargs):
        if self._on_change:
            val = self._entry.get()
            self._on_change(val)

    def get(self) -> str:
        return self._var.get()

    def set(self, value: str):
        self._var.set(value)
        if self._on_change:
            self._on_change(value)

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
        self._menu = ctk.CTkComboBox(
            self,
            values=options,
            variable=self._var,
            command=self._changed,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
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
class DataTable(ctk.CTkFrame):
    """
    High-performance data table using ttk.Treeview.
    Renders hundreds of rows instantly. Click a row to select it,
    then use the action buttons that appear at the bottom.
    columns: list of (key, label, width) tuples
    rows: list of dicts
    on_row_click: called with the row dict when a row is selected
    actions: list of (label, color, callback) for action buttons per row
    """

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
        self._selected_row: Optional[dict] = None

        self._apply_style()
        self._build_tree()
        if self._actions:
            self._build_action_bar()

    def _apply_style(self):
        style = ttk.Style()
        try:
            style.theme_use("default")
        except Exception:
            pass

        bg      = COLORS.get("bg_surface", "#1e1e2e")
        bg_alt  = COLORS.get("bg_card",    "#252535")
        fg      = COLORS.get("text_primary","#e0e0e0")
        sel_bg  = COLORS.get("primary",    "#6c63ff")
        head_bg = COLORS.get("bg_card",    "#252535")
        head_fg = COLORS.get("text_muted", "#888888")

        style.configure(".",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            troughcolor=bg_alt,
            borderwidth=0
        )

        style.configure("IP.Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            rowheight=42,
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", 11),
        )
        style.configure("IP.Treeview.Heading",
            background=head_bg,
            foreground=head_fg,
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("IP.Treeview",
            background=[("selected", sel_bg)],
            foreground=[("selected", "#ffffff")],
        )
        style.map("IP.Treeview.Heading",
            background=[("active", head_bg)],
            relief=[("active", "flat")],
        )
        self._bg     = bg
        self._bg_alt = bg_alt

    def _build_tree(self):
        col_ids = [c[0] for c in self._columns]

        bg = COLORS.get("bg_surface", "#1e1e2e")
        wrapper = ctk.CTkFrame(self, fg_color=bg, corner_radius=0)
        wrapper.pack(fill="both", expand=True, padx=1, pady=(8, 1))

        self._tree = ttk.Treeview(
            wrapper,
            columns=col_ids,
            show="headings",
            style="IP.Treeview",
            selectmode="browse",
        )

        # Custom scrollbar matching dark theme
        vsb = ttk.Scrollbar(wrapper, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        for col_key, col_label, col_w in self._columns:
            self._tree.heading(col_key, text=col_label.upper(), anchor="w")
            self._tree.column(col_key, width=col_w, minwidth=col_w, anchor="w", stretch=True)

        fg = COLORS.get("text_primary", "#e0e0e0")
        self._tree.tag_configure("even", background=self._bg, foreground=fg)
        self._tree.tag_configure("odd",  background=self._bg_alt, foreground=fg)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", self._on_double_click)

    def _build_action_bar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent", height=50)
        bar.pack(fill="x", padx=12, pady=(4, 8))
        bar.pack_propagate(False)

        self._action_buttons: list[ctk.CTkButton] = []
        for action_label, action_color, action_cb in self._actions:
            hover = COLORS.get("primary_hover", action_color)
            btn = ctk.CTkButton(
                bar,
                text=action_label,
                font=get_font(11, "bold"),
                fg_color=action_color,
                hover_color=hover,
                corner_radius=6,
                height=34,
                width=88,
                state="disabled",
                command=lambda cb=action_cb: self._run_action(cb),
            )
            btn.pack(side="left", padx=(0, 8))
            self._action_buttons.append(btn)

        self._count_label = ctk.CTkLabel(
            bar, text="",
            font=get_font(11),
            text_color=COLORS.get("text_secondary", "#888")
        )
        self._count_label.pack(side="right")

    def _on_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            self._selected_row = None
            self._set_buttons("disabled")
            return

        idx = int(sel[0])
        if 0 <= idx < len(self._rows):
            self._selected_row = self._rows[idx]
            self._set_buttons("normal")

    def _on_double_click(self, _event=None):
        if self._selected_row and self._on_row_click:
            self._on_row_click(self._selected_row)

    def _set_buttons(self, state: str):
        for btn in getattr(self, "_action_buttons", []):
            btn.configure(state=state)

    def _run_action(self, cb: Callable):
        if self._selected_row is not None:
            cb(self._selected_row)

    def load(self, rows: list[dict]):
        """Load all rows at once — renders in milliseconds regardless of count."""
        self._rows = rows
        self._selected_row = None
        self._set_buttons("disabled")

        children = self._tree.get_children()
        if children:
            self._tree.delete(*children)

        for i, row in enumerate(rows):
            values = [str(row.get(c[0], "") or "—") for c in self._columns]
            tag = "even" if i % 2 == 0 else "odd"
            self._tree.insert("", "end", iid=str(i), values=values, tags=(tag,))

        if hasattr(self, "_count_label"):
            self._count_label.configure(text=f"{len(rows)} record(s)")


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
            corner_radius=8, width=120, height=36,
            command=self.destroy
        ).pack(side="left", padx=8)

        confirm_color = COLORS["danger"] if danger else COLORS["primary"]
        ctk.CTkButton(
            btn_frame, text="Confirm",
            fg_color=confirm_color,
            hover_color=COLORS.get("danger_hover", confirm_color),
            font=get_font(12, "bold"),
            corner_radius=8, width=120, height=36,
            command=lambda: (on_confirm(), self.destroy())
        ).pack(side="left", padx=8)


# ── Toast Notification ────────────────────────────────────────────────────────
class Toast:
    """Temporary floating notification."""

    @staticmethod
    def show(parent, message: str, kind: str = "info", duration: int = 3000):
        colors = {
            "success": ("#fff", COLORS.get("success", "#22c55e")),
            "error":   ("#fff", COLORS.get("danger",  "#ef4444")),
            "warning": ("#fff", COLORS.get("warning", "#f59e0b")),
            "info":    ("#fff", COLORS.get("primary", "#6c63ff")),
        }
        fg, bg = colors.get(kind, colors["info"])

        toast = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10)
        ctk.CTkLabel(
            toast, text=message,
            font=get_font(12, "bold"),
            text_color=fg,
        ).pack(padx=18, pady=10)

        toast.place(relx=0.5, rely=0.95, anchor="s")
        parent.after(duration, toast.destroy)


# ── Empty State ───────────────────────────────────────────────────────────────
class EmptyState(ctk.CTkFrame):
    """Centered empty state placeholder."""

    def __init__(self, parent, icon: str = "📭",
                 title: str = "Nothing here",
                 subtitle: str = "", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        ctk.CTkLabel(self, text=icon,   font=get_font(40)).pack(pady=(40, 8))
        ctk.CTkLabel(self, text=title,  font=get_font(16, "bold"),
                     text_color=COLORS["text_primary"]).pack()
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=get_font(12),
                         text_color=COLORS["text_secondary"],
                         wraplength=300).pack(pady=(4, 0))

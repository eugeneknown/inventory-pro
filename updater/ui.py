"""
InventoryPro - Update Banner UI
A non-intrusive banner shown at the top of the app when an update is available.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font
from typing import Callable


class UpdateBanner(ctk.CTkFrame):
    """
    A slim banner that appears at the top of the main window.
    Shows the new version and a single "Update & Restart" button.
    """

    def __init__(self, parent, new_version: str, on_update: Callable, **kwargs):
        super().__init__(
            parent,
            fg_color="#1A2A1A",
            corner_radius=0,
            height=44,
            **kwargs
        )
        self.pack_propagate(False)
        self._new_version = new_version
        self._on_update   = on_update
        self._build()

    def _build(self):
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16)

        ctk.CTkLabel(
            inner,
            text=f"✨  Update available — v{self._new_version} is ready.",
            font=get_font(12),
            text_color="#86EFAC"
        ).pack(side="left", pady=12)

        # Dismiss button
        ctk.CTkButton(
            inner, text="Later",
            font=get_font(10),
            fg_color="transparent",
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_muted"],
            corner_radius=6, height=28, width=60,
            command=self.destroy
        ).pack(side="right", padx=(4, 0), pady=8)

        # Update button
        self._update_btn = ctk.CTkButton(
            inner, text="Update & Restart",
            font=get_font(11, "bold"),
            fg_color="#16A34A",
            hover_color="#15803D",
            text_color="white",
            corner_radius=6, height=28,
            command=self._do_update
        )
        self._update_btn.pack(side="right", padx=(8, 4), pady=8)

        # Progress label (hidden until update starts)
        self._progress_label = ctk.CTkLabel(
            inner, text="",
            font=get_font(10),
            text_color="#86EFAC"
        )
        self._progress_label.pack(side="right", padx=12)

    def _do_update(self):
        self._update_btn.configure(state="disabled", text="Updating...")
        self._on_update(self._new_version, self._on_progress, self._on_done)

    def _on_progress(self, message: str, current: int, total: int):
        try:
            self._progress_label.configure(text=message)
        except Exception:
            pass

    def _on_done(self, success: bool, message: str):
        if success:
            try:
                self._progress_label.configure(text="Restarting...")
                self.after(800, self._restart)
            except Exception:
                self._restart()
        else:
            try:
                self._progress_label.configure(text=f"Failed: {message}")
                self._update_btn.configure(state="normal", text="Retry")
            except Exception:
                pass

    def _restart(self):
        from updater.core import restart_app
        restart_app()

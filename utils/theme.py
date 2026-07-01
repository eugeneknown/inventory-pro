"""
InventoryPro - Theme (Dark OLED Enterprise)
All color tokens, font config, and widget style helpers.
"""
import customtkinter as ctk

# ── Color Palette ─────────────────────────────────────────
COLORS = {
    # Backgrounds
    "bg_app":       "#0A0A0F",
    "bg_sidebar":   "#0F1117",
    "bg_surface":   "#161B27",
    "bg_card":      "#1C2333",
    "bg_input":     "#1E2538",
    "bg_hover":     "#242D42",
    "bg_selected":  "#1E3A5F",

    # Brand / Primary
    "primary":      "#3B82F6",
    "primary_hover":"#2563EB",
    "primary_dim":  "#1D3461",
    "secondary":    "#60A5FA",

    # Status / Accent
    "success":      "#22C55E",
    "success_dim":  "#14532D",
    "warning":      "#F59E0B",
    "warning_dim":  "#451A03",
    "danger":       "#EF4444",
    "danger_dim":   "#450A0A",
    "cta":          "#F97316",
    "cta_hover":    "#EA6C0A",
    "info":         "#06B6D4",

    # Text
    "text_primary": "#F1F5F9",
    "text_secondary":"#94A3B8",
    "text_muted":   "#64748B",
    "text_disabled":"#374151",

    # Borders
    "border":       "#1E293B",
    "border_focus": "#3B82F6",
    "border_light": "#2D3748",

    # Sync / Status bar
    "sync_online":  "#22C55E",
    "sync_offline": "#EF4444",
    "sync_syncing": "#F59E0B",
}

# ── Item Status Colors ────────────────────────────────────
STATUS_COLORS = {
    "available":    ("#22C55E", "#14532D"),
    "assigned":     ("#3B82F6", "#1D3461"),
    "under_repair": ("#F59E0B", "#451A03"),
    "retired":      ("#64748B", "#1E293B"),
    "disposed":     ("#64748B", "#1E293B"),
    "lost":         ("#EF4444", "#450A0A"),
    "missing":      ("#EF4444", "#450A0A"),
    "reserved":     ("#A855F7", "#3B0764"),
    "borrowed":     ("#06B6D4", "#083344"),
}

def get_status_color(status: str) -> tuple:
    """Returns (fg_color, bg_color) for a status badge."""
    key = status.lower().replace(" ", "_")
    return STATUS_COLORS.get(key, ("#94A3B8", "#1E293B"))


def apply_theme():
    """Apply the dark OLED theme globally to CustomTkinter."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def get_font(size: int = 13, weight: str = "normal", family: str = "body") -> ctk.CTkFont:
    """Return a CTkFont with the correct family.
    Uses Segoe UI (standard on all Windows 10/11) for body text
    and Cascadia Code (Windows Terminal font, widely available) for mono.
    Falls back gracefully if not installed.
    """
    font_family = "Cascadia Code" if family == "mono" else "Segoe UI"
    return ctk.CTkFont(family=font_family, size=size, weight=weight)

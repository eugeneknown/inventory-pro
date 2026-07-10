"""
InventoryPro - Main Application Window
Sidebar navigation + content frame switcher.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font
from sync.sync_manager import SyncManager, SyncState
from utils.barcode_listener import BarcodeListener


NAV_ITEMS = [
    ("dashboard",    "📊   Dashboard",    "Dashboard"),
    ("employees",    "👥   Employees",    "Employees"),
    ("inventory",    "📦   Inventory",    "Items"),
    ("assignments",  "🔗   Assignments",  "Assignments"),
    ("performance",  "📈   Performance",  "Performance"),
    ("audit",        "📋   Audit Log",    "Audit Log"),
    ("settings",     "⚙️   Settings",    "Settings"),
]


class AppWindow(ctk.CTk):

    def __init__(self, current_user: dict, sync_manager: SyncManager):
        super().__init__()
        self._user = current_user
        self._sync = sync_manager
        self._active_page = None
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._pages: dict = {}

        self.title("InventoryPro")
        self.geometry("1280x800")
        self.minsize(1100, 680)
        self.configure(fg_color=COLORS["bg_app"])

        self._build_layout()
        self._build_sidebar()
        self._build_status_bar()
        self._navigate("dashboard")

        # Listen for sync state changes
        self._sync._on_state_change = self._on_sync_state

        # Start global barcode scanner listener
        self._barcode_listener = BarcodeListener(self, on_scan=self._on_barcode_scan)
        self._barcode_listener.start()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_layout(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._sidebar = ctk.CTkFrame(
            self, fg_color=COLORS["bg_sidebar"],
            corner_radius=0, width=220
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)

        self._content = ctk.CTkFrame(self, fg_color=COLORS["bg_app"], corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)

        self._status_bar = ctk.CTkFrame(
            self, fg_color=COLORS["bg_surface"],
            corner_radius=0, height=30
        )
        self._status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        # App logo
        logo_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent", height=80)
        logo_frame.pack(fill="x", padx=20, pady=(20, 8))
        logo_frame.pack_propagate(False)

        ctk.CTkLabel(
            logo_frame, text="Inventory",
            font=ctk.CTkFont(family="Fira Code", size=18, weight="bold"),
            text_color=COLORS["primary"]
        ).pack(anchor="w")
        import config
        ctk.CTkLabel(
            logo_frame, text=f"PRO  v{config.APP_VERSION}",
            font=ctk.CTkFont(family="Fira Code", size=10),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w")

        # Divider
        ctk.CTkFrame(self._sidebar, fg_color=COLORS["border"], height=1).pack(fill="x", padx=16, pady=8)

        # User info
        user_frame = ctk.CTkFrame(self._sidebar, fg_color=COLORS["bg_surface"], corner_radius=10)
        user_frame.pack(fill="x", padx=12, pady=(0, 16))
        ctk.CTkLabel(
            user_frame,
            text=self._user.get("display_name", "Admin"),
            font=get_font(12, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(padx=12, pady=(10, 2), anchor="w")
        role = self._user.get("role", "admin").upper()
        ctk.CTkLabel(
            user_frame,
            text=role,
            font=get_font(10),
            text_color=COLORS["primary"]
        ).pack(padx=12, pady=(0, 10), anchor="w")

        # Nav items
        for page_id, label, _ in NAV_ITEMS:
            btn = ctk.CTkButton(
                self._sidebar,
                text=label,
                font=get_font(13),
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLORS["bg_hover"],
                text_color=COLORS["text_secondary"],
                command=lambda p=page_id: self._navigate(p)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_buttons[page_id] = btn

        # Logout at bottom
        ctk.CTkFrame(self._sidebar, fg_color=COLORS["border"], height=1).pack(
            fill="x", padx=16, pady=8, side="bottom"
        )
        ctk.CTkButton(
            self._sidebar,
            text="🚪  Sign Out",
            font=get_font(12),
            anchor="w",
            height=38,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLORS["danger_dim"],
            text_color=COLORS["text_muted"],
            command=self._logout
        ).pack(fill="x", padx=12, pady=(0, 16), side="bottom")

    # ── Status Bar ────────────────────────────────────────────────────────────
    def _build_status_bar(self):
        self._sync_dot = ctk.CTkLabel(
            self._status_bar, text="●",
            font=get_font(12),
            text_color=COLORS["sync_offline"]
        )
        self._sync_dot.pack(side="left", padx=(12, 4))

        self._sync_label = ctk.CTkLabel(
            self._status_bar, text="Offline — changes saved locally",
            font=get_font(10),
            text_color=COLORS["text_muted"]
        )
        self._sync_label.pack(side="left")

        ctk.CTkButton(
            self._status_bar,
            text="Sync Now",
            font=get_font(10),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=6, height=22, width=80,
            command=self._sync.force_sync
        ).pack(side="right", padx=12, pady=4)

        ctk.CTkLabel(
            self._status_bar,
            text=f"Machine: {__import__('config').MACHINE_ID[:20]}",
            font=get_font(9),
            text_color=COLORS["text_muted"]
        ).pack(side="right", padx=(0, 8))

    # ── Navigation ────────────────────────────────────────────────────────────
    def _navigate(self, page_id: str):
        # Reset previous active button
        if self._active_page and self._active_page in self._nav_buttons:
            self._nav_buttons[self._active_page].configure(
                fg_color="transparent",
                text_color=COLORS["text_secondary"]
            )

        # Set active
        if page_id in self._nav_buttons:
            self._nav_buttons[page_id].configure(
                fg_color=COLORS["primary_dim"],
                text_color=COLORS["primary"]
            )
        self._active_page = page_id

        # Clear content
        for w in self._content.winfo_children():
            w.destroy()

        # Load page and cache reference for external access (e.g. barcode scanner)
        page = self._get_page(page_id)
        self._pages[page_id] = page
        page.pack(fill="both", expand=True, padx=24, pady=20)

    def _get_page(self, page_id: str):
        """Lazy-load page views."""
        if page_id == "dashboard":
            from ui.dashboard import DashboardPage
            return DashboardPage(self._content, self._user)
        elif page_id == "employees":
            from ui.employees.employee_list import EmployeeListPage
            return EmployeeListPage(self._content, self._user)
        elif page_id == "inventory":
            from ui.inventory.item_list import ItemListPage
            return ItemListPage(self._content, self._user)
        elif page_id == "assignments":
            from ui.assignments.assignment_panel import AssignmentPanel
            return AssignmentPanel(self._content, self._user)
        elif page_id == "performance":
            from ui.performance.performance_page import PerformancePage
            return PerformancePage(self._content, self._user)
        elif page_id == "audit":
            from ui.audit.audit_log import AuditLogPage
            return AuditLogPage(self._content, self._user)
        elif page_id == "settings":
            from ui.settings.settings_page import SettingsPage
            return SettingsPage(self._content, self._user)
        else:
            return ctk.CTkLabel(self._content, text="Page not found")

    # ── Sync State ────────────────────────────────────────────────────────────
    def _on_sync_state(self, state: SyncState):
        state_map = {
            SyncState.ONLINE:         ("●", COLORS["sync_online"],  "Synced"),
            SyncState.OFFLINE:        ("●", COLORS["sync_offline"], "Offline — saved locally"),
            SyncState.SYNCING:        ("●", COLORS["sync_syncing"], "Syncing…"),
            SyncState.CONFLICT:       ("●", COLORS["warning"],      "Conflict — action needed"),
            SyncState.NOT_CONFIGURED: ("●", COLORS["text_muted"],   "Sync not configured"),
        }
        dot_char, dot_color, label_text = state_map.get(
            state, ("●", COLORS["text_muted"], str(state))
        )
        # Update from main thread — guard against window being destroyed on exit
        try:
            self.after(0, lambda: self._sync_dot.configure(text=dot_char, text_color=dot_color))
            self.after(0, lambda: self._sync_label.configure(text=label_text))
        except RuntimeError:
            pass

    def _logout(self):
        from data.database import get_connection
        conn = get_connection()
        conn.execute("DELETE FROM app_settings WHERE key = 'remember_user_id'")
        conn.commit()
        conn.close()

        from ui.login import LoginScreen
        # Recreate login overlay
        LoginScreen(self, on_login_success=self._on_relogin)

    def _on_relogin(self, user: dict):
        self._user = user
        self._navigate("dashboard")

    # ── Barcode Scanner Handler ───────────────────────────────────────────────
    def _on_barcode_scan(self, serial: str):
        """
        Called by BarcodeListener when a barcode scanner input is detected.
        1. If an ItemFormDialog is open → inject serial into its SN field.
        2. Else if serial exists in DB → navigate to Inventory and search it.
        3. Else → open Add Item dialog with SN pre-filled.
        """
        print(f"[Barcode] Scanned: {serial}")

        # 1. Check if an ItemFormDialog is currently open
        from ui.inventory.item_form import ItemFormDialog
        for widget in self.winfo_children():
            if isinstance(widget, ItemFormDialog):
                sn_field = widget._fields.get("serial_number")
                if sn_field:
                    sn_field.delete(0, "end")
                    sn_field.insert(0, serial)
                    widget.lift()
                    widget.focus_force()
                    from ui.components import Toast
                    Toast.show(self, f"Serial number filled: {serial}", "success")
                return

        # 2. Check the database
        from data.repositories.item_repo import ItemRepository
        repo = ItemRepository()
        item = repo.get_by_serial(serial)

        from ui.components import Toast

        if item:
            # Item found — navigate to inventory and search
            self._navigate("inventory")
            self.after(100, lambda: self._inject_inventory_search(serial))
        else:
            # Item not found — open Add Item form with SN pre-filled
            self._navigate("inventory")
            self.after(100, lambda: self._open_add_with_serial(serial))

    def _inject_inventory_search(self, serial: str):
        """Push a serial number into the active Inventory page's search bar."""
        page = self._pages.get("inventory")
        if page and hasattr(page, "scan_search"):
            page.scan_search(serial)

    def _open_add_with_serial(self, serial: str):
        """Open the Add Item dialog pre-filled with a serial number."""
        from ui.inventory.item_form import ItemFormDialog
        from ui.components import Toast
        Toast.show(self, f"New item — serial '{serial}' pre-filled.", "info")
        ItemFormDialog(
            self._content,
            user=self._user,
            prefill_serial=serial,
            on_save=lambda: self._pages.get("inventory") and self._pages["inventory"]._load()
        )

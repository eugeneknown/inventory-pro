"""
InventoryPro - Main Entry Point
Initializes the database, applies the theme, shows login, starts the app.
"""
import sys
import os

# Ensure the project root is always in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize directories
from config import DATA_DIR, LABELS_DIR, ASSETS_DIR
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LABELS_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Initialize database (creates tables + seeds defaults)
from data.database import init_db
init_db()

# ── Load app config from DB ──────────────────────────────────────────────────
from data.database import get_connection as _get_conn

def _load_setting(key: str) -> str:
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""

# ── Install Discord error reporter ───────────────────────────────────────────
from utils.error_reporter import configure as _cfg_reporter, install_global_handler
_cfg_reporter(
    webhook_url=_load_setting("discord_webhook_url"),
    version=open(os.path.join(os.path.dirname(__file__), "version.txt")).read().strip()
         if os.path.exists(os.path.join(os.path.dirname(__file__), "version.txt")) else "unknown"
)
install_global_handler()

# ── Configure auto-updater ───────────────────────────────────────────────────
from updater.core import set_config as _cfg_updater, cleanup_old_exe
_cfg_updater(
    github_repo=_load_setting("github_repo"),
    github_token=_load_setting("github_token"),
)
cleanup_old_exe()

# Apply theme
from utils.theme import apply_theme
apply_theme()

import customtkinter as ctk


def main():
    # Temporary root for login screen
    root = ctk.CTk()
    root.title("InventoryPro")
    root.geometry("1000x660")
    root.minsize(860, 580)
    root.configure(fg_color="#0A0A0F")

    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (1000 // 2)
    y = (root.winfo_screenheight() // 2) - (660 // 2)
    root.geometry(f"1000x660+{x}+{y}")

    from ui.login import LoginScreen
    from sync.sync_manager import SyncManager

    sync_manager = SyncManager()

    def on_login_success(user: dict):
        """Called when login succeeds — launch the full app window."""
        root.withdraw()  # hide the login root

        from ui.app_window import AppWindow
        app = AppWindow(current_user=user, sync_manager=sync_manager)

        # Fetch saved window geometry
        from data.database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT value FROM app_settings WHERE key = 'window_geometry'")
        row = c.fetchone()
        conn.close()

        saved_geometry = row[0] if row else None
        
        # Position and size the main window
        app.update_idletasks()
        if saved_geometry:
            app.geometry(saved_geometry)
        else:
            ax = (app.winfo_screenwidth() // 2) - (1280 // 2)
            ay = (app.winfo_screenheight() // 2) - (800 // 2)
            app.geometry(f"1280x800+{ax}+{ay}")

        # Start background sync
        sync_manager.start()

        # ── Check for updates silently in the background ──────────────────
        from updater.core import check_async, apply_update
        from updater.ui import UpdateBanner

        def _on_update_check(new_version):
            if new_version:
                # Schedule banner creation on the main thread
                app.after(0, lambda: _show_update_banner(new_version))

        def _show_update_banner(new_version):
            banner = UpdateBanner(
                app, new_version=new_version,
                on_update=apply_update
            )
            # Insert banner at the very top by shifting rows down
            app.rowconfigure(0, weight=0)  # new row for banner
            app.rowconfigure(1, weight=1)  # sidebar and content
            
            # Move existing grid children down by 1 row
            for child in app.winfo_children():
                info = child.grid_info()
                if info and "row" in info and child != banner:
                    child.grid(row=int(info["row"]) + 1)
                    
            banner.grid(row=0, column=0, columnspan=2, sticky="ew")

        check_async(_on_update_check)

        # ── Test Gemini Model ────────────────────────────────────────────────
        from utils.ai_autofill import test_gemini_model
        from ui.components import Toast
        import threading
        
        def _verify_gemini():
            is_valid, err_msg = test_gemini_model()
            if not is_valid:
                app.after(1000, lambda: Toast.show(
                    app, 
                    f"AI Warning: {err_msg}\nPlease update your model in Settings.", 
                    kind="warning", 
                    duration=10000
                ))
                
        threading.Thread(target=_verify_gemini, daemon=True).start()

        def on_close():
            # Save the current window geometry
            current_geom = app.geometry()
            conn = get_connection()
            conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('window_geometry', ?)", (current_geom,))
            conn.commit()
            conn.close()

            sync_manager.stop()
            app.destroy()
            root.destroy()

        app.protocol("WM_DELETE_WINDOW", on_close)
        app.mainloop()

    LoginScreen(root, on_login_success=on_login_success)
    root.mainloop()


if __name__ == "__main__":
    main()

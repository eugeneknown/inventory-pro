"""
InventoryPro - Discord Error Reporter
Catches all unhandled exceptions and sends them to a Discord channel via webhook.
"""
import sys
import os
import traceback
import threading
import platform
import requests
import json
from datetime import datetime
from config import DATA_DIR

LOCAL_LOG_FILE = os.path.join(DATA_DIR, "system_errors.log")

_WEBHOOK_URL = ""
APP_VERSION  = "unknown"


def configure(webhook_url: str, version: str = "unknown"):
    global _WEBHOOK_URL, APP_VERSION
    _WEBHOOK_URL = webhook_url.strip()
    APP_VERSION  = version.strip()


def _send_to_discord(title: str, description: str, color: int = 0xFF4444):
    """Fire-and-forget POST to the Discord webhook."""
    if not _WEBHOOK_URL:
        return
    payload = {
        "username": "InventoryPro Error Reporter",
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
        "embeds": [{
            "title": title,
            "description": description[:4000],  # Discord embed limit
            "color": color,
            "footer": {
                "text": f"InventoryPro v{APP_VERSION}  •  {platform.node()}  •  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }]
    }
    try:
        requests.post(_WEBHOOK_URL, json=payload, timeout=8)
    except Exception as e:
        print(f"[ErrorReporter] Failed to send to Discord: {e}")


def report_exception(exc_type, exc_value, exc_tb):
    """Format and send an exception to Discord."""
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    tb_text  = "".join(tb_lines)

    # Find the most relevant file/line (last frame that's in our app, not stdlib)
    location = "unknown location"
    for line in reversed(tb_lines):
        if "File" in line and "Inventory System" in line:
            location = line.strip()
            break

    title = f"❌ {exc_type.__name__}: {str(exc_value)[:100]}"
    description = (
        f"**Location:** `{location}`\n\n"
        f"```python\n{tb_text[-2000:]}\n```"
    )
    
    # ── Local File Logging ──
    try:
        os.makedirs(os.path.dirname(LOCAL_LOG_FILE), exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {exc_type.__name__}: {str(exc_value)}\nLocation: {location}\n{tb_text}\n" + ("-"*60) + "\n"
        with open(LOCAL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as log_e:
        print(f"[ErrorReporter] Failed to write local log: {log_e}")

    threading.Thread(
        target=_send_to_discord,
        args=(title, description),
        daemon=True
    ).start()


def report_message(title: str, message: str, color: int = 0xF59E0B):
    """Send a plain informational or warning message to Discord."""
    # ── Local File Logging ──
    try:
        os.makedirs(os.path.dirname(LOCAL_LOG_FILE), exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(LOCAL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] INFO: {title}\n{message}\n" + ("-"*60) + "\n")
    except Exception as log_e:
        print(f"[ErrorReporter] Failed to write local log: {log_e}")

    threading.Thread(
        target=_send_to_discord,
        args=(title, message, color),
        daemon=True
    ).start()


def install_global_handler():
    """
    Installs a global exception hook so ALL unhandled exceptions
    (including those in Tkinter callbacks) are sent to Discord.
    """
    original_excepthook = sys.excepthook

    def _global_handler(exc_type, exc_value, exc_tb):
        # Always print to console as normal
        original_excepthook(exc_type, exc_value, exc_tb)
        # Then silently send to Discord
        report_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _global_handler

    # Also patch Tkinter's internal exception handler
    try:
        import tkinter
        import customtkinter
        
        original_tk_report = getattr(tkinter.Tk, 'report_callback_exception', None)
        def _tk_handler(self, exc_type, exc_value, exc_tb):
            if original_tk_report:
                original_tk_report(self, exc_type, exc_value, exc_tb)
            report_exception(exc_type, exc_value, exc_tb)
            
        tkinter.Tk.report_callback_exception = _tk_handler
        customtkinter.CTk.report_callback_exception = _tk_handler
    except Exception:
        pass
        pass

    print("[ErrorReporter] Global exception handler installed.")

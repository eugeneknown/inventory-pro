"""
InventoryPro - Configuration
Central config for paths, constants, and app metadata.
"""
import os
import uuid
import platform

# ── App Metadata ──────────────────────────────────────────
APP_NAME = "InventoryPro"
APP_VERSION = "1.1"

import sys

# ── Paths ──────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # Running as a compiled EXE
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as a python script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data", "local_db")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LABELS_DIR = os.path.join(BASE_DIR, "labels")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "google_credentials.json")
DB_PATH = os.path.join(DATA_DIR, "inventorypro.db")

# ── Machine Identity ──────────────────────────────────────
MACHINE_ID_FILE = os.path.join(DATA_DIR, "machine_id.txt")

def get_machine_id() -> str:
    """Get or create a unique machine ID for sync tracking."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(MACHINE_ID_FILE):
        with open(MACHINE_ID_FILE, "r") as f:
            return f.read().strip()
    machine_id = f"{platform.node()}-{str(uuid.uuid4())[:8]}"
    with open(MACHINE_ID_FILE, "w") as f:
        f.write(machine_id)
    return machine_id

MACHINE_ID = get_machine_id()

# ── Google Sheets ─────────────────────────────────────────
if getattr(sys, 'frozen', False):
    SHEETS_CORE_NAME = "InventoryPro - Core Data"
    SHEETS_AUDIT_NAME = "InventoryPro - Audit Log"
else:
    SHEETS_CORE_NAME = "InventoryPro - Core Data - TESTING"
    SHEETS_AUDIT_NAME = "InventoryPro - Audit Log - TESTING"

SYNC_INTERVAL_SECONDS = 300  # 5 minutes — reduces API quota usage

# ── Serial Number ─────────────────────────────────────────
SERIAL_PREFIX = "INV"

# ── Barcode Lookup APIs ──────────────────────────────────
UPCITEMDB_URL = "https://api.upcitemdb.com/prod/trial/lookup"
OPEN_PRODUCT_URL = "https://world.openfoodfacts.org/api/v0/product/{}.json"

# ── UI ────────────────────────────────────────────────────
WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 700
SIDEBAR_WIDTH = 240
SIDEBAR_COLLAPSED_WIDTH = 64

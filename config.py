"""
InventoryPro - Configuration
Central config for paths, constants, and app metadata.
"""
import os
import uuid
import platform

# ── App Metadata ──────────────────────────────────────────
APP_NAME = "InventoryPro"
APP_VERSION = "1.0.0"

# ── Paths ──────────────────────────────────────────────────
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
SHEETS_CORE_NAME = "InventoryPro - Core Data"
SHEETS_AUDIT_NAME = "InventoryPro - Audit Log"
SYNC_INTERVAL_SECONDS = 30

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

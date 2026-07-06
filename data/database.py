"""
InventoryPro - Database Initialization & Migration
Creates and migrates the local SQLite database.
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH, DATA_DIR


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory and WAL mode."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize all tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()

    # ── Departments ───────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── Categories ────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── Statuses (Item lifecycle + custom) ────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS statuses (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            color_hex   TEXT NOT NULL DEFAULT '#94A3B8',
            is_default  INTEGER NOT NULL DEFAULT 0,
            is_system   INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── Employees ─────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id              TEXT PRIMARY KEY,
            employee_id     TEXT NOT NULL UNIQUE,
            full_name       TEXT NOT NULL,
            department_id   TEXT REFERENCES departments(id),
            position        TEXT,
            email           TEXT,
            phone           TEXT,
            status          TEXT NOT NULL DEFAULT 'active',
            notes           TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
            sync_status     TEXT NOT NULL DEFAULT 'pending'
        )
    """)

    # ── Items / Equipment ─────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id              TEXT PRIMARY KEY,
            item_id         TEXT UNIQUE,
            serial_number   TEXT,
            serial_source   TEXT NOT NULL DEFAULT 'manual',
            name            TEXT NOT NULL,
            brand           TEXT,
            model           TEXT,
            category_id     TEXT REFERENCES categories(id),
            description     TEXT,
            purchase_date   TEXT,
            purchase_price  REAL,
            status_id       TEXT REFERENCES statuses(id),
            image_path      TEXT,
            notes           TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
            sync_status     TEXT NOT NULL DEFAULT 'pending'
        )
    """)

    # ── Assignments ───────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id              TEXT PRIMARY KEY,
            item_id         TEXT NOT NULL REFERENCES items(id),
            employee_id     TEXT NOT NULL REFERENCES employees(id),
            assigned_at     TEXT NOT NULL DEFAULT (datetime('now')),
            returned_at     TEXT,
            assigned_by     TEXT NOT NULL,
            notes           TEXT,
            is_active       INTEGER NOT NULL DEFAULT 1,
            sync_status     TEXT NOT NULL DEFAULT 'pending'
        )
    """)

    # ── Audit Log ─────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id              TEXT PRIMARY KEY,
            action_type     TEXT NOT NULL,
            entity_type     TEXT NOT NULL,
            entity_id       TEXT NOT NULL,
            before_state    TEXT,
            after_state     TEXT,
            performed_by    TEXT NOT NULL DEFAULT 'system',
            machine_id      TEXT NOT NULL,
            timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
            is_reverted     INTEGER NOT NULL DEFAULT 0,
            revertible      INTEGER NOT NULL DEFAULT 0,
            sync_status     TEXT NOT NULL DEFAULT 'pending'
        )
    """)

    # ── Pending Sync Queue ────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS sync_queue (
            id              TEXT PRIMARY KEY,
            audit_id        TEXT REFERENCES audit_log(id),
            table_name      TEXT NOT NULL,
            record_id       TEXT NOT NULL,
            action_type     TEXT NOT NULL,
            payload         TEXT NOT NULL,
            machine_id      TEXT NOT NULL,
            timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
            sync_status     TEXT NOT NULL DEFAULT 'pending',
            conflict_data   TEXT,
            retry_count     INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ── User Sessions / Roles ─────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              TEXT PRIMARY KEY,
            username        TEXT NOT NULL UNIQUE,
            display_name    TEXT NOT NULL,
            role            TEXT NOT NULL DEFAULT 'manager',
            password_hash   TEXT NOT NULL,
            department_id   TEXT REFERENCES departments(id),
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── App Settings ──────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key     TEXT PRIMARY KEY,
            value   TEXT NOT NULL
        )
    """)

    # ── Computer Specs (only for Computer/Laptop/Desktop items) ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS computer_specs (
            id              TEXT PRIMARY KEY,
            item_id         TEXT NOT NULL UNIQUE REFERENCES items(id) ON DELETE CASCADE,
            cpu             TEXT,
            cpu_cores       INTEGER,
            cpu_ghz         REAL,
            ram_gb          INTEGER,
            storage_gb      INTEGER,
            storage_type    TEXT DEFAULT 'SSD',
            gpu             TEXT,
            purchase_year   INTEGER,
            perf_score      INTEGER,
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    _seed_defaults(conn)
    _migrate_item_id(conn)
    conn.close()
    print(f"[DB] Database initialized at: {DB_PATH}")


def _migrate_item_id(conn: sqlite3.Connection):
    """Add item_id column to items table if it doesn't exist."""
    c = conn.cursor()
    c.execute("PRAGMA table_info(items)")
    columns = [row[1] for row in c.fetchall()]
    if "item_id" not in columns:
        c.execute("ALTER TABLE items ADD COLUMN item_id TEXT")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_items_item_id ON items(item_id)")
        conn.commit()
        print("[DB] Migrated items table: added item_id column.")


def _seed_defaults(conn: sqlite3.Connection):
    """Insert default data if tables are empty."""
    import uuid
    c = conn.cursor()

    # Default departments
    default_departments = [
        "IT", "HR", "Finance", "Operations", "Marketing", "Management"
    ]
    for dept in default_departments:
        c.execute(
            "INSERT OR IGNORE INTO departments (id, name) VALUES (?, ?)",
            (str(uuid.uuid4()), dept)
        )

    # Default categories
    default_categories = [
        "Laptop", "Desktop", "Monitor", "Keyboard", "Mouse",
        "Phone", "Tablet", "Printer", "Scanner", "Network Equipment",
        "UPS / Power", "Headset", "Camera", "Other"
    ]
    for cat in default_categories:
        c.execute(
            "INSERT OR IGNORE INTO categories (id, name) VALUES (?, ?)",
            (str(uuid.uuid4()), cat)
        )

    # Default system statuses
    default_statuses = [
        ("available",    "#22C55E", 1, 1),
        ("assigned",     "#3B82F6", 0, 1),
        ("under_repair", "#F59E0B", 0, 1),
        ("retired",      "#64748B", 0, 1),
        ("disposed",     "#475569", 0, 1),
        ("lost",         "#EF4444", 0, 1),
        ("missing",      "#DC2626", 0, 1),
        ("reserved",     "#A855F7", 0, 1),
        ("borrowed",     "#06B6D4", 0, 1),
    ]
    for name, color, is_default, is_system in default_statuses:
        c.execute(
            """INSERT OR IGNORE INTO statuses (id, name, color_hex, is_default, is_system)
               VALUES (?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), name, color, is_default, is_system)
        )

    # Default admin user (password: admin123 — user should change)
    import hashlib
    default_pw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute(
        """INSERT OR IGNORE INTO users (id, username, display_name, role, password_hash)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), "admin", "Administrator", "admin", default_pw)
    )

    # App settings
    c.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('setup_complete', '0')")
    c.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('org_name', 'My Organization')")

    conn.commit()


if __name__ == "__main__":
    init_db()

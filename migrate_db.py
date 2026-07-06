import sqlite3

conn = sqlite3.connect('data/local_db/inventorypro.db')
c = conn.cursor()
c.execute('DROP TABLE IF EXISTS items')
c.execute('''
    CREATE TABLE items (
        id TEXT PRIMARY KEY,
        item_id TEXT UNIQUE,
        serial_number TEXT,
        serial_source TEXT NOT NULL DEFAULT 'manual',
        name TEXT NOT NULL,
        brand TEXT,
        model TEXT,
        category_id TEXT REFERENCES categories(id),
        description TEXT,
        purchase_date TEXT,
        purchase_price REAL,
        status_id TEXT REFERENCES statuses(id),
        image_path TEXT,
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        sync_status TEXT NOT NULL DEFAULT 'pending'
    )
''')
c.execute('''
    INSERT INTO items (
        id, item_id, serial_number, serial_source, name, brand, model, 
        category_id, description, purchase_date, purchase_price, status_id, 
        image_path, notes, created_at, updated_at, sync_status
    )
    SELECT 
        id, item_id, serial_number, serial_source, name, brand, model, 
        category_id, description, purchase_date, purchase_price, status_id, 
        image_path, notes, created_at, updated_at, sync_status
    FROM items_new
''')
c.execute('DROP TABLE items_new')
conn.commit()
conn.close()
print("Migration completed successfully.")

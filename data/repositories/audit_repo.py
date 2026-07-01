"""
InventoryPro - Audit Repository
Logs every action and supports selective revert.
"""
import uuid
import json
from datetime import datetime
from typing import Optional
import sqlite3

from data.database import get_connection
from data.models import AuditEntry
from config import MACHINE_ID

# Actions that can be reverted
REVERTIBLE_ACTIONS = {"assign", "return", "status_change"}


class AuditRepository:

    def log(self, action_type: str, entity_type: str, entity_id: str,
            before: Optional[dict], after: Optional[dict],
            performed_by: str = "system") -> AuditEntry:
        """Log an action to the audit table and add to sync queue."""
        conn = get_connection()
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        revertible = action_type in REVERTIBLE_ACTIONS
        conn.execute("""
            INSERT INTO audit_log
                (id, action_type, entity_type, entity_id, before_state, after_state,
                 performed_by, machine_id, timestamp, revertible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id, action_type, entity_type, entity_id,
            json.dumps(before) if before else None,
            json.dumps(after) if after else None,
            performed_by, MACHINE_ID, now, int(revertible)
        ))
        # Add to sync queue
        queue_id = str(uuid.uuid4())
        payload = {"action_type": action_type, "entity_type": entity_type,
                   "entity_id": entity_id, "before": before, "after": after}
        conn.execute("""
            INSERT INTO sync_queue
                (id, audit_id, table_name, record_id, action_type, payload, machine_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            queue_id, entry_id, entity_type, entity_id,
            action_type, json.dumps(payload), MACHINE_ID, now
        ))
        conn.commit()
        conn.close()

        # Wake the sync manager immediately so changes push to Google Sheets right away
        try:
            from sync.sync_manager import wake_sync
            wake_sync()
        except Exception:
            pass  # sync not configured — no-op

        return self.get_by_id(entry_id)

    def get_all(self, entity_type: Optional[str] = None,
                action_type: Optional[str] = None,
                entity_id: Optional[str] = None,
                limit: int = 200) -> list[AuditEntry]:
        conn = get_connection()
        c = conn.cursor()
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        query += f" ORDER BY timestamp DESC LIMIT {limit}"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [self._row_to_model(r) for r in rows]

    def get_by_id(self, entry_id: str) -> Optional[AuditEntry]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM audit_log WHERE id = ?", (entry_id,))
        row = c.fetchone()
        conn.close()
        return self._row_to_model(row) if row else None

    def mark_reverted(self, entry_id: str):
        conn = get_connection()
        conn.execute(
            "UPDATE audit_log SET is_reverted=1 WHERE id=?", (entry_id,)
        )
        conn.commit()
        conn.close()

    def get_pending_sync(self) -> list[dict]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM sync_queue
            WHERE sync_status = 'pending'
            ORDER BY timestamp ASC
        """)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def mark_synced(self, queue_id: str):
        conn = get_connection()
        conn.execute(
            "UPDATE sync_queue SET sync_status='synced' WHERE id=?", (queue_id,)
        )
        conn.commit()
        conn.close()

    def mark_conflict(self, queue_id: str, conflict_data: dict):
        conn = get_connection()
        conn.execute(
            "UPDATE sync_queue SET sync_status='conflict', conflict_data=? WHERE id=?",
            (json.dumps(conflict_data), queue_id)
        )
        conn.commit()
        conn.close()

    def get_conflicts(self) -> list[dict]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM sync_queue WHERE sync_status='conflict'")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def _row_to_model(self, row: sqlite3.Row) -> AuditEntry:
        d = dict(row)
        return AuditEntry(
            id=d["id"],
            action_type=d["action_type"],
            entity_type=d["entity_type"],
            entity_id=d["entity_id"],
            machine_id=d.get("machine_id", ""),
            performed_by=d.get("performed_by", "system"),
            before_state=d.get("before_state"),
            after_state=d.get("after_state"),
            timestamp=d.get("timestamp", ""),
            is_reverted=bool(d.get("is_reverted", 0)),
            revertible=bool(d.get("revertible", 0)),
            sync_status=d.get("sync_status", "pending"),
        )

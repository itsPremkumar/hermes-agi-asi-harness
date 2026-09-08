#!/usr/bin/env python3
"""
state_store.py — Transactional State Store with Snapshot & Rollback
Guarantees ACID compliance for cognitive state and mission progress.
"""

import time
import json
import sqlite3
import pathlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class StateSnapshot:
    snapshot_id: str
    timestamp: float
    description: str
    state_data: Dict[str, Any]

class TransactionalStateStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            self.db_path = ":memory:"
        else:
            p = pathlib.Path(db_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(p)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS state_kv (
                    key TEXT PRIMARY KEY,
                    value_json TEXT,
                    updated_at REAL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    description TEXT,
                    timestamp REAL,
                    data_json TEXT
                )
            """)

    def set(self, key: str, value: Any):
        """Sets a key with JSON serialization atomically."""
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO state_kv (key, value_json, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time())
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a key from the state store."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT value_json FROM state_kv WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return row[0]
        return default

    def get_all(self) -> Dict[str, Any]:
        """Returns all keys in the state store as a dictionary."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT key, value_json FROM state_kv")
        rows = cursor.fetchall()
        out = {}
        for k, v in rows:
            try:
                out[k] = json.loads(v)
            except Exception:
                out[k] = v
        return out

    def delete(self, key: str):
        with self._conn:
            self._conn.execute("DELETE FROM state_kv WHERE key = ?", (key,))

    def create_snapshot(self, description: str = "") -> str:
        """Creates a point-in-time snapshot of the entire state."""
        state = self.get_all()
        snapshot_id = f"snap_{int(time.time() * 1000)}"
        with self._conn:
            self._conn.execute(
                "INSERT INTO snapshots (snapshot_id, description, timestamp, data_json) VALUES (?, ?, ?, ?)",
                (snapshot_id, description, time.time(), json.dumps(state))
            )
        return snapshot_id

    def list_snapshots(self) -> List[Dict[str, Any]]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT snapshot_id, description, timestamp FROM snapshots ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        return [{"snapshot_id": r[0], "description": r[1], "timestamp": r[2]} for r in rows]

    def rollback_to_snapshot(self, snapshot_id: str) -> bool:
        """Rolls back the entire state to a saved snapshot."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT data_json FROM snapshots WHERE snapshot_id = ?", (snapshot_id,))
        row = cursor.fetchone()
        if not row:
            return False

        data = json.loads(row[0])
        with self._conn:
            self._conn.execute("DELETE FROM state_kv")
            for k, v in data.items():
                self._conn.execute(
                    "INSERT INTO state_kv (key, value_json, updated_at) VALUES (?, ?, ?)",
                    (k, json.dumps(v), time.time())
                )
        return True

    def close(self):
        self._conn.close()

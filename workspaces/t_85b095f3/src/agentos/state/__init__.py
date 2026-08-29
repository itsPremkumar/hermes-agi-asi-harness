"""Persistent state management using SQLite with WAL mode."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

# Type alias for sqlite3.Connection
sqliteConnection = sqlite3.Connection


class StateError(Exception):
    """Raised when state operations fail."""
    pass


@dataclass
class StateEntry:
    """A single state entry."""
    key: str
    value: Any
    tenant_id: str = "default"
    created_at: float = 0.0
    updated_at: float = 0.0
    version: int = 1


class StateManager:
    """Persistent state manager using SQLite with WAL mode."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn: sqliteConnection | None = None
        self._connect()
        self._init_schema()

    def _connect(self) -> None:
        """Establish database connection."""
        self._conn = sqliteConnection(self.db_path)
        self._conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        if self.db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def _init_schema(self) -> None:
        """Initialize database schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                value TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (key, tenant_id)
            );

            CREATE TABLE IF NOT EXISTS state_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                operation TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                timestamp REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_state_tenant
                ON state(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_state_log_key
                ON state_log(key, tenant_id);
        """)
        self._conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database transactions."""
        if self._conn is None:
            raise StateError("Database connection is closed")
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def get(self, key: str, tenant_id: str = "default") -> Any:
        """Get a value by key."""
        if self._conn is None:
            raise StateError("Database connection is closed")

        row = self._conn.execute(
            "SELECT value, version FROM state WHERE key = ? AND tenant_id = ?",
            (key, tenant_id),
        ).fetchone()

        if row is None:
            return None
        return json.loads(row["value"])

    def set(self, key: str, value: Any, tenant_id: str = "default") -> StateEntry:
        """Set a value, creating or updating as needed."""
        if self._conn is None:
            raise StateError("Database connection is closed")

        now = time.time()
        existing = self._conn.execute(
            "SELECT version FROM state WHERE key = ? AND tenant_id = ?",
            (key, tenant_id),
        ).fetchone()

        serialized = json.dumps(value)

        if existing:
            version = existing["version"] + 1
            self._conn.execute(
                """UPDATE state SET value = ?, updated_at = ?, version = ?
                   WHERE key = ? AND tenant_id = ?""",
                (serialized, now, version, key, tenant_id),
            )
            operation = "UPDATE"
        else:
            version = 1
            self._conn.execute(
                """INSERT INTO state (key, tenant_id, value, created_at, updated_at, version)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (key, tenant_id, serialized, now, now, version),
            )
            operation = "INSERT"

        # Log the operation
        self._conn.execute(
            """INSERT INTO state_log (key, tenant_id, operation, new_value, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (key, tenant_id, operation, serialized, now),
        )
        self._conn.commit()

        return StateEntry(
            key=key,
            value=value,
            tenant_id=tenant_id,
            created_at=now if not existing else 0,
            updated_at=now,
            version=version,
        )

    def delete(self, key: str, tenant_id: str = "default") -> bool:
        """Delete a key."""
        if self._conn is None:
            raise StateError("Database connection is closed")

        existing = self._conn.execute(
            "SELECT value FROM state WHERE key = ? AND tenant_id = ?",
            (key, tenant_id),
        ).fetchone()

        if existing is None:
            return False

        self._conn.execute(
            "DELETE FROM state WHERE key = ? AND tenant_id = ?",
            (key, tenant_id),
        )
        self._conn.execute(
            """INSERT INTO state_log (key, tenant_id, operation, old_value, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (key, tenant_id, "DELETE", existing["value"], time.time()),
        )
        self._conn.commit()
        return True

    def list_keys(self, tenant_id: str = "default",
                  prefix: str | None = None) -> list[str]:
        """List all keys for a tenant, optionally filtered by prefix."""
        if self._conn is None:
            raise StateError("Database connection is closed")

        if prefix:
            rows = self._conn.execute(
                "SELECT key FROM state WHERE tenant_id = ? AND key LIKE ?",
                (tenant_id, f"{prefix}%"),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT key FROM state WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchall()

        return [row["key"] for row in rows]

    def get_history(self, key: str, tenant_id: str = "default",
                    limit: int = 100) -> list[dict[str, Any]]:
        """Get operation history for a key."""
        if self._conn is None:
            raise StateError("Database connection is closed")

        rows = self._conn.execute(
            """SELECT operation, old_value, new_value, timestamp
               FROM state_log WHERE key = ? AND tenant_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (key, tenant_id, limit),
        ).fetchall()

        return [
            {
                "operation": row["operation"],
                "old_value": json.loads(row["old_value"]) if row["old_value"] else None,
                "new_value": json.loads(row["new_value"]) if row["new_value"] else None,
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    def clear_tenant(self, tenant_id: str = "default") -> int:
        """Clear all state for a tenant. Returns count of deleted keys."""
        if self._conn is None:
            raise StateError("Database connection is closed")

        count = self._conn.execute(
            "SELECT COUNT(*) FROM state WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchone()[0]

        self._conn.execute(
            "DELETE FROM state WHERE tenant_id = ?",
            (tenant_id,),
        )
        self._conn.commit()
        return count

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> StateManager:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

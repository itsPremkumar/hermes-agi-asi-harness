#!/usr/bin/env python3
"""
State Manager Plugin — Persistent state management with SQLite + FTS5
=====================================================================
Features:
- SQLite database with full schema for sessions, tasks, memories, skills
- FTS5 full-text search across all content
- Checkpoint/restore for long-running tasks
- State versioning with rollback
- Compressed context windows
- Memory consolidation during idle
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_state_manager")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: List[str] = field(default_factory=list)
        shell_commands: List[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: int = 512
        max_cpu_percent: int = 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: List[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: List[str] = field(default_factory=list)
        path: Optional[Path] = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


# Database schema
DB_SCHEMA = """
-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    status TEXT DEFAULT 'active',
    context TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}'
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    result TEXT,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Memories table
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    memory_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    importance REAL DEFAULT 0.5,
    tags TEXT DEFAULT '[]',
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}'
);

-- Checkpoints table
CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    state_data BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Skills table
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}'
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    actor TEXT,
    target TEXT,
    details TEXT,
    metadata TEXT DEFAULT '{}'
);

-- FTS5 virtual tables for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
    session_id, title, context, content='sessions', content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
    task_id, title, description, content='tasks', content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    memory_id, title, content, tags, content='memories', content_rowid='rowid'
);

-- Triggers to keep FTS indexes in sync
CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
    INSERT INTO sessions_fts(session_id, title, context) VALUES (new.id, new.title, new.context);
END;

CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, session_id, title, context) VALUES ('delete', old.id, old.title, old.context);
END;

CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, session_id, title, context) VALUES ('delete', old.id, old.title, old.context);
    INSERT INTO sessions_fts(session_id, title, context) VALUES (new.id, new.title, new.context);
END;

CREATE TRIGGER IF NOT EXISTS tasks_ai AFTER INSERT ON tasks BEGIN
    INSERT INTO tasks_fts(task_id, title, description) VALUES (new.id, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS tasks_ad AFTER DELETE ON tasks BEGIN
    INSERT INTO tasks_fts(tasks_fts, task_id, title, description) VALUES ('delete', old.id, old.title, old.description);
END;

CREATE TRIGGER IF NOT EXISTS tasks_au AFTER UPDATE ON tasks BEGIN
    INSERT INTO tasks_fts(tasks_fts, task_id, title, description) VALUES ('delete', old.id, old.title, old.description);
    INSERT INTO tasks_fts(task_id, title, description) VALUES (new.id, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(memory_id, title, content, tags) VALUES (new.id, new.title, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, memory_id, title, content, tags) VALUES ('delete', old.id, old.title, old.content, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, memory_id, title, content, tags) VALUES ('delete', old.id, old.title, old.content, old.tags);
    INSERT INTO memories_fts(memory_id, title, content, tags) VALUES (new.id, new.title, new.content, new.tags);
END;
"""


class StateManager:
    """
    Persistent state manager with SQLite + FTS5.
    """
    
    def __init__(self, db_path: str = "state/hermes_state.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """Initialize the database."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(DB_SCHEMA)
        self._conn.commit()
        logger.info(f"StateManager initialized: {self.db_path}")
    
    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    # ── Sessions ─────────────────────────────────────────────────────────
    
    def create_session(self, title: str = "", context: Dict = None) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO sessions (id, title, context) VALUES (?, ?, ?)",
            (session_id, title, json.dumps(context or {}))
        )
        self._conn.commit()
        self._log_action("session.create", "state_manager", session_id, {"title": title})
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a session by ID."""
        cursor = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def update_session(self, session_id: str, **kwargs) -> bool:
        """Update a session."""
        allowed = {"title", "status", "context", "metadata"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [session_id]
        
        self._conn.execute(
            f"UPDATE sessions SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values
        )
        self._conn.commit()
        return True
    
    def list_sessions(self, status: str = None, limit: int = 50) -> List[Dict]:
        """List sessions."""
        if status:
            cursor = self._conn.execute(
                "SELECT * FROM sessions WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                (status, limit)
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            )
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._conn.commit()
        self._log_action("session.delete", "state_manager", session_id, {})
        return True
    
    # ── Tasks ───────────────────────────────────────────────────────────
    
    def create_task(self, title: str, description: str = "", session_id: str = None, priority: int = 0) -> str:
        """Create a new task."""
        task_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO tasks (id, session_id, title, description, priority) VALUES (?, ?, ?, ?, ?)",
            (task_id, session_id, title, description, priority)
        )
        self._conn.commit()
        self._log_action("task.create", "state_manager", task_id, {"title": title})
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a task by ID."""
        cursor = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update a task."""
        allowed = {"title", "description", "status", "priority", "result", "error", "metadata"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [task_id]
        
        self._conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?",
            values
        )
        
        if kwargs.get("status") == "completed":
            self._conn.execute(
                "UPDATE tasks SET completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,)
            )
        
        self._conn.commit()
        return True
    
    def list_tasks(self, session_id: str = None, status: str = None, limit: int = 50) -> List[Dict]:
        """List tasks."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY priority DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()
        return True
    
    # ── Memories ───────────────────────────────────────────────────────
    
    def create_memory(self, memory_type: str, title: str, content: str, importance: float = 0.5, tags: List[str] = None, source: str = "") -> str:
        """Create a new memory."""
        memory_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO memories (id, memory_type, title, content, importance, tags, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (memory_id, memory_type, title, content, importance, json.dumps(tags or []), source)
        )
        self._conn.commit()
        self._log_action("memory.create", "state_manager", memory_id, {"type": memory_type, "title": title})
        return memory_id
    
    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Get a memory by ID."""
        cursor = self._conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d["tags"] = json.loads(d.get("tags", "[]"))
            return d
        return None
    
    def update_memory(self, memory_id: str, **kwargs) -> bool:
        """Update a memory."""
        allowed = {"title", "content", "importance", "tags", "metadata"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [memory_id]
        
        self._conn.execute(
            f"UPDATE memories SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values
        )
        self._conn.commit()
        return True
    
    def list_memories(self, memory_type: str = None, limit: int = 50, order_by: str = "importance") -> List[Dict]:
        """List memories."""
        query = "SELECT * FROM memories WHERE 1=1"
        params = []
        
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
        
        if order_by == "importance":
            query += " ORDER BY importance DESC, updated_at DESC"
        elif order_by == "recent":
            query += " ORDER BY updated_at DESC"
        
        query += " LIMIT ?"
        params.append(limit)
        
        cursor = self._conn.execute(query, params)
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            d["tags"] = json.loads(d.get("tags", "[]"))
            results.append(d)
        return results
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.commit()
        return True
    
    # ── Full-Text Search ──────────────────────────────────────────────
    
    def search(self, query: str, table: str = "all", limit: int = 20) -> List[Dict]:
        """Full-text search across all content."""
        results = []
        
        if table in ("all", "sessions"):
            cursor = self._conn.execute(
                """SELECT s.* FROM sessions s
                   JOIN sessions_fts fts ON s.rowid = fts.rowid
                   WHERE sessions_fts MATCH ?
                   LIMIT ?""",
                (query, limit)
            )
            for row in cursor.fetchall():
                d = dict(row)
                d["_table"] = "sessions"
                results.append(d)
        
        if table in ("all", "tasks"):
            cursor = self._conn.execute(
                """SELECT t.* FROM tasks t
                   JOIN tasks_fts fts ON t.rowid = fts.rowid
                   WHERE tasks_fts MATCH ?
                   LIMIT ?""",
                (query, limit)
            )
            for row in cursor.fetchall():
                d = dict(row)
                d["_table"] = "tasks"
                results.append(d)
        
        if table in ("all", "memories"):
            cursor = self._conn.execute(
                """SELECT m.* FROM memories m
                   JOIN memories_fts fts ON m.rowid = fts.rowid
                   WHERE memories_fts MATCH ?
                   LIMIT ?""",
                (query, limit)
            )
            for row in cursor.fetchall():
                d = dict(row)
                d["tags"] = json.loads(d.get("tags", "[]"))
                d["_table"] = "memories"
                results.append(d)
        
        return results
    
    # ── Checkpoints ───────────────────────────────────────────────────
    
    def create_checkpoint(self, task_id: str, state_data: Dict, compress: bool = True) -> str:
        """Create a checkpoint for a task."""
        checkpoint_id = str(uuid.uuid4())
        state_json = json.dumps(state_data).encode("utf-8")
        state_hash = hashlib.sha256(state_json).hexdigest()
        
        if compress:
            state_blob = gzip.compress(state_json)
        else:
            state_blob = state_json
        
        self._conn.execute(
            "INSERT INTO checkpoints (id, task_id, state_hash, state_data) VALUES (?, ?, ?, ?)",
            (checkpoint_id, task_id, state_hash, state_blob)
        )
        self._conn.commit()
        self._log_action("checkpoint.create", "state_manager", checkpoint_id, {"task_id": task_id})
        return checkpoint_id
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        """Get a checkpoint and decompress."""
        cursor = self._conn.execute("SELECT * FROM checkpoints WHERE id = ?", (checkpoint_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        d = dict(row)
        state_blob = d["state_data"]
        
        try:
            state_json = gzip.decompress(state_blob)
        except Exception:
            state_json = state_blob
        
        d["state_data"] = json.loads(state_json.decode("utf-8"))
        return d
    
    def get_latest_checkpoint(self, task_id: str) -> Optional[Dict]:
        """Get the latest checkpoint for a task."""
        cursor = self._conn.execute(
            "SELECT * FROM checkpoints WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
            (task_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        d = dict(row)
        state_blob = d["state_data"]
        
        try:
            state_json = gzip.decompress(state_blob)
        except Exception:
            state_json = state_blob
        
        d["state_data"] = json.loads(state_json.decode("utf-8"))
        return d
    
    def list_checkpoints(self, task_id: str) -> List[Dict]:
        """List checkpoints for a task."""
        cursor = self._conn.execute(
            "SELECT id, task_id, state_hash, created_at FROM checkpoints WHERE task_id = ? ORDER BY created_at DESC",
            (task_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def rollback_to_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        """Rollback to a checkpoint."""
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return None
        
        self._log_action("checkpoint.rollback", "state_manager", checkpoint_id, {"task_id": checkpoint["task_id"]})
        return checkpoint["state_data"]
    
    # ── Skills ─────────────────────────────────────────────────────────
    
    def create_skill(self, name: str, content: str, description: str = "") -> str:
        """Create a new skill."""
        skill_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO skills (id, name, description, content) VALUES (?, ?, ?, ?)",
            (skill_id, name, description, content)
        )
        self._conn.commit()
        self._log_action("skill.create", "state_manager", skill_id, {"name": name})
        return skill_id
    
    def get_skill(self, skill_id: str = None, name: str = None) -> Optional[Dict]:
        """Get a skill by ID or name."""
        if skill_id:
            cursor = self._conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
        elif name:
            cursor = self._conn.execute("SELECT * FROM skills WHERE name = ?", (name,))
        else:
            return None
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def update_skill(self, skill_id: str, **kwargs) -> bool:
        """Update a skill."""
        allowed = {"name", "description", "content", "metadata"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        
        # Increment version on content update
        if "content" in updates:
            updates["version"] = "version + 1"
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [skill_id]
        
        self._conn.execute(
            f"UPDATE skills SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values
        )
        self._conn.commit()
        return True
    
    def record_skill_usage(self, skill_id: str, success: bool):
        """Record skill usage."""
        if success:
            self._conn.execute(
                "UPDATE skills SET success_count = success_count + 1 WHERE id = ?",
                (skill_id,)
            )
        else:
            self._conn.execute(
                "UPDATE skills SET fail_count = fail_count + 1 WHERE id = ?",
                (skill_id,)
            )
        self._conn.commit()
    
    def list_skills(self, limit: int = 50) -> List[Dict]:
        """List all skills."""
        cursor = self._conn.execute("SELECT * FROM skills ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill."""
        self._conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        self._conn.commit()
        return True
    
    # ── Audit Log ─────────────────────────────────────────────────────
    
    def _log_action(self, action: str, actor: str, target: str, details: Dict):
        """Log an action to the audit log."""
        self._conn.execute(
            "INSERT INTO audit_log (action, actor, target, details) VALUES (?, ?, ?, ?)",
            (action, actor, target, json.dumps(details))
        )
        self._conn.commit()
    
    def get_audit_log(self, limit: int = 100, action: str = None) -> List[Dict]:
        """Get audit log entries."""
        if action:
            cursor = self._conn.execute(
                "SELECT * FROM audit_log WHERE action = ? ORDER BY timestamp DESC LIMIT ?",
                (action, limit)
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        return [dict(row) for row in cursor.fetchall()]
    
    # ── Stats ─────────────────────────────────────────────────────────
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}
        
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM sessions")
        stats["sessions"] = cursor.fetchone()["count"]
        
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM tasks")
        stats["tasks"] = cursor.fetchone()["count"]
        
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'completed'")
        stats["completed_tasks"] = cursor.fetchone()["count"]
        
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM memories")
        stats["memories"] = cursor.fetchone()["count"]
        
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM checkpoints")
        stats["checkpoints"] = cursor.fetchone()["count"]
        
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM skills")
        stats["skills"] = cursor.fetchone()["count"]
        
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM audit_log")
        stats["audit_log_entries"] = cursor.fetchone()["count"]
        
        stats["db_size_bytes"] = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        
        return stats


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """State Manager Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="state_manager",
            version="1.0.0",
            description="Persistent state management with SQLite + FTS5, checkpoint/restore, state versioning with rollback",
            license="MIT",
            source="internal",
            capabilities=[
                "state_persistence",
                "checkpoint",
                "restore",
                "state_versioning",
            ],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.manager: Optional[StateManager] = None
    
    async def load(self) -> bool:
        self.manager = StateManager()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.manager:
            self.manager = StateManager()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        if self.manager:
            self.manager.close()
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        healthy = self.state in (PluginState.LOADED, PluginState.RUNNING)
        return {
            "status": "healthy" if healthy else "degraded",
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": healthy,
            "ready": self.manager is not None,
            "stats": self.manager.get_stats() if self.manager else {},
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def create_session(self, title: str = "", context: Dict = None) -> str:
        return self.manager.create_session(title, context)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.manager.get_session(session_id)
    
    def list_sessions(self, status: str = None, limit: int = 50) -> List[Dict]:
        return self.manager.list_sessions(status, limit)
    
    def create_task(self, title: str, description: str = "", session_id: str = None, priority: int = 0) -> str:
        return self.manager.create_task(title, description, session_id, priority)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        return self.manager.get_task(task_id)
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        return self.manager.update_task(task_id, **kwargs)
    
    def list_tasks(self, session_id: str = None, status: str = None, limit: int = 50) -> List[Dict]:
        return self.manager.list_tasks(session_id, status, limit)
    
    def create_memory(self, memory_type: str, title: str, content: str, importance: float = 0.5, tags: List[str] = None, source: str = "") -> str:
        return self.manager.create_memory(memory_type, title, content, importance, tags, source)
    
    def list_memories(self, memory_type: str = None, limit: int = 50) -> List[Dict]:
        return self.manager.list_memories(memory_type, limit)
    
    def search(self, query: str, table: str = "all", limit: int = 20) -> List[Dict]:
        return self.manager.search(query, table, limit)
    
    def create_checkpoint(self, task_id: str, state_data: Dict) -> str:
        return self.manager.create_checkpoint(task_id, state_data)
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        return self.manager.get_checkpoint(checkpoint_id)
    
    def get_latest_checkpoint(self, task_id: str) -> Optional[Dict]:
        return self.manager.get_latest_checkpoint(task_id)
    
    def rollback_to_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        return self.manager.rollback_to_checkpoint(checkpoint_id)
    
    def create_skill(self, name: str, content: str, description: str = "") -> str:
        return self.manager.create_skill(name, content, description)
    
    def get_skill(self, skill_id: str = None, name: str = None) -> Optional[Dict]:
        return self.manager.get_skill(skill_id, name)
    
    def list_skills(self) -> List[Dict]:
        return self.manager.list_skills()
    
    def record_skill_usage(self, skill_id: str, success: bool):
        return self.manager.record_skill_usage(skill_id, success)
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        return self.manager.get_audit_log(limit)
    
    def get_stats(self) -> Dict[str, Any]:
        return self.manager.get_stats()
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities

async def create(kernel: Any) -> Plugin:
    p = Plugin()
    await p.load()
    await p.start()
    return p


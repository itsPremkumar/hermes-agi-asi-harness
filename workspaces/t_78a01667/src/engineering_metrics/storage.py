"""SQLite persistence layer for engineering metrics."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS deployments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo TEXT NOT NULL,
    env TEXT NOT NULL DEFAULT 'prod',
    timestamp REAL NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo TEXT NOT NULL,
    PR_number INTEGER,
    lead_time_hours REAL,
    failed INTEGER NOT NULL DEFAULT 0,
    timestamp REAL NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    started_at REAL NOT NULL,
    resolved_at REAL,
    mttr_minutes REAL,
    severity TEXT DEFAULT 'medium',
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS cycle_times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_item_id TEXT NOT NULL,
    repo TEXT,
    cycle_time_hours REAL NOT NULL,
    wip_at_start INTEGER DEFAULT 0,
    timestamp REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pulse_surveys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id TEXT NOT NULL,
    respondent TEXT NOT NULL,
    timestamp REAL NOT NULL,
    period TEXT DEFAULT 'current',
    scores TEXT NOT NULL,
    comments TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS dashboard_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class MetricsStorage:
    """SQLite-backed storage for all metrics."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    # --- Deployments ---

    def insert_deployment(
        self, repo: str, env: str, timestamp: float, metadata: Dict[str, Any] = None
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO deployments (repo, env, timestamp, metadata) VALUES (?, ?, ?, ?)",
                (repo, env, timestamp, self._json_dumps(metadata or {})),
            )
            conn.commit()
            return cur.lastrowid

    def get_deployments(self, since: float, env: Optional[str] = None) -> List[Dict]:
        with self._conn() as conn:
            if env:
                rows = conn.execute(
                    "SELECT * FROM deployments WHERE timestamp >= ? AND env = ? ORDER BY timestamp DESC",
                    (since, env),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM deployments WHERE timestamp >= ? ORDER BY timestamp DESC",
                    (since,),
                ).fetchall()
            return [dict(r) for r in rows]

    # --- Changes ---

    def insert_change(
        self,
        repo: str,
        lead_time_hours: float,
        failed: bool = False,
        PR_number: Optional[int] = None,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict] = None,
    ) -> int:
        ts = timestamp or time.time()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO changes (repo, PR_number, lead_time_hours, failed, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (repo, PR_number, lead_time_hours, 1 if failed else 0, ts, self._json_dumps(metadata or {})),
            )
            conn.commit()
            return cur.lastrowid

    def get_changes(self, since: float, until: Optional[float] = None) -> List[Dict]:
        with self._conn() as conn:
            if until is not None:
                rows = conn.execute(
                    "SELECT * FROM changes WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp DESC",
                    (since, until),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM changes WHERE timestamp >= ? ORDER BY timestamp DESC",
                    (since,),
                ).fetchall()
            return [dict(r) for r in rows]

    # --- Incidents ---

    def insert_incident(
        self, title: str, started_at: float, severity: str = "medium", metadata: Optional[Dict] = None
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO incidents (title, started_at, severity, metadata) VALUES (?, ?, ?, ?)",
                (title, started_at, severity, self._json_dumps(metadata or {})),
            )
            conn.commit()
            return cur.lastrowid

    def resolve_incident(self, incident_id: int, resolved_at: float) -> None:
        with self._conn() as conn:
            row = conn.execute("SELECT started_at FROM incidents WHERE id = ?", (incident_id,)).fetchone()
            if row is None:
                return
            started = row["started_at"]
            mttr = (resolved_at - started) / 60 if resolved_at > started else 0.0
            conn.execute(
                "UPDATE incidents SET resolved_at = ?, mttr_minutes = ? WHERE id = ?",
                (resolved_at, mttr, incident_id),
            )
            conn.commit()

    def get_incidents(self, since: float) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM incidents WHERE started_at >= ? ORDER BY started_at DESC",
                (since,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Cycle times ---

    def insert_cycle_time(
        self, work_item_id: str, cycle_time_hours: float, repo: str = "", wip_at_start: int = 0, timestamp: Optional[float] = None, metadata: Optional[Dict] = None
    ) -> int:
        ts = timestamp or time.time()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO cycle_times (work_item_id, repo, cycle_time_hours, wip_at_start, timestamp) VALUES (?, ?, ?, ?, ?)",
                (work_item_id, repo, cycle_time_hours, wip_at_start, ts),
            )
            conn.commit()
            return cur.lastrowid

    def get_cycle_times(self, since: float) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM cycle_times WHERE timestamp >= ? ORDER BY timestamp DESC",
                (since,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Pulse surveys ---

    def insert_pulse_survey(self, survey: "PulseSurvey") -> int:
        from .models import PulseSurvey as PS
        if isinstance(survey, PS):
            scores_str = json.dumps(survey.scores, default=str)
        else:
            scores_str = json.dumps(survey.get("scores", {}), default=str)
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO pulse_surveys (survey_id, respondent, timestamp, period, scores, comments) VALUES (?, ?, ?, ?, ?, ?)",
                (survey.survey_id, survey.respondent, survey.timestamp, survey.period, scores_str, survey.comments),
            )
            conn.commit()
            return cur.lastrowid

    def get_pulse_surveys(self, since: float, period: Optional[str] = None) -> List[Dict]:
        with self._conn() as conn:
            if period:
                rows = conn.execute(
                    "SELECT * FROM pulse_surveys WHERE timestamp >= ? AND period = ? ORDER BY timestamp DESC",
                    (since, period),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM pulse_surveys WHERE timestamp >= ? ORDER BY timestamp DESC",
                    (since,),
                ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("scores"), str):
                    try:
                        d["scores"] = json.loads(d["scores"])
                    except (json.JSONDecodeError, ValueError):
                        pass
                result.append(d)
            return result

    # --- Config ---

    def set_config(self, key: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO dashboard_config (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()

    def get_config(self, key: str, default: str = "") -> str:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM dashboard_config WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    # --- Helpers ---

    @staticmethod
    def _json_dumps(obj: Any) -> str:
        import json
        return json.dumps(obj, default=str)

    def vacuum(self) -> None:
        with self._conn() as conn:
            conn.execute("VACUUM")
            conn.commit()
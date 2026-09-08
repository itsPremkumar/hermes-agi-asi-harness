"""
Research Memory — SQLite-backed storage for research state.

Stores papers, summaries, hypotheses, experiments, drafts, and
evaluation results for persistence and retrieval across sessions.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Optional

from deepresearch.config import ResearchConfig
from deepresearch.state import ResearchState


class ResearchMemory:
    """SQLite-backed memory store for research artifacts."""

    def __init__(self, config: ResearchConfig | None = None):
        self.config = config or ResearchConfig()
        self.db_path = self.config.sqlite_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database schema."""
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS research_runs (
                run_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS papers (
                paper_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                title TEXT,
                authors TEXT,  -- JSON array
                abstract TEXT,
                year INTEGER,
                venue TEXT,
                url TEXT,
                metadata_json TEXT,
                FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS hypotheses (
                hypothesis_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                statement TEXT,
                rationale TEXT,
                counterfactual_basis TEXT,
                novelty_score REAL,
                supporting_papers TEXT,  -- JSON array
                falsifiability INTEGER,
                resource_cost TEXT,
                FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                hypothesis_id TEXT,
                experiment_type TEXT,
                description TEXT,
                methodology TEXT,
                resources TEXT,  -- JSON array
                timeline TEXT,
                simulated_outcome TEXT,
                confidence_intervals TEXT,  -- JSON
                FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS drafts (
                draft_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                title TEXT,
                abstract TEXT,
                sections TEXT,  -- JSON
                latex TEXT,
                bibliography TEXT,
                FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS evaluations (
                eval_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                hypothesis_novelty REAL,
                experiment_feasibility REAL,
                paper_quality REAL,
                overall_score REAL,
                feedback TEXT,  -- JSON array
                recommendations TEXT,  -- JSON array
                FOREIGN KEY (run_id) REFERENCES research_runs(run_id)
            );
        """)
        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        """Get a SQLite connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def store_state(self, state: ResearchState) -> None:
        """Store the full research state for a run."""
        run_id = state.get("run_id", "")
        if not run_id:
            run_id = str(time.time())
            state["run_id"] = run_id

        conn = self._connect()

        state_json = json.dumps(state, default=str, indent=2)

        # Store run
        conn.execute("""
            INSERT OR REPLACE INTO research_runs
            (run_id, query, state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            run_id,
            state.get("query", ""),
            state_json,
            state.get("created_at", time.time()),
            time.time(),
        ))

        # Store papers
        for p in state.get("papers", []):
            pid = p.get("arxiv_id") or p.get("pubmed_id") or p.get("doi", "")
            if pid:
                conn.execute("""
                    INSERT OR REPLACE INTO papers
                    (paper_id, run_id, title, authors, abstract, year, venue, url, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pid, run_id,
                    p.get("title", ""),
                    json.dumps(p.get("authors", [])),
                    p.get("abstract", ""),
                    p.get("year", 0),
                    p.get("venue", ""),
                    p.get("url", ""),
                    json.dumps(p, default=str),
                ))

        # Store hypotheses
        for h in state.get("hypotheses", []):
            conn.execute("""
                INSERT OR REPLACE INTO hypotheses
                (hypothesis_id, run_id, statement, rationale, counterfactual_basis,
                 novelty_score, supporting_papers, falsifiability, resource_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                h.get("id", ""), run_id,
                h.get("statement", ""),
                h.get("rationale", ""),
                h.get("counterfactual_basis", ""),
                h.get("novelty_score", 0.0),
                json.dumps(h.get("supporting_papers", [])),
                int(h.get("falsifiability", True)),
                h.get("estimated_resource_cost", ""),
            ))

        # Store experiments
        for e in state.get("experiments", []):
            conn.execute("""
                INSERT OR REPLACE INTO experiments
                (experiment_id, run_id, hypothesis_id, experiment_type,
                 description, methodology, resources, timeline,
                 simulated_outcome, confidence_intervals)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                e.get("id", ""), run_id,
                e.get("hypothesis_id", ""),
                e.get("experiment_type", ""),
                e.get("description", ""),
                e.get("methodology", ""),
                json.dumps(e.get("required_resources", [])),
                e.get("estimated_timeline", ""),
                e.get("simulated_outcome", ""),
                json.dumps(e.get("confidence_intervals", {})),
            ))

        # Store drafts
        for d in state.get("drafts", []):
            conn.execute("""
                INSERT OR REPLACE INTO drafts
                (draft_id, run_id, title, abstract, sections, latex, bibliography)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                d.get("id", ""), run_id,
                d.get("title", ""),
                d.get("abstract", ""),
                json.dumps(d.get("sections", {})),
                "",  # latex stored separately via get_paper_latex
                d.get("bibliography_tex", ""),
            ))

        # Store evaluations
        for ev in state.get("evaluations", []):
            conn.execute("""
                INSERT OR REPLACE INTO evaluations
                (eval_id, run_id, hypothesis_novelty, experiment_feasibility,
                 paper_quality, overall_score, feedback, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(time.time()), run_id,
                ev.get("hypothesis_novelty", 0.0),
                ev.get("experiment_feasibility", 0.0),
                ev.get("paper_quality", 0.0),
                ev.get("overall_score", 0.0),
                json.dumps(ev.get("feedback", [])),
                json.dumps(ev.get("recommendations", [])),
            ))

        conn.commit()
        conn.close()

    def retrieve_state(self, run_id: str) -> Optional[ResearchState]:
        """Retrieve the full research state for a run."""
        conn = self._connect()
        row = conn.execute(
            "SELECT state_json FROM research_runs WHERE run_id = ?",
            (run_id,)
        ).fetchone()
        conn.close()

        if row:
            return json.loads(row["state_json"])
        return None

    def list_runs(self) -> list[dict[str, Any]]:
        """List all research runs."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT run_id, query, created_at, updated_at FROM research_runs ORDER BY updated_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def search_papers(self, query: str) -> list[dict[str, Any]]:
        """Search stored papers by title/abstract keywords."""
        conn = self._connect()
        pattern = f"%{query}%"
        rows = conn.execute(
            "SELECT * FROM papers WHERE title LIKE ? OR abstract LIKE ?",
            (pattern, pattern)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_hypotheses(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve hypotheses for a specific run."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM hypotheses WHERE run_id = ?",
            (run_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def clear(self) -> None:
        """Clear all stored data."""
        conn = self._connect()
        conn.executescript("""
            DELETE FROM research_runs;
            DELETE FROM papers;
            DELETE FROM hypotheses;
            DELETE FROM experiments;
            DELETE FROM drafts;
            DELETE FROM evaluations;
        """)
        conn.commit()
        conn.close()

    def close(self) -> None:
        """Close the memory store."""
        # SQLite connections are per-call, nothing to close
        pass

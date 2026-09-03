"""
Hermes AGI/ASI Harness — Overnight Notes Curator.

Maintains the persistent `notes.md` memory log across iterations:
- Accumulates verified progress, lessons learned, and remaining tasks
- Compacts historical context so prompt tokens remain bounded
- Enables the agent to maintain continuity across multi-hour runs
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.overnight.notes")


class NotesCurator:
    """Curates and compacts notes.md context for overnight iterations."""

    def __init__(self, run_dir: Path, objective: str):
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.notes_file = self.run_dir / "notes.md"
        self.objective = objective
        self._history: list[dict[str, Any]] = []

        if not self.notes_file.exists():
            self._write_header()

    def _write_header(self) -> None:
        header = (
            f"# Hermes Overnight Iteration Notes\n\n"
            f"- **Objective**: {self.objective}\n"
            f"- **Started**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **Architecture**: Atomic Commits & Hard Rollbacks (gnhf-pattern)\n\n"
            f"---\n\n"
            f"## Iteration Log\n\n"
        )
        with open(self.notes_file, "w", encoding="utf-8") as f:
            f.write(header)

    def record_success(
        self,
        iteration: int,
        description: str,
        commit_info: str = "",
        findings: list[str] | None = None,
    ) -> None:
        """Record a successful iteration in notes.md."""
        entry = {
            "iteration": iteration,
            "status": "success",
            "description": description,
            "commit": commit_info,
            "timestamp": time.time(),
        }
        self._history.append(entry)

        md_entry = (
            f"### Iteration {iteration}: SUCCESS\n"
            f"- **Action**: {description}\n"
            f"- **Commit**: `{commit_info}`\n"
            f"- **Time**: {time.strftime('%H:%M:%S')}\n"
        )
        if findings:
            md_entry += "- **Learnings**:\n"
            for f in findings:
                md_entry += f"  - {f}\n"
        md_entry += "\n"

        with open(self.notes_file, "a", encoding="utf-8") as f:
            f.write(md_entry)

    def record_failure(
        self,
        iteration: int,
        error_message: str,
        diagnosis: str = "",
    ) -> None:
        """Record a failed and rolled-back iteration in notes.md."""
        entry = {
            "iteration": iteration,
            "status": "failed",
            "error": error_message,
            "timestamp": time.time(),
        }
        self._history.append(entry)

        md_entry = (
            f"### Iteration {iteration}: ROLLED BACK (FAILED)\n"
            f"- **Error**: {error_message[:200]}\n"
            f"- **Diagnosis**: {diagnosis or 'State rolled back via git reset --hard'}\n"
            f"- **Time**: {time.strftime('%H:%M:%S')}\n\n"
        )

        with open(self.notes_file, "a", encoding="utf-8") as f:
            f.write(md_entry)

    def get_prompt_context(self, max_recent: int = 4) -> str:
        """
        Produce a compact context block for the next iteration prompt.
        Focuses on the high-level objective and recent successes/failures.
        """
        if not self._history:
            return "No previous iterations completed yet. Starting clean."

        recent = self._history[-max_recent:]
        lines = ["Previous Iteration Learnings:"]
        for item in recent:
            if item["status"] == "success":
                lines.append(f"- Iteration {item['iteration']} succeeded: {item['description']}")
            else:
                lines.append(f"- Iteration {item['iteration']} failed & rolled back: {item.get('error', '')[:100]} (avoid repeating)")
        return "\n".join(lines)

    @property
    def path(self) -> Path:
        return self.notes_file

"""
Hermes AGI/ASI Harness — Semantic Branch Summarizer.

Ported from Prime Agent (packages/coding-agent/src/core/compaction/branch-summarization.ts):
When switching or cutting branches in overnight/gnhf workflows, this generates
a structured semantic summary of modified files, read files, and diff statistics
so working context is preserved across branch transitions.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from .git_manager import GitManager

logger = logging.getLogger("hermes.overnight.branch_summarizer")


@dataclass
class BranchSummary:
    """Semantic record of activity on an isolated branch."""
    branch_name: str
    base_branch: str
    modified_files: list[str] = field(default_factory=list)
    diff_stats: str = ""
    key_decisions: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_markdown(self) -> str:
        lines = [
            f"### Branch Context: `{self.branch_name}` (from `{self.base_branch}`)",
            f"- **Timestamp**: {time.strftime('%H:%M:%S', time.localtime(self.timestamp))}",
            f"- **Modified Files ({len(self.modified_files)})**:",
        ]
        for f in self.modified_files[:8]:
            lines.append(f"  - `{f}`")
        if len(self.modified_files) > 8:
            lines.append(f"  - *...and {len(self.modified_files) - 8} more*")

        if self.key_decisions:
            lines.append("- **Key Decisions / Invariants**:")
            for d in self.key_decisions:
                lines.append(f"  - {d}")

        if self.diff_stats:
            lines.append("\n```\n" + self.diff_stats.strip() + "\n```")

        return "\n".join(lines)


class SemanticBranchSummarizer:
    """Generates cross-branch semantic summaries to maintain long-horizon context."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.git = GitManager(workspace_root=str(self.workspace_root))

    def summarize_transition(
        self,
        from_branch: str,
        to_branch: str,
        decisions: list[str] | None = None,
    ) -> BranchSummary:
        """Create a summary of changes between two branches."""
        diff_stats = self.git.get_diff_stats(from_branch)

        # Extract file names from diff stats lines
        modified_files: list[str] = []
        for line in diff_stats.splitlines():
            parts = line.strip().split("|")
            if len(parts) == 2:
                file_name = parts[0].strip()
                if file_name and "." in file_name:
                    modified_files.append(file_name)

        return BranchSummary(
            branch_name=to_branch,
            base_branch=from_branch,
            modified_files=modified_files,
            diff_stats=diff_stats,
            key_decisions=decisions or ["Maintained test verification invariant."],
        )

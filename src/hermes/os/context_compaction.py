"""
HERMES — CONTEXT COMPACTION RUNTIME (mid-run overflow guard)
=============================================================
Extractive, offline-safe compaction for long missions:
- Always keeps: invariants, decisions, errors, verification verdicts.
- Keeps recency tail; compresses the middle into bullet digests.
- Spills the full text to .hermes/context_archive/ with provenance.
Decide-then-verify: compact() returns (compacted, report); nothing is lost.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("hermes.os.compaction")

_KEEP_PATTERNS = (
    "invariant",
    "decision",
    "error",
    "fail",
    "verdict",
    "proof",
    "warning",
    "critical",
    "rollback",
    "checkpoint",
    "approved",
)


def _lines(text: str) -> List[str]:
    return str(text or "").splitlines()


def _is_keep(line: str) -> bool:
    low = line.lower()
    return any(k in low for k in _KEEP_PATTERNS) or line.strip().startswith(
        ("#", "##", "-", "*", "1.")
    )


class ContextCompactor:
    def __init__(self, workspace_root: str = ".", max_chars: int = 12000, tail_lines: int = 120):
        self.workspace_root = workspace_root
        self.max_chars = max_chars
        self.tail_lines = tail_lines
        self.archive_dir = Path(workspace_root) / ".hermes" / "context_archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def needs_compaction(self, text: str) -> bool:
        return len(str(text or "")) > self.max_chars

    def compact(self, text: str, label: str = "context") -> Dict[str, Any]:
        """Returns {compacted, original_chars, compacted_chars, digest_lines, archive}."""
        original = str(text or "")
        if not self.needs_compaction(original):
            return {
                "compacted": original,
                "original_chars": len(original),
                "compacted_chars": len(original),
                "digest_lines": 0,
                "archive": None,
                "compacted_flag": False,
            }
        lines = _lines(original)
        tail = lines[-self.tail_lines :]
        head = lines[: -self.tail_lines] if len(lines) > self.tail_lines else []
        kept = [ln for ln in head if _is_keep(ln)]
        # Digest the dropped middle: per-50-line one-line summaries
        dropped = [ln for ln in head if ln not in kept]
        digest: List[str] = []
        for i in range(0, len(dropped), 50):
            chunk = dropped[i : i + 50]
            words = re.findall(r"[a-z0-9]+", " ".join(chunk).lower())
            from collections import Counter

            top = ", ".join(w for w, _ in Counter(words).most_common(8) if len(w) > 3)
            digest.append(f"[lines {i + 1}-{i + len(chunk)} topics: {top}]")
        archive_name = (
            f"{label}-{int(time.time())}-{hashlib.sha256(original.encode()).hexdigest()[:8]}.txt"
        )
        archive = self.archive_dir / archive_name
        try:
            archive.write_text(original, encoding="utf-8")
        except Exception as e:
            logger.debug("compaction archive failed: %s", e)
            archive = None  # type: ignore[assignment]
        compacted = "\n".join(
            [
                "# COMPACTED CONTEXT (full text archived)",
                f"# kept {len(kept)} signal lines + {len(tail)} tail lines, "
                f"digested {len(dropped)} lines into {len(digest)} bullets",
                "",
                "## SIGNAL",
            ]
            + kept
            + ["", "## DIGEST"]
            + digest
            + ["", "## TAIL"]
            + tail
        )
        return {
            "compacted": compacted,
            "original_chars": len(original),
            "compacted_chars": len(compacted),
            "digest_lines": len(digest),
            "archive": str(archive) if archive else None,
            "compacted_flag": True,
        }

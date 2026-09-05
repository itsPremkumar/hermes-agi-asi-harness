"""
HERMES MEMORY — P22 CONSOLIDATION (sleep / dream cycle, offline-safe)
=====================================================================
Nightly job for continuous operation:
1. rank + dedupe semantic entries (token-overlap merge)
2. archive stale episodic events (keep ring buffer)
3. calibrate capability self-model (Brier-style: success_rate vs predicted)
4. flush all domains to disk
Designed to run via ContinuousScheduler daily 02:00 as P22 after P0-P21.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict

logger = logging.getLogger("hermes.memory.consolidation")


def _norm(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def consolidate(
    memory_os: Any, max_semantic: int = 2000, episodic_keep: int = 500
) -> Dict[str, Any]:
    report: Dict[str, Any] = {"merged": 0, "archived": 0, "calibrated": 0, "ts": time.time()}
    try:
        sem = getattr(memory_os, "semantic", None)
        if sem is not None and hasattr(sem, "_entries"):
            entries = list(sem._entries.values())
            seen: Dict[frozenset, Any] = {}
            for e in entries:
                key = frozenset(list(_norm(getattr(e, "fact", "")))[:12])
                if key in seen:
                    # merge confidence upward, drop duplicate
                    try:
                        seen[key].confidence = min(
                            1.0, max(seen[key].confidence, getattr(e, "confidence", 0.9))
                        )
                        del sem._entries[getattr(e, "entry_id", "")]
                        report["merged"] += 1
                    except Exception:
                        pass
                else:
                    seen[key] = e
            # cap size: drop lowest-confidence oldest
            if len(sem._entries) > max_semantic:
                ordered = sorted(
                    sem._entries.values(),
                    key=lambda x: (getattr(x, "confidence", 0), -getattr(x, "created_at", 0)),
                )
                for drop in ordered[: len(sem._entries) - max_semantic]:
                    try:
                        del sem._entries[drop.entry_id]
                        report["merged"] += 1
                    except Exception:
                        pass
    except Exception as e:
        logger.debug("consolidate semantic failed: %s", e)
    try:
        epi = getattr(memory_os, "episodic", None)
        if epi is not None and hasattr(epi, "_events") and len(epi._events) > episodic_keep:
            overflow = len(epi._events) - episodic_keep
            del epi._events[:overflow]
            report["archived"] = overflow
    except Exception as e:
        logger.debug("consolidate episodic failed: %s", e)
    try:
        cap = getattr(memory_os, "capability", None)
        if cap is not None and hasattr(cap, "_capabilities"):
            for c in cap._capabilities.values():
                # Brier-style calibration: shrink extreme rates with few samples
                n = max(1, int(getattr(c, "invocations", 1)))
                r = float(getattr(c, "success_rate", 0.5))
                calibrated = (r * n + 0.5 * 4) / (n + 4)  # Laplace smoothing k=4
                c.success_rate = round(calibrated, 4)
                report["calibrated"] += 1
    except Exception as e:
        logger.debug("consolidate calibration failed: %s", e)
    try:
        save = getattr(memory_os, "save_to_disk", None)
        if callable(save):
            save()
    except Exception as e:
        logger.debug("consolidate flush failed: %s", e)
    return report

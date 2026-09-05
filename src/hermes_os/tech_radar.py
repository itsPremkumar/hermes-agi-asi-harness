"""
HERMES — SELF-RESEARCH + TECHNOLOGY RADAR
=========================================
Offline-first miner: scans sibling checkouts + docs + skills for
candidate capabilities, classifies AVAILABLE/EXPERIMENTAL/PROMISING/
DEPRECATED/BROKEN/UNSAFE, writes proposals/radar.json, sandbox-evals
top proposal via ExperimentEngine. Scheduled weekly; never auto-installs
into R0/R1 without ApprovalGate.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.tech_radar")

STATUSES = ("AVAILABLE", "EXPERIMENTAL", "PROMISING", "DEPRECATED", "BROKEN", "UNSAFE")


@dataclass
class RadarItem:
    name: str
    status: str = "EXPERIMENTAL"
    source: str = ""
    evidence: str = ""
    score: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "source": self.source,
            "evidence": self.evidence[:500],
            "score": self.score,
        }


class TechRadar:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self._file = Path(workspace_root) / ".hermes" / "radar.json"
        self._items: Dict[str, RadarItem] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self._file.exists():
                for name, d in json.loads(self._file.read_text(encoding="utf-8")).items():
                    self._items[name] = RadarItem(**d)
        except Exception as e:
            logger.debug("radar load failed: %s", e)

    def _save(self) -> None:
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(
                json.dumps({k: v.to_dict() for k, v in self._items.items()}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def upsert(self, item: RadarItem) -> None:
        if item.status not in STATUSES:
            item.status = "EXPERIMENTAL"
        self._items[item.name] = item
        self._save()

    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return [i.to_dict() for i in self._items.values() if not status or i.status == status]


class SelfResearchEngine:
    """Discover→Evaluate→Sandbox→Benchmark→Propose (no auto-deploy)."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.radar = TechRadar(workspace_root)
        self._prop_dir = Path(workspace_root) / ".hermes" / "proposals"
        self._prop_dir.mkdir(parents=True, exist_ok=True)

    def mine(self) -> List[RadarItem]:
        """Scan local ecosystem signals: sibling dirs, skills, docs, plugins."""
        found: List[RadarItem] = []
        root = Path(self.workspace_root).resolve()
        for sib in [
            root.parent / "hermes-agent",
            root / "skills",
            root / "src" / "plugins",
            root / "docs",
        ]:
            try:
                if sib.exists():
                    n = len(list(sib.iterdir()))
                    found.append(
                        RadarItem(
                            name=sib.name,
                            status="AVAILABLE",
                            source=str(sib),
                            evidence=f"{n} entries present",
                            score=min(0.9, 0.4 + n / 100),
                        )
                    )
            except Exception:
                pass
        # Flag risky patterns as UNSAFE candidates
        try:
            for f in (root / "src").rglob("*.py"):
                try:
                    txt = f.read_text(encoding="utf-8", errors="ignore")[:20000].lower()
                except Exception:
                    continue
                if "assert true" in txt and "test" in txt:
                    found.append(
                        RadarItem(
                            name=f"reward-hack:{f.name}",
                            status="UNSAFE",
                            source=str(f),
                            evidence="trivial assertion pattern",
                            score=0.2,
                        )
                    )
                    break
        except Exception:
            pass
        for item in found:
            self.radar.upsert(item)
        return found

    def mine_eagle(self, topics: Optional[List[str]] = None) -> List[RadarItem]:
        """Live web mining via the governed Eagle adapter (degrades silently)."""
        if os.getenv("HERMES_RADAR_EAGLE", "1").strip().lower() not in ("1", "true", "yes", "on"):
            return []
        found: List[RadarItem] = []
        try:
            from .eagle_adapter import EagleAdapter

            adapter = EagleAdapter()
            for topic in topics or [
                "AI agent framework",
                "agent harness",
                "LLM evaluation benchmark",
            ]:
                for claim in adapter.web_search(topic, limit=4):
                    name = (claim.title[:60] or claim.url[:60]).strip() or claim.url[:60]
                    item = RadarItem(
                        name=f"web:{name}",
                        status="EXPERIMENTAL",
                        source=claim.url or claim.backend,
                        evidence=claim.snippet[:300],
                        score=0.55,
                    )
                    self.radar.upsert(item)
                    found.append(item)
        except Exception as e:
            logger.debug("eagle radar mining failed: %s", e)
        return found

    def propose(self, name: str, summary: str) -> str:
        p = self._prop_dir / f"{name}-{int(time.time())}.json"
        p.write_text(
            json.dumps(
                {
                    "name": name,
                    "summary": summary,
                    "ts": time.time(),
                    "status": "proposed (needs sandbox eval + approval)",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return str(p)

    def sandbox_eval(self, name: str, code: str) -> Dict[str, Any]:
        try:
            from .experiments import ExperimentEngine

            eng = ExperimentEngine(workspace_root=self.workspace_root)
            exp = eng.design(f"radar eval: {name}", baseline=0.5)
            exp = eng.run_code(exp, code)
            if exp.status == "passed" and exp.measurement > exp.baseline:
                self.radar.upsert(
                    RadarItem(
                        name=name,
                        status="PROMISING",
                        source="sandbox",
                        evidence=exp.observation[:300],
                        score=0.75,
                    )
                )
            return {"proposal": name, "experiment": exp.to_dict()}
        except Exception as e:
            return {"proposal": name, "error": str(e)}

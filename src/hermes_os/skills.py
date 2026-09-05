"""
HERMES — SKILL OPERATING SYSTEM (dynamic lifecycle)
===================================================
Need detected → search registry → select → load → execute → evaluate → improve.
Versioned skills under skills/<name>/{SKILL.md, skill.json, tests/, benchmarks/, provenance.json}.
Offline-safe: filesystem only, no network required.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.os.skills")


@dataclass
class SkillVersion:
    name: str
    version: str = "0.1.0"
    description: str = ""
    triggers: List[str] = field(default_factory=list)
    success_rate: float = 0.5
    invocations: int = 0
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "version": self.version, "description": self.description,
                "triggers": self.triggers, "success_rate": self.success_rate,
                "invocations": self.invocations, "path": self.path}


class SkillRegistry:
    """Dynamic registry with success-rate routing + versioning."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.root = Path(workspace_root) / "skills"
        self.root.mkdir(parents=True, exist_ok=True)
        self._skills: Dict[str, SkillVersion] = {}
        self._discover()

    def _discover(self) -> None:
        for d in sorted(self.root.iterdir()) if self.root.exists() else []:
            if not d.is_dir():
                continue
            meta = d / "skill.json"
            body = d / "SKILL.md"
            if meta.exists():
                try:
                    data = json.loads(meta.read_text(encoding="utf-8"))
                    self._skills[d.name] = SkillVersion(
                        name=d.name, version=data.get("version", "0.1.0"),
                        description=data.get("description", ""), triggers=list(data.get("triggers", [])),
                        success_rate=float(data.get("success_rate", 0.5)),
                        invocations=int(data.get("invocations", 0)), path=str(d))
                    continue
                except Exception:
                    pass
            if body.exists():
                self._skills[d.name] = SkillVersion(name=d.name, description=f"Skill {d.name}", path=str(d))

    def search(self, need: str, limit: int = 5) -> List[SkillVersion]:
        import re
        q = set(re.findall(r"[a-z0-9]+", need.lower()))
        scored = []
        for s in self._skills.values():
            doc = f"{s.name} {s.description} {' '.join(s.triggers)}".lower()
            d = set(re.findall(r"[a-z0-9]+", doc))
            overlap = len(q & d) / max(1, len(q))
            score = 0.7 * overlap + 0.3 * s.success_rate
            if overlap > 0 or s.success_rate >= 0.7:
                scored.append((score, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    def load(self, name: str) -> Optional[str]:
        s = self._skills.get(name)
        if not s:
            return None
        for cand in (Path(s.path) / "SKILL.md", self.root / name / "SKILL.md"):
            try:
                if cand.exists():
                    return cand.read_text(encoding="utf-8")
            except Exception:
                pass
        return f"# Skill: {name}\n\n{ s.description}"

    def record_outcome(self, name: str, success: bool) -> None:
        s = self._skills.get(name)
        if not s:
            return
        n = s.invocations + 1
        s.success_rate = round((s.success_rate * s.invocations + (1.0 if success else 0.0)) / n, 4)
        s.invocations = n
        self._persist(s)

    def _persist(self, s: SkillVersion) -> None:
        try:
            d = Path(s.path) if s.path else (self.root / s.name)
            d.mkdir(parents=True, exist_ok=True)
            (d / "skill.json").write_text(json.dumps(s.to_dict(), indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("skill persist failed: %s", e)

    def install(self, name: str, body_md: str, description: str = "", triggers: Optional[List[str]] = None) -> SkillVersion:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(body_md, encoding="utf-8")
        (d / "provenance.json").write_text(json.dumps(
            {"name": name, "created_at": time.time(), "skill_id": f"sk-{uuid.uuid4().hex[:8]}"}), encoding="utf-8")
        s = SkillVersion(name=name, description=description or f"Skill {name}",
                         triggers=list(triggers or []), path=str(d))
        self._skills[name] = s
        self._persist(s)
        return s

    def improve(self, name: str, notes: str) -> Optional[SkillVersion]:
        """Bump patch version + append improvement notes (evaluation loop writes back)."""
        s = self._skills.get(name)
        if not s:
            return None
        try:
            major, minor, patch = (s.version.split(".") + ["0", "0", "0"])[:3]
            s.version = f"{major}.{minor}.{int(patch) + 1}"
        except Exception:
            s.version = "0.1.1"
        try:
            d = Path(s.path)
            hist = d / "IMPROVEMENTS.md"
            prev = hist.read_text(encoding="utf-8") if hist.exists() else ""
            hist.write_text(prev + f"\n## v{s.version} {time.strftime('%Y-%m-%d')}\n{notes}\n", encoding="utf-8")
        except Exception:
            pass
        self._persist(s)
        return s

    def list(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._skills.values()]

    def sync_from_dir(self, source_root: str, prefix: str = "hermes",
                      limit: int = 60) -> Dict[str, Any]:
        """Import hermes-agent style skills (nested <category>/<name>/SKILL.md).

        Copies bodies into skills/<prefix>-<category>-<name>/ with provenance
        pointing at the source file. Never overwrites locally-forged skills
        with the same name unless the source is newer. Returns sync report.
        """
        import shutil
        src = Path(source_root)
        found = sorted(src.rglob("SKILL.md")) if src.is_dir() else []
        # Coding-adjacent categories first so limits keep the highest-value skills.
        priority = ("software-development", "research", "web", "devops", "productivity")

        def _rank(p: Path) -> tuple:
            s = str(p).lower()
            for i, key in enumerate(priority):
                if key in s:
                    return (i, str(p))
            return (len(priority), str(p))

        found = sorted(found, key=_rank)
        imported, skipped, updated = 0, 0, 0
        for md in found[:limit * 3]:  # scan cap above import cap
            if imported >= limit:
                break
            try:
                rel = md.parent.relative_to(src)
                parts = [p for p in rel.parts if p not in (".",)]
                name = f"{prefix}-" + "-".join(parts)[:60].strip("-")
                if not name or name == f"{prefix}-":
                    skipped += 1
                    continue
                body = md.read_text(encoding="utf-8", errors="replace")
                first = next((ln.strip("# ").strip() for ln in body.splitlines() if ln.strip()), name)
                dest = self.root / name
                if dest.exists():
                    # Update only when source is newer
                    try:
                        if md.stat().st_mtime <= (dest / "SKILL.md").stat().st_mtime:
                            skipped += 1
                            continue
                    except Exception:
                        pass
                    shutil.copy2(str(md), str(dest / "SKILL.md"))
                    updated += 1
                else:
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(md), str(dest / "SKILL.md"))
                    (dest / "provenance.json").write_text(json.dumps(
                        {"name": name, "synced_from": str(md), "synced_at": time.time()}),
                        encoding="utf-8")
                    imported += 1
                if name not in self._skills:
                    self._skills[name] = SkillVersion(
                        name=name, description=first[:200],
                        triggers=[parts[-1].replace("-", " ")] if parts else [],
                        path=str(dest))
                    self._persist(self._skills[name])
            except Exception as e:
                logger.debug("skill sync skip %s: %s", md, e)
                skipped += 1
        return {"scanned": len(found), "imported": imported, "updated": updated,
                "skipped": skipped, "total": len(self._skills)}


class SkillForge:
    """Research→Design→Implement→Sandbox test→Evaluate→Package→Install→Version→Store."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def forge(self, need: str, body_md: str, triggers: Optional[List[str]] = None,
              test_fn: Any = None) -> Dict[str, Any]:
        name = "".join(c if (c.isalnum() or c in "-_") else "-" for c in need.lower().replace(" ", "-"))[:40].strip("-") or f"skill-{uuid.uuid4().hex[:6]}"
        if test_fn is not None:
            try:
                ok = bool(test_fn(body_md))
            except Exception as e:
                return {"success": False, "reason": f"sandbox test failed: {e}"}
            if not ok:
                return {"success": False, "reason": "sandbox test returned false"}
        s = self.registry.install(name, body_md, description=f"Forged for need: {need}", triggers=triggers or [])
        return {"success": True, "skill": s.to_dict()}

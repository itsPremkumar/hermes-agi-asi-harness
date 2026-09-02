"""skill_forge.py — Convert execution traces → parameterized skills → test → review → registry.

The forge turns raw execution traces (sequences of steps that succeeded or failed)
into named, parameterized skills that can be stored, tested, and reused.

Pipeline:
    trace → extract_pattern → parameterize → Skill object → test → review → registry

Module API:
- SkillParameter: a parameter in a skill's template
- Skill: a parameterized, testable unit of behaviour
- ForgeLog: result of running a skill against a test case
- SkillForge: the main forge — extract, test, review, register
- SkillRegistry: persistent store of validated skills
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class SkillParameter:
    """A single parameter extracted from a concrete trace."""

    name: str
    description: str = ""
    required: bool = True
    default: Any = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillParameter":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Skill:
    """A parameterized, testable skill."""

    name: str
    description: str
    template: str  # uses {param_name} placeholders
    parameters: list[SkillParameter] = field(default_factory=list)
    version: int = 1
    test_pass_rate: float = 0.0
    test_count: int = 0
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def instantiate(self, **kwargs: Any) -> str:
        """Render the template with given params. Raises on missing required param."""
        for p in self.parameters:
            if p.required and p.name not in kwargs and p.default is None:
                raise ValueError(f"Missing required parameter: {p.name}")
        merged = {p.name: p.default for p in self.parameters if p.default is not None}
        merged.update(kwargs)
        return self.template.format(**merged)

    def hash(self) -> str:
        """Stable content hash for dedup."""
        payload = json.dumps(
            {"name": self.name, "template": self.template, "parameters": [p.to_dict() for p in self.parameters]},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_skill_md(self) -> str:
        """Render this skill as a Hermes-compatible SKILL.md string."""
        frontmatter = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
        }
        lines = ["---"]
        for k, v in frontmatter.items():
            lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.name}")
        lines.append("")
        lines.append(self.description)
        lines.append("")
        if self.parameters:
            lines.append("## Parameters")
            lines.append("")
            for p in self.parameters:
                req = "required" if p.required else "optional"
                default = f", default: {p.default!r}" if p.default is not None else ""
                lines.append(f"- **{p.name}** ({req}){default}: {p.description}")
            lines.append("")
        lines.append("## Template")
        lines.append("")
        lines.append(f"```\n{self.template}\n```")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "parameters": [p.to_dict() for p in self.parameters],
            "version": self.version,
            "test_pass_rate": self.test_pass_rate,
            "test_count": self.test_count,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Skill":
        params = [SkillParameter.from_dict(p) for p in data.pop("parameters", [])]
        return cls(parameters=params, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ForgeLog:
    """Outcome of a single test run against a skill."""

    skill_name: str
    inputs: dict[str, Any]
    output: str
    success: bool
    duration: float = 0.0
    error: str = ""
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Forge
# ---------------------------------------------------------------------------


class SkillForge:
    """Turn execution traces into parameterized skills.

    Usage:
        forge = SkillForge()
        skill = forge.extract("write_file", template="Write {content} to {path}")
        forge.test(skill, [{"content": "hello", "path": "/tmp/a", "expected": "written"}])
        forge.register(skill)
    """

    def __init__(self) -> None:
        self.logs: list[ForgeLog] = []
        self.registry = SkillRegistry()

    # -- extraction --------------------------------------------------------

    def extract(
        self,
        name: str,
        *,
        description: str = "",
        template: str = "",
        parameters: list[SkillParameter] | None = None,
        source_trace: list[dict[str, Any]] | None = None,
    ) -> Skill:
        """Build a Skill. Either pass an explicit template, or pass a source_trace
        and the forge will auto-extract a template by replacing concrete values
        with {placeholders}."""
        if source_trace and not template:
            template = self._auto_template(source_trace)
        return Skill(
            name=name,
            description=description,
            template=template,
            parameters=parameters or [],
        )

    # -- testing -----------------------------------------------------------

    def test(
        self,
        skill: Skill,
        cases: list[dict[str, Any]],
        runner: Callable[..., str] | None = None,
        pass_fn: Callable[[str, Any], bool] | None = None,
    ) -> list[ForgeLog]:
        """Run a skill against test cases. Each case must contain the template
        params plus an 'expected' key (unless pass_fn is given).

        Returns list of ForgeLog. Updates skill.test_pass_rate and test_count.
        """
        if not cases:
            return []
        logs: list[ForgeLog] = []
        for case in cases:
            case = dict(case)
            expected = case.pop("expected", None)
            start = time.time()
            try:
                output = skill.instantiate(**case)
                if runner is not None:
                    output = runner(**case)
                success = pass_fn(output, expected) if pass_fn else (output == expected)
                error = ""
            except Exception as exc:  # noqa: BLE001
                output = ""
                success = False
                error = str(exc)
            duration = time.time() - start
            log = ForgeLog(
                skill_name=skill.name,
                inputs=case,
                output=str(output),
                success=success,
                duration=duration,
                error=error,
            )
            logs.append(log)
        self.logs.extend(logs)
        skill.test_count += len(logs)
        skill.test_pass_rate = sum(1 for l in logs if l.success) / len(logs)
        return logs

    # -- review & register -------------------------------------------------

    def review(self, skill: Skill, min_pass_rate: float = 0.8) -> dict[str, Any]:
        """Decide whether a skill passes review."""
        recent = [l for l in self.logs if l.skill_name == skill.name][-skill.test_count:]
        pass_rate = sum(1 for l in recent if l.success) / len(recent) if recent else 0.0
        avg_duration = statistics.mean(l.duration for l in recent) if recent else 0.0
        return {
            "name": skill.name,
            "pass": pass_rate >= min_pass_rate,
            "pass_rate": pass_rate,
            "avg_duration": avg_duration,
            "error_count": sum(1 for l in recent if l.error),
            "min_pass_rate": min_pass_rate,
        }

    def register(self, skill: Skill, min_pass_rate: float = 0.8) -> bool:
        """Attempt to register a skill. Returns True if accepted."""
        verdict = self.review(skill, min_pass_rate)
        if verdict["pass"]:
            self.registry.add(skill)
            return True
        return False

    # -- bulk --------------------------------------------------------------

    def forge_pipeline(
        self,
        name: str,
        *,
        description: str = "",
        template: str = "",
        parameters: list[SkillParameter] | None = None,
        source_trace: list[dict[str, Any]] | None = None,
        test_cases: list[dict[str, Any]] | None = None,
        min_pass_rate: float = 0.8,
        runner: Callable[..., str] | None = None,
    ) -> tuple[Skill, dict[str, Any]]:
        """Full forge pipeline: extract → test → review → register."""
        skill = self.extract(
            name,
            description=description,
            template=template,
            parameters=parameters,
            source_trace=source_trace,
        )
        if test_cases:
            self.test(skill, test_cases, runner=runner)
        verdict = self.review(skill, min_pass_rate)
        verdict["registered"] = self.register(skill, min_pass_rate)
        return skill, verdict

    # -- internal ----------------------------------------------------------

    @staticmethod
    def _auto_template(trace: list[dict[str, Any]]) -> str:
        """Auto-generate a template by replacing concrete values in successive
        steps with {placeholder} tokens based on key names."""
        if not trace:
            return ""
        parts: list[str] = []
        for step in trace:
            for key, value in step.items():
                parts.append(f"{key}={{{key}}}")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class SkillRegistry:
    """Persistent registry of validated skills (in-memory with JSON persistence)."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def add(self, skill: Skill) -> None:
        key = skill.name
        if key in self._skills:
            existing = self._skills[key]
            if skill.test_pass_rate >= existing.test_pass_rate:
                skill.version = existing.version + 1
                self._skills[key] = skill
        else:
            self._skills[key] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def remove(self, name: str) -> bool:
        return self._skills.pop(name, None) is not None

    def list(self, capability: str | None = None) -> list[Skill]:
        skills = list(self._skills.values())
        if capability:
            skills = [s for s in skills if s.metadata.get("capability") == capability]
        return sorted(skills, key=lambda s: s.test_pass_rate, reverse=True)

    def top(self, k: int = 5) -> list[Skill]:
        return sorted(self._skills.values(), key=lambda s: s.test_pass_rate, reverse=True)[:k]

    def stats(self) -> dict[str, Any]:
        if not self._skills:
            return {"count": 0, "avg_pass_rate": 0.0}
        rates = [s.test_pass_rate for s in self._skills.values()]
        return {
            "count": len(self._skills),
            "avg_pass_rate": statistics.mean(rates),
            "min_pass_rate": min(rates),
            "max_pass_rate": max(rates),
        }

    def save(self, path: str | Path) -> None:
        data = {name: skill.to_dict() for name, skill in self._skills.items()}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SkillRegistry":
        reg = cls()
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        for name, skill_data in raw.items():
            reg._skills[name] = Skill.from_dict(skill_data)
        return reg

    # -- Hermes plugin export ----------------------------------------------

    def export_hermes_skill(self, name: str, dest: str | Path) -> Path:
        """Export a skill as a Hermes-compatible skill plugin directory.

        Creates <dest>/<name>/SKILL.md with YAML frontmatter and body.
        """
        skill = self._skills.get(name)
        if skill is None:
            raise KeyError(f"Skill not found: {name}")
        dest = Path(dest) / name
        dest.mkdir(parents=True, exist_ok=True)
        skill_md = skill.to_skill_md()
        md_path = dest / "SKILL.md"
        md_path.write_text(skill_md, encoding="utf-8")
        return md_path

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills

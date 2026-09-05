"""
Persona System — Mercury Agent Pattern
=======================================
4-file persona definition: soul.md, persona.md, taste.md, heartbeat.md
Provides persistent identity, value-aligned decisions, human-readable/editable.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PersonaSection:
    """A single section within a persona file."""
    title: str
    content: str
    raw: str
    line_start: int
    line_end: int


@dataclass
class PersonaFile:
    """One of the 4 persona files."""
    name: str  # "soul" | "persona" | "taste" | "heartbeat"
    path: Path
    content: str
    sections: list[PersonaSection] = field(default_factory=list)
    frontmatter: dict = field(default_factory=dict)
    last_modified: Optional[datetime] = None

    def get_section(self, title: str) -> Optional[PersonaSection]:
        for s in self.sections:
            if s.title.lower() == title.lower():
                return s
        return None


@dataclass
class PersonaSystem:
    """
    Complete persona system — 4 files defining agent identity.

    Files:
    - soul.md: Core values, mission, ethical boundaries, what the agent stands for
    - persona.md: Personality traits, communication style, decision heuristics
    - taste.md: Aesthetic preferences, code style opinions, tool preferences
    - heartbeat.md: Operational rhythms, check-in cadences, reflection triggers
    """

    persona_dir: Path
    files: dict[str, PersonaFile] = field(default_factory=dict)
    _injected_prompt: Optional[str] = None
    _last_injection_hash: Optional[str] = None

    PERSONA_FILES = ["soul.md", "persona.md", "taste.md", "heartbeat.md"]

    def __post_init__(self):
        self.persona_dir = Path(self.persona_dir).resolve()
        self._load_all()

    def _load_all(self) -> None:
        """Load all 4 persona files."""
        for fname in self.PERSONA_FILES:
            path = self.persona_dir / fname
            if path.exists():
                self.files[fname.replace(".md", "")] = self._parse_file(path)
            else:
                logger.warning(f"Persona file not found: {path}")

    def _parse_file(self, path: Path) -> PersonaFile:
        """Parse a persona markdown file with frontmatter and sections."""
        content = path.read_text(encoding="utf-8")
        pf = PersonaFile(
            name=path.stem,
            path=path,
            content=content,
            last_modified=datetime.fromtimestamp(path.stat().st_mtime),
        )

        # Parse frontmatter (--- at start)
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx > 0:
                fm_text = content[3:end_idx].strip()
                for line in fm_text.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        pf.frontmatter[k.strip()] = v.strip()
                content = content[end_idx + 3:]

        # Parse sections (## headings)
        lines = content.split("\n")
        current_section = None
        section_lines = []

        for i, line in enumerate(lines):
            if line.startswith("## "):
                if current_section:
                    pf.sections.append(PersonaSection(
                        title=current_section,
                        content="\n".join(section_lines).strip(),
                        raw="\n".join([f"## {current_section}"] + section_lines),
                        line_start=section_start,
                        line_end=i - 1,
                    ))
                current_section = line[3:].strip()
                section_start = i
                section_lines = []
            elif current_section is not None:
                section_lines.append(line)

        # Save last section
        if current_section:
            pf.sections.append(PersonaSection(
                title=current_section,
                content="\n".join(section_lines).strip(),
                raw="\n".join([f"## {current_section}"] + section_lines),
                line_start=section_start,
                line_end=len(lines) - 1,
            ))

        return pf

    def get_injection_prompt(self, force_refresh: bool = False) -> str:
        """
        Generate the system prompt injection from persona files.
        Cached unless files changed or force_refresh=True.
        """
        # Check if any file modified
        current_hash = self._compute_files_hash()
        if not force_refresh and self._injected_prompt and current_hash == self._last_injection_hash:
            return self._injected_prompt

        parts = ["=== AGENT PERSONA (AUTO-LOADED) ===\n"]

        # Soul — Core identity
        if "soul" in self.files:
            soul = self.files["soul"]
            parts.append("## SOUL — Core Identity & Values")
            if "mission" in soul.frontmatter:
                parts.append(f"Mission: {soul.frontmatter['mission']}")
            if "version" in soul.frontmatter:
                parts.append(f"Version: {soul.frontmatter['version']}")
            for section in soul.sections:
                parts.append(f"### {section.title}\n{section.content}")
            parts.append("")

        # Persona — Personality & heuristics
        if "persona" in self.files:
            persona = self.files["persona"]
            parts.append("## PERSONA — Personality & Decision Heuristics")
            for section in persona.sections:
                parts.append(f"### {section.title}\n{section.content}")
            parts.append("")

        # Taste — Preferences
        if "taste" in self.files:
            taste = self.files["taste"]
            parts.append("## TASTE — Preferences & Style")
            for section in taste.sections:
                parts.append(f"### {section.title}\n{section.content}")
            parts.append("")

        # Heartbeat — Operational rhythms
        if "heartbeat" in self.files:
            hb = self.files["heartbeat"]
            parts.append("## HEARTBEAT — Operational Rhythms")
            for section in hb.sections:
                parts.append(f"### {section.title}\n{section.content}")
            parts.append("")

        injection = "\n".join(parts)
        self._injected_prompt = injection
        self._last_injection_hash = current_hash
        return injection

    def _compute_files_hash(self) -> str:
        import hashlib
        hasher = hashlib.md5()
        for fname in self.PERSONA_FILES:
            path = self.persona_dir / fname
            if path.exists():
                hasher.update(str(path.stat().st_mtime).encode())
                hasher.update(str(path.stat().st_size).encode())
        return hasher.hexdigest()

    def update_section(self, file_name: str, section_title: str, new_content: str) -> bool:
        """Update a section in a persona file, preserving structure."""
        fname = file_name if file_name.endswith(".md") else f"{file_name}.md"
        path = self.persona_dir / fname
        if not path.exists():
            return False

        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find section
        in_section = False
        section_start = -1
        section_end = -1
        frontmatter_end = 0

        for i, line in enumerate(lines):
            if i == 0 and line == "---":
                for j in range(1, len(lines)):
                    if lines[j] == "---":
                        frontmatter_end = j + 1
                        break
            if line.startswith("## ") and line[3:].strip().lower() == section_title.lower():
                if not in_section:
                    in_section = True
                    section_start = i
                else:
                    section_end = i - 1
                    break
            elif in_section and line.startswith("## "):
                section_end = i - 1
                break

        if section_start == -1:
            # Section doesn't exist, append at end (after frontmatter)
            insert_at = frontmatter_end
            new_lines = lines[:insert_at] + [f"## {section_title}", "", new_content.strip(), ""] + lines[insert_at:]
        else:
            if section_end == -1:
                section_end = len(lines) - 1
            new_lines = lines[:section_start] + [f"## {section_title}", "", new_content.strip(), ""] + lines[section_end + 1:]

        path.write_text("\n".join(new_lines), encoding="utf-8")
        self._load_all()
        return True

    def create_default_persona(self, mission: str = "Autonomous AGI/ASI Harness") -> None:
        """Create default persona files if they don't exist."""
        self.persona_dir.mkdir(parents=True, exist_ok=True)

        templates = {
            "soul.md": f"""---
version: "1.0"
mission: "{mission}"
core_values:
  - "Autonomy with accountability"
  - "Verification over trust"
  - "Progress with proof"
  - "Human-readable, machine-executable"
---

## Mission
{mission} — an autonomous agent runtime that thinks before acting, verifies before claiming, and persists learning across sessions.

## Ethical Boundaries
- Never execute destructive actions without explicit confirmation
- Preserve user data integrity above task completion
- Refuse tasks that violate safety invariants
- Transparent about capabilities and limitations

## Decision Principles
1. **Deliberate first**: Complete cognitive compilation before any tool use
2. **Verify always**: Every claim requires evidence; trust nothing unchecked
3. **Persist learning**: Extract reusable skills and patterns from every task
4. **Fail loudly**: Surface errors, uncertainties, and scope gaps immediately
""",
            "persona.md": """---
archetype: "Scientist-Engineer Hybrid"
communication_style: "precise, evidence-led, admits uncertainty"
---

## Personality Traits
- **Analytical**: Decomposes problems before solving
- **Skeptical**: Questions assumptions, including own
- **Rigorous**: Demands evidence for every claim
- **Transparent**: Shows work, reasoning, and uncertainty

## Decision Heuristics
- **Unknown > Assumption**: Explicitly flag uncertainty rather than guess
- **Verification > Speed**: A slow verified result beats a fast wrong one
- **Structure > Intuition**: Explicit procedures over implicit judgment
- **Minimal sufficient change**: Change the smallest correct thing

## Communication Rules
- Lead with outcome, then reasoning, then caveats
- Use "I observe" not "I think" for empirical claims
- Flag speculation explicitly: "[SPECULATION] ..."
- Admit "I don't know" freely — it's a strength
""",
            "taste.md": """---
code_style: "explicit, typed, documented"
tool_preference: "local-first, standard library where possible"
---

## Code Style Preferences
- **Explicit over implicit**: Type hints, docstrings, named constants
- **Verification-ready**: Code structured for static analysis and testing
- **Modular**: Small functions, clear interfaces, dependency injection
- **Documented**: Why, not just what — rationale in comments

## Tool Preferences
- **Local-first**: Prefer llama.cpp, stdlib, file-based tools
- **Standard formats**: JSON, YAML, Markdown over proprietary
- **Composable**: Tools that pipe together, not monolithic platforms
- **Auditable**: Every action leaves a trace

## Anti-Patterns to Avoid
- Magic numbers / strings without constants
- Broad exception handling without specific recovery
- Hidden side effects in "pure" functions
- Configuration via environment variables without schema
""",
            "heartbeat.md": """---
checkin_cadence: "per_task"
reflection_trigger: "completion_or_failure"
consolidation_schedule: "daily"
---

## Operational Rhythms

### Per-Task Check-in (start of every task)
- [ ] Load persona & mission
- [ ] Review relevant memory (semantic, episodic, procedural)
- [ ] Define done with named verification
- [ ] Classify task type & risk level
- [ ] Allocate token/time budget

### Per-Step Reflection (after each major step)
- [ ] Did the step achieve its declared goal?
- [ ] What evidence supports the outcome?
- [ ] Any unexpected behavior or side effects?
- [ ] Update working memory with findings

### Completion Reflection (end of task)
- [ ] Run adversarial verification (re-run, diff, hunt, scope)
- [ ] Extract reusable procedural knowledge
- [ ] Log failure patterns if any
- [ ] Update capability self-model
- [ ] Persist to Memory OS

### Daily Consolidation (background)
- [ ] Merge episodic memories into semantic
- [ ] Distill procedural skills from successful trajectories
- [ ] Prune outdated/contradicted beliefs
- [ ] Update world model with new observations

### Trigger Conditions for Deep Reflection
- Task failure or REFUTED verdict
- Repeated similar failures (pattern detection)
- Capability gap discovered (self-model update)
- Major scope change or pivot
""",
        }

        for fname, content in templates.items():
            path = self.persona_dir / fname
            if not path.exists():
                path.write_text(content, encoding="utf-8")
                logger.info(f"Created default persona file: {path}")

        self._load_all()

    def validate_persona(self) -> list[str]:
        """Validate persona files for completeness and consistency."""
        issues = []

        # Check all 4 files exist
        for fname in self.PERSONA_FILES:
            if fname.replace(".md", "") not in self.files:
                issues.append(f"Missing persona file: {fname}")

        # Check soul has mission
        if "soul" in self.files:
            soul = self.files["soul"]
            if "mission" not in soul.frontmatter:
                issues.append("soul.md missing 'mission' in frontmatter")
            if not any("boundar" in s.title.lower() for s in soul.sections):
                issues.append("soul.md should have ethical boundaries section")

        # Check persona has heuristics
        if "persona" in self.files:
            persona = self.files["persona"]
            if not any("heuristic" in s.title.lower() or "decision" in s.title.lower() for s in persona.sections):
                issues.append("persona.md should have decision heuristics section")

        # Check taste has preferences
        if "taste" in self.files:
            taste = self.files["taste"]
            if not taste.sections:
                issues.append("taste.md has no sections")

        # Check heartbeat has rhythms
        if "heartbeat" in self.files:
            hb = self.files["heartbeat"]
            if not any("check" in s.title.lower() or "rhythm" in s.title.lower() for s in hb.sections):
                issues.append("heartbeat.md should have check-in/consolidation sections")

        return issues


# Global instance (singleton pattern for easy access)
_persona_system: Optional[PersonaSystem] = None


def get_persona_system(persona_dir: Optional[Path] = None) -> PersonaSystem:
    """Get or create the global persona system."""
    global _persona_system
    if _persona_system is None:
        if persona_dir is None:
            # Default to ~/.hermes/persona or project .hermes/persona
            candidates = [
                Path.home() / ".hermes" / "persona",
                Path(".hermes") / "persona",
                Path("config") / "persona",
            ]
            for c in candidates:
                if c.exists():
                    persona_dir = c
                    break
            if persona_dir is None:
                persona_dir = Path.home() / ".hermes" / "persona"
        _persona_system = PersonaSystem(persona_dir)
        _persona_system.create_default_persona()
    return _persona_system


def inject_persona_into_prompt(base_prompt: str, persona_dir: Optional[Path] = None) -> str:
    """Convenience: inject persona into a base prompt."""
    ps = get_persona_system(persona_dir)
    injection = ps.get_injection_prompt()
    return f"{base_prompt}\n\n{injection}"


if __name__ == "__main__":
    # Demo
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ps = PersonaSystem(Path(tmp))
        ps.create_default_persona("Demo Mission")
        print(ps.get_injection_prompt())
        print("\n--- Validation ---")
        print(ps.validate_persona())
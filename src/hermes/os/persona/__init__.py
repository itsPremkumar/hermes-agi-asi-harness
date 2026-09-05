"""
Persona System — Mercury Agent Pattern
=======================================
4-file persona definition: soul.md, persona.md, taste.md, heartbeat.md
"""

from .persona import (
    PersonaSystem,
    PersonaFile,
    PersonaSection,
    get_persona_system,
    inject_persona_into_prompt,
)

__all__ = [
    "PersonaSystem",
    "PersonaFile",
    "PersonaSection",
    "get_persona_system",
    "inject_persona_into_prompt",
]
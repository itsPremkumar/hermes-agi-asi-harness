"""Specification Parser — parse formal specifications from multiple formats."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class SpecFormat(Enum):
    Z = "z"
    TLA = "tla"
    ALLOY = "alloy"
    ACL2 = "acl2"
    COQ = "coq"
    LEAN = "lean"
    CUSTOM = "custom"


@dataclass
class Specification:
    """A formal specification."""
    id: str
    name: str
    format: SpecFormat
    content: str
    variables: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseResult:
    """Result of parsing a specification."""
    spec_id: str
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    spec: Optional[Specification] = None


class SpecificationParser:
    """Parse formal specifications from various formats."""

    def __init__(self):
        self._specs: dict[str, Specification] = {}
        self._parsers = {
            SpecFormat.Z: self._parse_z,
            SpecFormat.TLA: self._parse_tla,
            SpecFormat.ALLOY: self._parse_alloy,
            SpecFormat.ACL2: self._parse_acl2,
            SpecFormat.COQ: self._parse_coq,
            SpecFormat.LEAN: self._parse_lean,
            SpecFormat.CUSTOM: self._parse_custom,
        }

    def register(self, spec: Specification) -> None:
        self._specs[spec.id] = spec

    def get(self, spec_id: str) -> Optional[Specification]:
        return self._specs.get(spec_id)

    def parse(self, content: str, format: SpecFormat, spec_id: str = "", name: str = "") -> ParseResult:
        """Parse a specification from content."""
        parser = self._parsers.get(format, self._parse_custom)
        return parser(content, spec_id, name)

    def _parse_z(self, content: str, spec_id: str, name: str) -> ParseResult:
        """Parse Z notation."""
        errors = []
        variables = re.findall(r'(\w+)\s*:\s*[\w\s\[\]]+', content)
        invariants = [line.strip() for line in content.split('\n') if '∀' in line or '∃' in line or '⇒' in line]

        spec = Specification(
            id=spec_id or f"z_{len(self._specs)}",
            name=name or "Z Specification",
            format=SpecFormat.Z,
            content=content,
            variables=variables,
            invariants=invariants,
        )
        self._specs[spec.id] = spec
        return ParseResult(spec_id=spec.id, success=True, spec=spec, errors=errors)

    def _parse_tla(self, content: str, spec_id: str, name: str) -> ParseResult:
        """Parse TLA+ specification."""
        errors = []
        variables = re.findall(r'VARIABLES?\s+([\w\s,]+)', content, re.IGNORECASE)
        invariants = re.findall(r'INVARIANT\s+(\w+)', content, re.IGNORECASE)

        spec = Specification(
            id=spec_id or f"tla_{len(self._specs)}",
            name=name or "TLA+ Specification",
            format=SpecFormat.TLA,
            content=content,
            variables=[v.strip() for v in variables[0].split(',')] if variables else [],
            invariants=invariants,
        )
        self._specs[spec.id] = spec
        return ParseResult(spec_id=spec.id, success=True, spec=spec, errors=errors)

    def _parse_alloy(self, content: str, spec_id: str, name: str) -> ParseResult:
        """Parse Alloy specification."""
        errors = []
        facts = re.findall(r'fact\s+(\w+)', content, re.IGNORECASE)
        assertions = re.findall(r'assert\s+(\w+)', content, re.IGNORECASE)

        spec = Specification(
            id=spec_id or f"alloy_{len(self._specs)}",
            name=name or "Alloy Specification",
            format=SpecFormat.ALLOY,
            content=content,
            invariants=facts + assertions,
        )
        self._specs[spec.id] = spec
        return ParseResult(spec_id=spec.id, success=True, spec=spec, errors=errors)

    def _parse_acl2(self, content: str, spec_id: str, name: str) -> ParseResult:
        """Parse ACL2 specification."""
        errors = []
        functions = re.findall(r'defun\s+(\w+)', content)

        spec = Specification(
            id=spec_id or f"acl2_{len(self._specs)}",
            name=name or "ACL2 Specification",
            format=SpecFormat.ACL2,
            content=content,
            variables=functions,
        )
        self._specs[spec.id] = spec
        return ParseResult(spec_id=spec.id, success=True, spec=spec, errors=errors)

    def _parse_coq(self, content: str, spec_id: str, name: str) -> ParseResult:
        """Parse Coq specification."""
        errors = []
        theorems = re.findall(r'Theorem\s+(\w+)', content)
        lemmas = re.findall(r'Lemma\s+(\w+)', content)

        spec = Specification(
            id=spec_id or f"coq_{len(self._specs)}",
            name=name or "Coq Specification",
            format=SpecFormat.COQ,
            content=content,
            invariants=theorems + lemmas,
        )
        self._specs[spec.id] = spec
        return ParseResult(spec_id=spec.id, success=True, spec=spec, errors=errors)

    def _parse_lean(self, content: str, spec_id: str, name: str) -> ParseResult:
        """Parse Lean specification."""
        errors = []
        theorems = re.findall(r'theorem\s+(\w+)', content, re.IGNORECASE)

        spec = Specification(
            id=spec_id or f"lean_{len(self._specs)}",
            name=name or "Lean Specification",
            format=SpecFormat.LEAN,
            content=content,
            invariants=theorems,
        )
        self._specs[spec.id] = spec
        return ParseResult(spec_id=spec.id, success=True, spec=spec, errors=errors)

    def _parse_custom(self, content: str, spec_id: str, name: str) -> ParseResult:
        """Parse custom specification format."""
        spec = Specification(
            id=spec_id or f"custom_{len(self._specs)}",
            name=name or "Custom Specification",
            format=SpecFormat.CUSTOM,
            content=content,
        )
        self._specs[spec.id] = spec
        return ParseResult(spec_id=spec.id, success=True, spec=spec)

    def list_specs(self) -> list[str]:
        return list(self._specs.keys())

    def get_all(self) -> list[Specification]:
        return list(self._specs.values())


__all__ = [
    "SpecificationParser",
    "Specification",
    "SpecFormat",
    "ParseResult",
]

"""ARC-AGI-3 Rule Inference Engine — infer transformation rules from examples."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleType(str, Enum):
    """Types of transformation rules."""
    IDENTITY = "identity"
    ROTATE = "rotate"
    FLIP = "flip"
    SCALE = "scale"
    TRANSLATE = "translate"
    COLOR_MAP = "color_map"
    FILL = "fill"
    BORDER = "border"
    PATTERN = "pattern"
    SHAPE_MATCH = "shape_match"
    COUNT = "count"
    SORT = "sort"
    FILTER = "filter"
    MERGE = "merge"
    SPLIT = "split"
    UNKNOWN = "unknown"


@dataclass
class Rule:
    """An inferred rule."""
    id: str
    rule_type: RuleType
    confidence: float  # 0.0 to 1.0
    description: str
    params: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Example:
    """A single input/output example."""
    id: str
    input_grid: list[list[int]]
    output_grid: list[list[int]]
    metadata: dict[str, Any] = field(default_factory=dict)


class RuleInferenceEngine:
    """Infer transformation rules from input/output examples."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._rules: list[Rule] = []

    def infer(self, examples: list[Example]) -> list[Rule]:
        """Infer rules from a list of examples."""
        if not examples:
            return []

        rules: list[Rule] = []

        # Check for identity
        identity_rule = self._check_identity(examples)
        if identity_rule:
            rules.append(identity_rule)

        # Check for rotation
        rotate_rule = self._check_rotation(examples)
        if rotate_rule:
            rules.append(rotate_rule)

        # Check for flip
        flip_rule = self._check_flip(examples)
        if flip_rule:
            rules.append(flip_rule)

        # Check for color mapping
        color_rule = self._check_color_map(examples)
        if color_rule:
            rules.append(color_rule)

        # Check for scale
        scale_rule = self._check_scale(examples)
        if scale_rule:
            rules.append(scale_rule)

        # Check for fill
        fill_rule = self._check_fill(examples)
        if fill_rule:
            rules.append(fill_rule)

        # Check for border
        border_rule = self._check_border(examples)
        if border_rule:
            rules.append(border_rule)

        self._rules = rules
        return rules

    def _check_identity(self, examples: list[Example]) -> Rule | None:
        """Check if output is identical to input."""
        for ex in examples:
            if ex.input_grid != ex.output_grid:
                return None
        return Rule(
            id=str(uuid.uuid4()),
            rule_type=RuleType.IDENTITY,
            confidence=1.0,
            description="Output is identical to input",
        )

    def _check_rotation(self, examples: list[Example]) -> Rule | None:
        """Check if output is a rotation of input."""
        for ex in examples:
            inp = ex.input_grid
            out = ex.output_grid
            if not inp or not out:
                return None
            # Check 90 degree rotation
            rows = len(inp)
            cols = len(inp[0]) if inp else 0
            if len(out) != cols or (out and len(out[0]) != rows):
                return None
            rotated = True
            for r in range(rows):
                for c in range(cols):
                    if inp[r][c] != out[c][rows - 1 - r]:
                        rotated = False
                        break
                if not rotated:
                    break
            if not rotated:
                return None
        return Rule(
            id=str(uuid.uuid4()),
            rule_type=RuleType.ROTATE,
            confidence=0.9,
            description="Output is input rotated 90 degrees clockwise",
            params={"degrees": 90},
        )

    def _check_flip(self, examples: list[Example]) -> Rule | None:
        """Check if output is a flip of input."""
        for ex in examples:
            inp = ex.input_grid
            out = ex.output_grid
            if not inp or not out:
                return None
            # Check horizontal flip
            for r in range(len(inp)):
                if inp[r] != out[r][::-1]:
                    return None
        return Rule(
            id=str(uuid.uuid4()),
            rule_type=RuleType.FLIP,
            confidence=0.9,
            description="Output is input flipped horizontally",
        )

    def _check_color_map(self, examples: list[Example]) -> Rule | None:
        """Check if output is a color mapping of input."""
        mapping: dict[int, int] = {}
        for ex in examples:
            inp = ex.input_grid
            out = ex.output_grid
            if not inp or not out:
                return None
            for r in range(len(inp)):
                for c in range(len(inp[r])):
                    inp_val = inp[r][c]
                    out_val = out[r][c] if r < len(out) and c < len(out[r]) else None
                    if out_val is None:
                        return None
                    if inp_val in mapping:
                        if mapping[inp_val] != out_val:
                            return None
                    else:
                        mapping[inp_val] = out_val
        if mapping:
            return Rule(
                id=str(uuid.uuid4()),
                rule_type=RuleType.COLOR_MAP,
                confidence=0.85,
                description=f"Color mapping: {mapping}",
                params={"mapping": mapping},
            )
        return None

    def _check_scale(self, examples: list[Example]) -> Rule | None:
        """Check if output is a scaled version of input."""
        for ex in examples:
            inp = ex.input_grid
            out = ex.output_grid
            if not inp or not out:
                return None
            in_rows = len(inp)
            in_cols = len(inp[0]) if inp else 0
            out_rows = len(out)
            out_cols = len(out[0]) if out else 0
            if out_rows % in_rows != 0 or out_cols % in_cols != 0:
                return None
        return Rule(
            id=str(uuid.uuid4()),
            rule_type=RuleType.SCALE,
            confidence=0.7,
            description="Output is a scaled version of input",
        )

    def _check_fill(self, examples: list[Example]) -> Rule | None:
        """Check if output involves filling regions."""
        for ex in examples:
            inp = ex.input_grid
            out = ex.output_grid
            if not inp or not out:
                return None
            # Check if same dimensions
            if len(inp) != len(out):
                return None
        return Rule(
            id=str(uuid.uuid4()),
            rule_type=RuleType.FILL,
            confidence=0.6,
            description="Output involves filling regions",
        )

    def _check_border(self, examples: list[Example]) -> Rule | None:
        """Check if output adds a border."""
        for ex in examples:
            inp = ex.input_grid
            out = ex.output_grid
            if not inp or not out:
                return None
            if len(out) != len(inp) + 2 or (out and len(out[0]) != len(inp[0]) + 2):
                return None
        return Rule(
            id=str(uuid.uuid4()),
            rule_type=RuleType.BORDER,
            confidence=0.75,
            description="Output adds a border around input",
        )

    def get_best_rule(self) -> Rule | None:
        """Get the highest confidence rule."""
        if not self._rules:
            return None
        return max(self._rules, key=lambda r: r.confidence)

    def apply_rule(self, rule: Rule, grid: list[list[int]]) -> list[list[int]]:
        """Apply a rule to a grid."""
        if rule.rule_type == RuleType.IDENTITY:
            return [row[:] for row in grid]
        elif rule.rule_type == RuleType.ROTATE:
            return self._rotate(grid)
        elif rule.rule_type == RuleType.FLIP:
            return self._flip(grid)
        elif rule.rule_type == RuleType.COLOR_MAP:
            mapping = rule.params.get("mapping", {})
            return [[mapping.get(c, c) for c in row] for row in grid]
        return grid

    def _rotate(self, grid: list[list[int]]) -> list[list[int]]:
        """Rotate grid 90 degrees clockwise."""
        if not grid:
            return []
        rows = len(grid)
        cols = len(grid[0])
        return [[grid[rows - 1 - r][c] for r in range(rows)] for c in range(cols)]

    def _flip(self, grid: list[list[int]]) -> list[list[int]]:
        """Flip grid horizontally."""
        return [row[::-1] for row in grid]

    def get_state(self) -> dict[str, Any]:
        return {
            "rules_found": len(self._rules),
            "best_rule": self.get_best_rule().rule_type.value if self.get_best_rule() else None,
        }

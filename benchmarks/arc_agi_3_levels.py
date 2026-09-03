"""ARC-AGI-3 Levels — difficulty-based level definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Level:
    """An ARC-AGI-3 difficulty level."""
    id: int
    name: str
    description: str
    grid_size: tuple[int, int]
    colors: int
    complexity: int
    metadata: dict[str, Any] = field(default_factory=dict)


ARC_AGI_3_LEVELS: list[Level] = [
    Level(1, "Basic Pattern Recognition", "Identify simple patterns", (3, 3), 2, 1),
    Level(2, "Color Matching", "Match colors in grids", (3, 3), 3, 2),
    Level(3, "Shape Detection", "Detect basic shapes", (4, 4), 3, 3),
    Level(4, "Rotation", "Handle rotated patterns", (4, 4), 4, 4),
    Level(5, "Reflection", "Handle reflected patterns", (5, 5), 4, 5),
    Level(6, "Translation", "Handle translated patterns", (5, 5), 5, 6),
    Level(7, "Scaling", "Handle scaled patterns", (6, 6), 5, 7),
    Level(8, "Composition", "Combine multiple patterns", (6, 6), 6, 8),
    Level(9, "Abstraction", "Abstract pattern recognition", (7, 7), 6, 9),
    Level(10, "Generalization", "Generalize across patterns", (8, 8), 7, 10),
    Level(11, "Complex Composition", "Complex pattern composition", (9, 9), 7, 11),
    Level(12, "Hierarchical Patterns", "Hierarchical pattern recognition", (10, 10), 8, 12),
    Level(13, "Recursive Patterns", "Recursive pattern detection", (10, 10), 8, 13),
    Level(14, "Non-local Dependencies", "Handle non-local dependencies", (12, 12), 9, 14),
    Level(15, "Full Reasoning", "Full abstract reasoning", (15, 15), 10, 15),
]


def get_level(level_id: int) -> Level | None:
    """Get a level by ID."""
    for level in ARC_AGI_3_LEVELS:
        if level.id == level_id:
            return level
    return None


def get_levels_by_complexity(min_complexity: int = 0, max_complexity: int = 15) -> list[Level]:
    """Get levels within a complexity range."""
    return [l for l in ARC_AGI_3_LEVELS if min_complexity <= l.complexity <= max_complexity]


def get_max_level() -> int:
    """Get the maximum level ID."""
    return max(l.id for l in ARC_AGI_3_LEVELS)


__all__ = ["Level", "ARC_AGI_3_LEVELS", "get_level", "get_levels_by_complexity", "get_max_level"]

"""CanvasUI — visual canvas and diagramming."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ElementType(str, Enum):
    RECT = "rect"
    CIRCLE = "circle"
    TEXT = "text"
    LINE = "line"
    ARROW = "arrow"


@dataclass
class CanvasElement:
    id: str
    element_type: ElementType
    x: float
    y: float
    width: float
    height: float
    metadata: dict[str, Any] = field(default_factory=dict)


class CanvasUI:
    """Manage canvas elements."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._elements: dict[str, CanvasElement] = {}

    def add(self, element_type: ElementType, x: float, y: float, width: float, height: float,
            metadata: dict[str, Any] | None = None) -> CanvasElement:
        element = CanvasElement(id=str(uuid.uuid4()), element_type=element_type, x=x, y=y, width=width, height=height, metadata=metadata or {})
        self._elements[element.id] = element
        return element

    def remove(self, element_id: str) -> bool:
        return self._elements.pop(element_id, None) is not None

    def get(self, element_id: str) -> CanvasElement | None:
        return self._elements.get(element_id)

    def list_all(self) -> list[CanvasElement]:
        return list(self._elements.values())

    def clear(self) -> None:
        self._elements.clear()

    def count(self) -> int:
        return len(self._elements)

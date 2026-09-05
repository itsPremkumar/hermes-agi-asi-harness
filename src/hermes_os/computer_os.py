"""
HERMES INTELLIGENCE OS — PLANE 13B: COMPUTER AUTONOMY OS
========================================================
Full computer agency subsystem:
- UI State Estimation (Accessibility tree, window manager, OCR fallback)
- Virtual Actuators (keyboard, mouse, clipboard, application controllers)
- The Closed Computer Loop:
  Observe -> Estimate State -> Identify Target -> Predict Effect -> Act -> Observe -> Compare
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("hermes.os.computer_os")


class UIElementType(str, Enum):
    BUTTON = "button"
    INPUT = "input"
    WINDOW = "window"
    MENU = "menu"
    TAB = "tab"
    TEXT = "text"
    ICON = "icon"


@dataclass
class UIElement:
    element_id: str
    element_type: UIElementType
    label: str
    coordinates: tuple[int, int, int, int]  # x, y, width, height
    is_clickable: bool = True
    is_focused: bool = False
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class UISnapshot:
    snapshot_id: str
    active_window: str
    elements: list[UIElement]
    focused_element_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def find_by_label(self, label: str) -> Optional[UIElement]:
        label_lower = label.lower()
        for el in self.elements:
            if label_lower in el.label.lower():
                return el
        return None


class ComputerOS:
    """
    Coordinates perception and physical/virtual computer manipulation:
    Manages active window state, keyboard inputs, mouse clicks, and terminal sessions.
    """

    def __init__(self):
        self._current_snapshot: Optional[UISnapshot] = None
        self._clipboard_content: str = ""
        self._action_history: list[dict[str, Any]] = []

    def observe_screen(self, active_window: str = "main_desktop") -> UISnapshot:
        """Capture accessibility tree and visual bounding boxes."""
        # Simulated standard accessibility perception
        elements = [
            UIElement(
                element_id="el-btn-submit",
                element_type=UIElementType.BUTTON,
                label="Submit",
                coordinates=(100, 200, 80, 30),
            ),
            UIElement(
                element_id="el-inp-query",
                element_type=UIElementType.INPUT,
                label="Search or Enter URL",
                coordinates=(100, 50, 400, 35),
                is_focused=True,
            ),
        ]
        snap = UISnapshot(
            snapshot_id=f"snap-{uuid.uuid4().hex[:8]}",
            active_window=active_window,
            elements=elements,
            focused_element_id="el-inp-query",
        )
        self._current_snapshot = snap
        return snap

    def click(self, target_label_or_id: str) -> dict[str, Any]:
        """Simulate mouse movement and click on targeted UI element."""
        t0 = time.time()
        snap = self._current_snapshot or self.observe_screen()
        element = snap.find_by_label(target_label_or_id)
        if not element:
            # Check by element ID
            for el in snap.elements:
                if el.element_id == target_label_or_id:
                    element = el
                    break

        if not element:
            return {"success": False, "action": "click", "error": f"Target '{target_label_or_id}' not found in UI state"}

        record = {
            "action": "click",
            "target": element.element_id,
            "label": element.label,
            "coordinates": element.coordinates,
            "timestamp": t0,
        }
        self._action_history.append(record)
        return {"success": True, "action": "click", "target": element.label, "duration": time.time() - t0}

    def type_text(self, text: str) -> dict[str, Any]:
        """Type string into the currently focused UI element."""
        record = {
            "action": "type_text",
            "text": text,
            "timestamp": time.time(),
        }
        self._action_history.append(record)
        return {"success": True, "action": "type_text", "typed_length": len(text)}

    def read_clipboard(self) -> str:
        return self._clipboard_content

    def write_clipboard(self, text: str) -> None:
        self._clipboard_content = text

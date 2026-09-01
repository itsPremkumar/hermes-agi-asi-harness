"""Deep Research Engine — Frontend UI components."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UIComponent:
    """A UI component."""
    id: str
    component_type: str
    props: dict[str, Any] = field(default_factory=dict)
    children: list["UIComponent"] = field(default_factory=list)


class DeepResearchFrontend:
    """Frontend UI for the Deep Research Engine."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._components: dict[str, UIComponent] = {}

    def create_topic_input(self) -> UIComponent:
        """Create topic input component."""
        component = UIComponent(
            id="topic_input",
            component_type="text_input",
            props={
                "label": "Research Topic",
                "placeholder": "Enter a research topic...",
                "required": True,
            },
        )
        self._components[component.id] = component
        return component

    def create_depth_selector(self) -> UIComponent:
        """Create depth selector component."""
        component = UIComponent(
            id="depth_selector",
            component_type="select",
            props={
                "label": "Research Depth",
                "options": [
                    {"value": 1, "label": "Basic (1)"},
                    {"value": 2, "label": "Standard (2)"},
                    {"value": 3, "label": "Deep (3)"},
                    {"value": 4, "label": "Comprehensive (4)"},
                    {"value": 5, "label": "Exhaustive (5)"},
                ],
                "default_value": 3,
            },
        )
        self._components[component.id] = component
        return component

    def create_progress_bar(self, progress: float = 0.0) -> UIComponent:
        """Create progress bar component."""
        component = UIComponent(
            id="progress_bar",
            component_type="progress_bar",
            props={
                "progress": progress,
                "label": f"{int(progress * 100)}% Complete",
            },
        )
        self._components[component.id] = component
        return component

    def create_phase_list(self, phases: list[dict[str, Any]]) -> UIComponent:
        """Create phase list component."""
        children = []
        for phase in phases:
            child = UIComponent(
                id=f"phase_{phase['id']}",
                component_type="phase_item",
                props=phase,
            )
            children.append(child)

        component = UIComponent(
            id="phase_list",
            component_type="list",
            props={"title": "Research Phases"},
            children=children,
        )
        self._components[component.id] = component
        return component

    def create_results_view(self, results: dict[str, Any]) -> UIComponent:
        """Create results view component."""
        component = UIComponent(
            id="results_view",
            component_type="results",
            props={
                "title": "Research Results",
                "data": results,
            },
        )
        self._components[component.id] = component
        return component

    def create_session_card(self, session: dict[str, Any]) -> UIComponent:
        """Create session card component."""
        component = UIComponent(
            id=f"session_{session['id']}",
            component_type="card",
            props=session,
        )
        self._components[component.id] = component
        return component

    def get_component(self, component_id: str) -> UIComponent | None:
        """Get a UI component."""
        return self._components.get(component_id)

    def list_components(self) -> list[UIComponent]:
        """List all UI components."""
        return list(self._components.values())

    def remove_component(self, component_id: str) -> bool:
        """Remove a UI component."""
        if component_id in self._components:
            del self._components[component_id]
            return True
        return False

    def render_dashboard(self, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """Render the main dashboard."""
        return {
            "title": "Deep Research Dashboard",
            "sessions": sessions,
            "total_sessions": len(sessions),
            "components": len(self._components),
        }

    def render_session_detail(self, session: dict[str, Any]) -> dict[str, Any]:
        """Render session detail view."""
        return {
            "title": f"Session: {session.get('topic', 'Unknown')}",
            "session": session,
            "phases": session.get("phases", []),
            "result": session.get("result", {}),
        }

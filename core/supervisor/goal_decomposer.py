"""Goal Decomposer — Hierarchical decomposition of mission contracts.

Decomposes missions into a hierarchy:
    Mission → Goals → Sub-goals → Tasks → Actions

Supports dynamic re-decomposition when new complexity is discovered.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class GoalLevel(str, Enum):
    """Levels in the goal hierarchy."""
    MISSION = "mission"
    GOAL = "goal"
    SUBGOAL = "subgoal"
    TASK = "task"
    ACTION = "action"


class GoalStatus(str, Enum):
    """Status of a goal."""
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class GoalNode:
    """A node in the goal hierarchy."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    level: GoalLevel = GoalLevel.MISSION
    title: str = ""
    description: str = ""
    status: GoalStatus = GoalStatus.PENDING

    # Hierarchy
    parent_id: str = ""
    children: List[str] = field(default_factory=list)

    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # IDs of goals that must complete first

    # Requirements
    required_capabilities: List[str] = field(default_factory=list)
    required_resources: List[str] = field(default_factory=list)

    # Success criteria
    success_criteria: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)

    # Assignment
    assigned_to: str = ""  # Worker ID

    # Progress
    progress: float = 0.0  # 0.0 to 1.0
    confidence: float = 1.0
    risk: float = 0.0

    # Health
    health: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self) -> bool:
        """Check if this goal is ready to execute."""
        return self.status == GoalStatus.READY

    def is_complete(self) -> bool:
        """Check if this goal is complete."""
        return self.status == GoalStatus.COMPLETED

    def is_blocked(self) -> bool:
        """Check if this goal is blocked."""
        return self.status == GoalStatus.BLOCKED

    def update_health(self) -> None:
        """Update health metrics."""
        self.health = {
            "progress": self.progress,
            "confidence": self.confidence,
            "risk": self.risk,
            "dependency_health": 1.0,  # Will be computed by manager
            "resource_health": 1.0,
            "schedule_health": 1.0,
            "blockers": [],
        }


@dataclass
class GoalHierarchy:
    """A complete goal hierarchy for a mission."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mission_id: str = ""
    root_id: str = ""  # Root goal ID
    nodes: Dict[str, GoalNode] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[GoalNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> List[GoalNode]:
        """Get children of a node."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[cid] for cid in node.children if cid in self.nodes]

    def get_ready_tasks(self) -> List[GoalNode]:
        """Get all tasks that are ready to execute."""
        return [
            node for node in self.nodes.values()
            if node.level == GoalLevel.TASK and node.status == GoalStatus.READY
        ]

    def get_blocked_tasks(self) -> List[GoalNode]:
        """Get all blocked tasks."""
        return [
            node for node in self.nodes.values()
            if node.level == GoalLevel.TASK and node.status == GoalStatus.BLOCKED
        ]

    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress."""
        total = len([n for n in self.nodes.values() if n.level == GoalLevel.TASK])
        completed = len([n for n in self.nodes.values() if n.level == GoalLevel.TASK and n.status == GoalStatus.COMPLETED])
        in_progress = len([n for n in self.nodes.values() if n.level == GoalLevel.TASK and n.status == GoalStatus.IN_PROGRESS])
        blocked = len([n for n in self.nodes.values() if n.level == GoalLevel.TASK and n.status == GoalStatus.BLOCKED])

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "blocked": blocked,
            "percent": (completed / total * 100) if total > 0 else 0,
        }


class GoalDecomposer:
    """Decompose mission contracts into hierarchical goal structures."""

    def __init__(self):
        self._hierarchies: Dict[str, GoalHierarchy] = {}

    def decompose(self, mission_contract: Any) -> GoalHierarchy:
        """Decompose a mission contract into a goal hierarchy."""
        hierarchy = GoalHierarchy(mission_id=mission_contract.id)

        # Create root mission node
        root = GoalNode(
            level=GoalLevel.MISSION,
            title=mission_contract.title,
            description=mission_contract.description,
            status=GoalStatus.READY,
            success_criteria=mission_contract.success_criteria,
        )
        hierarchy.nodes[root.id] = root
        hierarchy.root_id = root.id

        # Decompose based on goal type
        if mission_contract.goal_type.value == "build":
            self._decompose_build(root, hierarchy, mission_contract)
        elif mission_contract.goal_type.value == "research":
            self._decompose_research(root, hierarchy, mission_contract)
        elif mission_contract.goal_type.value == "fix":
            self._decompose_fix(root, hierarchy, mission_contract)
        elif mission_contract.goal_type.value == "deploy":
            self._decompose_deploy(root, hierarchy, mission_contract)
        else:
            self._decompose_generic(root, hierarchy, mission_contract)

        # Set initial statuses
        self._update_statuses(hierarchy)

        self._hierarchies[hierarchy.id] = hierarchy
        return hierarchy

    def _decompose_build(self, root: GoalNode, hierarchy: GoalHierarchy, mission: Any) -> None:
        """Decompose a build mission."""
        # Level 1: Major goals
        goals = [
            ("Requirements", "Analyze and document requirements"),
            ("Architecture", "Design system architecture"),
            ("Implementation", "Implement the solution"),
            ("Testing", "Test the implementation"),
            ("Documentation", "Document the solution"),
        ]

        for title, desc in goals:
            goal = GoalNode(
                level=GoalLevel.GOAL,
                title=title,
                description=desc,
                parent_id=root.id,
            )
            root.children.append(goal.id)
            hierarchy.nodes[goal.id] = goal

            # Level 2: Sub-goals
            self._add_subgoals(goal, hierarchy, title)

    def _decompose_research(self, root: GoalNode, hierarchy: GoalHierarchy, mission: Any) -> None:
        """Decompose a research mission."""
        goals = [
            ("Initial Search", "Search for relevant information"),
            ("Deep Extraction", "Extract detailed information from sources"),
            ("Analysis", "Analyze findings"),
            ("Synthesis", "Synthesize into coherent report"),
        ]

        for title, desc in goals:
            goal = GoalNode(
                level=GoalLevel.GOAL,
                title=title,
                description=desc,
                parent_id=root.id,
            )
            root.children.append(goal.id)
            hierarchy.nodes[goal.id] = goal

    def _decompose_fix(self, root: GoalNode, hierarchy: GoalHierarchy, mission: Any) -> None:
        """Decompose a fix mission."""
        goals = [
            ("Reproduce", "Reproduce the bug"),
            ("Root Cause Analysis", "Find the root cause"),
            ("Implement Fix", "Implement the fix"),
            ("Verify Fix", "Verify the fix works"),
        ]

        for title, desc in goals:
            goal = GoalNode(
                level=GoalLevel.GOAL,
                title=title,
                description=desc,
                parent_id=root.id,
            )
            root.children.append(goal.id)
            hierarchy.nodes[goal.id] = goal

    def _decompose_deploy(self, root: GoalNode, hierarchy: GoalHierarchy, mission: Any) -> None:
        """Decompose a deploy mission."""
        goals = [
            ("Pre-flight Checks", "Verify readiness for deployment"),
            ("Build Artifacts", "Build deployment artifacts"),
            ("Deploy", "Execute deployment"),
            ("Verify", "Verify deployment success"),
        ]

        for title, desc in goals:
            goal = GoalNode(
                level=GoalLevel.GOAL,
                title=title,
                description=desc,
                parent_id=root.id,
            )
            root.children.append(goal.id)
            hierarchy.nodes[goal.id] = goal

    def _decompose_generic(self, root: GoalNode, hierarchy: GoalHierarchy, mission: Any) -> None:
        """Decompose a generic mission."""
        goals = [
            ("Analyze", "Analyze the goal"),
            ("Execute", "Execute the main work"),
            ("Verify", "Verify completion"),
        ]

        for title, desc in goals:
            goal = GoalNode(
                level=GoalLevel.GOAL,
                title=title,
                description=desc,
                parent_id=root.id,
            )
            root.children.append(goal.id)
            hierarchy.nodes[goal.id] = goal

    def _add_subgoals(self, goal: GoalNode, hierarchy: GoalHierarchy, goal_title: str) -> None:
        """Add sub-goals based on goal type."""
        subgoals = {
            "Requirements": [
                ("Gather Requirements", "Collect all requirements"),
                ("Document Requirements", "Document requirements clearly"),
                ("Validate Requirements", "Validate with stakeholders"),
            ],
            "Architecture": [
                ("System Design", "Design the overall system"),
                ("Component Design", "Design individual components"),
                ("Interface Design", "Design interfaces between components"),
            ],
            "Implementation": [
                ("Setup Project", "Setup project structure"),
                ("Implement Core", "Implement core functionality"),
                ("Implement Features", "Implement features"),
                ("Add Tests", "Add tests"),
            ],
            "Testing": [
                ("Unit Tests", "Write and run unit tests"),
                ("Integration Tests", "Write and run integration tests"),
                ("E2E Tests", "Write and run end-to-end tests"),
            ],
            "Documentation": [
                ("API Documentation", "Document APIs"),
                ("User Guide", "Write user guide"),
                ("README", "Write README"),
            ],
        }

        for title, desc in subgoals.get(goal_title, []):
            subgoal = GoalNode(
                level=GoalLevel.SUBGOAL,
                title=title,
                description=desc,
                parent_id=goal.id,
            )
            goal.children.append(subgoal.id)
            hierarchy.nodes[subgoal.id] = subgoal

            # Add tasks for each sub-goal
            self._add_tasks(subgoal, hierarchy, title)

    def _add_tasks(self, subgoal: GoalNode, hierarchy: GoalHierarchy, subgoal_title: str) -> None:
        """Add tasks for a sub-goal."""
        tasks = {
            "Implement Core": [
                ("Write core modules", "Write the core modules"),
                ("Add error handling", "Add error handling"),
                ("Add logging", "Add logging"),
            ],
            "Implement Features": [
                ("Implement feature A", "Implement feature A"),
                ("Implement feature B", "Implement feature B"),
                ("Implement feature C", "Implement feature C"),
            ],
            "Add Tests": [
                ("Write unit tests", "Write unit tests"),
                ("Write integration tests", "Write integration tests"),
                ("Run test suite", "Run the full test suite"),
            ],
        }

        for title, desc in tasks.get(subgoal_title, [("Complete", f"Complete: {subgoal_title}")]):
            task = GoalNode(
                level=GoalLevel.TASK,
                title=title,
                description=desc,
                parent_id=subgoal.id,
            )
            subgoal.children.append(task.id)
            hierarchy.nodes[task.id] = task

    def _update_statuses(self, hierarchy: GoalHierarchy) -> None:
        """Update statuses based on dependencies."""
        for node in hierarchy.nodes.values():
            if node.level == GoalLevel.MISSION:
                node.status = GoalStatus.READY
            elif not node.dependencies and node.level != GoalLevel.MISSION:
                node.status = GoalStatus.READY
            elif node.dependencies:
                # Check if dependencies are complete
                deps_complete = all(
                    hierarchy.nodes.get(dep_id) and hierarchy.nodes[dep_id].status == GoalStatus.COMPLETED
                    for dep_id in node.dependencies
                )
                node.status = GoalStatus.READY if deps_complete else GoalStatus.BLOCKED

    def re_decompose(self, hierarchy_id: str, node_id: str, new_subtasks: List[Tuple[str, str]]) -> GoalHierarchy:
        """Re-decompose a node with new subtasks (dynamic re-decomposition)."""
        hierarchy = self._hierarchies.get(hierarchy_id)
        if not hierarchy:
            raise ValueError(f"Hierarchy {hierarchy_id} not found")

        node = hierarchy.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        # Remove old children
        for child_id in node.children:
            del hierarchy.nodes[child_id]
        node.children = []

        # Add new subtasks
        for title, desc in new_subtasks:
            task = GoalNode(
                level=GoalLevel.TASK,
                title=title,
                description=desc,
                parent_id=node.id,
            )
            node.children.append(task.id)
            hierarchy.nodes[task.id] = task

        # Update statuses
        self._update_statuses(hierarchy)

        return hierarchy

    def get_hierarchy(self, hierarchy_id: str) -> Optional[GoalHierarchy]:
        """Get a hierarchy by ID."""
        return self._hierarchies.get(hierarchy_id)

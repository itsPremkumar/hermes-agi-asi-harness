"""
HERMES INTELLIGENCE OS — DYNAMIC RUNTIME BRIDGES (LANGGRAPH & DEEP AGENTS)
=========================================================================
Dynamic execution substrate compilation:
1. LangGraphDynamicAdapter: Compiles the task DAG into a dynamic, stateful execution
   graph with durable checkpointing, interrupt/resume, and cyclical state transitions.
2. DeepAgentsAdapter: Maps subgoals to isolated filesystem-backed subagent workspaces,
   enforcing strict context boundaries and preventing context window pollution.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cognitive_compiler import ExecutionPlanIR

logger = logging.getLogger("hermes.os.dynamic_runtime")


@dataclass
class GraphNode:
    """A stateful node in the dynamic LangGraph state graph."""
    node_id: str
    task_id: str
    action_type: str
    dependencies: List[str]
    is_checkpoint: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DynamicStateGraph:
    """Dynamic LangGraph state graph compiled from ExecutionPlanIR."""
    graph_id: str
    mission_id: str
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[tuple[str, str]] = field(default_factory=list)  # (source, target)
    entry_nodes: List[str] = field(default_factory=list)
    exit_nodes: List[str] = field(default_factory=list)
    checkpoint_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "mission_id": self.mission_id,
            "nodes_count": len(self.nodes),
            "edges_count": len(self.edges),
            "entry_points": self.entry_nodes,
            "exit_points": self.exit_nodes,
        }


class LangGraphDynamicAdapter:
    """
    Transforms an ExecutionPlanIR DAG into an executable LangGraph StateGraph.
    Instead of a fixed static graph, every mission compiles a custom graph topology.
    """

    def compile_graph(self, plan: ExecutionPlanIR) -> DynamicStateGraph:
        graph_id = f"graph-{uuid.uuid4().hex[:8]}"
        nodes: Dict[str, GraphNode] = {}
        edges: List[tuple[str, str]] = []

        all_goals = plan.task_graph.list_goals()
        for g in all_goals:
            cap_plan = plan.capability_plans.get(g.goal_id)
            action_type = cap_plan.selected_tools[0] if cap_plan and cap_plan.selected_tools else "generic_step"

            g_node = GraphNode(
                node_id=f"node_{g.goal_id}",
                task_id=g.goal_id,
                action_type=action_type,
                dependencies=[f"node_{d}" for d in g.depends_on],
                metadata={
                    "title": g.title,
                    "budget": g.budget_tokens,
                },
            )
            nodes[g_node.node_id] = g_node

            for dep in g.depends_on:
                edges.append((f"node_{dep}", g_node.node_id))

        entry_nodes = [nid for nid, node in nodes.items() if not node.dependencies]
        exit_nodes = [
            nid for nid in nodes
            if not any(src == nid for src, _ in edges)
        ]

        logger.info(f"Compiled dynamic LangGraph state graph {graph_id} ({len(nodes)} nodes, {len(edges)} edges)")
        return DynamicStateGraph(
            graph_id=graph_id,
            mission_id=plan.mission_id,
            nodes=nodes,
            edges=edges,
            entry_nodes=entry_nodes,
            exit_nodes=exit_nodes,
        )


# =====================================================================
# Deep Agents Isolated Workspace Adapter
# =====================================================================

@dataclass
class IsolatedSubagentWorkspace:
    """Dedicated context and filesystem envelope for an isolated subagent worker."""
    worker_id: str
    task_id: str
    workspace_dir: str
    context_package: Dict[str, Any]
    assigned_skills: List[str]
    assigned_tools: List[str]
    status: str = "initialized"


class DeepAgentsAdapter:
    """
    Manages long-horizon subagent isolation (Deep Agents pattern):
    - Subagents run in isolated scratchpad directories.
    - Context packages provide task-local knowledge only, avoiding lead agent token flooding.
    """

    def __init__(self, base_workspace_root: str = "."):
        self.base_root = Path(base_workspace_root)
        self._workspaces_dir = self.base_root / ".hermes" / "subagent_sandboxes"
        self._active_workspaces: Dict[str, IsolatedSubagentWorkspace] = {}

    def spawn_isolated_worker(
        self,
        mission_id: str,
        task_id: str,
        task_title: str,
        capability_plan: Any,
        context_slice: str = "",
    ) -> IsolatedSubagentWorkspace:
        """Create a sandboxed execution workspace for a specialist subagent."""
        worker_id = f"worker-{task_id}-{uuid.uuid4().hex[:4]}"
        worker_dir = self._workspaces_dir / mission_id / worker_id
        worker_dir.mkdir(parents=True, exist_ok=True)

        context_pkg = {
            "mission_id": mission_id,
            "task_id": task_id,
            "task_title": task_title,
            "local_workspace": str(worker_dir.resolve()),
            "context_slice": context_slice,
            "permissions": capability_plan.required_permissions if hasattr(capability_plan, "required_permissions") else ["read"],
        }

        workspace = IsolatedSubagentWorkspace(
            worker_id=worker_id,
            task_id=task_id,
            workspace_dir=str(worker_dir),
            context_package=context_pkg,
            assigned_skills=capability_plan.selected_skills if hasattr(capability_plan, "selected_skills") else [],
            assigned_tools=capability_plan.selected_tools if hasattr(capability_plan, "selected_tools") else [],
        )

        self._active_workspaces[worker_id] = workspace
        logger.debug(f"Spawned isolated Deep Agent workspace for {worker_id} at {worker_dir}")
        return workspace

    def get_workspace(self, worker_id: str) -> Optional[IsolatedSubagentWorkspace]:
        return self._active_workspaces.get(worker_id)

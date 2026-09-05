"""Dependency resolver — resolve plugin dependencies and detect cycles."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class DependencyNode:
    """A node in the dependency graph."""
    plugin_id: str
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    resolved: bool = False
    resolving: bool = False  # For cycle detection


class DependencyGraph:
    """Graph of plugin dependencies."""

    def __init__(self):
        self._lock = threading.RLock()
        self._nodes: dict[str, DependencyNode] = {}

    def add_plugin(self, plugin_id: str, dependencies: list[str]) -> None:
        with self._lock:
            node = self._nodes.get(plugin_id)
            if node is None:
                node = DependencyNode(plugin_id=plugin_id)
                self._nodes[plugin_id] = node
            node.dependencies = list(dependencies)
            # Add dependents
            for dep in dependencies:
                dep_node = self._nodes.get(dep)
                if dep_node is None:
                    dep_node = DependencyNode(plugin_id=dep)
                    self._nodes[dep] = dep_node
                if plugin_id not in dep_node.dependents:
                    dep_node.dependents.append(plugin_id)

    def remove_plugin(self, plugin_id: str) -> bool:
        with self._lock:
            node = self._nodes.pop(plugin_id, None)
            if node is None:
                return False
            # Remove from dependents
            for dep in node.dependencies:
                dep_node = self._nodes.get(dep)
                if dep_node and plugin_id in dep_node.dependents:
                    dep_node.dependents.remove(plugin_id)
            # Remove from dependencies' dependents
            for dependent in node.dependents:
                dep_node = self._nodes.get(dependent)
                if dep_node and plugin_id in dep_node.dependencies:
                    dep_node.dependencies.remove(plugin_id)
            return True

    def get_dependencies(self, plugin_id: str) -> list[str]:
        with self._lock:
            node = self._nodes.get(plugin_id)
            return list(node.dependencies) if node else []

    def get_dependents(self, plugin_id: str) -> list[str]:
        with self._lock:
            node = self._nodes.get(plugin_id)
            return list(node.dependents) if node else []

    def get_all(self) -> list[str]:
        with self._lock:
            return list(self._nodes.keys())


class DependencyResolver:
    """Resolves plugin dependencies and determines load order."""

    def __init__(self, graph: DependencyGraph):
        self._lock = threading.RLock()
        self._graph = graph

    def resolve_load_order(self) -> list[str]:
        """Resolve the order in which plugins should be loaded using topological sort."""
        with self._lock:
            visited: set[str] = set()
            order: list[str] = []

            def visit(plugin_id: str) -> None:
                if plugin_id in visited:
                    return
                visited.add(plugin_id)
                deps = self._graph.get_dependencies(plugin_id)
                for dep in deps:
                    visit(dep)
                order.append(plugin_id)

            for plugin_id in self._graph.get_all():
                visit(plugin_id)

            return order

    def resolve_unload_order(self) -> list[str]:
        """Resolve the order in which plugins should be unloaded (reverse of load)."""
        return list(reversed(self.resolve_load_order()))

    def detect_cycles(self) -> list[list[str]]:
        """Detect cycles in the dependency graph."""
        with self._lock:
            cycles = []
            visited: set[str] = set()
            rec_stack: set[str] = set()

            def dfs(node_id: str, path: list[str]) -> None:
                visited.add(node_id)
                rec_stack.add(node_id)
                path.append(node_id)

                deps = self._graph.get_dependencies(node_id)
                for dep in deps:
                    if dep not in visited:
                        dfs(dep, list(path))
                    elif dep in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(dep)
                        cycle = path[cycle_start:] + [dep]
                        cycles.append(cycle)

                rec_stack.remove(node_id)

            for plugin_id in self._graph.get_all():
                if plugin_id not in visited:
                    dfs(plugin_id, [])

            return cycles

    def get_missing_dependencies(self, plugin_id: str, available: set[str]) -> list[str]:
        """Get dependencies that are not in the available set."""
        with self._lock:
            deps = self._graph.get_dependencies(plugin_id)
            return [d for d in deps if d not in available]

    def get_dependents_to_stop(self, plugin_id: str) -> list[str]:
        """Get all plugins that depend on this plugin (transitively)."""
        with self._lock:
            result = []
            stack = [plugin_id]
            visited = set()
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                dependents = self._graph.get_dependents(current)
                for dep in dependents:
                    if dep not in visited:
                        result.append(dep)
                        stack.append(dep)
            return result

    def can_unload(self, plugin_id: str) -> bool:
        """Check if a plugin can be safely unloaded (no active dependents)."""
        with self._lock:
            dependents = self._graph.get_dependents(plugin_id)
            # In a real system, check if dependents are active
            return len(dependents) == 0

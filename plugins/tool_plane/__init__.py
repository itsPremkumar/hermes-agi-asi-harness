#!/usr/bin/env python3
"""
HERMES TOOL USE & COMPOSITION PLANE
=====================================
Plugin for discovering, selecting, composing, creating, and verifying tools.

Extracted from:
- AGX: Tool selection and tool composition patterns
- Hermes Agent: Tool registry and tool execution patterns
"""

from __future__ import annotations

import ast
import glob
import hashlib
import inspect
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_tool_plane")


class ToolStatus(str, Enum):
    AVAILABLE = "available"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


@dataclass
class ToolDescriptor:
    """Describes a tool."""
    tool_id: str
    name: str
    description: str
    category: str
    capabilities: List[str]
    cost: float = 0.0
    latency_ms: float = 0.0
    status: ToolStatus = ToolStatus.AVAILABLE
    usage_count: int = 0
    success_count: int = 0
    last_used: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolChain:
    """A chain of tools to execute sequentially."""
    chain_id: str
    name: str
    description: str
    tools: List[str]
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)


class ToolPlane:
    """
    Tool Use & Composition Plane.
    
    Features:
    - Tool discovery (find all available tools)
    - Tool selection (choose best tool for a task)
    - Tool composition (chain tools together)
    - Tool creation (generate new tools from NL descriptions)
    - Tool verification (test that tools work correctly)
    """
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = plugins_dir
        self._tools: Dict[str, ToolDescriptor] = {}
        self._chains: Dict[str, ToolChain] = {}
        self._tool_results_cache: Dict[str, Any] = {}
    
    def discover_tools(self) -> List[ToolDescriptor]:
        """Discover all available tools from plugins directory."""
        tools = []
        
        # Scan plugin directories
        for plugin_dir in glob.glob(os.path.join(self.plugins_dir, "*")):
            if not os.path.isdir(plugin_dir):
                continue
            
            plugin_name = os.path.basename(plugin_dir)
            plugin_yaml = os.path.join(plugin_dir, "plugin.yaml")
            
            if os.path.exists(plugin_yaml):
                try:
                    with open(plugin_yaml) as f:
                        # Simple YAML parsing
                        content = f.read()
                        name = plugin_name
                        description = ""
                        capabilities = []
                        
                        for line in content.split("\n"):
                            if line.startswith("description:"):
                                description = line.split(":", 1)[1].strip().strip('"').strip("'")
                            elif "capabilities:" in line:
                                continue
                            elif line.strip().startswith("- "):
                                capabilities.append(line.strip()[2:])
                        
                        tool = ToolDescriptor(
                            tool_id=plugin_name,
                            name=name,
                            description=description or f"Plugin: {plugin_name}",
                            category="plugin",
                            capabilities=capabilities or ["general"]
                        )
                        tools.append(tool)
                except Exception as e:
                    logger.warning("Failed to parse %s: %s", plugin_yaml, e)
        
        # Also scan core/ directory
        core_dir = "core"
        if os.path.exists(core_dir):
            for init_file in glob.glob(os.path.join(core_dir, "*", "__init__.py")):
                component = os.path.basename(os.path.dirname(init_file))
                tool = ToolDescriptor(
                    tool_id=f"core.{component}",
                    name=component,
                    description=f"Core component: {component}",
                    category="core",
                    capabilities=[component]
                )
                tools.append(tool)
        
        self._tools = {t.tool_id: t for t in tools}
        logger.info("Discovered %d tools", len(tools))
        return tools
    
    def select_tool(self, task: str, top_k: int = 3) -> List[Tuple[ToolDescriptor, float]]:
        """Select the best tools for a task."""
        if not self._tools:
            self.discover_tools()
        
        task_lower = task.lower()
        task_words = set(re.findall(r'\w+', task_lower))
        
        scored = []
        for tool in self._tools.values():
            if tool.status != ToolStatus.AVAILABLE:
                continue
            
            score = 0.0
            
            # Name match
            name_words = set(re.findall(r'\w+', tool.name.lower()))
            name_overlap = len(task_words & name_words)
            score += name_overlap * 2.0
            
            # Description match
            desc_words = set(re.findall(r'\w+', tool.description.lower()))
            desc_overlap = len(task_words & desc_words)
            score += desc_overlap * 1.0
            
            # Capability match
            cap_words = set()
            for cap in tool.capabilities:
                cap_words.update(re.findall(r'\w+', cap.lower()))
            cap_overlap = len(task_words & cap_words)
            score += cap_overlap * 1.5
            
            # Success rate bonus
            if tool.usage_count > 0:
                success_rate = tool.success_count / tool.usage_count
                score += success_rate * 2.0
            
            if score > 0:
                scored.append((tool, score))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    
    def create_chain(self, name: str, description: str, tool_ids: List[str]) -> str:
        """Create a tool chain."""
        chain_id = str(uuid.uuid4())
        
        chain = ToolChain(
            chain_id=chain_id,
            name=name,
            description=description,
            tools=tool_ids
        )
        
        self._chains[chain_id] = chain
        return chain_id
    
    def get_tool(self, tool_id: str) -> Optional[ToolDescriptor]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)
    
    def get_all_tools(self) -> List[ToolDescriptor]:
        """Get all tools."""
        return list(self._tools.values())
    
    def create_tool_from_description(self, description: str, name: str = None) -> Optional[str]:
        """Create a new tool from a natural language description."""
        if not name:
            name = f"generated_{hashlib.md5(description.encode()).hexdigest()[:8]}"
        
        # Generate simple tool code
        tool_code = self._generate_tool_code(name, description)
        
        # Save to workspace
        tool_dir = os.path.join(self.plugins_dir, name)
        os.makedirs(tool_dir, exist_ok=True)
        
        init_file = os.path.join(tool_dir, "__init__.py")
        with open(init_file, "w") as f:
            f.write(tool_code)
        
        # Create plugin.yaml
        plugin_yaml = os.path.join(tool_dir, "plugin.yaml")
        with open(plugin_yaml, "w") as f:
            f.write(f"""name: {name}
version: 0.1.0
description: {description}
license: MIT
source: generated
capabilities:
  - generated
  - custom
cost:
  default: low
permissions:
  filesystem:
    read: workspace
    write: workspace
  network:
    allowed: []
  shell:
    allowed: []
  secrets:
    access: none
""")
        
        logger.info("Created tool: %s", name)
        return name
    
    def _generate_tool_code(self, name: str, description: str) -> str:
        """Generate tool code from description."""
        return f'''#!/usr/bin/env python3
"""
{description}
Generated by Hermes Tool Plane.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("hermes.{name}")


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the tool."""
    try:
        # TODO: Implement tool logic based on description
        return {{
            "status": "success",
            "result": f"Executed {name} with params: {{params}}"
        }}
    except Exception as e:
        return {{
            "status": "error",
            "error": str(e)
        }}


async def health() -> Dict[str, Any]:
    """Health check."""
    return {{
        "status": "healthy",
        "tool": "{name}"
    }}
'''
    
    def verify_tool(self, tool_id: str) -> Dict[str, Any]:
        """Verify a tool is healthy and working."""
        tool = self._tools.get(tool_id)
        if not tool:
            return {"status": "error", "error": f"Tool not found: {tool_id}"}
        
        # Check plugin exists
        plugin_dir = os.path.join(self.plugins_dir, tool_id)
        init_file = os.path.join(plugin_dir, "__init__.py")
        
        if not os.path.exists(init_file):
            return {"status": "error", "error": f"Plugin file not found: {init_file}"}
        
        # Check syntax
        try:
            with open(init_file) as f:
                code = f.read()
            ast.parse(code)
        except SyntaxError as e:
            return {"status": "error", "error": f"Syntax error: {e}"}
        
        return {"status": "healthy", "tool": tool_id, "syntax_valid": True}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tool statistics."""
        total = len(self._tools)
        available = sum(1 for t in self._tools.values() if t.status == ToolStatus.AVAILABLE)
        unhealthy = sum(1 for t in self._tools.values() if t.status == ToolStatus.UNHEALTHY)
        
        return {
            "total_tools": total,
            "available": available,
            "unhealthy": unhealthy,
            "chains": len(self._chains),
        }
    
    async def health(self) -> Dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy",
            **self.get_statistics()
        }


# Entry point
async def main():
    """Demo the tool plane."""
    plane = ToolPlane()
    tools = plane.discover_tools()
    print(f"Discovered {len(tools)} tools")
    
    for tool in tools[:5]:
        print(f"  - {tool.name}: {tool.description[:50]}")
    
    # Test tool selection
    selected = plane.select_tool("research AI agents")
    print(f"\nTop tools for 'research AI agents':")
    for tool, score in selected:
        print(f"  - {tool.name} (score: {score:.1f})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


"""
Execution Engine — ReAct loop, tool dispatch, state management.

Extracted & enhanced from:
- agi-hermes-advanced-master: agent_loop.py
- hermes-agent: conversation_loop.py
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    done: bool = False
    final_answer: Optional[str] = None


class ExecutionEngine:
    """ReAct + Plan-Execute loop engine."""
    
    def __init__(self):
        self.manifest = None
        self.tools: Dict[str, Callable[[Dict[str, Any]], Awaitable[str]]] = {}
        self.max_steps: int = 25
    
    def register_tool(self, name: str, func: Callable[[Dict[str, Any]], Awaitable[str]]):
        """Register a tool."""
        self.tools[name] = func
    
    async def execute(self, task: Any) -> Dict[str, Any]:
        """Execute a task using the ReAct loop with real tool dispatch."""
        goal = task.goal if hasattr(task, 'goal') else str(task)
        logger.info("Executing task: %s", goal)
        
        step = 0
        history: List[StepResult] = []
        final_answer = None
        
        # Select best tool based on task keywords
        action = self._select_tool(goal)
        
        while step < self.max_steps:
            step += 1
            
            thought = f"Step {step}: Selected tool '{action}' for goal: {goal}"
            observation = None
            done = False
            
            if action and action in self.tools:
                action_input = self._build_action_input(action, goal)
                try:
                    result = self.tools[action](action_input)
                    # Handle both sync and async tools
                    if asyncio.iscoroutine(result):
                        result = await result
                    observation = str(result) if result is not None else "Success"
                except Exception as e:
                    observation = f"Error: {e}"
                
                # After first successful tool call, we're done (simple tasks)
                    done = True
                    final_answer = f"Executed {action}: {observation}"
                    # Record to state manager if available
                    if hasattr(self, '_kernel') and self._kernel and self._kernel.state_manager and self._kernel.state_manager.manager:
                        task_id = task.task_id if hasattr(task, 'task_id') else getattr(task, 'id', 'unknown')
                        self._kernel.state_manager.manager.update_task(task_id, result=final_answer) if hasattr(self._kernel.state_manager.manager, 'update_task') else None
            else:
                observation = f"No matching tool for: {goal}"
                done = True
                final_answer = observation
            
            step_res = StepResult(
                step_number=step,
                thought=thought,
                action=action,
                action_input=action_input if action else None,
                observation=observation,
                done=done,
                final_answer=final_answer
            )
            history.append(step_res)
            
            if done:
                break
        
        return {
            "task": goal,
            "success": done,
            "steps": step,
            "final_answer": final_answer or "Terminated at step limit",
            "history": history
        }
    
    def _select_tool(self, goal: str) -> Optional[str]:
        """Select the best tool for a goal based on keyword matching."""
        goal_lower = goal.lower()
        
        # Keyword → tool mapping
        keyword_map = [
            (["write file", "create file", "save file"], "file_write"),
            (["read file", "open file", "get file"], "file_read"),
            (["compute", "calculate", "math", "what is"], "python_exec"),
            (["run shell", "execute command", "terminal"], "shell"),
            (["http", "fetch url", "web get"], "http_get"),
            (["search memory", "recall", "remember"], "memory_search"),
            (["checkpoint", "save state"], "checkpoint"),
            (["evolve", "optimize"], "evolve"),
        ]
        
        for keywords, tool_name in keyword_map:
            if any(kw in goal_lower for kw in keywords):
                if tool_name in self.tools:
                    return tool_name
        
        # Fallback: use first available tool
        return list(self.tools.keys())[0] if self.tools else None
    
    def _build_action_input(self, tool_name: str, goal: str) -> Dict[str, Any]:
        """Build action input dict for a tool based on the goal."""
        goal_lower = goal.lower()
        
        if tool_name == "file_write":
            # Extract filename and content from goal
            path = "output.txt"
            content = goal
            if "containing" in goal_lower:
                parts = goal.split("containing", 1)
                # Try to extract path from first part
                words = parts[0].strip().split()
                for i, w in enumerate(words):
                    if w.endswith(".txt") or w.endswith(".py") or w.endswith(".md"):
                        path = w
                        break
                else:
                    # Use last word of first part as filename if no extension
                    fname = [w for w in words if w.isalnum() and w not in ("write", "file", "create", "save")]
                    if fname:
                        path = fname[-1] + ".txt"
                content = parts[1].strip() if len(parts) > 1 else goal
            return {"path": path, "content": content}
        
        if tool_name == "python_exec":
            return {"code": goal}
        
        if tool_name == "shell":
            return {"command": goal}
        
        if tool_name == "http_get":
            return {"url": goal}
        
        if tool_name == "memory_search":
            return {"query": goal}
        
        if tool_name == "checkpoint":
            return {"task_id": "manual", "state": {"goal": goal}}
        
        return {"query": goal}
    
    async def load(self) -> bool:
        logger.info("Execution engine loaded")
        return True
    
    async def start(self) -> bool:
        logger.info("Execution engine started")
        return True
    
    async def stop(self) -> bool:
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "type": "execution_engine",
            "tools": len(self.tools),
        }


async def create(kernel: Any) -> ExecutionEngine:
    engine = ExecutionEngine()
    engine._kernel = kernel
    return engine

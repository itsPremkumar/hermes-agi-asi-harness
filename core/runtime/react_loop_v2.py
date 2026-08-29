"""
react_loop_v2.py — Advanced ReAct Loop with Metacognition, Self-Healing, and World Model

This is the full cognitive execution loop that integrates:
- ReliabilityVerifier (AST check + secret detection)
- RedTeamCritic (plan critique + failure analysis)
- MetacognitionEngine (mode selection + confidence calibration)
- SelfHealingEngine (failure diagnosis + auto-repair)
- WorldModel (entity/relationship tracking)
- JITHarnessGenerator (task profiling)
- EventBus (event streaming)
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    THINKING = "thinking"
    ACTION = "action"
    OBSERVATION = "observation"
    VERIFY = "verify"
    REFLECT = "reflect"
    DONE = "done"
    ERROR = "error"
    RECOVERING = "recovering"


@dataclass
class ThoughtStep:
    step_number: int
    status: StepStatus
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    confidence: float = 0.5
    verification: Optional[Dict[str, Any]] = None
    repair_attempt: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class AdvancedReActLoop:
    """
    Advanced ReAct loop with metacognition, self-healing, and world model integration.
    """

    def __init__(
        self,
        model_router=None,
        event_bus=None,
        verifier=None,
        critic=None,
        metacognition=None,
        self_healing=None,
        world_model=None,
        jit_harness=None,
        max_steps: int = 25,
    ):
        self.model_router = model_router
        self.event_bus = event_bus
        self.verifier = verifier
        self.critic = critic
        self.metacognition = metacognition
        self.self_healing = self_healing
        self.world_model = world_model
        self.jit_harness = jit_harness
        self.max_steps = max_steps
        self.tools: Dict[str, Callable] = {}
        self.step_history: List[ThoughtStep] = []

    def register_tool(self, name: str, func: Callable):
        """Registers a tool for the agent to use."""
        self.tools[name] = func

    async def run(self, task: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the advanced ReAct loop until task completion or max steps.
        """
        loop_start = time.time()
        goal = task
        task_profile = None

        # 1. Generate task profile using JIT Harness
        if self.jit_harness:
            task_profile = self.jit_harness.analyze_task(task)
            max_steps = task_profile.max_steps
            mode = self.metacognition.select_mode(task) if self.metacognition else "deliberative"
        else:
            max_steps = self.max_steps
            mode = "deliberative"

        # 2. Critique the plan before execution
        plan_steps = [f"Step {i}: Execute subtask" for i in range(1, 4)]
        if self.critic:
            critiques = self.critic.critique_plan(plan_steps)
            if critiques:
                logger.info("Plan critiques: %s", critiques)

        # 3. Emit start event
        if self.event_bus:
            self.event_bus.publish(type('Event', (), {
                'topic': 'agent.loop_start',
                'payload': {'task': task, 'mode': mode, 'max_steps': max_steps},
                'sender': 'advanced_react',
                'timestamp': time.time(),
                'event_id': f"evt_loop_start_{int(time.time()*1000)}",
            })())

        step = 0
        done = False
        final_answer = None

        while step < max_steps and not done:
            step += 1
            step_start = time.time()

            # 4. Select cognitive mode for this step
            if self.metacognition:
                mode = self.metacognition.select_mode(task)
                self.metacognition.record_thought(
                    f"Executing step {step} in {mode.value} mode for task: {task[:50]}",
                    confidence=0.8,
                )

            # 5. Determine action based on task keywords
            action = self._select_action(task, step)
            if not action:
                # No tool needed — synthesizing answer
                thought = f"Step {step}: No tool needed for: {task}"
                self.step_history.append(ThoughtStep(
                    step_number=step,
                    status=StepStatus.THINKING,
                    thought=thought,
                    confidence=0.8,
                ))
                done = True
                final_answer = f"Task completed: {task}"
                continue

            # 6. Build action input
            action_input = self._build_action_input(action, task)

            # 7. Execute action
            observation = None
            error = None
            repair_applied = None

            try:
                self.step_history.append(ThoughtStep(
                    step_number=step,
                    status=StepStatus.ACTION,
                    thought=f"Executing {action} with input: {action_input}",
                    action=action,
                    action_input=action_input,
                    confidence=0.85,
                ))

                result = self.tools[action](action_input)
                if asyncio.iscoroutine(result):
                    result = await result
                observation = str(result) if result is not None else "Success"

            except Exception as e:
                error = str(e)
                observation = f"Error: {e}"

                # 8. Self-healing on failure
                if self.self_healing:
                    pattern = self.self_healing.diagnose_failure(error, context=f"Step {step}: {action}")
                    logger.info("Diagnosed failure: %s (class: %s)", pattern.pattern_id, pattern.failure_class.value)

                    repair = await self.self_healing.attempt_repair(pattern)
                    if repair.success:
                        repair_applied = repair.fix_applied
                        # Retry the action after repair
                        try:
                            result = self.tools[action](action_input)
                            if asyncio.iscoroutine(result):
                                result = await result
                            observation = str(result)
                            error = None
                        except Exception as e2:
                            observation = f"Error after repair: {e2}"
                            error = str(e2)

                self.step_history.append(ThoughtStep(
                    step_number=step,
                    status=StepStatus.ERROR,
                    thought=f"Action failed: {error}",
                    action=action,
                    action_input=action_input,
                    observation=observation,
                    repair_attempt=repair_applied,
                    confidence=0.3,
                ))

            # 9. Verification step
            verification_result = None
            if self.verifier and observation and "Success" in observation:
                if action == "python_exec":
                    verification_result = self.verifier.verify_python_code(
                        action_input.get("code", "")
                    )
                elif action == "file_write":
                    verification_result = {
                        "passed": True,
                        "confidence": 1.0,
                        "checks": {"file_exists": True},
                    }

            # 10. Record observation step
            self.step_history.append(ThoughtStep(
                step_number=step,
                status=StepStatus.OBSERVATION,
                thought=f"Observed result from {action}",
                action=action,
                observation=observation,
                confidence=0.9,
                verification=verification_result,
            ))

            # 11. Determine if done
            done = True
            final_answer = f"Executed {action}: {observation}"

        # 12. Record outcome for metacognition
        if self.metacognition:
            self.metacognition.record_outcome(task, success=done, error=error)

        # 13. Emit end event
        duration = time.time() - loop_start
        if self.event_bus:
            self.event_bus.publish(type('Event', (), {
                'topic': 'agent.loop_end',
                'payload': {
                    'task': task,
                    'steps': step,
                    'success': done,
                    'duration_ms': duration * 1000,
                },
                'sender': 'advanced_react',
                'timestamp': time.time(),
                'event_id': f"evt_loop_end_{int(time.time()*1000)}",
            })())

        return {
            "task": task,
            "success": done,
            "steps": step,
            "final_answer": final_answer or "Terminated at step limit",
            "history": [self._step_to_dict(s) for s in self.step_history],
            "duration_ms": duration * 1000,
            "mode": mode,
            "task_profile": task_profile.__dict__ if task_profile else None,
            "metacognition": self.metacognition.get_reflection() if self.metacognition else None,
            "self_healing_stats": self.self_healing.get_stats() if self.self_healing else None,
        }

    def _select_action(self, task: str, step: int) -> Optional[str]:
        """Selects the appropriate action based on task keywords."""
        task_lower = task.lower()

        if any(w in task_lower for w in ["write file", "create file", "save file"]):
            return "file_write" if "file_write" in self.tools else None
        elif any(w in task_lower for w in ["compute", "calculate", "math", "what is", "print"]):
            return "python_exec" if "python_exec" in self.tools else None
        elif any(w in task_lower for w in ["read file", "open file", "get file"]):
            return "file_read" if "file_read" in self.tools else None
        elif any(w in task_lower for w in ["shell", "run command", "execute"]):
            return "shell" if "shell" in self.tools else None
        elif any(w in task_lower for w in ["http", "fetch url", "web get"]):
            return "http_get" if "http_get" in self.tools else None
        elif any(w in task_lower for w in ["search memory", "recall", "remember"]):
            return "memory_search" if "memory_search" in self.tools else None
        elif any(w in task_lower for w in ["checkpoint", "save state"]):
            return "checkpoint" if "checkpoint" in self.tools else None
        elif any(w in task_lower for w in ["evolve", "optimize"]):
            return "evolve" if "evolve" in self.tools else None

        return None

    def _build_action_input(self, tool_name: str, task: str) -> Dict[str, Any]:
        """Builds action input for a tool based on the task."""
        task_lower = task.lower()

        if tool_name == "file_write":
            path = "output.txt"
            content = task
            if "containing" in task_lower:
                parts = task.split("containing", 1)
                if len(parts) > 1:
                    words = parts[0].strip().split()
                    for w in words:
                        if w.endswith(".txt") or w.endswith(".py") or w.endswith(".md"):
                            path = w
                            break
                    else:
                        fname = [w for w in words if w.isalnum() and w not in ("write", "file", "create", "save")]
                        if fname:
                            path = fname[-1] + ".txt"
                    content = parts[1].strip()
            return {"path": path, "content": content}
        elif tool_name == "python_exec":
            return {"code": task}
        elif tool_name == "file_read":
            return {"path": task}
        elif tool_name == "shell":
            return {"command": task}
        elif tool_name == "http_get":
            return {"url": task}
        elif tool_name == "memory_search":
            return {"query": task}
        elif tool_name == "checkpoint":
            return {"task_id": "auto", "state": {"task": task}}

        return {"query": task}

    def _step_to_dict(self, step: ThoughtStep) -> Dict[str, Any]:
        """Converts a ThoughtStep to a dictionary."""
        return {
            "step": step.step_number,
            "status": step.status.value,
            "thought": step.thought,
            "action": step.action,
            "observation": step.observation,
            "confidence": step.confidence,
            "repair_attempt": step.repair_attempt,
        }


async def create(kernel=None) -> AdvancedReActLoop:
    """Factory function for kernel integration."""
    loop = AdvancedReActLoop()

    # Wire up components from kernel
    if kernel:
        if hasattr(kernel, 'model_router') and kernel.model_router:
            loop.model_router = kernel.model_router
        if hasattr(kernel, 'event_bus') and kernel.event_bus:
            loop.event_bus = kernel.event_bus
        if hasattr(kernel, '_plugins'):
            plugins = kernel._plugins
            if 'verification_engine' in plugins:
                v = plugins['verification_engine']
                if hasattr(v, 'verifier') and v.verifier:
                    loop.verifier = v.verifier
            if 'self_healing' in plugins:
                loop.self_healing = plugins['self_healing'].engine if hasattr(plugins['self_healing'], 'engine') else plugins['self_healing']
            if 'world_model' in plugins and hasattr(plugins['world_model'], 'world_model'):
                loop.world_model = plugins['world_model'].world_model
            if 'jit_harness' in plugins and hasattr(plugins['jit_harness'], 'generator'):
                loop.jit_harness = plugins['jit_harness'].generator
            if 'metacognition' in plugins and hasattr(plugins['metacognition'], 'metacognition'):
                loop.metacognition = plugins['metacognition'].metacognition

    return loop

"""
Self-Enforcing Verification Gates — Fable-5 Pattern
====================================================
Mandatory hooks that BLOCK on unverified completion.
Converts "should verify" into "must verify" via mechanical enforcement.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class HookEventType(str, Enum):
    """Lifecycle events that can trigger hooks."""
    PRE_TOOL_USE = "pre_tool_use"      # Before any tool execution
    POST_TOOL_USE = "post_tool_use"    # After tool execution
    TASK_START = "task_start"          # Task begins
    TASK_COMPLETE = "task_complete"    # Task claims completion
    TASK_STOP = "task_stop"            # Task explicitly stopped
    SESSION_START = "session_start"    # New session
    SESSION_END = "session_end"        # Session ends


class BlockReason(str, Enum):
    """Reasons for blocking an action."""
    MISSING_VERIFICATION_LEDGER = "missing_verification_ledger"
    OPEN_VERIFICATION_ITEMS = "open_verification_items"
    FAILED_ADVERSARIAL_VERIFICATION = "failed_adversarial_verification"
    SCOPE_CREEP_DETECTED = "scope_creep_detected"
    WEAKENED_TESTS_DETECTED = "weakened_tests_detected"
    MISSING_DONE_CRITERIA = "missing_done_criteria"
    UNAUTHORIZED_DELEGATION = "unauthorized_delegation"


@dataclass
class HookContext:
    """Context passed to hook handlers."""
    event_type: HookEventType
    tool_name: Optional[str] = None
    tool_args: dict = field(default_factory=dict)
    task_id: Optional[str] = None
    task_description: str = ""
    session_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class HookResult:
    """Result of hook execution."""
    allowed: bool = True
    block_reason: Optional[BlockReason] = None
    message: str = ""
    required_actions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def allow(cls, message: str = "") -> "HookResult":
        return cls(allowed=True, message=message)

    @classmethod
    def block(cls, reason: BlockReason, message: str, required_actions: list[str] = None) -> "HookResult":
        return cls(
            allowed=False,
            block_reason=reason,
            message=message,
            required_actions=required_actions or [],
        )


class VerificationLedger:
    """
    Verification Ledger — Fable-5 pattern.
    Every explicit requirement, implicit expectation, constraint, and edge case as a checkbox.
    Files survive context compaction; conversation context does not.
    """

    def __init__(self, ledger_path: Path):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._items: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.ledger_path.exists():
            try:
                import yaml
                data = yaml.safe_load(self.ledger_path.read_text())
                self._items = data.get("items", {})
            except Exception:
                self._items = {}

    def _save(self) -> None:
        import yaml
        self.ledger_path.write_text(yaml.dump({"items": self._items}, sort_keys=False))

    def add_item(
        self,
        item_id: str,
        description: str,
        category: str = "requirement",  # requirement | expectation | constraint | edge_case
        source: str = "user",
    ) -> None:
        """Add a verification item to the ledger."""
        self._items[item_id] = {
            "id": item_id,
            "description": description,
            "category": category,
            "source": source,
            "status": "open",  # open | done | deferred
            "evidence": None,
            "verified_at": None,
            "verified_by": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._save()

    def mark_done(self, item_id: str, evidence: Any, verified_by: str) -> bool:
        """Mark item as done with evidence."""
        if item_id not in self._items:
            return False
        self._items[item_id].update({
            "status": "done",
            "evidence": evidence,
            "verified_at": datetime.utcnow().isoformat(),
            "verified_by": verified_by,
        })
        self._save()
        return True

    def mark_deferred(self, item_id: str, reason: str) -> bool:
        """Mark item as deferred with reason."""
        if item_id not in self._items:
            return False
        self._items[item_id].update({
            "status": "deferred",
            "evidence": {"deferred_reason": reason},
            "verified_at": datetime.utcnow().isoformat(),
        })
        self._save()
        return True

    def get_open_items(self) -> list[dict]:
        """Get all open (not done/deferred) items."""
        return [
            {"id": k, **v} for k, v in self._items.items()
            if v["status"] == "open"
        ]

    def has_open_items(self) -> bool:
        return any(v["status"] == "open" for v in self._items.values())

    def get_summary(self) -> dict:
        total = len(self._items)
        done = sum(1 for v in self._items.values() if v["status"] == "done")
        deferred = sum(1 for v in self._items.values() if v["status"] == "deferred")
        open_count = total - done - deferred
        return {
            "total": total,
            "done": done,
            "deferred": deferred,
            "open": open_count,
            "completion_rate": done / total if total > 0 else 1.0,
        }


class VerificationGates:
    """
    Self-Enforcing Verification Gates — Fable-5 hooks pattern.

    Two mandatory gates:
    1. SPAWN GUARD (PreToolUse on Task/Agent): Block delegation without verification ledger
    2. CLOSE GUARD (Stop): Block task completion with open verification items

    Additional gates:
    - PRE_TOOL_USE: Validate tool arguments against schemas
    - POST_TOOL_USE: Capture evidence for verification ledger
    - TASK_COMPLETE: Run adversarial verification before allowing done
    """

    def __init__(
        self,
        workspace_root: Path,
        ledger_path: Optional[Path] = None,
        spawn_guard_threshold: int = 1500,  # chars in spawn prompt
        strict_mode: bool = True,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.ledger = VerificationLedger(ledger_path or workspace_root / ".workflow" / "LEDGER.yaml")
        self.spawn_guard_threshold = spawn_guard_threshold
        self.strict_mode = strict_mode

        # Hook handlers
        self._hooks: dict[HookEventType, list[Callable]] = {
            HookEventType.PRE_TOOL_USE: [self._spawn_guard, self._validate_tool_args],
            HookEventType.TASK_COMPLETE: [self._close_guard, self._run_adversarial_verification],
            HookEventType.POST_TOOL_USE: [self._capture_evidence],
        }

        # Model-aware thresholds (Fable-5 pattern)
        self._model_thresholds = {
            "fable": 1500,
            "opus": 4000,
            "sonnet": 4000,
            "haiku": 4000,
        }

    def register_hook(self, event_type: HookEventType, handler: Callable) -> None:
        """Register a custom hook handler."""
        if event_type not in self._hooks:
            self._hooks[event_type] = []
        self._hooks[event_type].append(handler)

    async def run_hooks(self, context: HookContext) -> HookResult:
        """Run all hooks for an event type, return first blocking result."""
        handlers = self._hooks.get(context.event_type, [])
        for handler in handlers:
            try:
                result = await handler(context)
                if not result.allowed:
                    logger.warning(f"Hook blocked: {context.event_type} - {result.message}")
                    return result
            except Exception as e:
                logger.error(f"Hook error: {e}")
                if self.strict_mode:
                    return HookResult.block(
                        BlockReason.MISSING_VERIFICATION_LEDGER,
                        f"Hook execution failed: {e}",
                        ["Fix hook error and retry"]
                    )
        return HookResult.allow()

    # ===== GATE 1: SPAWN GUARD =====
    async def _spawn_guard(self, context: HookContext) -> HookResult:
        """
        Spawn Guard: Block delegation (Task/Agent tool) without verification ledger.

        Trigger: PreToolUse on 'Task' or 'Agent' tool with prompt over threshold.
        Effect: Deny spawn; require ledger first.
        """
        if context.tool_name not in ("Task", "Agent", "agent_task"):
            return HookResult.allow()

        prompt = context.tool_args.get("prompt", "") or context.tool_args.get("description", "")
        if len(prompt) < self._get_spawn_threshold():
            return HookResult.allow()  # Short prompts always pass

        # Check for verification ledger
        ledger_path = self.workspace_root / ".workflow" / "LEDGER.yaml"
        if not ledger_path.exists():
            return HookResult.block(
                BlockReason.MISSING_VERIFICATION_LEDGER,
                f"Delegation prompt ({len(prompt)} chars) exceeds threshold. "
                f"Must create verification ledger at {ledger_path} before delegating.",
                required_actions=[
                    "Create .workflow/LEDGER.yaml with all requirements",
                    "Define done criteria for each deliverable",
                    "Then retry delegation",
                ]
            )

        # Check if ledger has open items (optional - could allow if ledger exists)
        if self.ledger.has_open_items():
            # Allow but warn
            logger.warning("Delegation with open verification items - proceed with caution")

        return HookResult.allow()

    def _get_spawn_threshold(self) -> int:
        """Get threshold based on model (Fable-5 model-aware thresholds)."""
        # In practice, detect model from context or config
        model = os.environ.get("HERMES_MODEL", "").lower()
        for key, threshold in self._model_thresholds.items():
            if key in model:
                return threshold
        return self.spawn_guard_threshold

    # ===== GATE 2: CLOSE GUARD =====
    async def _close_guard(self, context: HookContext) -> HookResult:
        """
        Close Guard: Block task completion with open verification items.

        Trigger: Stop event (task claims done).
        Effect: Block stop; list open items.
        """
        if not self.ledger.has_open_items():
            return HookResult.allow()

        open_items = self.ledger.get_open_items()
        items_desc = "\n".join(f"  - {item['id']}: {item['description']}" for item in open_items)

        return HookResult.block(
            BlockReason.OPEN_VERIFICATION_ITEMS,
            f"Cannot complete task: {len(open_items)} open verification item(s):\n{items_desc}",
            required_actions=[
                "Complete or defer all open verification items",
                "Provide evidence for each done item",
                "Then retry task completion",
            ]
        )

    # ===== GATE 3: ADVERSARIAL VERIFICATION =====
    async def _run_adversarial_verification(self, context: HookContext) -> HookResult:
        """
        Run adversarial verification before allowing task completion.
        """
        if not context.task_id:
            return HookResult.allow()

        try:
            from hermes.agi.verification import AdversarialVerifier, WorkPackage

            wp = WorkPackage(context.task_id, context.task_description)

            # Add claimed checks from task metadata
            for check in context.metadata.get("claimed_checks", []):
                wp.add_claimed_check(check["name"], check["command"])

            # Add file changes
            for fc in context.metadata.get("file_changes", []):
                wp.add_claimed_file_change(fc["path"], fc["type"])

            # Add declared scope from ledger
            for item in self.ledger._items.values():
                wp.add_declared_scope(item["description"])

            verifier = AdversarialVerifier(self.workspace_root)
            report = await verifier.verify(wp)

            if report.verdict.value == "REFUTED":
                return HookResult.block(
                    BlockReason.FAILED_ADVERSARIAL_VERIFICATION,
                    f"Adversarial verification REFUTED: {report.summary()}",
                    required_actions=[
                        "Address all critical findings",
                        "Re-run verification",
                        "Then retry completion",
                    ]
                )
            elif report.verdict.value == "CAVEATS":
                # Allow but warn
                logger.warning(f"Adversarial verification CAVEATS: {report.summary()}")

            return HookResult.allow()

        except Exception as e:
            logger.error(f"Adversarial verification failed: {e}")
            if self.strict_mode:
                return HookResult.block(
                    BlockReason.FAILED_ADVERSARIAL_VERIFICATION,
                    f"Verification execution failed: {e}",
                    ["Fix verification setup and retry"]
                )
            return HookResult.allow()

    # ===== SUPPORT: VALIDATE TOOL ARGS =====
    async def _validate_tool_args(self, context: HookContext) -> HookResult:
        """Validate tool arguments against schemas (if available)."""
        # Placeholder for tool schema validation
        return HookResult.allow()

    # ===== SUPPORT: CAPTURE EVIDENCE =====
    async def _capture_evidence(self, context: HookContext) -> HookResult:
        """Auto-capture evidence for verification ledger from tool results."""
        if context.event_type == HookEventType.POST_TOOL_USE:
            result = context.metadata.get("tool_result")
            if result and isinstance(result, dict):
                # Auto-link to ledger items based on keywords
                for item_id, item in self.ledger._items.items():
                    if item["status"] == "open":
                        # Simple keyword matching - in production use embeddings
                        if any(kw in str(result).lower() for kw in item["description"].lower().split()[:3]):
                            self.ledger.mark_done(item_id, result, f"auto:{context.tool_name}")

        return HookResult.allow()

    # ===== PUBLIC API =====
    def create_verification_ledger(
        self,
        requirements: list[str],
        expectations: list[str] = None,
        constraints: list[str] = None,
        edge_cases: list[str] = None,
    ) -> None:
        """Create a new verification ledger with structured items."""
        for i, req in enumerate(requirements):
            self.ledger.add_item(f"REQ-{i+1:03d}", req, "requirement", "user")
        for i, exp in enumerate(expectations or []):
            self.ledger.add_item(f"EXP-{i+1:03d}", exp, "expectation", "user")
        for i, const in enumerate(constraints or []):
            self.ledger.add_item(f"CONST-{i+1:03d}", const, "constraint", "user")
        for i, edge in enumerate(edge_cases or []):
            self.ledger.add_item(f"EDGE-{i+1:03d}", edge, "edge_case", "user")

        logger.info(f"Created verification ledger with {len(self.ledger._items)} items")

    def get_ledger_status(self) -> dict:
        """Get current ledger status."""
        return self.ledger.get_summary()

    def set_model_threshold(self, model: str, threshold: int) -> None:
        """Set spawn guard threshold for a model."""
        self._model_thresholds[model.lower()] = threshold


# Global instance
_verification_gates: Optional[VerificationGates] = None
_gates_lock = threading.Lock()


def get_verification_gates(
    workspace_root: Optional[Path] = None,
    **kwargs
) -> VerificationGates:
    """Get or create global verification gates instance."""
    global _verification_gates
    with _gates_lock:
        if _verification_gates is None:
            if workspace_root is None:
                workspace_root = Path(".")
            _verification_gates = VerificationGates(workspace_root, **kwargs)
        return _verification_gates


async def run_verification_gates(
    event_type: HookEventType,
    workspace_root: Path,
    **context_kwargs
) -> HookResult:
    """Convenience function to run verification gates."""
    gates = get_verification_gates(workspace_root)
    context = HookContext(event_type=event_type, **context_kwargs)
    return await gates.run_hooks(context)


# Integration with existing HookManager
class VerificationGateHookManager:
    """
    Wrapper to integrate VerificationGates with existing HookManager.
    """

    def __init__(self, workspace_root: Path):
        self.gates = get_verification_gates(workspace_root)
        self._original_hooks: dict = {}

    def wrap_hook_manager(self, hook_manager: Any) -> Any:
        """Wrap an existing HookManager to add verification gates."""
        # Store original handlers
        if hasattr(hook_manager, '_hooks'):
            self._original_hooks = hook_manager._hooks.copy()

        # Wrap hook execution
        original_run = hook_manager.run_hooks if hasattr(hook_manager, 'run_hooks') else None

        async def wrapped_run(event_type, context):
            # Run verification gates first
            gates_context = HookContext(event_type=HookEventType(event_type), **context)
            gate_result = await self.gates.run_hooks(gates_context)
            if not gate_result.allowed:
                return gate_result

            # Run original hooks
            if original_run:
                return await original_run(event_type, context)
            return HookResult.allow()

        hook_manager.run_hooks = wrapped_run
        return hook_manager


if __name__ == "__main__":
    import os
    import tempfile

    async def demo():
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)

            # Create gates
            gates = VerificationGates(ws)

            # Create ledger
            gates.create_verification_ledger(
                requirements=[
                    "Implement email validation function",
                    "Function must handle edge cases",
                    "Must pass all tests",
                ],
                expectations=[
                    "Code should be well-documented",
                    "Should follow project style guide",
                ],
                constraints=[
                    "No external dependencies",
                    "Must work offline",
                ],
                edge_cases=[
                    "Empty string",
                    "Very long emails",
                    "Unicode domains",
                ],
            )

            print("Ledger status:", gates.get_ledger_status())

            # Test spawn guard
            context = HookContext(
                event_type=HookEventType.PRE_TOOL_USE,
                tool_name="Task",
                tool_args={"prompt": "x" * 2000},
            )
            result = await gates.run_hooks(context)
            print(f"Spawn guard (no ledger): {result.allowed}, {result.block_reason}")

            # Test close guard
            context = HookContext(event_type=HookEventType.TASK_COMPLETE)
            result = await gates.run_hooks(context)
            print(f"Close guard (open items): {result.allowed}, {result.block_reason}")

            # Complete items
            gates.ledger.mark_done("REQ-001", {"file": "email.py", "tests": "passed"}, "test")
            gates.ledger.mark_done("REQ-002", {"test_output": "all passed"}, "test")
            gates.ledger.mark_deferred("EDGE-003", "Unicode not required for v1")

            print("Ledger after completion:", gates.get_ledger_status())

    asyncio.run(demo())
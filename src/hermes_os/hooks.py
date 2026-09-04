"""
HERMES INTELLIGENCE OS — DETERMINISTIC LIFECYCLE HOOKS
=====================================================
Inspired by Claude Code's deterministic lifecycle architecture.
Provides non-LLM, hard policy guarantees across the OS execution lifecycle.
Hooks can inspect, modify, or block actions before and after tool calls,
context compaction, subagent lifecycles, and user interactions.
"""

from __future__ import annotations

import enum
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("hermes.os.hooks")


class HookEventType(str, enum.Enum):
    """Lifecycle events where deterministic hooks can execute."""
    SESSION_START = "session_start"
    SESSION_STOP = "session_stop"
    USER_PROMPT_SUBMIT = "user_prompt_submit"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    POST_TOOL_FAILURE = "post_tool_failure"
    SUBAGENT_START = "subagent_start"
    SUBAGENT_STOP = "subagent_stop"
    PRE_COMPACT = "pre_compact"
    POST_COMPACT = "post_compact"
    FILE_CHANGED = "file_changed"
    PERMISSION_REQUEST = "permission_request"


class HookAction(str, enum.Enum):
    """Action outcome from a lifecycle hook."""
    CONTINUE = "continue"       # Proceed with execution unchanged
    MODIFY = "modify"           # Proceed with mutated payload / parameters
    BLOCK = "block"             # Halt execution and return reason to agent


@dataclass
class HookResult:
    """Result returned by an executed hook."""
    action: HookAction = HookAction.CONTINUE
    modified_payload: Optional[Dict[str, Any]] = None
    reason: str = ""
    hook_name: str = ""

    @property
    def is_blocked(self) -> bool:
        return self.action == HookAction.BLOCK


@dataclass
class LifecycleHook:
    """Definition of a deterministic lifecycle hook."""
    name: str
    event_type: HookEventType
    handler: Callable[[Dict[str, Any]], HookResult]
    priority: int = 100          # Lower number executes first (e.g. 10 runs before 100)
    enabled: bool = True
    is_blocking: bool = True     # If True, a BLOCK action halts the event chain


# =====================================================================
# Built-in Default Safety & Quality Hooks (Claude Code Inspired)
# =====================================================================

def git_safety_handler(payload: Dict[str, Any]) -> HookResult:
    """
    Deterministic safety hook: Blocks destructive git commands
    (e.g., git reset --hard, git push --force, git clean -fdx).
    """
    command = str(payload.get("command", "") or payload.get("code", "")).lower()
    dangerous_patterns = [
        r"git\s+reset\s+--hard",
        r"git\s+clean\s+-[a-z]*f",
        r"git\s+push\s+.*--force",
        r"git\s+checkout\s+--\s+\.",
        r"git\s+restore\s+\.",
        r"rm\s+-rf\s+/",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, command):
            return HookResult(
                action=HookAction.BLOCK,
                reason=f"GitSafetyHook blocked dangerous command matching pattern '{pattern}'",
                hook_name="git_safety",
            )
    return HookResult(action=HookAction.CONTINUE, hook_name="git_safety")


def secret_scrubber_handler(payload: Dict[str, Any]) -> HookResult:
    """
    Deterministic privacy hook: Redacts API keys, bearer tokens, and credentials
    from tool outputs before passing them to the context window.
    """
    secret_patterns = [
        (r"(sk-[a-zA-Z0-9]{20,})", "[REDACTED_OPENAI_KEY]"),
        (r"(ghp_[a-zA-Z0-9]{20,})", "[REDACTED_GITHUB_TOKEN]"),
        (r"(Bearer\s+[a-zA-Z0-9_\-\.]{20,})", "Bearer [REDACTED_BEARER_TOKEN]"),
        (r"(password\s*[:=]\s*['\"][^'\"]+['\"])", "password='[REDACTED_PASSWORD]'"),
    ]

    modified = False
    payload_copy = dict(payload)

    def _scrub_text(text: str) -> tuple[str, bool]:
        nonlocal modified
        scrubbed = text
        for pat, repl in secret_patterns:
            if re.search(pat, scrubbed, re.IGNORECASE):
                scrubbed = re.sub(pat, repl, scrubbed, flags=re.IGNORECASE)
                modified = True
        return scrubbed, modified

    for k, v in list(payload_copy.items()):
        if isinstance(v, str):
            new_v, changed = _scrub_text(v)
            if changed:
                payload_copy[k] = new_v
        elif isinstance(v, dict):
            # Nested dictionary scrub
            for sub_k, sub_v in list(v.items()):
                if isinstance(sub_v, str):
                    new_sub_v, changed = _scrub_text(sub_v)
                    if changed:
                        payload_copy[k][sub_k] = new_sub_v

    if modified:
        return HookResult(
            action=HookAction.MODIFY,
            modified_payload=payload_copy,
            reason="SecretScrubberHook redacted sensitive secrets from payload",
            hook_name="secret_scrubber",
        )
    return HookResult(action=HookAction.CONTINUE, hook_name="secret_scrubber")


def file_change_audit_handler(payload: Dict[str, Any]) -> HookResult:
    """
    Deterministic audit hook: Tracks file modifications and adds audit metadata.
    """
    file_path = payload.get("file_path") or payload.get("path") or payload.get("target_file")
    if file_path:
        audit_payload = dict(payload)
        audit_payload["_audited_by_hook"] = True
        audit_payload["_target_path"] = str(file_path)
        return HookResult(
            action=HookAction.MODIFY,
            modified_payload=audit_payload,
            reason=f"FileChangeAuditor recorded change to {file_path}",
            hook_name="file_change_auditor",
        )
    return HookResult(action=HookAction.CONTINUE, hook_name="file_change_auditor")


# =====================================================================
# Hook Manager
# =====================================================================

class HookManager:
    """
    Central deterministic lifecycle hook registry and execution manager.
    Coordinates hook registration, prioritization, execution, and error isolation.
    """

    def __init__(self, register_defaults: bool = True):
        self._hooks: Dict[HookEventType, List[LifecycleHook]] = {
            event_type: [] for event_type in HookEventType
        }
        self._history: List[Dict[str, Any]] = []

        if register_defaults:
            self._register_default_hooks()

    def _register_default_hooks(self) -> None:
        """Register default safety, privacy, and audit hooks."""
        self.register(LifecycleHook(
            name="git_safety",
            event_type=HookEventType.PRE_TOOL_USE,
            handler=git_safety_handler,
            priority=10,
            is_blocking=True,
        ))
        self.register(LifecycleHook(
            name="secret_scrubber",
            event_type=HookEventType.POST_TOOL_USE,
            handler=secret_scrubber_handler,
            priority=20,
            is_blocking=False,
        ))
        self.register(LifecycleHook(
            name="file_change_auditor",
            event_type=HookEventType.FILE_CHANGED,
            handler=file_change_audit_handler,
            priority=50,
            is_blocking=False,
        ))

    def register(self, hook: LifecycleHook) -> None:
        """Register a new lifecycle hook sorted by priority."""
        hooks = self._hooks.setdefault(hook.event_type, [])
        # Remove existing hook with same name if present
        self._hooks[hook.event_type] = [h for h in hooks if h.name != hook.name]
        self._hooks[hook.event_type].append(hook)
        self._hooks[hook.event_type].sort(key=lambda h: h.priority)
        logger.debug(f"Registered hook '{hook.name}' for {hook.event_type.value} (priority={hook.priority})")

    def unregister(self, name: str, event_type: Optional[HookEventType] = None) -> bool:
        """Unregister a hook by name."""
        removed = False
        target_types = [event_type] if event_type else list(self._hooks.keys())
        for et in target_types:
            orig_len = len(self._hooks.get(et, []))
            self._hooks[et] = [h for h in self._hooks.get(et, []) if h.name != name]
            if len(self._hooks[et]) < orig_len:
                removed = True
        return removed

    def get_hooks(self, event_type: HookEventType) -> List[LifecycleHook]:
        """Get all hooks registered for an event type."""
        return list(self._hooks.get(event_type, []))

    def dispatch(
        self,
        event_type: HookEventType,
        payload: Dict[str, Any],
    ) -> HookResult:
        """
        Dispatch an event through all registered hooks for that event type.
        Supports short-circuiting on BLOCK if the hook is blocking.
        Accumulates payload modifications across chained MODIFY hooks.
        """
        current_payload = dict(payload)
        hooks = [h for h in self._hooks.get(event_type, []) if h.enabled]

        for hook in hooks:
            try:
                result = hook.handler(current_payload)
                self._history.append({
                    "event_type": event_type.value,
                    "hook_name": hook.name,
                    "action": result.action.value,
                    "reason": result.reason,
                })

                if result.action == HookAction.BLOCK:
                    logger.warning(f"Hook '{hook.name}' BLOCKED {event_type.value}: {result.reason}")
                    if hook.is_blocking:
                        return result

                elif result.action == HookAction.MODIFY and result.modified_payload:
                    current_payload = result.modified_payload

            except Exception as e:
                logger.error(f"Error executing hook '{hook.name}' on {event_type.value}: {e}", exc_info=True)
                if hook.is_blocking:
                    return HookResult(
                        action=HookAction.BLOCK,
                        reason=f"Hook '{hook.name}' raised unexpected exception: {e}",
                        hook_name=hook.name,
                    )

        # All hooks executed without blocking
        return HookResult(
            action=HookAction.MODIFY if current_payload != payload else HookAction.CONTINUE,
            modified_payload=current_payload if current_payload != payload else None,
            reason="All lifecycle hooks passed successfully",
            hook_name="chain",
        )

    def get_history(self) -> List[Dict[str, Any]]:
        """Return history of dispatched hooks."""
        return list(self._history)

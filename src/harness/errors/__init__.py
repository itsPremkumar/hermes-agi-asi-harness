"""Structured exception hierarchy for the Harness."""

from __future__ import annotations

from typing import Any, Optional


class HarnessError(Exception):
    """Base exception for all Harness errors."""

    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"type": type(self).__name__, "message": self.message, "details": self.details}


class NodeError(HarnessError):
    """Error raised by a graph node."""

    def __init__(self, message: str, *, node_id: str = "", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.node_id = node_id


class GraphError(HarnessError):
    """Error raised during graph execution."""

    def __init__(self, message: str, *, graph_id: str = "", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.graph_id = graph_id


class EvalError(HarnessError):
    """Error raised during evaluation."""

    def __init__(self, message: str, *, eval_name: str = "", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.eval_name = eval_name


class ToolError(HarnessError):
    """Error raised by a tool."""

    def __init__(self, message: str, *, tool_name: str = "", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.tool_name = tool_name


class MemoryError(HarnessError):
    """Error raised by the memory layer."""

    def __init__(self, message: str, *, operation: str = "", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.operation = operation


class FeedbackError(HarnessError):
    """Error raised by the feedback engine."""

    def __init__(self, message: str, *, node_id: str = "", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.node_id = node_id


class PluginError(HarnessError):
    """Error raised by a plugin."""

    def __init__(self, message: str, *, plugin_id: str = "", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.plugin_id = plugin_id


class LangSmithError(HarnessError):
    """Error raised by LangSmith integration."""

    def __init__(self, message: str, *, operation: str = "", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.operation = operation


class DeepAgentError(HarnessError):
    """Error raised by Deep Agents coordination."""

    def __init__(self, message: str, *, agent_id: str = "", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.agent_id = agent_id


class CircuitBreakerOpenError(HarnessError):
    """Raised when the circuit breaker is open."""

    def __init__(self, message: str = "Circuit breaker is open", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class RateLimitError(HarnessError):
    """Raised when a rate limit is hit."""

    def __init__(self, message: str = "Rate limit exceeded", *, retry_after: float = 0.0, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class DeadLetterError(HarnessError):
    """Raised when a node is sent to the dead-letter queue."""

    def __init__(self, message: str, *, node_id: str = "", attempts: int = 0, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.node_id = node_id
        self.attempts = attempts


# Also expose resilience classes
from .resilience import CircuitBreaker, DeadLetterQueue, make_retry_decorator, CircuitState

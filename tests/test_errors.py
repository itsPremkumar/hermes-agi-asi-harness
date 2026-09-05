"""Tests for errors/ — Error Handling."""

from __future__ import annotations

import pytest

from src.harness.errors import (
    CircuitBreakerOpenError,
    DeadLetterError,
    DeepAgentError,
    EvalError,
    FeedbackError,
    GraphError,
    HarnessError,
    LangSmithError,
    MemoryError,
    NodeError,
    PluginError,
    RateLimitError,
    ToolError,
)
from src.harness.errors.resilience import (
    CircuitBreaker,
    CircuitState,
    DeadLetterQueue,
    make_retry_decorator,
)


class TestHarnessError:
    """Tests for HarnessError base class."""

    def test_create_error(self):
        err = HarnessError("something failed")
        assert err.message == "something failed"
        assert str(err) == "something failed"

    def test_error_with_details(self):
        err = HarnessError("fail", details={"key": "value"})
        assert err.details == {"key": "value"}

    def test_to_dict(self):
        err = HarnessError("fail", details={"a": 1})
        d = err.to_dict()
        assert d["type"] == "HarnessError"
        assert d["message"] == "fail"


class TestNodeError:
    """Tests for NodeError."""

    def test_create(self):
        err = NodeError("node failed", node_id="n1")
        assert err.node_id == "n1"
        assert "node failed" in err.message


class TestGraphError:
    """Tests for GraphError."""

    def test_create(self):
        err = GraphError("graph failed", graph_id="g1")
        assert err.graph_id == "g1"


class TestEvalError:
    """Tests for EvalError."""

    def test_create(self):
        err = EvalError("eval failed", eval_name="e1")
        assert err.eval_name == "e1"


class TestToolError:
    """Tests for ToolError."""

    def test_create(self):
        err = ToolError("tool failed", tool_name="t1")
        assert err.tool_name == "t1"


class TestMemoryError:
    """Tests for MemoryError."""

    def test_create(self):
        err = MemoryError("memory failed", operation="store")
        assert err.operation == "store"


class TestFeedbackError:
    """Tests for FeedbackError."""

    def test_create(self):
        err = FeedbackError("feedback failed", node_id="n1")
        assert err.node_id == "n1"


class TestPluginError:
    """Tests for PluginError."""

    def test_create(self):
        err = PluginError("plugin failed", plugin_id="p1")
        assert err.plugin_id == "p1"


class TestLangSmithError:
    """Tests for LangSmithError."""

    def test_create(self):
        err = LangSmithError("ls failed", operation="trace")
        assert err.operation == "trace"


class TestDeepAgentError:
    """Tests for DeepAgentError."""

    def test_create(self):
        err = DeepAgentError("agent failed", agent_id="a1")
        assert err.agent_id == "a1"


class TestCircuitBreakerOpenError:
    """Tests for CircuitBreakerOpenError."""

    def test_default_message(self):
        err = CircuitBreakerOpenError()
        assert "open" in err.message.lower()


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_create(self):
        err = RateLimitError(retry_after=30.0)
        assert err.retry_after == 30.0


class TestDeadLetterError:
    """Tests for DeadLetterError."""

    def test_create(self):
        err = DeadLetterError("sent to DLQ", node_id="n1", attempts=3)
        assert err.node_id == "n1"
        assert err.attempts == 3


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_allow_request_when_closed(self):
        cb = CircuitBreaker()
        assert cb.allow_request() is True

    def test_circuit_opens_after_failures(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        import time
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

    def test_decorator_success(self):
        cb = CircuitBreaker()

        @cb
        def my_func():
            return "ok"

        assert my_func() == "ok"

    def test_decorator_failure(self):
        cb = CircuitBreaker(failure_threshold=1)

        @cb
        def my_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            my_func()
        assert cb.state == CircuitState.OPEN


class TestDeadLetterQueue:
    """Tests for DeadLetterQueue."""

    def test_enqueue(self):
        dlq = DeadLetterQueue()
        entry = dlq.enqueue("n1", ValueError("fail"))
        assert entry["node_id"] == "n1"

    def test_dequeue(self):
        dlq = DeadLetterQueue()
        dlq.enqueue("n1", ValueError("fail"))
        entry = dlq.dequeue()
        assert entry is not None
        assert entry["node_id"] == "n1"

    def test_size(self):
        dlq = DeadLetterQueue()
        dlq.enqueue("n1", ValueError("fail"))
        assert dlq.size == 1

    def test_clear(self):
        dlq = DeadLetterQueue()
        dlq.enqueue("n1", ValueError("fail"))
        dlq.clear()
        assert dlq.size == 0

    def test_all(self):
        dlq = DeadLetterQueue()
        dlq.enqueue("n1", ValueError("fail"))
        dlq.enqueue("n2", ValueError("fail2"))
        assert len(dlq.all()) == 2

    def test_max_size(self):
        dlq = DeadLetterQueue(max_size=2)
        dlq.enqueue("n1", ValueError("fail"))
        dlq.enqueue("n2", ValueError("fail2"))
        dlq.enqueue("n3", ValueError("fail3"))
        assert dlq.size == 2


class TestMakeRetryDecorator:
    """Tests for make_retry_decorator."""

    def test_successful_call(self):
        decorator = make_retry_decorator(max_attempts=3)

        @decorator
        def my_func():
            return "ok"

        assert my_func() == "ok"

    def test_retry_on_error(self):
        attempts = [0]
        decorator = make_retry_decorator(max_attempts=3, min_wait=0.01, max_wait=0.02)

        @decorator
        def my_func():
            attempts[0] += 1
            if attempts[0] < 2:
                raise HarnessError("fail")
            return "ok"

        assert my_func() == "ok"
        assert attempts[0] == 2

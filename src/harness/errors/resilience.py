"""Circuit breaker, retry policies, and dead-letter queue."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from . import (
    CircuitBreakerOpenError,
    HarnessError,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker pattern for LLM calls."""

    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _failure_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)
    _half_open_calls: int = field(default=0, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
            self._half_open_calls = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def allow_request(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN and self._half_open_calls < self.half_open_max_calls:
            self._half_open_calls += 1
            return True
        return False

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.allow_request():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open (failures={self._failure_count})"
                )
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise
        return wrapper


def make_retry_decorator(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: tuple[type[Exception], ...] = (HarnessError,),
) -> Callable[..., Any]:
    """Create a tenacity retry decorator with exponential backoff."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=min_wait,
            max=max_wait,
            exp_base=exponential_base,
        ),
        retry=retry_if_exception_type(retry_on),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry {retry_state.attempt_number}/{max_attempts} after error: {retry_state.outcome.exception() if retry_state.outcome else 'unknown'}"
        ),
        reraise=True,
    )


@dataclass
class DeadLetterQueue:
    """Dead-letter queue for failed graph nodes."""

    max_size: int = 1000
    _queue: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def enqueue(self, node_id: str, error: Exception, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = {
            "node_id": node_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "payload": payload or {},
            "timestamp": time.time(),
        }
        with self._lock:
            if len(self._queue) >= self.max_size:
                self._queue.pop(0)
            self._queue.append(entry)
        logger.error(f"Node {node_id} sent to dead-letter queue: {error}")
        return entry

    def dequeue(self) -> dict[str, Any] | None:
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
        return None

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def clear(self) -> None:
        with self._lock:
            self._queue.clear()

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._queue)

"""Utility functions for MCPTest."""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator to retry async functions on failure."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (2 ** attempt))
            if last_exception:
                raise last_exception
            return None

        return wrapper  # type: ignore

    return decorator


def timing_ms(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to measure function execution time in milliseconds."""

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        start = time.monotonic()
        result = await func(*args, **kwargs)
        duration = (time.monotonic() - start) * 1000
        return result, duration

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        start = time.monotonic()
        result = func(*args, **kwargs)
        duration = (time.monotonic() - start) * 1000
        return result, duration

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def truncate_string(s: str, max_len: int = 100) -> str:
    """Truncate a string with ellipsis if it exceeds max_len."""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def sanitize_error_message(msg: str) -> str:
    """Sanitize an error message to remove sensitive information."""
    import re
    # Remove file paths
    msg = re.sub(r"[A-Za-z]:\\[^\s]+", "<path>", msg)
    # Remove URLs with credentials
    msg = re.sub(r"https?://[^/\s]+:[^@\s]+@", "https://<creds>@", msg)
    # Remove IP addresses
    msg = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<ip>", msg)
    return msg

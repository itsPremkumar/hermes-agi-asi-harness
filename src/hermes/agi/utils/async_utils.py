"""Async utilities."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Iterable, TypeVar

T = TypeVar("T")


async def run_async(coro: Awaitable[T]) -> T:
    """Run an awaitable synchronously."""
    return await coro


async def gather_limited(
    coros: Iterable[Awaitable[T]],
    limit: int = 5,
) -> list[T]:
    """Gather with concurrency limit."""
    semaphore = asyncio.Semaphore(limit)
    
    async def limited(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro
    
    return await asyncio.gather(*[limited(c) for c in coros])

"""Redis client for caching."""
import os
import json
import hashlib
from typing import Optional, Any

import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class RedisClient:
    """Async Redis helper with graceful fallback."""

    def __init__(self):
        self._pool: Optional[redis.Redis] = None
        self._available = False

    async def connect(self):
        try:
            self._pool = redis.from_url(REDIS_URL, decode_responses=True)
            await self._pool.ping()
            self._available = True
        except Exception:
            self._available = False

    async def disconnect(self):
        if self._pool:
            await self._pool.close()

    def _cache_key(self, prefix: str, identifier: str) -> str:
        h = hashlib.md5(identifier.encode()).hexdigest()[:12]
        return f"mcphub:{prefix}:{h}"

    async def get(self, prefix: str, identifier: str) -> Optional[Any]:
        if not self._available:
            return None
        try:
            raw = await self._pool.get(self._cache_key(prefix, identifier))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def set(self, prefix: str, identifier: str, value: Any, ttl: int = 300):
        if not self._available:
            return
        try:
            await self._pool.set(self._cache_key(prefix, identifier), json.dumps(value), ex=ttl)
        except Exception:
            pass

    async def invalidate(self, prefix: str, identifier: str):
        if not self._available:
            return
        try:
            await self._pool.delete(self._cache_key(prefix, identifier))
        except Exception:
            pass


redis_client = RedisClient()

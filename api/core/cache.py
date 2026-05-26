from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from api.core.config import settings


class RedisCache:
    """Async Redis cache wrapper."""

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = await aioredis.from_url(settings.redis_url)

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        if not self._redis:
            return default
        value = await self._redis.get(key)
        if value is None:
            return default
        return json.loads(value)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        if not self._redis:
            return
        await self._redis.setex(
            key,
            ttl if ttl is not None else self.ttl,
            json.dumps(value, default=str),
        )

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        if not self._redis:
            return
        await self._redis.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern."""
        if not self._redis:
            return
        keys = await self._redis.keys(pattern)
        if keys:
            await self._redis.delete(*keys)


analytics_cache = RedisCache(ttl=300)
jobs_cache = RedisCache(ttl=60)

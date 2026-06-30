from __future__ import annotations

import json
import logging
import time
from typing import Any

import redis.asyncio as aioredis

from api.core.config import settings

logger = logging.getLogger(__name__)

# After a failed Redis call, skip retrying for this long. Without it, an
# unreachable Redis (e.g. unresolvable host) would pay a full connect
# timeout on every single request instead of just the first.
_CIRCUIT_BREAKER_SECONDS = 10


class RedisCache:
    """Async Redis cache wrapper.

    All operations fail open: if Redis is unreachable, reads behave as a
    cache miss, writes are silently dropped, and locks/limits report as
    "go ahead". Redis is a coordination layer here, not a source of
    truth, so an outage should degrade the app rather than take it down.
    """

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._redis: aioredis.Redis | None = None
        self._unavailable_until: float = 0.0

    async def connect(self) -> None:
        """Connect to Redis.

        Short socket timeouts keep a slow/unreachable Redis from making
        every request hang — operations fail fast and the fail-open
        methods below take over.
        """
        self._redis = await aioredis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        self._unavailable_until = 0.0

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _available(self) -> bool:
        return self._redis is not None and time.monotonic() >= self._unavailable_until

    def _mark_unavailable(self) -> None:
        self._unavailable_until = time.monotonic() + _CIRCUIT_BREAKER_SECONDS

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        if not self._available():
            return default
        try:
            value = await self._redis.get(key)  # type: ignore[union-attr]
        except Exception:
            logger.warning("Redis get failed for key %s", key, exc_info=True)
            self._mark_unavailable()
            return default
        if value is None:
            return default
        return json.loads(value)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        if not self._available():
            return
        try:
            await self._redis.setex(  # type: ignore[union-attr]
                key,
                ttl if ttl is not None else self.ttl,
                json.dumps(value, default=str),
            )
        except Exception:
            logger.warning("Redis set failed for key %s", key, exc_info=True)
            self._mark_unavailable()

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        if not self._available():
            return
        try:
            await self._redis.delete(key)  # type: ignore[union-attr]
        except Exception:
            logger.warning("Redis delete failed for key %s", key, exc_info=True)
            self._mark_unavailable()

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern."""
        if not self._available():
            return
        try:
            keys = await self._redis.keys(pattern)  # type: ignore[union-attr]
            if keys:
                await self._redis.delete(*keys)  # type: ignore[union-attr]
        except Exception:
            logger.warning(
                "Redis delete_pattern failed for pattern %s", pattern, exc_info=True
            )
            self._mark_unavailable()

    async def increment(self, key: str, ttl: int) -> int:
        """Atomically increment a counter, expiring it `ttl` seconds after
        its first increment. Returns 0 (i.e. "no limit hit yet") if Redis
        is unavailable.
        """
        if not self._available():
            return 0
        try:
            count: int = await self._redis.incr(key)  # type: ignore[union-attr]
            if count == 1:
                await self._redis.expire(key, ttl)  # type: ignore[union-attr]
            return count
        except Exception:
            logger.warning("Redis increment failed for key %s", key, exc_info=True)
            self._mark_unavailable()
            return 0

    async def acquire_lock(self, key: str, ttl: int) -> bool:
        """Try to claim a short-lived lock, expiring after `ttl` seconds.

        Returns True if the lock was acquired (or Redis is unavailable,
        in which case there's no coordination to honor). Returns False
        if another holder already has the lock.
        """
        if not self._available():
            return True
        try:
            return bool(
                await self._redis.set(key, "1", nx=True, ex=ttl)  # type: ignore[union-attr]
            )
        except Exception:
            logger.warning("Redis acquire_lock failed for key %s", key, exc_info=True)
            self._mark_unavailable()
            return True


analytics_cache = RedisCache(ttl=300)
jobs_cache = RedisCache(ttl=60)
rate_limit_cache = RedisCache(ttl=60)
domain_throttle_cache = RedisCache(ttl=60)

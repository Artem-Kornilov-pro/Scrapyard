import time

from fastapi import HTTPException, Request, status

from api.core.cache import rate_limit_cache
from api.core.config import settings


async def enforce_rate_limit(request: Request) -> None:
    """Fixed-window rate limit per client IP, backed by Redis.

    Window is the current UTC minute, so the limit resets on minute
    boundaries. Fails open if Redis is unreachable — see RedisCache.
    """
    if settings.rate_limit_per_minute <= 0:
        return

    client_ip = request.client.host if request.client else "unknown"
    window = int(time.time() // 60)
    key = f"ratelimit:{client_ip}:{window}"

    count = await rate_limit_cache.increment(key, ttl=60)
    if count > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded, try again later",
        )

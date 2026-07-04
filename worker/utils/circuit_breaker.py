from api.core.cache import domain_throttle_cache
from api.core.config import settings


def _failures_key(domain: str) -> str:
    return f"circuit:failures:{domain}"


def _open_key(domain: str) -> str:
    return f"circuit:open:{domain}"


async def is_open(domain: str) -> bool:
    """True if `domain` is in cooldown after repeated 403/429 responses.

    While open, the caller should defer scrapes to this domain instead
    of retrying immediately -- a site that's actively blocking us won't
    stop because we hit it faster.
    """
    return bool(await domain_throttle_cache.get(_open_key(domain)))


async def record_blocked(domain: str) -> None:
    """Record a 403/429 response for `domain`.

    After `circuit_breaker_failure_threshold` consecutive blocks, the
    circuit opens for `circuit_breaker_cooldown_seconds`.
    """
    ttl = settings.circuit_breaker_cooldown_seconds
    count = await domain_throttle_cache.increment(_failures_key(domain), ttl=ttl)
    if count >= settings.circuit_breaker_failure_threshold:
        await domain_throttle_cache.set(_open_key(domain), True, ttl=ttl)


async def record_success(domain: str) -> None:
    """Reset the failure count for `domain` after a non-blocked response."""
    await domain_throttle_cache.delete(_failures_key(domain))

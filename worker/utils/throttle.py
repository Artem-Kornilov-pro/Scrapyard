from urllib.parse import urlparse

from api.core.cache import domain_throttle_cache
from api.core.config import settings


def extract_domain(url: str) -> str:
    """Return the host:port part of a URL, used as the throttle key."""
    return urlparse(url).netloc


async def acquire_domain_slot(domain: str) -> bool:
    """Try to claim the right to scrape `domain` right now.

    Backed by a short-lived Redis lock shared across all workers, so
    concurrent jobs targeting the same domain don't hit it at once.
    Returns False if another job already holds the slot within the
    current throttle window; the caller should defer and retry later.
    """
    if settings.domain_throttle_seconds <= 0:
        return True

    key = f"throttle:domain:{domain}"
    ttl = max(1, int(settings.domain_throttle_seconds))
    return await domain_throttle_cache.acquire_lock(key, ttl)

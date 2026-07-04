import hashlib
from typing import Any

from api.core.config import settings


def get_proxy_for_domain(domain: str) -> dict[str, Any] | None:
    """Pick a proxy for `domain` from the configured pool.

    Assignment is deterministic (hash of the domain), so a given domain
    consistently uses the same proxy across runs -- useful for sites
    that fingerprint by IP -- while different domains spread across
    the pool. Returns None if no proxies are configured.
    """
    proxies = settings.proxy_list
    if not proxies:
        return None
    index = int(hashlib.sha256(domain.encode()).hexdigest(), 16) % len(proxies)
    return {"server": proxies[index]}

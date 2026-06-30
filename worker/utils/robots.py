import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from celery.utils.log import get_task_logger

from api.core.config import settings

logger = get_task_logger(__name__)

# robots.txt rarely changes; one fetch per origin per day is plenty and
# avoids an extra request on every single scrape run.
_CACHE_TTL_SECONDS = 24 * 60 * 60

# Per-process cache: (cached_at, parser_or_none). A missing/unreachable
# robots.txt is cached as None, meaning "no restrictions found".
_cache: dict[str, tuple[float, RobotFileParser | None]] = {}


async def is_allowed(url: str, user_agent: str | None = None) -> bool:
    """Check whether `url` may be fetched per the site's robots.txt.

    Fails open (returns True) if robots.txt is disabled, missing, or
    can't be fetched/parsed — a broken robots.txt should never block a
    scrape outright.
    """
    if not settings.respect_robots_txt:
        return True

    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    parser = await _get_parser(origin)
    if parser is None:
        return True

    return parser.can_fetch(user_agent or settings.scraper_user_agent, url)


async def _get_parser(origin: str) -> RobotFileParser | None:
    """Fetch and cache the robots.txt parser for an origin."""
    now = time.monotonic()
    cached = _cache.get(origin)
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    robots_url = f"{origin}/robots.txt"
    parser: RobotFileParser | None = None

    try:
        async with httpx.AsyncClient(
            timeout=5.0, follow_redirects=True
        ) as client:
            response = await client.get(robots_url)
        if response.status_code < 400:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
    except httpx.HTTPError:
        logger.warning("Failed to fetch %s, allowing by default", robots_url)
        parser = None

    _cache[origin] = (now, parser)
    return parser

import asyncio
from typing import Any

from celery.utils.log import get_task_logger

from api.core.config import settings
from worker.celery_app import app
from worker.engines.browser_pool import browser_pool
from worker.engines.parsers.pagination import collect_page_items
from worker.engines.playwright_engine import PlaywrightEngine
from worker.utils.proxy import get_proxy_for_domain
from worker.utils.throttle import extract_domain

logger = get_task_logger(__name__)

# Cap the preview payload — dry runs are for checking selectors work, not
# for pulling a full dataset.
DRY_RUN_ITEM_LIMIT = 20


@app.task(name="worker.tasks.dry_run_job")
def dry_run_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Test selectors against a live page without persisting anything."""
    return asyncio.get_event_loop().run_until_complete(_run_dry_run(payload))


async def _run_dry_run(payload: dict[str, Any]) -> dict[str, Any]:
    url = payload["url"]
    selectors = payload["selectors"]
    pagination_config = (payload.get("settings") or {}).get("pagination") or {}

    try:
        browser = await browser_pool.get_browser()
        proxy = get_proxy_for_domain(extract_domain(url))
        async with PlaywrightEngine(
            headless=True,
            user_agent=settings.scraper_user_agent,
            browser=browser,
            proxy=proxy,
        ) as engine:
            await engine.navigate(url)
            items = await collect_page_items(
                engine._page, selectors, pagination_config
            )

        return {
            "success": True,
            "items_count": len(items),
            "items": items[:DRY_RUN_ITEM_LIMIT],
            "truncated": len(items) > DRY_RUN_ITEM_LIMIT,
            "error": None,
        }
    except Exception as exc:
        logger.warning("Dry run failed for %s: %s", url, exc)
        return {
            "success": False,
            "items_count": 0,
            "items": [],
            "truncated": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

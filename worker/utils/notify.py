from typing import Any

import httpx
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


async def send_webhook_notification(webhook_url: str, payload: dict[str, Any]) -> None:
    """Best-effort webhook delivery.

    Failures are logged, never raised — a broken notification target
    shouldn't disrupt the scraping pipeline that triggered it.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError:
        logger.warning(
            "Webhook notification to %s failed", webhook_url, exc_info=True
        )

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from worker.utils.notify import send_webhook_notification


def _mock_http_client(raise_for_status_error: Exception | None = None):
    mock_response = MagicMock()
    if raise_for_status_error:
        mock_response.raise_for_status = MagicMock(side_effect=raise_for_status_error)
    else:
        mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestSendWebhookNotification:
    """Tests for best-effort webhook delivery."""

    @pytest.mark.asyncio
    async def test_posts_payload_to_webhook_url(self):
        mock_client = _mock_http_client()
        with patch(
            "worker.utils.notify.httpx.AsyncClient", return_value=mock_client
        ):
            await send_webhook_notification(
                "https://hooks.example.com/alert", {"event": "job.error"}
            )

        mock_client.post.assert_called_once_with(
            "https://hooks.example.com/alert", json={"event": "job.error"}
        )

    @pytest.mark.asyncio
    async def test_http_error_status_is_swallowed(self):
        mock_client = _mock_http_client(
            raise_for_status_error=httpx.HTTPStatusError(
                "500", request=MagicMock(), response=MagicMock()
            )
        )
        with patch(
            "worker.utils.notify.httpx.AsyncClient", return_value=mock_client
        ):
            # Should not raise.
            await send_webhook_notification(
                "https://hooks.example.com/alert", {"event": "job.error"}
            )

    @pytest.mark.asyncio
    async def test_connection_error_is_swallowed(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("boom"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "worker.utils.notify.httpx.AsyncClient", return_value=mock_client
        ):
            # Should not raise.
            await send_webhook_notification(
                "https://hooks.example.com/alert", {"event": "job.error"}
            )

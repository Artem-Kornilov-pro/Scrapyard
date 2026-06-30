from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from worker.utils import robots as robots_module
from worker.utils.robots import is_allowed


@pytest.fixture(autouse=True)
def clear_robots_cache():
    """Each test gets a clean per-origin cache."""
    robots_module._cache.clear()
    yield
    robots_module._cache.clear()


def _mock_http_client(status_code: int = 200, text: str = ""):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestIsAllowed:
    """Tests for the robots.txt allow/disallow decision."""

    @pytest.mark.asyncio
    async def test_disabled_setting_always_allows(self, monkeypatch):
        monkeypatch.setattr(robots_module.settings, "respect_robots_txt", False)
        assert await is_allowed("https://example.com/blocked") is True

    @pytest.mark.asyncio
    async def test_allows_when_no_disallow_rule(self, monkeypatch):
        monkeypatch.setattr(robots_module.settings, "respect_robots_txt", True)
        text = "User-agent: *\nAllow: /\n"
        mock_client = _mock_http_client(200, text)
        with patch(
            "worker.utils.robots.httpx.AsyncClient", return_value=mock_client
        ):
            assert await is_allowed("https://example.com/products") is True

    @pytest.mark.asyncio
    async def test_blocks_disallowed_path(self, monkeypatch):
        monkeypatch.setattr(robots_module.settings, "respect_robots_txt", True)
        text = "User-agent: *\nDisallow: /private\n"
        mock_client = _mock_http_client(200, text)
        with patch(
            "worker.utils.robots.httpx.AsyncClient", return_value=mock_client
        ):
            assert await is_allowed("https://example.com/private/data") is False

    @pytest.mark.asyncio
    async def test_missing_robots_txt_allows(self, monkeypatch):
        monkeypatch.setattr(robots_module.settings, "respect_robots_txt", True)
        mock_client = _mock_http_client(404, "")
        with patch(
            "worker.utils.robots.httpx.AsyncClient", return_value=mock_client
        ):
            assert await is_allowed("https://example.com/anything") is True

    @pytest.mark.asyncio
    async def test_fetch_error_allows(self, monkeypatch):
        monkeypatch.setattr(robots_module.settings, "respect_robots_txt", True)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("boom"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch(
            "worker.utils.robots.httpx.AsyncClient", return_value=mock_client
        ):
            assert await is_allowed("https://example.com/x") is True

    @pytest.mark.asyncio
    async def test_caches_parser_per_origin(self, monkeypatch):
        """A second lookup for the same origin doesn't refetch robots.txt."""
        monkeypatch.setattr(robots_module.settings, "respect_robots_txt", True)
        text = "User-agent: *\nDisallow: /private\n"
        mock_client = _mock_http_client(200, text)
        with patch(
            "worker.utils.robots.httpx.AsyncClient", return_value=mock_client
        ) as mock_cls:
            await is_allowed("https://example.com/a")
            await is_allowed("https://example.com/b")

        assert mock_cls.call_count == 1

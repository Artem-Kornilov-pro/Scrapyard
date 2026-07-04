from unittest.mock import AsyncMock, patch

import pytest

from worker.engines.browser_pool import BrowserPool


@pytest.fixture
def mock_playwright():
    """Mock Playwright and browser for BrowserPool."""
    with patch("worker.engines.browser_pool.async_playwright") as mock_pw:
        mock_browser = AsyncMock()
        mock_browser.is_connected = lambda: True

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch = AsyncMock(
            return_value=mock_browser
        )
        mock_pw.return_value.start = AsyncMock(
            return_value=mock_playwright_instance
        )

        yield mock_pw, mock_browser, mock_playwright_instance


class TestBrowserPool:
    """Tests for the process-wide shared browser pool."""

    @pytest.mark.asyncio
    async def test_launches_browser_on_first_call(self, mock_playwright):
        _, mock_browser, _ = mock_playwright
        pool = BrowserPool()

        browser = await pool.get_browser()

        assert browser is mock_browser

    @pytest.mark.asyncio
    async def test_reuses_browser_across_calls(self, mock_playwright):
        _, _, mock_playwright_instance = mock_playwright
        pool = BrowserPool()

        first = await pool.get_browser()
        second = await pool.get_browser()

        assert first is second
        mock_playwright_instance.chromium.launch.assert_called_once()

    @pytest.mark.asyncio
    async def test_relaunches_if_browser_disconnected(self, mock_playwright):
        _, mock_browser, mock_playwright_instance = mock_playwright
        pool = BrowserPool()

        await pool.get_browser()
        mock_browser.is_connected = lambda: False
        await pool.get_browser()

        assert mock_playwright_instance.chromium.launch.call_count == 2

    @pytest.mark.asyncio
    async def test_close_tears_down_browser_and_driver(self, mock_playwright):
        _, mock_browser, mock_playwright_instance = mock_playwright
        pool = BrowserPool()
        await pool.get_browser()

        await pool.close()

        mock_browser.close.assert_called_once()
        mock_playwright_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_is_a_noop_when_never_launched(self):
        pool = BrowserPool()
        await pool.close()  # should not raise

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.engines.playwright_engine import PlaywrightEngine


@pytest.fixture
def mock_playwright():
    """Mock Playwright and browser."""
    with patch("worker.engines.playwright_engine.async_playwright") as mock_pw:
        mock_response = MagicMock()
        mock_response.status = 200

        mock_page = MagicMock()
        mock_page.goto = AsyncMock(return_value=mock_response)

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.set_default_timeout = MagicMock()
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch = AsyncMock(
            return_value=mock_browser
        )
        mock_pw.return_value.__aenter__ = AsyncMock(
            return_value=mock_playwright_instance
        )
        mock_pw.return_value.__aexit__ = AsyncMock()
        mock_pw.return_value.start = AsyncMock(
            return_value=mock_playwright_instance
        )

        yield mock_pw


class TestPlaywrightEngine:
    """Tests for PlaywrightEngine."""

    @pytest.mark.asyncio
    async def test_launch(self, mock_playwright):
        """Test browser launch."""
        engine = PlaywrightEngine()
        await engine.launch()

        assert engine._browser is not None

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_playwright):
        """Test using engine as context manager."""
        async with PlaywrightEngine() as engine:
            assert engine._browser is not None

    @pytest.mark.asyncio
    async def test_new_page(self, mock_playwright):
        """Test creating a new page."""
        engine = PlaywrightEngine()
        await engine.launch()
        page = await engine.new_page()

        assert page is not None

    @pytest.mark.asyncio
    async def test_new_page_without_launch(self):
        """Test new_page before launch raises error."""
        engine = PlaywrightEngine()

        with pytest.raises(RuntimeError, match="not launched"):
            await engine.new_page()

    @pytest.mark.asyncio
    async def test_navigate(self, mock_playwright):
        """Test navigating to URL."""
        engine = PlaywrightEngine()
        await engine.launch()
        await engine.new_page()

        page = await engine.navigate("https://example.com")

        assert page is not None

    @pytest.mark.asyncio
    async def test_navigate_creates_page_if_none(self, mock_playwright):
        """Test navigate auto-creates page."""
        engine = PlaywrightEngine()
        await engine.launch()

        page = await engine.navigate("https://example.com")

        assert page is not None

    @pytest.mark.asyncio
    async def test_navigate_stores_response_status(self, mock_playwright):
        """Test navigate records the response for status inspection."""
        engine = PlaywrightEngine()
        await engine.launch()
        await engine.navigate("https://example.com")

        assert engine._last_response is not None
        assert engine._last_response.status == 200

    @pytest.mark.asyncio
    async def test_close(self, mock_playwright):
        """Test closing browser."""
        engine = PlaywrightEngine()
        await engine.launch()
        await engine.close()

        assert engine._browser is None
        assert engine._page is None
        assert engine._playwright is None

    @pytest.mark.asyncio
    async def test_default_values(self):
        """Test default values are set correctly."""
        engine = PlaywrightEngine()

        assert engine.headless is True
        assert engine.viewport == {"width": 1920, "height": 1080}
        assert engine.timeout == 30000

    @pytest.mark.asyncio
    async def test_custom_values(self):
        """Test custom values."""
        engine = PlaywrightEngine(
            headless=False,
            viewport={"width": 800, "height": 600},
            timeout=10000,
        )

        assert engine.headless is False
        assert engine.viewport == {"width": 800, "height": 600}
        assert engine.timeout == 10000


class TestPlaywrightEngineWithSharedBrowser:
    """Regression: an externally-provided browser (pool mode) must not
    be closed by the engine, only the per-task context it created.
    """

    @pytest.mark.asyncio
    async def test_launch_is_noop_with_external_browser(self):
        external_browser = AsyncMock()
        engine = PlaywrightEngine(browser=external_browser)

        await engine.launch()

        assert engine._browser is external_browser
        assert engine._playwright is None

    @pytest.mark.asyncio
    async def test_close_does_not_close_external_browser(self):
        external_browser = AsyncMock()
        mock_context = AsyncMock()
        external_browser.new_context = AsyncMock(return_value=mock_context)

        engine = PlaywrightEngine(browser=external_browser)
        await engine.launch()
        await engine.new_page()
        await engine.close()

        mock_context.close.assert_called_once()
        external_browser.close.assert_not_called()
        assert engine._browser is external_browser

    @pytest.mark.asyncio
    async def test_new_page_passes_proxy_to_context(self):
        external_browser = AsyncMock()
        mock_context = AsyncMock()
        external_browser.new_context = AsyncMock(return_value=mock_context)
        proxy = {"server": "http://proxy.example.com:8080"}

        engine = PlaywrightEngine(browser=external_browser, proxy=proxy)
        await engine.launch()
        await engine.new_page()

        external_browser.new_context.assert_called_once()
        assert external_browser.new_context.call_args.kwargs["proxy"] == proxy

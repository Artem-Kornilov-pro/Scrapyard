from typing import Any, Optional

from playwright.async_api import Browser, Page, Playwright, Response, async_playwright


class PlaywrightEngine:
    """Async browser engine for web scraping using Playwright.

    Can either own its browser (default: launches and closes one per
    instance) or borrow one from a `BrowserPool` (pass `browser=`), in
    which case only a per-task `BrowserContext` is created and torn
    down, leaving the shared browser process running. A context gives
    full isolation (cookies, storage, cache) even when the underlying
    browser is shared, so pooling is safe across unrelated domains.
    """

    def __init__(
        self,
        headless: bool = True,
        viewport: dict[str, int] | None = None,
        timeout: int = 30000,
        user_agent: str | None = None,
        browser: Browser | None = None,
        proxy: dict[str, Any] | None = None,
    ):
        self.headless = headless
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.timeout = timeout
        self.user_agent = user_agent
        self.proxy = proxy
        self._owns_browser = browser is None
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = browser
        self._context = None
        self._page: Optional[Page] = None
        self._last_response: Optional[Response] = None

    async def __aenter__(self) -> "PlaywrightEngine":
        """Async context manager entry."""
        await self.launch()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await self.close()

    async def launch(self) -> None:
        """Launch a browser instance, unless one was already provided."""
        if self._browser is not None:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
        )

    async def new_page(self) -> Page:
        """Create a new page in a fresh, isolated browser context."""
        if not self._browser:
            raise RuntimeError("Browser not launched. Call launch() first.")
        self._context = await self._browser.new_context(
            viewport=self.viewport,
            user_agent=self.user_agent,
            proxy=self.proxy,
        )
        self._context.set_default_timeout(self.timeout)
        self._page = await self._context.new_page()
        return self._page

    async def navigate(
        self, url: str, wait_until: str = "networkidle"
    ) -> Page:
        """Navigate to URL and wait for page to load.

        Stores the navigation response on `self._last_response` so
        callers can inspect the HTTP status (e.g. to detect 403/429
        blocks) without changing this method's return type.
        """
        if not self._page:
            await self.new_page()
        self._last_response = await self._page.goto(url, wait_until=wait_until)
        return self._page

    async def close(self) -> None:
        """Close the page/context, and the browser if this engine owns it."""
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None
        if self._owns_browser:
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

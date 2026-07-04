import asyncio

from playwright.async_api import Browser, Playwright, async_playwright


class BrowserPool:
    """Keeps one Chromium instance alive per worker process instead of
    launching a fresh browser (~1-2s startup) for every task.

    Each task still gets an isolated `BrowserContext` via
    `PlaywrightEngine(browser=...)` -- only the underlying browser
    process is shared. If the shared browser dies (page crash, OOM),
    the next `get_browser()` call transparently relaunches it.
    """

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def get_browser(self) -> Browser:
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True
                )
            return self._browser

    async def close(self) -> None:
        async with self._lock:
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None


browser_pool = BrowserPool()

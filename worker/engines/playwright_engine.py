from typing import Optional

from playwright.async_api import Browser, Page, Playwright, async_playwright


class PlaywrightEngine:
    """Async browser engine for web scraping using Playwright."""

    def __init__(
        self,
        headless: bool = True,
        viewport: dict[str, int] | None = None,
        timeout: int = 30000,
        user_agent: str | None = None,
    ):
        self.headless = headless
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.timeout = timeout
        self.user_agent = user_agent
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    async def __aenter__(self) -> "PlaywrightEngine":
        """Async context manager entry."""
        await self.launch()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await self.close()

    async def launch(self) -> None:
        """Launch browser instance."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
        )

    async def new_page(self) -> Page:
        """Create a new page."""
        if not self._browser:
            raise RuntimeError("Browser not launched. Call launch() first.")
        self._page = await self._browser.new_page(
            viewport=self.viewport,
            user_agent=self.user_agent,
        )
        if self._page:
            self._page.set_default_timeout(self.timeout)
        return self._page

    async def navigate(
        self, url: str, wait_until: str = "networkidle"
    ) -> Page:
        """Navigate to URL and wait for page to load."""
        if not self._page:
            await self.new_page()
        await self._page.goto(url, wait_until=wait_until)
        return self._page

    async def close(self) -> None:
        """Close browser and clean up."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

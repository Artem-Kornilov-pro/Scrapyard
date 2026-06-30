from typing import Any

from playwright.async_api import Page

from worker.engines.parsers.generic import parse_with_selectors


async def handle_pagination(
    page: Page,
    pagination_config: dict[str, Any],
    selectors: dict[str, Any] | None = None,
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    """Handle pagination and collect items from multiple pages.

    Args:
        page: Playwright Page object.
        pagination_config: Config with type and optional param/selector.
        selectors: CSS selectors config used to parse each visited page.
            If omitted, pages are navigated/clicked/scrolled but not parsed.
        max_pages: Maximum number of pages to scrape.

    Returns:
        List of collected elements from all visited pages.
    """
    pagination_type = pagination_config.get("type")

    if pagination_type == "url":
        return await _handle_url_pagination(
            page, pagination_config, selectors, max_pages
        )
    elif pagination_type == "click":
        return await _handle_click_pagination(
            page, pagination_config, selectors, max_pages
        )
    elif pagination_type == "scroll":
        return await _handle_scroll_pagination(
            page, pagination_config, selectors, max_pages
        )

    # No pagination
    return []


async def _handle_url_pagination(
    page: Page,
    config: dict[str, Any],
    selectors: dict[str, Any] | None = None,
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    """Handle URL-based pagination (?page=1, ?page=2, ...)."""
    param = config.get("param", "page")
    start_page = config.get("start_page", 1)

    all_elements: list[dict[str, Any]] = []
    current_url = page.url

    for page_num in range(start_page, start_page + max_pages):
        if "?" in current_url:
            separator = "&"
        else:
            separator = "?"

        page_url = f"{current_url}{separator}{param}={page_num}"
        await page.goto(page_url, wait_until="networkidle")

        if selectors:
            all_elements.extend(await parse_with_selectors(page, selectors))

    return all_elements


async def _handle_click_pagination(
    page: Page,
    config: dict[str, Any],
    selectors: dict[str, Any] | None = None,
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    """Handle click-based pagination (Next button)."""
    next_selector = config.get("next_selector", "a.next")
    all_elements: list[dict[str, Any]] = []

    for _ in range(max_pages):
        try:
            next_button = await page.query_selector(next_selector)
            if not next_button:
                break

            is_disabled = await next_button.get_attribute("disabled")
            if is_disabled:
                break

            await next_button.click()
            await page.wait_for_load_state("networkidle")

            if selectors:
                all_elements.extend(
                    await parse_with_selectors(page, selectors)
                )

        except Exception:
            break

    return all_elements


async def _handle_scroll_pagination(
    page: Page,
    config: dict[str, Any],
    selectors: dict[str, Any] | None = None,
    max_pages: int = 10,
) -> list[dict[str, Any]]:
    """Handle infinite scroll pagination.

    New items are appended to the same DOM rather than replacing it, so
    the page is parsed once after scrolling settles instead of per step.
    """
    for _ in range(max_pages):
        previous_height = await page.evaluate(
            "document.body.scrollHeight"
        )
        await page.evaluate(
            "window.scrollTo(0, document.body.scrollHeight)"
        )
        await page.wait_for_timeout(1000)

        new_height = await page.evaluate(
            "document.body.scrollHeight"
        )
        if new_height == previous_height:
            break

    if selectors:
        return await parse_with_selectors(page, selectors)
    return []

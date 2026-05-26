from unittest.mock import AsyncMock, MagicMock

import pytest

from worker.engines.parsers.pagination import (
    _handle_click_pagination,
    _handle_scroll_pagination,
    _handle_url_pagination,
    handle_pagination,
)


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page."""
    page = MagicMock()
    page.url = "https://example.com/products"
    page.goto = AsyncMock()
    page.query_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.evaluate = AsyncMock()
    return page


class TestHandlePagination:
    """Tests for pagination dispatcher."""

    @pytest.mark.asyncio
    async def test_no_pagination(self, mock_page):
        """Test that None type returns empty list."""
        result = await handle_pagination(
            mock_page, {"type": None}, max_pages=5
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_url_pagination(self, mock_page):
        """Test URL pagination type is dispatched correctly."""
        result = await handle_pagination(
            mock_page, {"type": "url", "param": "page"}, max_pages=3
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_click_pagination(self, mock_page):
        """Test click pagination type is dispatched correctly."""
        result = await handle_pagination(
            mock_page,
            {"type": "click", "next_selector": ".next"},
            max_pages=2,
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_scroll_pagination(self, mock_page):
        """Test scroll pagination type is dispatched correctly."""
        result = await handle_pagination(
            mock_page, {"type": "scroll"}, max_pages=3
        )
        assert isinstance(result, list)


class TestUrlPagination:
    """Tests for URL-based pagination."""

    @pytest.mark.asyncio
    async def test_navigates_pages(self, mock_page):
        """Test that pages are navigated."""
        mock_page.url = "https://example.com/products"

        await _handle_url_pagination(
            mock_page, {"param": "page", "start_page": 1}, max_pages=3
        )

        assert mock_page.goto.call_count == 3

    @pytest.mark.asyncio
    async def test_custom_start_page(self, mock_page):
        """Test custom start page."""
        mock_page.url = "https://example.com/products"

        await _handle_url_pagination(
            mock_page, {"param": "page", "start_page": 5}, max_pages=2
        )

        first_call = mock_page.goto.call_args_list[0][0][0]
        assert "page=5" in first_call


class TestClickPagination:
    """Tests for click-based pagination."""

    @pytest.mark.asyncio
    async def test_clicks_next_button(self, mock_page):
        """Test that next button is clicked."""
        mock_button = MagicMock()
        mock_button.click = AsyncMock()
        mock_button.get_attribute = AsyncMock(return_value=None)
        mock_page.query_selector.return_value = mock_button

        await _handle_click_pagination(
            mock_page,
            {"next_selector": ".next"},
            max_pages=3,
        )

        assert mock_button.click.call_count == 3

    @pytest.mark.asyncio
    async def test_stops_when_no_button(self, mock_page):
        """Test stops when next button not found."""
        mock_page.query_selector.return_value = None

        await _handle_click_pagination(
            mock_page, {"next_selector": ".next"}, max_pages=3
        )

        assert mock_page.query_selector.call_count == 1

    @pytest.mark.asyncio
    async def test_stops_when_disabled(self, mock_page):
        """Test stops when next button is disabled."""
        mock_button = MagicMock()
        mock_button.get_attribute = AsyncMock(return_value="disabled")
        mock_page.query_selector.return_value = mock_button

        await _handle_click_pagination(
            mock_page, {"next_selector": ".next"}, max_pages=3
        )

        # Should not click
        mock_button.click.assert_not_called()


class TestScrollPagination:
    """Tests for infinite scroll pagination."""

    @pytest.mark.asyncio
    async def test_scrolls_pages(self, mock_page):
        """Test that page scrolls multiple times."""
        # 3 вызова за итерацию: previous_height, scrollTo, new_height
        # Для 3 итераций: 9 значений
        # Итерация 1: 1000 → scroll → 2000 (изменилась)
        # Итерация 2: 2000 → scroll → 3000 (изменилась)
        # Итерация 3: 3000 → scroll → 3000 (не изменилась → стоп)
        heights = iter([1000, None, 2000, 2000, None, 3000, 3000, None, 3000])
        mock_page.evaluate = AsyncMock(
            side_effect=lambda *args, **kwargs: next(heights)
        )

        await _handle_scroll_pagination(mock_page, {}, max_pages=10)

        # 3 итерации × 3 вызова = 9
        assert mock_page.evaluate.call_count == 9

    @pytest.mark.asyncio
    async def test_stops_when_no_new_content(self, mock_page):
        """Test stops scrolling when height unchanged."""
        # Первая итерация: 1000 → scroll → 1000 (не изменилась → стоп)
        heights = iter([1000, None, 1000])
        mock_page.evaluate = AsyncMock(
            side_effect=lambda *args, **kwargs: next(heights)
        )

        await _handle_scroll_pagination(mock_page, {}, max_pages=10)

        # 1 итерация × 3 вызова = 3
        assert mock_page.evaluate.call_count == 3

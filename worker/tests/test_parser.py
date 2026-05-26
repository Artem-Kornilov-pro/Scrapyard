import pytest
from unittest.mock import AsyncMock, MagicMock

from worker.engines.parsers.generic import parse_with_selectors, TRANSFORMS


VALID_SELECTORS = {
    "items": "div.product",
    "fields": {
        "title": {"selector": "h3", "attr": "text", "type": "string"},
        "price": {
            "selector": "span.price",
            "attr": "text",
            "type": "string",
            "transform": "strip_currency",
        },
        "url": {"selector": "a", "attr": "href", "type": "url"},
    },
}


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page."""
    page = MagicMock()
    page.query_selector_all = AsyncMock()
    return page


@pytest.fixture
def mock_element():
    """Create a mock DOM element."""
    el = MagicMock()
    el.inner_text = AsyncMock()
    el.get_attribute = AsyncMock()
    return el


class TestTransforms:
    """Tests for built-in transform functions."""

    def test_strip_currency(self):
        assert TRANSFORMS["strip_currency"]("$10.99 USD") == 10.99
        assert TRANSFORMS["strip_currency"]("1,234") == 1234.0

    def test_strip_whitespace(self):
        assert TRANSFORMS["strip_whitespace"]("  hello  ") == "hello"

    def test_parse_int(self):
        assert TRANSFORMS["parse_int"]("1,234") == 1234

    def test_parse_float(self):
        assert TRANSFORMS["parse_float"]("1,234.5") == 1234.5

    def test_has_class_in_stock(self):
        assert TRANSFORMS["has_class_in-stock"]("in-stock available") is True
        assert TRANSFORMS["has_class_in-stock"]("out-of-stock") is False

    def test_lowercase(self):
        assert TRANSFORMS["lowercase"]("HELLO") == "hello"

    def test_uppercase(self):
        assert TRANSFORMS["uppercase"]("hello") == "HELLO"


class TestParseWithSelectors:
    """Tests for parse_with_selectors function."""

    @pytest.mark.asyncio
    async def test_parse_single_item(self, mock_page, mock_element):
        """Test parsing a single item."""
        mock_element.inner_text = AsyncMock(return_value="Test Product")
        mock_element.get_attribute = AsyncMock(return_value="/product/1")
        mock_page.query_selector_all.return_value = [mock_element]

        results = await parse_with_selectors(mock_page, {
            "items": "div.product",
            "fields": {
                "title": {"selector": "h3", "attr": "text", "type": "string"},
            },
        })

        assert len(results) == 1
        assert results[0]["title"] == "Test Product"

    @pytest.mark.asyncio
    async def test_parse_multiple_items(self, mock_page, mock_element):
        """Test parsing multiple items."""
        el1 = MagicMock()
        el1.inner_text = AsyncMock(return_value="Item 1")
        el2 = MagicMock()
        el2.inner_text = AsyncMock(return_value="Item 2")

        mock_page.query_selector_all.return_value = [el1, el2]

        results = await parse_with_selectors(mock_page, {
            "items": "div.product",
            "fields": {
                "title": {"selector": "h3", "attr": "text", "type": "string"},
            },
        })

        assert len(results) == 2
        assert results[0]["title"] == "Item 1"
        assert results[1]["title"] == "Item 2"

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_page):
        """Test parsing page with no matching elements."""
        mock_page.query_selector_all.return_value = []

        results = await parse_with_selectors(mock_page, VALID_SELECTORS)

        assert results == []

    @pytest.mark.asyncio
    async def test_parse_with_transform(self, mock_page, mock_element):
        """Test parsing with transform function."""
        mock_element.inner_text = AsyncMock(return_value="$19.99 USD")
        mock_element.get_attribute = AsyncMock(return_value="/product/1")
        mock_page.query_selector_all.return_value = [mock_element]

        results = await parse_with_selectors(mock_page, {
            "items": "div.product",
            "fields": {
                "price": {
                    "selector": "span",
                    "attr": "text",
                    "type": "string",
                    "transform": "strip_currency",
                },
            },
        })

        assert results[0]["price"] == 19.99

    @pytest.mark.asyncio
    async def test_parse_with_class_attr(self, mock_page, mock_element):
        """Test parsing class attribute."""
        mock_element.get_attribute = AsyncMock(return_value="product in-stock")
        mock_page.query_selector_all.return_value = [mock_element]

        results = await parse_with_selectors(mock_page, {
            "items": "div.product",
            "fields": {
                "status": {
                    "selector": "span",
                    "attr": "class",
                    "type": "string",
                    "transform": "has_class_in-stock",
                },
            },
        })

        assert results[0]["status"] is True

    @pytest.mark.asyncio
    async def test_parse_missing_attribute(self, mock_page, mock_element):
        """Test parsing when attribute returns None."""
        mock_element.get_attribute = AsyncMock(return_value=None)
        mock_page.query_selector_all.return_value = [mock_element]

        results = await parse_with_selectors(mock_page, {
            "items": "div.product",
            "fields": {
                "url": {
                    "selector": "a",
                    "attr": "href",
                    "type": "url",
                },
            },
        })

        assert results[0]["url"] == ""

    @pytest.mark.asyncio
    async def test_transform_error_returns_none(self, mock_page, mock_element):
        """Test that transform error sets value to None."""
        mock_element.inner_text = AsyncMock(return_value="not-a-number")
        mock_page.query_selector_all.return_value = [mock_element]

        results = await parse_with_selectors(mock_page, {
            "items": "div.product",
            "fields": {
                "price": {
                    "selector": "span",
                    "attr": "text",
                    "type": "string",
                    "transform": "parse_int",
                },
            },
        })

        assert results[0]["price"] is None
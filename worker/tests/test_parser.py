from unittest.mock import AsyncMock, MagicMock

import pytest

from worker.engines.parsers.generic import TRANSFORMS, parse_with_selectors

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


def _mock_field_target(inner_text=None, attribute=None):
    """Create a mock sub-element returned by element.query_selector()."""
    target = MagicMock()
    target.inner_text = AsyncMock(return_value=inner_text)
    target.get_attribute = AsyncMock(return_value=attribute)
    return target


def _mock_item_element(field_targets: dict[str, MagicMock]):
    """Create a mock item element whose query_selector(selector) returns
    the matching sub-element from `field_targets` (keyed by selector).
    """
    element = MagicMock()
    element.query_selector = AsyncMock(
        side_effect=lambda selector: field_targets.get(selector)
    )
    return element


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
    async def test_parse_single_item(self, mock_page):
        """Test parsing a single item."""
        element = _mock_item_element({
            "h3": _mock_field_target(inner_text="Test Product"),
        })
        mock_page.query_selector_all.return_value = [element]

        results = await parse_with_selectors(mock_page, {
            "items": "div.product",
            "fields": {
                "title": {"selector": "h3", "attr": "text", "type": "string"},
            },
        })

        assert len(results) == 1
        assert results[0]["title"] == "Test Product"

    @pytest.mark.asyncio
    async def test_queries_field_selector_within_item_not_globally(
        self, mock_page
    ):
        """Regression: fields must be looked up via the item element's
        own query_selector(selector), not by passing the selector as an
        argument to inner_text()/get_attribute() (which Playwright's
        ElementHandle API doesn't accept).
        """
        target = _mock_field_target(inner_text="Test Product")
        element = _mock_item_element({"h3": target})
        mock_page.query_selector_all.return_value = [element]

        await parse_with_selectors(mock_page, {
            "items": "div.product",
            "fields": {
                "title": {"selector": "h3", "attr": "text"},
            },
        })

        element.query_selector.assert_called_once_with("h3")
        target.inner_text.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_parse_multiple_items(self, mock_page):
        """Test parsing multiple items."""
        el1 = _mock_item_element({
            "h3": _mock_field_target(inner_text="Item 1"),
        })
        el2 = _mock_item_element({
            "h3": _mock_field_target(inner_text="Item 2"),
        })

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
    async def test_parse_with_transform(self, mock_page):
        """Test parsing with transform function."""
        element = _mock_item_element({
            "span": _mock_field_target(inner_text="$19.99 USD"),
        })
        mock_page.query_selector_all.return_value = [element]

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
    async def test_parse_with_class_attr(self, mock_page):
        """Test parsing class attribute."""
        element = _mock_item_element({
            "span": _mock_field_target(attribute="product in-stock"),
        })
        mock_page.query_selector_all.return_value = [element]

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
    async def test_parse_missing_attribute(self, mock_page):
        """Test parsing when attribute returns None."""
        element = _mock_item_element({
            "a": _mock_field_target(attribute=None),
        })
        mock_page.query_selector_all.return_value = [element]

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
    async def test_parse_missing_sub_element(self, mock_page):
        """Test that a field selector matching nothing within the item
        yields an empty string instead of raising.
        """
        element = _mock_item_element({})  # no selectors resolve
        mock_page.query_selector_all.return_value = [element]

        results = await parse_with_selectors(mock_page, {
            "items": "div.product",
            "fields": {
                "title": {"selector": "h3", "attr": "text"},
            },
        })

        assert results[0]["title"] == ""

    @pytest.mark.asyncio
    async def test_transform_error_returns_none(self, mock_page):
        """Test that transform error sets value to None."""
        element = _mock_item_element({
            "span": _mock_field_target(inner_text="not-a-number"),
        })
        mock_page.query_selector_all.return_value = [element]

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

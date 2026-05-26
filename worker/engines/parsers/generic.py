from typing import Any

from playwright.async_api import Page


TRANSFORMS: dict[str, Any] = {
    "strip_currency": lambda v: float(
        str(v).replace("$", "").replace(" USD", "").replace(",", "").strip()
    ),
    "strip_whitespace": lambda v: str(v).strip(),
    "parse_int": lambda v: int(str(v).replace(",", "").strip()),
    "parse_float": lambda v: float(str(v).replace(",", "").strip()),
    "has_class_in-stock": lambda v: "in-stock" in str(v),
    "lowercase": lambda v: str(v).lower(),
    "uppercase": lambda v: str(v).upper(),
}


async def parse_with_selectors(
    page: Page,
    selectors: dict[str, Any],
) -> list[dict[str, Any]]:
    """Parse page content using CSS selectors configuration.

    Args:
        page: Playwright Page object.
        selectors: Configuration dict with 'items' and 'fields'.

    Returns:
        List of parsed items as dicts.
    """
    items_selector = selectors["items"]
    fields_config = selectors["fields"]

    elements = await page.query_selector_all(items_selector)
    results: list[dict[str, Any]] = []

    for element in elements:
        item: dict[str, Any] = {}
        for field_name, field_config in fields_config.items():
            selector = field_config["selector"]
            attr = field_config.get("attr", "text")

            if attr == "text":
                value = await element.inner_text(selector)
            elif attr == "class":
                value = await element.get_attribute(selector, "class")
            else:
                value = await element.get_attribute(selector, attr)

            if value is None:
                value = ""

            transform_name = field_config.get("transform")
            if transform_name and transform_name in TRANSFORMS:
                try:
                    value = TRANSFORMS[transform_name](value)
                except (ValueError, TypeError):
                    value = None

            item[field_name] = value

        results.append(item)

    return results
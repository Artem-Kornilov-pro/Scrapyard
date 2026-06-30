"""Shared field-validation logic reused across job and dry-run models."""


def validate_url_format(value: str) -> str:
    """Require an absolute http(s) URL."""
    if not value.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return value


def validate_selectors_structure(value: dict) -> dict:
    """Require the {items, fields} shape the parser expects."""
    if "items" not in value:
        raise ValueError("selectors must contain 'items' key")
    if "fields" not in value:
        raise ValueError("selectors must contain 'fields' key")
    if not isinstance(value["fields"], dict) or len(value["fields"]) == 0:
        raise ValueError("selectors.fields must be a non-empty dict")
    return value

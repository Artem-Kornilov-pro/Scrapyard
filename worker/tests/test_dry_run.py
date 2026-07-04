from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.tasks.dry_run import DRY_RUN_ITEM_LIMIT, _run_dry_run, dry_run_job

VALID_PAYLOAD = {
    "url": "https://example.com/products",
    "selectors": {
        "items": "div.product",
        "fields": {"title": {"selector": "h3", "attr": "text"}},
    },
}


@pytest.fixture
def mock_engine():
    """Mock PlaywrightEngine."""
    with patch("worker.tasks.dry_run.PlaywrightEngine") as mock_cls:
        mock_instance = MagicMock()
        mock_instance._page = MagicMock()
        mock_instance.navigate = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_cls


@pytest.fixture
def mock_collect():
    """Mock collect_page_items."""
    with patch("worker.tasks.dry_run.collect_page_items") as mock:
        mock.return_value = [{"title": "Product 1"}, {"title": "Product 2"}]
        yield mock


@pytest.fixture(autouse=True)
def mock_pool_and_proxy():
    """Default every test to "no proxy, pooled browser" instead of
    actually starting a Playwright driver process.
    """
    with patch(
        "worker.tasks.dry_run.browser_pool.get_browser",
        new=AsyncMock(return_value=MagicMock()),
    ), patch(
        "worker.tasks.dry_run.get_proxy_for_domain", return_value=None
    ) as mock_proxy:
        yield mock_proxy


class TestRunDryRun:
    """Tests for the dry-run preview logic."""

    @pytest.mark.asyncio
    async def test_success_returns_items(self, mock_engine, mock_collect):
        result = await _run_dry_run(VALID_PAYLOAD)

        assert result["success"] is True
        assert result["items_count"] == 2
        assert result["items"] == [
            {"title": "Product 1"}, {"title": "Product 2"},
        ]
        assert result["truncated"] is False
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_truncates_items_beyond_limit(self, mock_engine, mock_collect):
        mock_collect.return_value = [
            {"title": f"Item {i}"} for i in range(DRY_RUN_ITEM_LIMIT + 5)
        ]

        result = await _run_dry_run(VALID_PAYLOAD)

        assert result["items_count"] == DRY_RUN_ITEM_LIMIT + 5
        assert len(result["items"]) == DRY_RUN_ITEM_LIMIT
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_failure_returns_error_instead_of_raising(self, mock_engine):
        with patch(
            "worker.tasks.dry_run.collect_page_items",
            new=AsyncMock(side_effect=RuntimeError("selector blew up")),
        ):
            result = await _run_dry_run(VALID_PAYLOAD)

        assert result["success"] is False
        assert result["items_count"] == 0
        assert result["items"] == []
        assert "selector blew up" in result["error"]

    @pytest.mark.asyncio
    async def test_passes_pagination_settings_through(
        self, mock_engine, mock_collect
    ):
        payload = {
            **VALID_PAYLOAD,
            "settings": {"pagination": {"type": "url", "max_pages": 3}},
        }
        await _run_dry_run(payload)

        call_args = mock_collect.call_args[0]
        assert call_args[2] == {"type": "url", "max_pages": 3}


class TestDryRunJobBridging:
    """Regression: the Celery task must drive the coroutine, not just
    return it — same bridging pattern as scrape_job.
    """

    def test_drives_coroutine_to_completion(self, mock_engine, mock_collect):
        result = dry_run_job(VALID_PAYLOAD)

        assert result["success"] is True
        assert result["items_count"] == 2

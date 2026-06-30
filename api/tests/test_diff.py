"""Tests for AnalyticsService.get_diff and its helper functions."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.analytics_service import (
    AnalyticsService,
    _diff_items_by_content,
    _diff_items_by_key,
)


def _make_mock_cursor(return_value):
    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.to_list = AsyncMock(return_value=return_value)
    return mock_cursor


class TestDiffItemsByKey:
    """Tests for the per-field diff when a diff_key is configured."""

    def test_detects_added_and_removed(self):
        older = [{"title": "A", "price": 10}]
        newer = [{"title": "A", "price": 10}, {"title": "B", "price": 5}]

        result = _diff_items_by_key(older, newer, "title")

        assert result["added"] == [{"title": "B", "price": 5}]
        assert result["removed"] == []
        assert result["changed"] == []

    def test_detects_field_change(self):
        older = [{"title": "A", "price": 10}]
        newer = [{"title": "A", "price": 8}]

        result = _diff_items_by_key(older, newer, "title")

        assert result["added"] == []
        assert result["removed"] == []
        assert result["changed"] == [
            {"key": "A", "changes": {"price": {"old": 10, "new": 8}}}
        ]

    def test_items_missing_key_are_ignored(self):
        older = [{"price": 10}]
        newer = [{"price": 8}]

        result = _diff_items_by_key(older, newer, "title")

        assert result == {"added": [], "removed": [], "changed": []}

    def test_unchanged_items_produce_no_diff(self):
        items = [{"title": "A", "price": 10}]
        result = _diff_items_by_key(items, items, "title")
        assert result == {"added": [], "removed": [], "changed": []}


class TestDiffItemsByContent:
    """Tests for whole-item diffing when no diff_key is configured."""

    def test_identical_items_produce_no_diff(self):
        items = [{"title": "A", "price": 10}]
        result = _diff_items_by_content(items, items)
        assert result == {"added": [], "removed": [], "changed": []}

    def test_field_change_shows_as_remove_and_add(self):
        older = [{"title": "A", "price": 10}]
        newer = [{"title": "A", "price": 8}]

        result = _diff_items_by_content(older, newer)

        assert result["removed"] == [{"title": "A", "price": 10}]
        assert result["added"] == [{"title": "A", "price": 8}]
        assert result["changed"] == []


class TestGetDiff:
    """Tests for the get_diff service method."""

    @pytest.mark.asyncio
    async def test_returns_none_with_fewer_than_two_runs(self):
        with patch("api.services.analytics_service.db") as mock_db:
            mock_db.scraped_results.find.return_value = _make_mock_cursor([
                {"run_id": "r1", "items": [], "timestamp": datetime.now(UTC)}
            ])
            result = await AnalyticsService.get_diff("job-1")

        assert result is None

    @pytest.mark.asyncio
    async def test_compares_two_most_recent_runs_by_default(self):
        now = datetime.now(UTC)
        newer_doc = {
            "run_id": "r2", "timestamp": now,
            "items": [{"title": "B"}],
        }
        older_doc = {
            "run_id": "r1", "timestamp": now,
            "items": [{"title": "A"}],
        }

        with patch("api.services.analytics_service.db") as mock_db:
            mock_db.scraped_results.find.return_value = _make_mock_cursor(
                [newer_doc, older_doc]
            )
            mock_db.scraping_jobs.find_one = AsyncMock(return_value={
                "job_id": "job-1", "diff_key": None,
            })
            result = await AnalyticsService.get_diff("job-1")

        assert result is not None
        assert result["run_a"]["run_id"] == "r1"
        assert result["run_b"]["run_id"] == "r2"
        assert result["added"] == [{"title": "B"}]
        assert result["removed"] == [{"title": "A"}]

    @pytest.mark.asyncio
    async def test_uses_job_diff_key_when_configured(self):
        now = datetime.now(UTC)
        newer_doc = {
            "run_id": "r2", "timestamp": now,
            "items": [{"title": "Widget", "price": 8}],
        }
        older_doc = {
            "run_id": "r1", "timestamp": now,
            "items": [{"title": "Widget", "price": 10}],
        }

        with patch("api.services.analytics_service.db") as mock_db:
            mock_db.scraped_results.find.return_value = _make_mock_cursor(
                [newer_doc, older_doc]
            )
            mock_db.scraping_jobs.find_one = AsyncMock(return_value={
                "job_id": "job-1", "diff_key": "title",
            })
            result = await AnalyticsService.get_diff("job-1")

        assert result["diff_key"] == "title"
        assert result["changed"] == [
            {"key": "Widget", "changes": {"price": {"old": 10, "new": 8}}}
        ]

    @pytest.mark.asyncio
    async def test_explicit_run_ids_not_found_returns_none(self):
        with patch("api.services.analytics_service.db") as mock_db:
            mock_db.scraped_results.find_one = AsyncMock(return_value=None)
            result = await AnalyticsService.get_diff("job-1", "r1", "r2")

        assert result is None

    @pytest.mark.asyncio
    async def test_only_one_explicit_run_id_returns_none(self):
        with patch("api.services.analytics_service.db"):
            result = await AnalyticsService.get_diff("job-1", run_a="r1")

        assert result is None

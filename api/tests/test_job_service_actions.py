"""Tests for JobService.run_now and JobService.dry_run."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import TimeoutError as CeleryTimeoutError

from api.models.job import DryRunRequest
from api.services.job_service import JobService

VALID_SELECTORS = {
    "items": "div.product",
    "fields": {"title": {"selector": "h3", "attr": "text"}},
}


class TestRunNow:
    """Tests for dispatching a job immediately, bypassing its schedule."""

    @pytest.mark.asyncio
    async def test_returns_none_when_job_missing(self):
        with patch("api.services.job_service.db") as mock_db:
            mock_db.scraping_jobs.find_one = AsyncMock(return_value=None)
            result = await JobService.run_now("missing-job")

        assert result is None

    @pytest.mark.asyncio
    async def test_dispatches_job_doc_to_scrape_job(self):
        job_doc = {
            "job_id": "job-1",
            "url": "https://example.com",
            "selectors": VALID_SELECTORS,
        }
        mock_async_result = MagicMock(id="task-abc")
        mock_scrape_job = MagicMock()
        mock_scrape_job.delay = MagicMock(return_value=mock_async_result)

        with patch("api.services.job_service.db") as mock_db, patch(
            "worker.tasks.scraper.scrape_job", mock_scrape_job
        ):
            mock_db.scraping_jobs.find_one = AsyncMock(return_value=job_doc)
            result = await JobService.run_now("job-1")

        mock_scrape_job.delay.assert_called_once_with(job_doc)
        assert result == {
            "job_id": "job-1",
            "task_id": "task-abc",
            "status": "dispatched",
        }

    @pytest.mark.asyncio
    async def test_queries_without_object_id_field(self):
        """find_one must project out _id, which isn't JSON-serializable
        for Celery's task payload."""
        mock_scrape_job = MagicMock()
        mock_scrape_job.delay = MagicMock(return_value=MagicMock(id="t"))

        with patch("api.services.job_service.db") as mock_db, patch(
            "worker.tasks.scraper.scrape_job", mock_scrape_job
        ):
            mock_db.scraping_jobs.find_one = AsyncMock(return_value={
                "job_id": "job-1", "url": "https://example.com",
                "selectors": VALID_SELECTORS,
            })
            await JobService.run_now("job-1")

        call_args = mock_db.scraping_jobs.find_one.call_args[0]
        assert call_args[1] == {"_id": 0}


class TestDryRun:
    """Tests for previewing selectors without saving a job."""

    @pytest.mark.asyncio
    async def test_returns_worker_result(self):
        payload = DryRunRequest(
            url="https://example.com", selectors=VALID_SELECTORS
        )
        worker_result = {
            "success": True,
            "items_count": 1,
            "items": [{"title": "A"}],
            "truncated": False,
            "error": None,
        }
        mock_async_result = MagicMock()
        mock_async_result.get = MagicMock(return_value=worker_result)
        mock_dry_run_job = MagicMock()
        mock_dry_run_job.delay = MagicMock(return_value=mock_async_result)

        with patch("worker.tasks.dry_run.dry_run_job", mock_dry_run_job):
            result = await JobService.dry_run(payload)

        assert result == worker_result
        mock_dry_run_job.delay.assert_called_once_with(payload.model_dump())

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        payload = DryRunRequest(
            url="https://example.com", selectors=VALID_SELECTORS
        )
        mock_async_result = MagicMock()
        mock_async_result.get = MagicMock(side_effect=CeleryTimeoutError())
        mock_dry_run_job = MagicMock()
        mock_dry_run_job.delay = MagicMock(return_value=mock_async_result)

        with patch("worker.tasks.dry_run.dry_run_job", mock_dry_run_job):
            result = await JobService.dry_run(payload)

        assert result is None

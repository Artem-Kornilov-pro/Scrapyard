from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.tasks.scheduler import sync_scheduled_jobs


@pytest.fixture
def mock_db():
    """Mock MongoDB collections."""
    with patch("worker.tasks.scheduler.db") as mock:
        mock.scraping_jobs = MagicMock()
        mock.scraping_jobs.update_one = AsyncMock()

        mock_cursor = MagicMock()
        mock_cursor.__aiter__.return_value = [
            {
                "job_id": "job-1",
                "schedule": "0 */6 * * *",
                "url": "https://example.com",
                "selectors": {},
                "status": "active",
            },
        ]
        mock.scraping_jobs.find.return_value = mock_cursor
        yield mock


@pytest.fixture
def mock_scrape_job():
    """Mock scrape_job task."""
    with patch("worker.tasks.scheduler.scrape_job") as mock:
        mock.delay = MagicMock()
        yield mock


class TestSyncScheduledJobs:
    """Tests for sync_scheduled_jobs."""

    @pytest.mark.asyncio
    async def test_dispatches_due_jobs(self, mock_db, mock_scrape_job):
        """Test that due jobs are dispatched."""
        dispatched = await sync_scheduled_jobs(MagicMock())

        assert dispatched == 1
        mock_scrape_job.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_next_run(self, mock_db, mock_scrape_job):
        """Test that next_run is updated after dispatch."""
        await sync_scheduled_jobs(MagicMock())

        mock_db.scraping_jobs.update_one.assert_called_once()
        call_args = mock_db.scraping_jobs.update_one.call_args[0]
        assert call_args[0] == {"job_id": "job-1"}
        assert "next_run" in call_args[1]["$set"]
        assert "updated_at" in call_args[1]["$set"]

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worker.tasks.scraper import _run_scrape, scrape_job

VALID_JOB_CONFIG = {
    "job_id": "test-job-123",
    "url": "https://example.com",
    "selectors": {
        "items": "div.product",
        "fields": {
            "title": {"selector": "h3", "attr": "text", "type": "string"},
        },
    },
}


@pytest.fixture
def mock_db():
    """Mock MongoDB collections."""
    with patch("worker.tasks.scraper.db") as mock:
        mock.scraping_jobs = MagicMock()
        mock.scraping_jobs.update_one = AsyncMock()
        mock.scraping_jobs.find_one = AsyncMock()
        mock.scraped_results = MagicMock()
        mock.scraped_results.insert_one = AsyncMock()
        mock.job_logs = MagicMock()
        mock.job_logs.insert_one = AsyncMock()
        yield mock


@pytest.fixture
def mock_engine():
    """Mock PlaywrightEngine."""
    with patch("worker.tasks.scraper.PlaywrightEngine") as mock_cls:
        mock_instance = MagicMock()
        mock_instance._page = MagicMock()
        mock_instance.navigate = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(
            return_value=mock_instance
        )
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_cls


@pytest.fixture
def mock_parser():
    """Mock collect_page_items (parsing + pagination collection)."""
    with patch("worker.tasks.scraper.collect_page_items") as mock:
        mock.return_value = [
            {"title": "Product 1"},
            {"title": "Product 2"},
        ]
        yield mock


@pytest.fixture
def mock_task():
    """Mock Celery task self."""
    task = MagicMock()
    task.retry = MagicMock()
    task.setup = AsyncMock()
    task.apply_async = MagicMock()
    return task


@pytest.fixture(autouse=True)
def mock_robots_and_throttle():
    """Default every test to "allowed and not throttled".

    Individual tests override these to exercise the skip/defer paths.
    Without this, every test would issue a real HTTP request for
    robots.txt and a real Redis lock attempt.
    """
    with patch(
        "worker.tasks.scraper.is_allowed", new=AsyncMock(return_value=True)
    ) as mock_allowed, patch(
        "worker.tasks.scraper.acquire_domain_slot",
        new=AsyncMock(return_value=True),
    ) as mock_slot:
        yield mock_allowed, mock_slot


@pytest.fixture(autouse=True)
def mock_notify():
    """Default webhook sender to a no-op spy."""
    with patch(
        "worker.tasks.scraper.send_webhook_notification", new=AsyncMock()
    ) as mock:
        yield mock


class TestScrapeJob:
    """Tests for scrape_job Celery task."""

    @pytest.mark.asyncio
    async def test_scrape_success(
        self, mock_db, mock_engine, mock_parser, mock_task
    ):
        """Test successful scraping job."""
        result = await _run_scrape(mock_task, VALID_JOB_CONFIG)
        assert result["items_count"] == 2
        assert "run_id" in result

    @pytest.mark.asyncio
    async def test_scrape_saves_to_db(
        self, mock_db, mock_engine, mock_parser, mock_task
    ):
        """Test results are saved to MongoDB."""
        await _run_scrape(mock_task, VALID_JOB_CONFIG)

        mock_db.scraped_results.insert_one.assert_called_once()
        call_args = mock_db.scraped_results.insert_one.call_args[0][0]
        assert call_args["job_id"] == "test-job-123"
        assert call_args["items_count"] == 2
        assert call_args["metadata"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_scrape_updates_last_run(
        self, mock_db, mock_engine, mock_parser, mock_task
    ):
        """Test last_run is updated after successful job."""
        await _run_scrape(mock_task, VALID_JOB_CONFIG)

        # Check that update_one was called with correct job_id and fields
        called = False
        for call_args in mock_db.scraping_jobs.update_one.call_args_list:
            args, kwargs = call_args
            if args[0] == {"job_id": "test-job-123"}:
                called = True
                assert "last_run" in args[1]["$set"]
                assert args[1]["$set"]["consecutive_failures"] == 0
                break

        assert called, "update_one was not called with correct job_id"

    @pytest.mark.asyncio
    async def test_scrape_handles_error(
        self, mock_db, mock_engine, mock_parser, mock_task
    ):
        """Test error handling increments failure count."""
        mock_parser.side_effect = Exception("Parse error")
        mock_task.retry.side_effect = Exception("Retry")
        mock_db.scraping_jobs.find_one = AsyncMock(
            return_value={"consecutive_failures": 1}
        )

        with pytest.raises(Exception):
            await _run_scrape(mock_task, VALID_JOB_CONFIG)

        mock_db.scraping_jobs.update_one.assert_any_call(
            {"job_id": "test-job-123"},
            {"$inc": {"consecutive_failures": 1}},
        )

    @pytest.mark.asyncio
    async def test_scrape_calls_setup(
        self, mock_db, mock_engine, mock_parser, mock_task
    ):
        """Test that MongoDB connection setup runs before scraping."""
        await _run_scrape(mock_task, VALID_JOB_CONFIG)
        mock_task.setup.assert_called_once()


class TestScrapeJobUsesCollectPageItems:
    """Tests that scrape_job delegates item collection (incl. pagination
    branching) to collect_page_items and trusts its result, rather than
    branching on pagination type itself.
    """

    @pytest.mark.asyncio
    async def test_passes_selectors_and_pagination_config(
        self, mock_db, mock_engine, mock_task
    ):
        job_config = {
            **VALID_JOB_CONFIG,
            "settings": {"pagination": {"type": "url", "max_pages": 3}},
        }
        with patch(
            "worker.tasks.scraper.collect_page_items",
            new=AsyncMock(
                return_value=[{"title": "A"}, {"title": "B"}, {"title": "C"}]
            ),
        ) as mock_collect:
            result = await _run_scrape(mock_task, job_config)

        mock_collect.assert_called_once()
        call_args = mock_collect.call_args[0]
        assert call_args[1] == job_config["selectors"]
        assert call_args[2] == {"type": "url", "max_pages": 3}
        assert result["items_count"] == 3

    @pytest.mark.asyncio
    async def test_pages_processed_reflects_max_pages_when_paginated(
        self, mock_db, mock_engine, mock_task
    ):
        job_config = {
            **VALID_JOB_CONFIG,
            "settings": {"pagination": {"type": "scroll", "max_pages": 5}},
        }
        with patch(
            "worker.tasks.scraper.collect_page_items",
            new=AsyncMock(return_value=[{"title": "A"}]),
        ):
            await _run_scrape(mock_task, job_config)

        call_args = mock_db.scraped_results.insert_one.call_args[0][0]
        assert call_args["metadata"]["pages_processed"] == 5

    @pytest.mark.asyncio
    async def test_no_pagination_settings_defaults_to_empty_config(
        self, mock_db, mock_engine, mock_task
    ):
        with patch(
            "worker.tasks.scraper.collect_page_items",
            new=AsyncMock(return_value=[{"title": "A"}, {"title": "B"}]),
        ) as mock_collect:
            result = await _run_scrape(mock_task, VALID_JOB_CONFIG)

        call_args = mock_collect.call_args[0]
        assert call_args[2] == {}
        assert result["items_count"] == 2


class TestRobotsTxtBlocking:
    """Tests that disallowed URLs are skipped, not scraped."""

    @pytest.mark.asyncio
    async def test_blocked_url_skips_scraping(
        self, mock_db, mock_engine, mock_parser, mock_task,
        mock_robots_and_throttle,
    ):
        mock_allowed, _ = mock_robots_and_throttle
        mock_allowed.return_value = False

        result = await _run_scrape(mock_task, VALID_JOB_CONFIG)

        assert result["items_count"] == 0
        assert result["skipped"] == "robots_txt"
        mock_engine.assert_not_called()
        mock_db.scraped_results.insert_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocked_url_logs_skip_reason(
        self, mock_db, mock_engine, mock_parser, mock_task,
        mock_robots_and_throttle,
    ):
        mock_allowed, _ = mock_robots_and_throttle
        mock_allowed.return_value = False

        await _run_scrape(mock_task, VALID_JOB_CONFIG)

        call_args = mock_db.job_logs.insert_one.call_args[0][0]
        assert call_args["status"] == "skipped"
        assert call_args["reason"] == "blocked_by_robots_txt"

    @pytest.mark.asyncio
    async def test_blocked_url_does_not_count_as_failure(
        self, mock_db, mock_engine, mock_parser, mock_task,
        mock_robots_and_throttle,
    ):
        mock_allowed, _ = mock_robots_and_throttle
        mock_allowed.return_value = False

        await _run_scrape(mock_task, VALID_JOB_CONFIG)

        mock_db.scraping_jobs.update_one.assert_not_called()


class TestDomainThrottling:
    """Tests that throttled domains defer the run instead of scraping."""

    @pytest.mark.asyncio
    async def test_throttled_domain_defers_instead_of_scraping(
        self, mock_db, mock_engine, mock_parser, mock_task,
        mock_robots_and_throttle,
    ):
        _, mock_slot = mock_robots_and_throttle
        mock_slot.return_value = False

        result = await _run_scrape(mock_task, VALID_JOB_CONFIG)

        assert result["items_count"] == 0
        assert result["deferred"] == "domain_throttled"
        mock_engine.assert_not_called()
        mock_db.scraped_results.insert_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_throttled_domain_requeues_itself(
        self, mock_db, mock_engine, mock_parser, mock_task,
        mock_robots_and_throttle,
    ):
        _, mock_slot = mock_robots_and_throttle
        mock_slot.return_value = False

        await _run_scrape(mock_task, VALID_JOB_CONFIG)

        mock_task.apply_async.assert_called_once()
        _, kwargs = mock_task.apply_async.call_args
        assert kwargs["args"] == [VALID_JOB_CONFIG]
        assert "countdown" in kwargs

    @pytest.mark.asyncio
    async def test_throttled_domain_does_not_count_as_failure(
        self, mock_db, mock_engine, mock_parser, mock_task,
        mock_robots_and_throttle,
    ):
        _, mock_slot = mock_robots_and_throttle
        mock_slot.return_value = False

        await _run_scrape(mock_task, VALID_JOB_CONFIG)

        mock_db.scraping_jobs.update_one.assert_not_called()


class TestErrorWebhookNotification:
    """Tests that a webhook fires when a job crosses into 'error'."""

    @pytest.mark.asyncio
    async def test_sends_webhook_on_fifth_consecutive_failure(
        self, mock_db, mock_engine, mock_parser, mock_task, mock_notify
    ):
        mock_parser.side_effect = Exception("Parse error")
        mock_task.retry.side_effect = Exception("Retry")
        mock_db.scraping_jobs.find_one = AsyncMock(return_value={
            "job_id": "test-job-123",
            "name": "Test Job",
            "url": "https://example.com",
            "consecutive_failures": 5,
            "notify_webhook": "https://hooks.example.com/alert",
        })

        with pytest.raises(Exception):
            await _run_scrape(mock_task, VALID_JOB_CONFIG)

        mock_notify.assert_called_once()
        webhook_url, payload = mock_notify.call_args[0]
        assert webhook_url == "https://hooks.example.com/alert"
        assert payload["event"] == "job.error"
        assert payload["job_id"] == "test-job-123"
        assert payload["consecutive_failures"] == 5

    @pytest.mark.asyncio
    async def test_no_webhook_configured_does_not_call_notify(
        self, mock_db, mock_engine, mock_parser, mock_task, mock_notify
    ):
        mock_parser.side_effect = Exception("Parse error")
        mock_task.retry.side_effect = Exception("Retry")
        mock_db.scraping_jobs.find_one = AsyncMock(return_value={
            "job_id": "test-job-123",
            "consecutive_failures": 5,
            "notify_webhook": None,
        })

        with pytest.raises(Exception):
            await _run_scrape(mock_task, VALID_JOB_CONFIG)

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_below_threshold_does_not_notify(
        self, mock_db, mock_engine, mock_parser, mock_task, mock_notify
    ):
        mock_parser.side_effect = Exception("Parse error")
        mock_task.retry.side_effect = Exception("Retry")
        mock_db.scraping_jobs.find_one = AsyncMock(return_value={
            "job_id": "test-job-123",
            "consecutive_failures": 2,
            "notify_webhook": "https://hooks.example.com/alert",
        })

        with pytest.raises(Exception):
            await _run_scrape(mock_task, VALID_JOB_CONFIG)

        mock_notify.assert_not_called()


class TestScrapeJobBridging:
    """Regression: the Celery task must actually run the coroutine.

    scrape_job previously returned `_run_scrape(...)` directly, i.e. an
    un-awaited coroutine object, instead of driving it to completion —
    meaning real Celery execution never actually scraped anything.
    Calling the task object directly (not .delay()) is the standard way
    to exercise a bound Celery task's real `self` without a broker.
    """

    def test_scrape_job_drives_coroutine_to_completion(
        self, mock_db, mock_engine, mock_parser
    ):
        with patch(
            "worker.tasks.scraper.connect_to_mongo", new=AsyncMock()
        ):
            result = scrape_job(VALID_JOB_CONFIG)

        assert result["items_count"] == 2
        assert "run_id" in result
        mock_db.scraped_results.insert_one.assert_called_once()

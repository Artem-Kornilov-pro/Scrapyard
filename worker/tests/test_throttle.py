from unittest.mock import AsyncMock, patch

import pytest

from worker.utils import throttle as throttle_module
from worker.utils.throttle import acquire_domain_slot, extract_domain


class TestExtractDomain:
    """Tests for pulling the throttle key out of a URL."""

    def test_extracts_netloc(self):
        assert extract_domain("https://example.com/path?q=1") == "example.com"

    def test_extracts_netloc_with_port(self):
        assert extract_domain("http://example.com:8080/x") == "example.com:8080"


class TestAcquireDomainSlot:
    """Tests for the per-domain throttle lock."""

    @pytest.mark.asyncio
    async def test_disabled_when_throttle_seconds_zero(self, monkeypatch):
        monkeypatch.setattr(throttle_module.settings, "domain_throttle_seconds", 0)
        assert await acquire_domain_slot("example.com") is True

    @pytest.mark.asyncio
    async def test_delegates_to_redis_lock(self, monkeypatch):
        monkeypatch.setattr(
            throttle_module.settings, "domain_throttle_seconds", 2.0
        )
        with patch(
            "worker.utils.throttle.domain_throttle_cache.acquire_lock",
            new=AsyncMock(return_value=False),
        ) as mock_lock:
            result = await acquire_domain_slot("example.com")

        assert result is False
        mock_lock.assert_called_once_with("throttle:domain:example.com", 2)

    @pytest.mark.asyncio
    async def test_returns_true_when_lock_acquired(self, monkeypatch):
        monkeypatch.setattr(
            throttle_module.settings, "domain_throttle_seconds", 2.0
        )
        with patch(
            "worker.utils.throttle.domain_throttle_cache.acquire_lock",
            new=AsyncMock(return_value=True),
        ):
            assert await acquire_domain_slot("example.com") is True

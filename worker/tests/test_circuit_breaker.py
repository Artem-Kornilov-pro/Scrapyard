from unittest.mock import AsyncMock, patch

import pytest

from worker.utils import circuit_breaker as circuit_breaker_module
from worker.utils.circuit_breaker import is_open, record_blocked, record_success


class TestIsOpen:
    """Tests for reading circuit breaker state."""

    @pytest.mark.asyncio
    async def test_closed_by_default(self):
        with patch(
            "worker.utils.circuit_breaker.domain_throttle_cache.get",
            new=AsyncMock(return_value=None),
        ):
            assert await is_open("example.com") is False

    @pytest.mark.asyncio
    async def test_open_when_flag_set(self):
        with patch(
            "worker.utils.circuit_breaker.domain_throttle_cache.get",
            new=AsyncMock(return_value=True),
        ) as mock_get:
            assert await is_open("example.com") is True
        mock_get.assert_called_once_with("circuit:open:example.com")


class TestRecordBlocked:
    """Tests for tripping the breaker after repeated 403/429s."""

    @pytest.mark.asyncio
    async def test_below_threshold_does_not_open_circuit(self, monkeypatch):
        monkeypatch.setattr(
            circuit_breaker_module.settings, "circuit_breaker_failure_threshold", 3
        )
        with patch(
            "worker.utils.circuit_breaker.domain_throttle_cache.increment",
            new=AsyncMock(return_value=2),
        ), patch(
            "worker.utils.circuit_breaker.domain_throttle_cache.set",
            new=AsyncMock(),
        ) as mock_set:
            await record_blocked("example.com")

        mock_set.assert_not_called()

    @pytest.mark.asyncio
    async def test_reaching_threshold_opens_circuit(self, monkeypatch):
        monkeypatch.setattr(
            circuit_breaker_module.settings, "circuit_breaker_failure_threshold", 3
        )
        monkeypatch.setattr(
            circuit_breaker_module.settings, "circuit_breaker_cooldown_seconds", 300
        )
        with patch(
            "worker.utils.circuit_breaker.domain_throttle_cache.increment",
            new=AsyncMock(return_value=3),
        ), patch(
            "worker.utils.circuit_breaker.domain_throttle_cache.set",
            new=AsyncMock(),
        ) as mock_set:
            await record_blocked("example.com")

        mock_set.assert_called_once_with("circuit:open:example.com", True, ttl=300)


class TestRecordSuccess:
    """Tests for resetting the failure count."""

    @pytest.mark.asyncio
    async def test_deletes_failure_counter(self):
        with patch(
            "worker.utils.circuit_breaker.domain_throttle_cache.delete",
            new=AsyncMock(),
        ) as mock_delete:
            await record_success("example.com")

        mock_delete.assert_called_once_with("circuit:failures:example.com")

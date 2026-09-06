"""Tests for runtime health tracking and degradation."""
import pytest
from unittest.mock import patch, AsyncMock
from app.runtime.health import (
    RuntimeHealthTracker, RuntimeHealth, ComponentHealth, RuntimeStatus
)


class TestRuntimeHealthTracker:

    def test_initial_state(self):
        tracker = RuntimeHealthTracker("test-instance")
        assert tracker.overall == RuntimeHealth.UNKNOWN
        assert tracker.status == "starting"
        assert not tracker.is_db_healthy
        assert not tracker.is_redis_healthy

    def test_set_ready(self):
        tracker = RuntimeHealthTracker("test-instance")
        tracker.set_ready()
        assert tracker.status == "running"

    @pytest.mark.asyncio
    async def test_check_db_healthy(self):
        tracker = RuntimeHealthTracker("test")
        with patch("app.runtime.health.check_db", new=AsyncMock(return_value=True)):
            result = await tracker.check_db()
            assert result is True
            assert tracker.is_db_healthy

    @pytest.mark.asyncio
    async def test_check_db_unhealthy(self):
        tracker = RuntimeHealthTracker("test")
        with patch("app.runtime.health.check_db", new=AsyncMock(return_value=False)):
            result = await tracker.check_db()
            assert result is False
            assert not tracker.is_db_healthy

    @pytest.mark.asyncio
    async def test_check_db_exception(self):
        tracker = RuntimeHealthTracker("test")
        with patch("app.runtime.health.check_db", side_effect=Exception("boom")):
            result = await tracker.check_db()
            assert result is False
            assert not tracker.is_db_healthy

    @pytest.mark.asyncio
    async def test_check_redis_healthy(self):
        tracker = RuntimeHealthTracker("test")
        with patch("app.runtime.health.check_redis", new=AsyncMock(return_value=True)):
            result = await tracker.check_redis()
            assert result is True
            assert tracker.is_redis_healthy

    @pytest.mark.asyncio
    async def test_check_all_healthy(self):
        tracker = RuntimeHealthTracker("test")
        with patch("app.runtime.health.check_db", new=AsyncMock(return_value=True)):
            with patch("app.runtime.health.check_redis", new=AsyncMock(return_value=True)):
                result = await tracker.check_all()
                assert result == RuntimeHealth.HEALTHY
                assert tracker.status == "healthy"

    @pytest.mark.asyncio
    async def test_check_all_degraded_db_down(self):
        tracker = RuntimeHealthTracker("test")
        with patch("app.runtime.health.check_db", new=AsyncMock(return_value=False)):
            with patch("app.runtime.health.check_redis", new=AsyncMock(return_value=True)):
                result = await tracker.check_all()
                assert result == RuntimeHealth.DEGRADED

    @pytest.mark.asyncio
    async def test_check_all_degraded_redis_down(self):
        tracker = RuntimeHealthTracker("test")
        with patch("app.runtime.health.check_db", new=AsyncMock(return_value=True)):
            with patch("app.runtime.health.check_redis", new=AsyncMock(return_value=False)):
                result = await tracker.check_all()
                assert result == RuntimeHealth.DEGRADED

    @pytest.mark.asyncio
    async def test_check_all_unavailable(self):
        tracker = RuntimeHealthTracker("test")
        with patch("app.runtime.health.check_db", new=AsyncMock(return_value=False)):
            with patch("app.runtime.health.check_redis", new=AsyncMock(return_value=False)):
                result = await tracker.check_all()
                assert result == RuntimeHealth.UNAVAILABLE


class TestRuntimeStatus:

    def test_default_status(self):
        status = RuntimeStatus()
        assert status.status == "starting"
        assert status.persistence_status == "unknown"
        assert status.redis_status == "unknown"

    def test_to_dict(self):
        status = RuntimeStatus(instance_id="i1", status="healthy", persistence_status="healthy", redis_status="healthy")
        d = status.to_dict()
        assert d["instance_id"] == "i1"
        assert d["status"] == "healthy"
        assert d["persistence_status"] == "healthy"
        assert d["redis_status"] == "healthy"
        assert "uptime_seconds" in d

    def test_to_dict_with_components(self):
        status = RuntimeStatus(instance_id="i2", components={"pg": "healthy", "redis": "unavailable"})
        d = status.to_dict()
        assert d["components"]["pg"] == "healthy"
        assert d["components"]["redis"] == "unavailable"


class TestRuntimeHealthTrackerIntegration:

    def test_get_status_reflects_health(self):
        tracker = RuntimeHealthTracker("inst-1")
        status = tracker.get_status()
        assert status.instance_id == "inst-1"
        assert status.status == "starting"
        assert status.persistence_status == "unavailable"

    def test_get_status_after_set_ready(self):
        tracker = RuntimeHealthTracker("inst-1")
        tracker.set_ready()
        status = tracker.get_status()
        assert status.status == "running"

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        tracker = RuntimeHealthTracker("lifecycle-test")
        assert tracker.status == "starting"
        with patch("app.runtime.health.check_db", new=AsyncMock(return_value=True)):
            with patch("app.runtime.health.check_redis", new=AsyncMock(return_value=True)):
                await tracker.check_all()
                tracker.set_ready()
                assert tracker.status == "running"
                assert tracker.overall == RuntimeHealth.HEALTHY
                status = tracker.get_status()
                assert status.status == "running"
                assert status.persistence_status == "healthy"
                assert status.redis_status == "healthy"

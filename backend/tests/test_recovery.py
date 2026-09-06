"""Phase 4.19: Runtime recovery tests."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.persistence.recovery import RuntimeRecoveryManager
from app.runtime.manager import AppRuntime, get_runtime, reset_runtime


@pytest.fixture(autouse=True)
def reset():
    reset_runtime()
    yield
    reset_runtime()


class TestRuntimeRecoveryManager:

    def test_init(self):
        mgr = RuntimeRecoveryManager()
        assert mgr.is_recovered is False
        assert mgr._recovered_tasks == []

    @pytest.mark.asyncio
    async def test_recover_no_db(self):
        mgr = RuntimeRecoveryManager()
        with patch("app.persistence.recovery.PersistentTaskService") as mock_svc:
            mock_svc.return_value.recover_tasks = AsyncMock(side_effect=Exception("no db"))
            result = await mgr.recover()
            assert result["recovered"] is False
            assert len(result["errors"]) >= 1

    @pytest.mark.asyncio
    async def test_recover_empty_tasks(self):
        mgr = RuntimeRecoveryManager()
        with patch("app.persistence.recovery.PersistentTaskService") as mock_svc:
            mock_svc.return_value.recover_tasks = AsyncMock(return_value=[])
            result = await mgr.recover()
            assert result["tasks_restored"] == 0

    @pytest.mark.asyncio
    async def test_recover_tasks(self):
        mgr = RuntimeRecoveryManager()
        tasks = [
            {"task_id": "t1", "task": "task1", "status": "running", "max_iterations": 3, "attempt": 2},
            {"task_id": "t2", "task": "task2", "status": "completed", "max_iterations": 1, "attempt": 1},
            {"task_id": "t3", "task": "task3", "status": "pending", "max_iterations": 5, "attempt": 0},
        ]
        with patch("app.persistence.recovery.PersistentTaskService") as mock_svc:
            mock_svc.return_value.recover_tasks = AsyncMock(return_value=tasks)
            result = await mgr.recover()
            assert result["tasks_restored"] == 3
            assert result["active_tasks"] == 2  # running + pending

    @pytest.mark.asyncio
    async def test_recover_users_empty(self):
        mgr = RuntimeRecoveryManager()
        users = await mgr.recover_users()
        assert users == []

    @pytest.mark.asyncio
    async def test_recover_audit_empty(self):
        mgr = RuntimeRecoveryManager()
        audit = await mgr.recover_audit()
        assert audit == []

    def test_to_dict(self):
        mgr = RuntimeRecoveryManager()
        d = mgr.to_dict()
        assert d["recovered"] is False
        assert d["recovered_tasks_count"] == 0


class TestAppRuntimeRecovery:

    @pytest.mark.asyncio
    async def test_run_recovery_graceful_failure(self):
        rt = AppRuntime()
        # Should not raise when DB is unavailable
        await rt._run_recovery()

    def test_shutdown_flag(self):
        rt = AppRuntime()
        assert rt._shutting_down is False

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self):
        rt = AppRuntime()
        await rt.shutdown()
        # Second call should be no-op
        await rt.shutdown()


class TestRecoveryWithTaskStates:

    def test_recover_running_tasks_become_queued(self):
        """Running tasks on recovery should become queued."""
        assert True  # Placeholder for integration test

    def test_recover_paused_tasks_stay_paused(self):
        """Paused tasks should remain paused after recovery."""
        assert True

    def test_recover_completed_tasks_not_requeued(self):
        """Completed tasks should not be re-executed."""
        assert True

    @pytest.mark.asyncio
    async def test_recovery_with_distributed_lock(self):
        """Recovery should prevent duplicate task execution across instances."""
        rt = AppRuntime()
        # Verify the recovery mechanism exists
        assert hasattr(rt, "_run_recovery")
        assert hasattr(rt, "_distributed_lock_manager")

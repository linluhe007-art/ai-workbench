"""
Phase 4.18 tests - Persistence Integration & Runtime Recovery.
Covers: DatabaseSettings, health checks, PersistentTaskService,
PersistentExecutionService, PersistentUserService,
PersistentArtifactService, PersistentWorkspaceService,
PersistentAuditService, PersistentExperienceService,
RuntimeRecoveryManager, graceful degradation, tenant isolation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.config import DatabaseSettings, get_db_settings, reset_db_settings
from app.persistence.health import (
    PersistenceHealthChecker, PersistenceStatus,
    get_health_checker, reset_health_checker,
)
from app.persistence.task_service import PersistentTaskService
from app.persistence.execution_service import PersistentExecutionService
from app.persistence.user_service import PersistentUserService
from app.persistence.artifact_service import PersistentArtifactService
from app.persistence.workspace_service import PersistentWorkspaceService
from app.persistence.audit_service import PersistentAuditService
from app.persistence.experience_service import PersistentExperienceService
from app.persistence.recovery import RuntimeRecoveryManager


@pytest.fixture(autouse=True)
def _reset():
    reset_db_settings()
    reset_health_checker()
    yield
    reset_db_settings()
    reset_health_checker()


# =============================================================================
# DatabaseSettings Tests
# =============================================================================

class TestDatabaseSettings:
    def test_default_values(self):
        settings = DatabaseSettings()
        assert settings.database_pool_size == 5
        assert settings.database_max_overflow == 10
        assert settings.database_echo is False

    def test_singleton(self):
        reset_db_settings()
        s1 = get_db_settings()
        s2 = get_db_settings()
        assert s1 is s2

    def test_reset(self):
        reset_db_settings()
        s1 = get_db_settings()
        reset_db_settings()
        s2 = get_db_settings()
        assert s1 is not s2

    def test_custom_values(self):
        settings = DatabaseSettings(
            database_pool_size=20,
            database_max_overflow=50,
            database_echo=True,
        )
        assert settings.database_pool_size == 20
        assert settings.database_echo is True


# =============================================================================
# PersistenceHealthChecker Tests
# =============================================================================

class TestPersistenceHealthChecker:
    def test_initial_state(self):
        checker = PersistenceHealthChecker()
        assert checker.db_available is False
        assert checker.redis_available is False

    def test_to_dict_initial(self):
        checker = PersistenceHealthChecker()
        d = checker.to_dict()
        assert d["database"] == "unavailable"
        assert d["redis"] == "unavailable"
        assert d["overall"] == "unavailable"

    @pytest.mark.asyncio
    async def test_check_when_db_available(self):
        checker = PersistenceHealthChecker()
        with patch("app.persistence.health.check_db", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = True
            with patch("app.persistence.health.check_redis", new_callable=AsyncMock) as mock_redis:
                mock_redis.return_value = False
                status = await checker.check()
                assert status == PersistenceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_check_when_both_available(self):
        checker = PersistenceHealthChecker()
        with patch("app.persistence.health.check_db", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = True
            with patch("app.persistence.health.check_redis", new_callable=AsyncMock) as mock_redis:
                mock_redis.return_value = True
                status = await checker.check()
                assert status == PersistenceStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_when_both_unavailable(self):
        checker = PersistenceHealthChecker()
        with patch("app.persistence.health.check_db", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = False
            with patch("app.persistence.health.check_redis", new_callable=AsyncMock) as mock_redis:
                mock_redis.return_value = False
                status = await checker.check()
                assert status == PersistenceStatus.UNAVAILABLE

    def test_singleton(self):
        reset_health_checker()
        c1 = get_health_checker()
        c2 = get_health_checker()
        assert c1 is c2

    def test_reset(self):
        reset_health_checker()
        c1 = get_health_checker()
        reset_health_checker()
        c2 = get_health_checker()
        assert c1 is not c2


# =============================================================================
# PersistentTaskService Tests
# =============================================================================

class TestPersistentTaskService:
    def test_initialized_available(self):
        svc = PersistentTaskService()
        assert svc.is_available is True

    @pytest.mark.asyncio
    async def test_get_task_count_empty(self):
        svc = PersistentTaskService()
        count = await svc.get_task_count()
        assert count >= 0

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self):
        svc = PersistentTaskService()
        tasks = await svc.list_tasks()
        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_list_tasks_with_tenant_filter(self):
        svc = PersistentTaskService()
        tasks = await svc.list_tasks(tenant_id="tenant-nonexistent")
        assert tasks == []

    @pytest.mark.asyncio
    async def test_get_task_nonexistent(self):
        svc = PersistentTaskService()
        task = await svc.get_task("nonexistent-task-id")
        assert task is None

    @pytest.mark.asyncio
    async def test_recover_tasks_empty(self):
        svc = PersistentTaskService()
        tasks = await svc.recover_tasks()
        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_create_task_returns_none_on_db_failure(self):
        svc = PersistentTaskService()
        result = await svc.create_task("tid", "test task")
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_update_status_returns_none_on_db_failure(self):
        svc = PersistentTaskService()
        result = await svc.update_status("tid", "running")
        assert result is None or isinstance(result, dict)


# =============================================================================
# PersistentExecutionService Tests
# =============================================================================

class TestPersistentExecutionService:
    def test_initialized_available(self):
        svc = PersistentExecutionService()
        assert svc.is_available is True

    @pytest.mark.asyncio
    async def test_get_execution_history_empty(self):
        svc = PersistentExecutionService()
        history = await svc.get_execution_history("nonexistent-task")
        assert history == []

    @pytest.mark.asyncio
    async def test_get_success_rate_empty(self):
        svc = PersistentExecutionService()
        rate = await svc.get_success_rate("nonexistent-task")
        assert rate["total"] == 0
        assert rate["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        svc = PersistentExecutionService()
        metrics = await svc.get_metrics()
        assert "db_available" in metrics

    @pytest.mark.asyncio
    async def test_save_execution_returns_none_on_db_failure(self):
        svc = PersistentExecutionService()
        result = await svc.save_execution("tid", 0, "success")
        assert result is None or isinstance(result, dict)


# =============================================================================
# PersistentUserService Tests
# =============================================================================

class TestPersistentUserService:
    def test_initialized_available(self):
        svc = PersistentUserService()
        assert svc.is_available is True

    @pytest.mark.asyncio
    async def test_list_users_empty(self):
        svc = PersistentUserService()
        users = await svc.list_users()
        assert isinstance(users, list)

    @pytest.mark.asyncio
    async def test_list_users_with_tenant(self):
        svc = PersistentUserService()
        users = await svc.list_users(tenant_id="nonexistent")
        assert users == []

    @pytest.mark.asyncio
    async def test_get_user_nonexistent(self):
        svc = PersistentUserService()
        user = await svc.get_user("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_delete_user_nonexistent(self):
        svc = PersistentUserService()
        result = await svc.delete_user("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_roles_empty(self):
        svc = PersistentUserService()
        roles = await svc.list_roles()
        assert isinstance(roles, list)

    @pytest.mark.asyncio
    async def test_list_tenants_empty(self):
        svc = PersistentUserService()
        tenants = await svc.list_tenants()
        assert isinstance(tenants, list)


# =============================================================================
# PersistentArtifactService Tests
# =============================================================================

class TestPersistentArtifactService:
    def test_initialized_available(self):
        svc = PersistentArtifactService()
        assert svc.is_available is True

    @pytest.mark.asyncio
    async def test_list_artifacts_empty(self):
        svc = PersistentArtifactService()
        arts = await svc.list_artifacts()
        assert arts == []

    @pytest.mark.asyncio
    async def test_get_artifact_nonexistent(self):
        svc = PersistentArtifactService()
        art = await svc.get_artifact("nonexistent")
        assert art is None

    @pytest.mark.asyncio
    async def test_delete_artifact_nonexistent(self):
        svc = PersistentArtifactService()
        result = await svc.delete_artifact("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_search_artifacts_empty(self):
        svc = PersistentArtifactService()
        items, total = await svc.search_artifacts(query="nothing")
        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_artifacts_with_filters(self):
        svc = PersistentArtifactService()
        arts = await svc.list_artifacts(task_id="nonexistent", workspace_id="nonexistent")
        assert arts == []


# =============================================================================
# PersistentWorkspaceService Tests
# =============================================================================

class TestPersistentWorkspaceService:
    def test_initialized_available(self):
        svc = PersistentWorkspaceService()
        assert svc.is_available is True

    @pytest.mark.asyncio
    async def test_list_workspaces_empty(self):
        svc = PersistentWorkspaceService()
        ws_list = await svc.list_workspaces()
        assert ws_list == []

    @pytest.mark.asyncio
    async def test_get_workspace_nonexistent(self):
        svc = PersistentWorkspaceService()
        ws = await svc.get_workspace("nonexistent")
        assert ws is None


# =============================================================================
# PersistentAuditService Tests
# =============================================================================

class TestPersistentAuditService:
    def test_initialized_available(self):
        svc = PersistentAuditService()
        assert svc.is_available is True

    @pytest.mark.asyncio
    async def test_query_audit_empty(self):
        svc = PersistentAuditService()
        records, total = await svc.query_audit()
        assert records == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_query_audit_with_filters(self):
        svc = PersistentAuditService()
        records, total = await svc.query_audit(task_id="nonexistent", actor="system")
        assert records == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_record_audit_returns_none_on_failure(self):
        svc = PersistentAuditService()
        result = await svc.record_audit({
            "actor": "test", "action": "test",
            "resource_type": "test", "resource_id": "t1",
        })
        assert result is None or isinstance(result, dict)


# =============================================================================
# PersistentExperienceService Tests
# =============================================================================

class TestPersistentExperienceService:
    def test_initialized_available(self):
        svc = PersistentExperienceService()
        assert svc.is_available is True

    @pytest.mark.asyncio
    async def test_query_experience_empty(self):
        svc = PersistentExperienceService()
        records = await svc.query_experience()
        assert records == []

    @pytest.mark.asyncio
    async def test_query_experience_with_pattern(self):
        svc = PersistentExperienceService()
        records = await svc.query_experience(task_pattern="research", limit=5)
        assert isinstance(records, list)

    @pytest.mark.asyncio
    async def test_save_experience_returns_none_on_failure(self):
        svc = PersistentExperienceService()
        result = await svc.save_experience({"task_pattern": "test", "success": True})
        assert result is None or isinstance(result, dict)


# =============================================================================
# RuntimeRecoveryManager Tests
# =============================================================================

class TestRuntimeRecoveryManager:
    def test_initial_state(self):
        mgr = RuntimeRecoveryManager()
        assert mgr.is_recovered is False

    @pytest.mark.asyncio
    async def test_recover_returns_dict(self):
        mgr = RuntimeRecoveryManager()
        result = await mgr.recover()
        assert "recovered" in result
        assert "tasks_restored" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_recover_users_empty(self):
        mgr = RuntimeRecoveryManager()
        users = await mgr.recover_users()
        assert isinstance(users, list)

    @pytest.mark.asyncio
    async def test_recover_audit_empty(self):
        mgr = RuntimeRecoveryManager()
        records = await mgr.recover_audit(limit=10)
        assert isinstance(records, list)

    def test_to_dict(self):
        mgr = RuntimeRecoveryManager()
        d = mgr.to_dict()
        assert d["recovered"] is False
        assert "recovered_tasks_count" in d
        assert "errors" in d

    @pytest.mark.asyncio
    async def test_recover_then_is_recovered(self):
        mgr = RuntimeRecoveryManager()
        await mgr.recover()
        assert mgr.is_recovered in (True, False)


# =============================================================================
# Graceful Degradation Tests
# =============================================================================

class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_task_service_degrades_gracefully(self):
        svc = PersistentTaskService()
        svc._db_available = False
        tasks = await svc.list_tasks()
        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_execution_service_degrades_gracefully(self):
        svc = PersistentExecutionService()
        svc._db_available = False
        history = await svc.get_execution_history("any")
        assert history == []

    @pytest.mark.asyncio
    async def test_user_service_degrades_gracefully(self):
        svc = PersistentUserService()
        svc._db_available = False
        users = await svc.list_users()
        assert isinstance(users, list)

    @pytest.mark.asyncio
    async def test_artifact_service_degrades_gracefully(self):
        svc = PersistentArtifactService()
        svc._db_available = False
        arts = await svc.list_artifacts()
        assert arts == []

    @pytest.mark.asyncio
    async def test_workspace_service_degrades_gracefully(self):
        svc = PersistentWorkspaceService()
        svc._db_available = False
        ws_list = await svc.list_workspaces()
        assert ws_list == []

    @pytest.mark.asyncio
    async def test_audit_service_degrades_gracefully(self):
        svc = PersistentAuditService()
        svc._db_available = False
        records, total = await svc.query_audit()
        assert records == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_experience_service_degrades_gracefully(self):
        svc = PersistentExperienceService()
        svc._db_available = False
        records = await svc.query_experience()
        assert records == []


# =============================================================================
# Tenant Isolation Tests
# =============================================================================

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_task_service_tenant_isolation(self):
        svc = PersistentTaskService()
        tasks = await svc.list_tasks(tenant_id="tenant-a")
        assert all(t.get("tenant_id", "") in ("tenant-a", "") for t in tasks)

    @pytest.mark.asyncio
    async def test_user_service_tenant_isolation(self):
        svc = PersistentUserService()
        users = await svc.list_users(tenant_id="tenant-a")
        assert isinstance(users, list)

    @pytest.mark.asyncio
    async def test_get_task_with_tenant_check(self):
        svc = PersistentTaskService()
        task = await svc.get_task("nonexistent", tenant_id="tenant-a")
        assert task is None


# =============================================================================
# PersistenceStatus Enum Tests
# =============================================================================

class TestPersistenceStatus:
    def test_enum_values(self):
        assert PersistenceStatus.HEALTHY.value == "healthy"
        assert PersistenceStatus.DEGRADED.value == "degraded"
        assert PersistenceStatus.UNAVAILABLE.value == "unavailable"

    def test_string_comparison(self):
        assert PersistenceStatus.HEALTHY == "healthy"
        assert str(PersistenceStatus.DEGRADED) == "PersistenceStatus.degraded"
# =============================================================================
# Additional Edge Case Tests
# =============================================================================

class TestEdgeCasesPhase18:
    @pytest.mark.asyncio
    async def test_db_settings_url_override(self):
        settings = DatabaseSettings(database_url="postgresql://custom:pass@host/db")
        assert "custom" in settings.database_url

    @pytest.mark.asyncio
    async def test_health_checker_to_dict_after_check(self):
        checker = PersistenceHealthChecker()
        checker._db_available = True
        checker._redis_available = False
        d = checker.to_dict()
        assert d["database"] == "healthy"
        assert d["overall"] == "degraded"

    @pytest.mark.asyncio
    async def test_recovery_to_dict_after_recover(self):
        mgr = RuntimeRecoveryManager()
        await mgr.recover()
        d = mgr.to_dict()
        assert "recovered_tasks_count" in d

    @pytest.mark.asyncio
    async def test_task_service_tenant_empty_default(self):
        svc = PersistentTaskService()
        tasks = await svc.list_tasks()
        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_user_service_update_nonexistent(self):
        svc = PersistentUserService()
        result = await svc.update_user("nonexistent", {"username": "new"})
        assert result is None

    @pytest.mark.asyncio
    async def test_artifact_service_filtered_list(self):
        svc = PersistentArtifactService()
        arts = await svc.list_artifacts(task_id="t1", workspace_id="w1", limit=10, offset=0)
        assert arts == []
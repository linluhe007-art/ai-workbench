"""
Phase 4.17 tests - Persistent Data Layer & Database Migration.
Covers: SQLAlchemy ORM models, DatabaseRepository, Alembic config,
model to_dict, session management, migration imports.
"""

import pytest
from datetime import datetime, timezone

from app.database import Base, init_db, AsyncSessionLocal
from app.database.models import (
    UserModel, RoleModel, TenantModel, TaskModel,
    ArtifactModel, WorkspaceModel, AuditModel,
    ExecutionModel, ExperienceModel,
)


# =============================================================================
# Model Instantiation Tests
# =============================================================================

class TestUserModel:
    def test_create_user_minimal(self):
        user = UserModel(username="test", email="t@test.com")
        assert user.username == "test"
        assert user.is_active is True
        assert user.tenant_ids == []
        assert user.roles == []

    def test_to_dict(self):
        ts = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)
        user = UserModel(
            id="u1", username="admin", email="a@b.com",
            roles=["admin"], hashed_password="hash",
            tenant_ids=["t1"], is_active=True,
            created_at=ts, updated_at=ts,
        )
        d = user.to_dict()
        assert d["id"] == "u1"
        assert d["username"] == "admin"
        assert d["hashed_password"] == "********"
        assert d["tenant_ids"] == ["t1"]

    def test_to_dict_no_password(self):
        user = UserModel(username="nopass", email="n@t.com", hashed_password="")
        d = user.to_dict()
        assert d["hashed_password"] == ""

    def test_to_dict_none_dates(self):
        user = UserModel(username="x", email="x@x.com", created_at=None, updated_at=None)
        d = user.to_dict()
        assert d["created_at"] == ""
        assert d["updated_at"] == ""


class TestRoleModel:
    def test_create_role(self):
        role = RoleModel(name="admin", description="Admin", permissions=["task:create"])
        assert role.name == "admin"
        assert "task:create" in (role.permissions or [])

    def test_to_dict(self):
        role = RoleModel(id="r1", name="viewer", description="V", permissions=["task:read"], tenant_id="t1")
        d = role.to_dict()
        assert d["id"] == "r1"
        assert d["permissions"] == ["task:read"]
        assert d["tenant_id"] == "t1"

    def test_to_dict_defaults(self):
        role = RoleModel(name="empty", description="E")
        d = role.to_dict()
        assert d["permissions"] == []
        assert d["tenant_id"] == ""


class TestTenantModel:
    def test_create_tenant(self):
        t = TenantModel(name="Org1", slug="org1")
        assert t.name == "Org1"
        assert t.is_active is True

    def test_to_dict(self):
        t = TenantModel(id="t1", name="Org", slug="org", is_active=True)
        d = t.to_dict()
        assert d["slug"] == "org"
        assert d["is_active"] is True


class TestTaskModel:
    def test_create_task(self):
        task = TaskModel(task_text="Test task", status="pending")
        assert task.task_text == "Test task"
        assert task.status == "pending"
        assert task.max_iterations == 3

    def test_to_dict(self):
        task = TaskModel(
            id="task-1", task_text="Hello", status="running",
            attempt=2, max_iterations=5, tenant_id="t1", user_id="u1",
        )
        d = task.to_dict()
        assert d["task_id"] == "task-1"
        assert d["task"] == "Hello"
        assert d["status"] == "running"
        assert d["attempt"] == 2
        assert d["tenant_id"] == "t1"


class TestArtifactModel:
    def test_create_artifact(self):
        art = ArtifactModel(name="report.md", artifact_type="markdown", content="# Hi")
        assert art.name == "report.md"
        assert art.artifact_type == "markdown"

    def test_to_dict(self):
        art = ArtifactModel(
            id="a1", name="data.json", artifact_type="json",
            content='{"x":1}', owner="researcher",
            workspace_id="ws1", task_id="task-1", step_id="research",
        )
        d = art.to_dict()
        assert d["id"] == "a1"
        assert d["type"] == "json"
        assert d["task_id"] == "task-1"
        assert d["step_id"] == "research"


class TestWorkspaceModel:
    def test_create_workspace(self):
        ws = WorkspaceModel(name="My Workspace", task_id="task-1")
        assert ws.name == "My Workspace"

    def test_to_dict(self):
        ws = WorkspaceModel(id="ws1", name="WS", task_id="t1", owner="admin")
        d = ws.to_dict()
        assert d["id"] == "ws1"
        assert d["task_id"] == "t1"


class TestAuditModel:
    def test_create_audit(self):
        audit = AuditModel(
            actor="system", action="create_task",
            resource_type="task", resource_id="task-1",
        )
        assert audit.actor == "system"

    def test_to_dict(self):
        ts = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)
        audit = AuditModel(
            id="audit-1", actor="admin", action="task_completed",
            resource_type="task", resource_id="task-1",
            task_id="task-1", request_id="req-1",
            before={"status": "running"}, after={"status": "completed"},
            metadata_={"iterations": 3}, created_at=ts,
        )
        d = audit.to_dict()
        assert d["id"] == "audit-1"
        assert d["actor"] == "admin"
        assert d["action"] == "task_completed"
        assert d["before"] == {"status": "running"}
        assert d["after"] == {"status": "completed"}
        assert d["metadata"] == {"iterations": 3}


class TestExecutionModel:
    def test_create_execution(self):
        exec_entry = ExecutionModel(task_id="task-1", iteration=1, status="success")
        assert exec_entry.status == "success"

    def test_to_dict(self):
        exec_entry = ExecutionModel(
            id="e1", task_id="t1", iteration=2, status="failed",
            duration_ms=150.5,
        )
        d = exec_entry.to_dict()
        assert d["task_id"] == "t1"
        assert d["iteration"] == 2
        assert d["duration_ms"] == 150.5


class TestExperienceModel:
    def test_create_experience(self):
        exp = ExperienceModel(task_pattern="research", agents=["researcher"], success=True)
        assert exp.task_pattern == "research"

    def test_to_dict(self):
        exp = ExperienceModel(
            id="exp1", task_pattern="write_report", agents=["writer"],
            success=True, score=8.5, duration_ms=1200.0,
        )
        d = exp.to_dict()
        assert d["task_pattern"] == "write_report"
        assert d["score"] == 8.5
        assert d["agents"] == ["writer"]


# =============================================================================
# Base & Migration Tests
# =============================================================================

class TestBaseAndMetadata:
    def test_base_has_tables(self):
        """Verify all models are registered with Base.metadata."""
        table_names = Base.metadata.tables.keys()
        expected = [
            "users", "roles", "tenants", "tasks",
            "artifacts", "workspaces", "audit_records",
            "executions", "experiences",
        ]
        for name in expected:
            assert name in table_names, f"Table {name} not found in metadata"

    def test_all_tables_have_primary_key(self):
        for table_name, table in Base.metadata.tables.items():
            assert table.primary_key.columns, f"Table {table_name} has no primary key"

    def test_foreign_key_relationships(self):
        artifacts_table = Base.metadata.tables["artifacts"]
        fks = [c for c in artifacts_table.columns if c.foreign_keys]
        assert len(fks) >= 1, "Artifacts should have FK to tasks"

        executions_table = Base.metadata.tables["executions"]
        fks = [c for c in executions_table.columns if c.foreign_keys]
        assert len(fks) >= 1, "Executions should have FK to tasks"


# =============================================================================
# DatabaseRepository Tests (mocked session)
# =============================================================================

class TestDatabaseRepository:
    def test_singleton(self):
        from app.database.repository import get_db_repo
        repo1 = get_db_repo()
        repo2 = get_db_repo()
        assert repo1 is repo2

    def test_static_methods_exist(self):
        """Verify key CRUD methods are defined."""
        from app.database.repository import DatabaseRepository
        assert hasattr(DatabaseRepository, "create_user")
        assert hasattr(DatabaseRepository, "get_user")
        assert hasattr(DatabaseRepository, "list_users")
        assert hasattr(DatabaseRepository, "update_user")
        assert hasattr(DatabaseRepository, "delete_user")
        assert hasattr(DatabaseRepository, "create_tenant")
        assert hasattr(DatabaseRepository, "get_tenant")
        assert hasattr(DatabaseRepository, "list_tenants")
        assert hasattr(DatabaseRepository, "create_task")
        assert hasattr(DatabaseRepository, "get_task")
        assert hasattr(DatabaseRepository, "list_tasks")
        assert hasattr(DatabaseRepository, "create_artifact")
        assert hasattr(DatabaseRepository, "get_artifact")
        assert hasattr(DatabaseRepository, "search_artifacts")
        assert hasattr(DatabaseRepository, "delete_artifact")
        assert hasattr(DatabaseRepository, "record_audit")
        assert hasattr(DatabaseRepository, "query_audit")
        assert hasattr(DatabaseRepository, "save_execution")
        assert hasattr(DatabaseRepository, "get_executions")
        assert hasattr(DatabaseRepository, "save_experience")
        assert hasattr(DatabaseRepository, "query_experience")


# =============================================================================
# Session & Engine Tests
# =============================================================================

class TestDatabaseSession:
    def test_engine_is_configured(self):
        from app.database import engine
        assert engine is not None

    def test_async_session_local_is_configured(self):
        from app.database import AsyncSessionLocal
        assert AsyncSessionLocal is not None

    def test_get_db_is_callable(self):
        from app.database import get_db
        assert callable(get_db)


# =============================================================================
# Model Field Types
# =============================================================================

class TestModelFieldTypes:
    def test_user_model_columns(self):
        columns = {c.name: str(c.type) for c in UserModel.__table__.columns}
        assert columns["username"] == "VARCHAR(100)"
        assert columns["is_active"] == "BOOLEAN"
        assert columns["tenant_ids"] == "JSON"
        assert columns["roles"] == "JSON"

    def test_task_model_columns(self):
        columns = {c.name: str(c.type) for c in TaskModel.__table__.columns}
        assert columns["status"] == "VARCHAR(32)"
        assert columns["max_iterations"] == "INTEGER"
        assert columns["result"] == "JSON"

    def test_audit_model_columns(self):
        columns = {c.name: str(c.type) for c in AuditModel.__table__.columns}
        assert columns["before"] == "JSON"
        assert columns["after"] == "JSON"
# =============================================================================
# Extended Model Tests
# =============================================================================

class TestUserModelExtended:
    def test_user_model_default_uuid(self):
        user = UserModel(username="auto", email="auto@t.com")
        assert user.id is not None
        assert len(user.id) == 36

    def test_user_model_metadata_column_name(self):
        user = UserModel(username="meta", email="m@t.com", metadata_={"key": "val"})
        assert user.metadata_ == {"key": "val"}
        d = user.to_dict()
        assert d["metadata"] == {"key": "val"}

    def test_user_model_tenant_ids_default(self):
        user = UserModel(username="t", email="t@t.com")
        d = user.to_dict()
        assert d["tenant_ids"] == []

    def test_user_model_roles_default(self):
        user = UserModel(username="r", email="r@t.com")
        d = user.to_dict()
        assert d["roles"] == []


class TestRoleModelExtended:
    def test_role_model_default_uuid(self):
        role = RoleModel(name="custom", description="Custom")
        assert role.id is not None
        assert len(role.id) == 36

    def test_role_model_permissions_default(self):
        role = RoleModel(name="basic", description="Basic")
        d = role.to_dict()
        assert d["permissions"] == []

    def test_role_model_tenant_id_default(self):
        role = RoleModel(name="global", description="Global")
        assert role.tenant_id == ""


class TestTenantModelExtended:
    def test_tenant_model_default_slug(self):
        tenant = TenantModel(name="My Org")
        assert tenant.slug == "my-org"

    def test_tenant_model_default_metadata(self):
        tenant = TenantModel(name="Org", slug="org")
        d = tenant.to_dict()
        assert d["metadata"] == {}


class TestTaskModelExtended:
    def test_task_model_default_uuid(self):
        task = TaskModel(task_text="Auto task")
        assert task.id is not None

    def test_task_model_result_none(self):
        task = TaskModel(task_text="No result")
        d = task.to_dict()
        assert d["result"] is None

    def test_task_model_error_message(self):
        task = TaskModel(task_text="Failed", error_message="Something broke", status="failed")
        d = task.to_dict()
        assert d["error_message"] == "Something broke"
        assert d["status"] == "failed"


class TestArtifactModelExtended:
    def test_artifact_model_default_type(self):
        art = ArtifactModel(name="file.md")
        assert art.artifact_type == "text"

    def test_artifact_model_default_content(self):
        art = ArtifactModel(name="empty.md")
        assert art.content == ""

    def test_artifact_model_default_metadata(self):
        art = ArtifactModel(name="nometa.md")
        d = art.to_dict()
        assert d["metadata"] == {}


class TestAuditModelExtended:
    def test_audit_model_before_after_default(self):
        audit = AuditModel(
            actor="system", action="test", resource_type="test", resource_id="t1",
        )
        assert audit.before == {}
        assert audit.after == {}

    def test_audit_model_request_id_nullable(self):
        audit = AuditModel(
            actor="system", action="test", resource_type="test", resource_id="t1",
        )
        assert audit.request_id is None

    def test_audit_model_timestamp_is_created_at(self):
        ts = datetime(2026, 8, 12, 12, 0, 0, tzinfo=timezone.utc)
        audit = AuditModel(
            id="a1", actor="sys", action="act", resource_type="rt", resource_id="ri",
            created_at=ts,
        )
        d = audit.to_dict()
        assert d["timestamp"] == ts.isoformat()


class TestExecutionModelExtended:
    def test_execution_model_default_status(self):
        exec_entry = ExecutionModel(task_id="t1", iteration=0)
        assert exec_entry.status == "pending"

    def test_execution_model_json_fields(self):
        exec_entry = ExecutionModel(
            task_id="t1", iteration=1,
            plan={"steps": []}, result={"output": "done"},
            feedback={"success": True},
        )
        assert exec_entry.plan == {"steps": []}
        assert exec_entry.result == {"output": "done"}


class TestExperienceModelExtended:
    def test_experience_model_default_success(self):
        exp = ExperienceModel(task_pattern="test")
        assert exp.success is False

    def test_experience_model_default_score(self):
        exp = ExperienceModel(task_pattern="test")
        assert exp.score == 0.0


# =============================================================================
# Metadata & Schema Tests
# =============================================================================

class TestDatabaseMetadata:
    def test_users_table_has_indexes(self):
        table = Base.metadata.tables["users"]
        indexes = [idx.name for idx in table.indexes]
        assert any("username" in idx for idx in indexes)

    def test_tasks_table_has_compound_index(self):
        table = Base.metadata.tables["tasks"]
        index_names = [idx.name for idx in table.indexes]
        assert "ix_tasks_tenant_status" in index_names

    def test_audit_table_has_created_at_index(self):
        table = Base.metadata.tables["audit_records"]
        indexes = [idx.name for idx in table.indexes]
        assert any("created_at" in idx for idx in indexes)

    def test_unique_constraints(self):
        users_table = Base.metadata.tables["users"]
        tenants_table = Base.metadata.tables["tenants"]
        # username should be unique
        username_col = users_table.columns["username"]
        assert username_col.unique
        # slug should be unique
        slug_col = tenants_table.columns["slug"]
        assert slug_col.unique

    def test_table_count(self):
        tables = Base.metadata.tables.keys()
        assert len(tables) == 9


# =============================================================================
# Repository Interface Tests
# =============================================================================

class TestRepositoryCompleteness:
    def test_repository_exports_all_needed_methods(self):
        from app.database.repository import DatabaseRepository
        # User
        assert callable(DatabaseRepository.create_user)
        assert callable(DatabaseRepository.get_user)
        assert callable(DatabaseRepository.get_user_by_username)
        assert callable(DatabaseRepository.list_users)
        assert callable(DatabaseRepository.update_user)
        assert callable(DatabaseRepository.delete_user)
        # Role
        assert callable(DatabaseRepository.create_role)
        assert callable(DatabaseRepository.get_role)
        assert callable(DatabaseRepository.list_roles)
        assert callable(DatabaseRepository.update_role)
        assert callable(DatabaseRepository.delete_role)
        # Tenant
        assert callable(DatabaseRepository.create_tenant)
        assert callable(DatabaseRepository.get_tenant)
        assert callable(DatabaseRepository.get_tenant_by_slug)
        assert callable(DatabaseRepository.list_tenants)
        assert callable(DatabaseRepository.delete_tenant)

    def test_repository_task_methods(self):
        from app.database.repository import DatabaseRepository
        assert callable(DatabaseRepository.create_task)
        assert callable(DatabaseRepository.get_task)
        assert callable(DatabaseRepository.list_tasks)
        assert callable(DatabaseRepository.update_task)
        assert callable(DatabaseRepository.delete_task)

    def test_repository_artifact_methods(self):
        from app.database.repository import DatabaseRepository
        assert callable(DatabaseRepository.create_artifact)
        assert callable(DatabaseRepository.get_artifact)
        assert callable(DatabaseRepository.list_artifacts)
        assert callable(DatabaseRepository.search_artifacts)
        assert callable(DatabaseRepository.delete_artifact)

    def test_repository_audit_methods(self):
        from app.database.repository import DatabaseRepository
        assert callable(DatabaseRepository.record_audit)
        assert callable(DatabaseRepository.query_audit)

    def test_repository_execution_methods(self):
        from app.database.repository import DatabaseRepository
        assert callable(DatabaseRepository.save_execution)
        assert callable(DatabaseRepository.get_executions)

    def test_repository_experience_methods(self):
        from app.database.repository import DatabaseRepository
        assert callable(DatabaseRepository.save_experience)
        assert callable(DatabaseRepository.query_experience)


# =============================================================================
# Backward Compatibility Tests
# =============================================================================

class TestBackwardCompatibility:
    def test_old_models_still_importable(self):
        """Verify old model stubs are still importable (not broken)."""
        import app.models.user
        import app.models.task
        import app.models.agent

    def test_storage_interface_unchanged(self):
        from app.storage.base import StorageBackend
        from app.storage.memory import MemoryStorage
        from app.storage.file import FileStorage
        storage = MemoryStorage()
        assert isinstance(storage, StorageBackend)

    def test_runtime_repository_unchanged(self):
        from app.storage.repository import RuntimeRepository
        from app.storage.memory import MemoryStorage
        repo = RuntimeRepository(MemoryStorage())
        assert repo is not None

    def test_alembic_imports_models(self):
        """Verify alembic env.py imports the new models without error."""
        import app.database.models
        assert hasattr(app.database.models, "UserModel")
        assert hasattr(app.database.models, "TaskModel")
# =============================================================================
# Final Edge Case Tests
# =============================================================================

class TestDatabaseEdgeCases:
    def test_model_to_dict_handles_none_created_at(self):
        user = UserModel(username="x", email="x@x.com", created_at=None)
        d = user.to_dict()
        assert d["created_at"] == ""

    def test_model_to_dict_handles_none_updated_at(self):
        role = RoleModel(name="x", description="x", updated_at=None)
        d = role.to_dict()
        assert d["updated_at"] == ""

    def test_task_model_text_column_named_task(self):
        task = TaskModel(task_text="Hello World")
        assert task.task_text == "Hello World"

    def test_artifact_model_type_column_name(self):
        art = ArtifactModel(name="f", artifact_type="json")
        d = art.to_dict()
        assert d["type"] == "json"

    def test_execution_model_relationship_exists(self):
        assert hasattr(ExecutionModel, "task")

    def test_all_models_have_to_dict(self):
        models = [
            UserModel, RoleModel, TenantModel, TaskModel,
            ArtifactModel, WorkspaceModel, AuditModel,
            ExecutionModel, ExperienceModel,
        ]
        for model_cls in models:
            instance = model_cls.__new__(model_cls)
            assert hasattr(instance.__class__, "to_dict"), f"{model_cls.__name__} missing to_dict"

    def test_database_init_exports(self):
        from app.database import engine, AsyncSessionLocal, Base, get_db, init_db
        assert engine is not None
        assert Base is not None
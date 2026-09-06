"""
DatabaseRepository - SQLAlchemy async repository for persistent data layer.
Phase 4.17: Mirrors in-memory services with PostgreSQL-backed implementations.

Provides CRUD operations for: User, Role, Tenant, Task, Artifact, Workspace, Audit, Execution.
Compatible with existing StorageBackend interface pattern.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.database.models import (
    UserModel,
    RoleModel,
    TenantModel,
    TaskModel,
    ArtifactModel,
    WorkspaceModel,
    AuditModel,
    ExecutionModel,
    ExperienceModel,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseRepository:
    """Async repository backed by PostgreSQL via SQLAlchemy 2.0."""

    # ── User ──────────────────────────────────────────────

    @staticmethod
    async def create_user(data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            user = UserModel(**{k: v for k, v in data.items() if k != "metadata"})
            if "metadata" in data:
                user.metadata_ = data["metadata"]
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user.to_dict()

    @staticmethod
    async def get_user(user_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalar_one_or_none()
            return user.to_dict() if user else None

    @staticmethod
    async def get_user_by_username(username: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.username == username)
            )
            user = result.scalar_one_or_none()
            return user.to_dict() if user else None

    @staticmethod
    async def list_users(tenant_id: str = "") -> list[dict]:
        async with AsyncSessionLocal() as session:
            stmt = select(UserModel)
            if tenant_id:
                stmt = stmt.where(UserModel.tenant_ids.contains([tenant_id]))
            result = await session.execute(stmt)
            return [u.to_dict() for u in result.scalars().all()]

    @staticmethod
    async def update_user(user_id: str, data: dict) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                return None
            for key, value in data.items():
                if key == "metadata":
                    user.metadata_ = value
                elif hasattr(user, key):
                    setattr(user, key, value)
            user.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(user)
            return user.to_dict()

    @staticmethod
    async def delete_user(user_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(UserModel).where(UserModel.id == user_id)
            )
            await session.commit()
            return result.rowcount > 0

    # ── Role ──────────────────────────────────────────────

    @staticmethod
    async def create_role(data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            role = RoleModel(**data)
            session.add(role)
            await session.commit()
            await session.refresh(role)
            return role.to_dict()

    @staticmethod
    async def get_role(role_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(RoleModel).where(RoleModel.id == role_id))
            role = result.scalar_one_or_none()
            return role.to_dict() if role else None

    @staticmethod
    async def list_roles(tenant_id: str = "") -> list[dict]:
        async with AsyncSessionLocal() as session:
            stmt = select(RoleModel)
            if tenant_id:
                stmt = stmt.where(
                    or_(RoleModel.tenant_id == tenant_id, RoleModel.tenant_id == "")
                )
            result = await session.execute(stmt)
            return [r.to_dict() for r in result.scalars().all()]

    @staticmethod
    async def update_role(role_id: str, data: dict) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(RoleModel).where(RoleModel.id == role_id))
            role = result.scalar_one_or_none()
            if role is None:
                return None
            for key, value in data.items():
                if hasattr(role, key):
                    setattr(role, key, value)
            role.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(role)
            return role.to_dict()

    @staticmethod
    async def delete_role(role_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(RoleModel).where(RoleModel.id == role_id)
            )
            await session.commit()
            return result.rowcount > 0

    # ── Tenant ────────────────────────────────────────────

    @staticmethod
    async def create_tenant(data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            tenant = TenantModel(
                name=data["name"],
                slug=data.get("slug", data["name"].lower().replace(" ", "-")),
            )
            if "metadata" in data:
                tenant.metadata_ = data["metadata"]
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            return tenant.to_dict()

    @staticmethod
    async def get_tenant(tenant_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TenantModel).where(TenantModel.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            return tenant.to_dict() if tenant else None

    @staticmethod
    async def get_tenant_by_slug(slug: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TenantModel).where(TenantModel.slug == slug)
            )
            tenant = result.scalar_one_or_none()
            return tenant.to_dict() if tenant else None

    @staticmethod
    async def list_tenants() -> list[dict]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(TenantModel))
            return [t.to_dict() for t in result.scalars().all()]

    @staticmethod
    async def delete_tenant(tenant_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(TenantModel).where(TenantModel.id == tenant_id)
            )
            await session.commit()
            return result.rowcount > 0

    # ── Task ──────────────────────────────────────────────

    @staticmethod
    async def create_task(data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            task = TaskModel(
                id=data.get("task_id", data.get("id", "")),
                task_text=data.get("task", ""),
                status=data.get("status", "pending"),
                max_iterations=data.get("max_iterations", 3),
                tenant_id=data.get("tenant_id", ""),
                user_id=data.get("user_id", ""),
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task.to_dict()

    @staticmethod
    async def get_task(task_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TaskModel).where(TaskModel.id == task_id)
            )
            task = result.scalar_one_or_none()
            return task.to_dict() if task else None

    @staticmethod
    async def list_tasks(tenant_id: str = "") -> list[dict]:
        async with AsyncSessionLocal() as session:
            stmt = select(TaskModel)
            if tenant_id:
                stmt = stmt.where(TaskModel.tenant_id == tenant_id)
            result = await session.execute(stmt.order_by(TaskModel.created_at.desc()))
            return [t.to_dict() for t in result.scalars().all()]

    @staticmethod
    async def update_task(task_id: str, data: dict) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TaskModel).where(TaskModel.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task is None:
                return None
            for key, value in data.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(task)
            return task.to_dict()

    @staticmethod
    async def delete_task(task_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(TaskModel).where(TaskModel.id == task_id)
            )
            await session.commit()
            return result.rowcount > 0

    # ── Artifact ──────────────────────────────────────────

    @staticmethod
    async def create_artifact(data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            artifact = ArtifactModel(
                name=data.get("name", ""),
                artifact_type=data.get("type", "text"),
                content=data.get("content", ""),
                owner=data.get("owner", ""),
                workspace_id=data.get("workspace_id", data.get("task_id", "")),
                task_id=data.get("task_id"),
                step_id=data.get("step_id", ""),
            )
            if "metadata" in data:
                artifact.metadata_ = data["metadata"]
            session.add(artifact)
            await session.commit()
            await session.refresh(artifact)
            return artifact.to_dict()

    @staticmethod
    async def get_artifact(artifact_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ArtifactModel).where(ArtifactModel.id == artifact_id)
            )
            art = result.scalar_one_or_none()
            return art.to_dict() if art else None

    @staticmethod
    async def list_artifacts(
        task_id: str = "", workspace_id: str = "", limit: int = 50, offset: int = 0,
    ) -> list[dict]:
        async with AsyncSessionLocal() as session:
            stmt = select(ArtifactModel)
            if task_id:
                stmt = stmt.where(ArtifactModel.task_id == task_id)
            if workspace_id:
                stmt = stmt.where(ArtifactModel.workspace_id == workspace_id)
            stmt = stmt.order_by(ArtifactModel.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return [a.to_dict() for a in result.scalars().all()]

    @staticmethod
    async def search_artifacts(
        query: str = "",
        artifact_type: str = "",
        owner: str = "",
        task_id: str = "",
        workspace_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        async with AsyncSessionLocal() as session:
            stmt = select(ArtifactModel)
            count_stmt = select(func.count(ArtifactModel.id))

            conditions = []
            if query:
                pattern = f"%{query}%"
                conditions.append(
                    or_(
                        ArtifactModel.name.ilike(pattern),
                        ArtifactModel.content.ilike(pattern),
                    )
                )
            if artifact_type:
                conditions.append(ArtifactModel.artifact_type == artifact_type)
            if owner:
                conditions.append(ArtifactModel.owner == owner)
            if task_id:
                conditions.append(ArtifactModel.task_id == task_id)
            if workspace_id:
                conditions.append(ArtifactModel.workspace_id == workspace_id)

            if conditions:
                stmt = stmt.where(and_(*conditions))
                count_stmt = count_stmt.where(and_(*conditions))

            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0

            stmt = stmt.order_by(ArtifactModel.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return [a.to_dict() for a in result.scalars().all()], total

    @staticmethod
    async def delete_artifact(artifact_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(ArtifactModel).where(ArtifactModel.id == artifact_id)
            )
            await session.commit()
            return result.rowcount > 0

    # ── Workspace ─────────────────────────────────────────

    @staticmethod
    async def create_workspace(data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            ws = WorkspaceModel(
                name=data.get("name", ""),
                task_id=data.get("task_id"),
                owner=data.get("owner", ""),
            )
            if "metadata" in data:
                ws.metadata_ = data["metadata"]
            session.add(ws)
            await session.commit()
            await session.refresh(ws)
            return ws.to_dict()

    @staticmethod
    async def get_workspace(workspace_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WorkspaceModel).where(WorkspaceModel.id == workspace_id)
            )
            ws = result.scalar_one_or_none()
            return ws.to_dict() if ws else None

    @staticmethod
    async def list_workspaces(tenant_id: str = "") -> list[dict]:
        async with AsyncSessionLocal() as session:
            stmt = select(WorkspaceModel).order_by(WorkspaceModel.created_at.desc())
            result = await session.execute(stmt)
            return [w.to_dict() for w in result.scalars().all()]

    # ── Audit ─────────────────────────────────────────────

    @staticmethod
    async def record_audit(data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            record = AuditModel(
                actor=data["actor"],
                action=data["action"],
                resource_type=data["resource_type"],
                resource_id=data["resource_id"],
                task_id=data.get("task_id"),
                request_id=data.get("request_id"),
            )
            if "before" in data:
                record.before = data["before"]
            if "after" in data:
                record.after = data["after"]
            if "metadata" in data:
                record.metadata_ = data["metadata"]
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record.to_dict()

    @staticmethod
    async def query_audit(
        task_id: str = "",
        actor: str = "",
        action: str = "",
        resource_type: str = "",
        resource_id: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        async with AsyncSessionLocal() as session:
            stmt = select(AuditModel)
            count_stmt = select(func.count(AuditModel.id))
            conditions = []
            if task_id:
                conditions.append(AuditModel.task_id == task_id)
            if actor:
                conditions.append(AuditModel.actor == actor)
            if action:
                conditions.append(AuditModel.action == action)
            if resource_type:
                conditions.append(AuditModel.resource_type == resource_type)
            if resource_id:
                conditions.append(AuditModel.resource_id == resource_id)
            if conditions:
                stmt = stmt.where(and_(*conditions))
                count_stmt = count_stmt.where(and_(*conditions))

            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0
            stmt = stmt.order_by(AuditModel.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return [a.to_dict() for a in result.scalars().all()], total

    # ── Execution ─────────────────────────────────────────

    @staticmethod
    async def save_execution(data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            exec_entry = ExecutionModel(
                task_id=data["task_id"],
                iteration=data.get("iteration", 0),
                status=data.get("status", "pending"),
                plan=data.get("plan"),
                result=data.get("result"),
                feedback=data.get("feedback"),
                duration_ms=data.get("duration_ms", 0.0),
            )
            session.add(exec_entry)
            await session.commit()
            await session.refresh(exec_entry)
            return exec_entry.to_dict()

    @staticmethod
    async def get_executions(task_id: str) -> list[dict]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ExecutionModel)
                .where(ExecutionModel.task_id == task_id)
                .order_by(ExecutionModel.iteration.asc())
            )
            return [e.to_dict() for e in result.scalars().all()]

    # ── Experience ────────────────────────────────────────

    @staticmethod
    async def save_experience(data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            exp = ExperienceModel(
                task_pattern=data["task_pattern"],
                agents=data.get("agents", []),
                success=data.get("success", False),
                score=data.get("score", 0.0),
                duration_ms=data.get("duration_ms", 0.0),
            )
            if "metadata" in data:
                exp.metadata_ = data["metadata"]
            session.add(exp)
            await session.commit()
            await session.refresh(exp)
            return exp.to_dict()

    @staticmethod
    async def query_experience(task_pattern: str = "", limit: int = 10) -> list[dict]:
        async with AsyncSessionLocal() as session:
            stmt = select(ExperienceModel).order_by(ExperienceModel.created_at.desc())
            if task_pattern:
                stmt = stmt.where(ExperienceModel.task_pattern.ilike(f"%{task_pattern}%"))
            stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return [e.to_dict() for e in result.scalars().all()]


# Singleton
_repo: DatabaseRepository | None = None


def get_db_repo() -> DatabaseRepository:
    global _repo
    if _repo is None:
        _repo = DatabaseRepository()
    return _repo
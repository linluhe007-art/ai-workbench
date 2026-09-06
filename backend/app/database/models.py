"""
SQLAlchemy ORM models for persistent data layer.
Phase 4.17: Mirrors auth/service dataclass models as database tables.

Uses SQLAlchemy 2.0 async declarative base.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Float,
    Table,
    Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


# ── User ──────────────────────────────────────────────────

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=new_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), nullable=False)
    hashed_password = Column(String(256), default="")
    is_active = Column(Boolean, default=True)
    tenant_ids = Column(JSON, default=list)
    roles = Column(JSON, default=list)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "hashed_password": "********" if self.hashed_password else "",
            "is_active": self.is_active,
            "tenant_ids": self.tenant_ids or [],
            "roles": self.roles or [],
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


# ── Role ──────────────────────────────────────────────────

class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(String(64), primary_key=True, default=new_uuid)
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), default="")
    permissions = Column(JSON, default=list)
    tenant_id = Column(String(64), default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions or [],
            "tenant_id": self.tenant_id or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


# ── Tenant ────────────────────────────────────────────────

class TenantModel(Base):
    __tablename__ = "tenants"

    id = Column(String(64), primary_key=True, default=new_uuid)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "is_active": self.is_active,
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


# ── Task ──────────────────────────────────────────────────

class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True, default=new_uuid)
    task_text = Column("task", Text, nullable=False)
    status = Column(String(32), default="pending", index=True)
    attempt = Column(Integer, default=0)
    max_iterations = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    tenant_id = Column(String(64), default="", index=True)
    user_id = Column(String(64), default="")
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_tasks_tenant_status", "tenant_id", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "task_id": self.id,
            "task": self.task_text,
            "status": self.status,
            "attempt": self.attempt,
            "max_iterations": self.max_iterations,
            "error_message": self.error_message,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


# ── Artifact ──────────────────────────────────────────────

class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id = Column(String(64), primary_key=True, default=new_uuid)
    name = Column(String(300), nullable=False)
    artifact_type = Column("type", String(50), default="text", index=True)
    content = Column(Text, default="")
    owner = Column(String(64), default="")
    workspace_id = Column(String(64), default="", index=True)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    step_id = Column(String(64), default="")
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.artifact_type,
            "content": self.content,
            "owner": self.owner,
            "workspace_id": self.workspace_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


# ── Workspace ─────────────────────────────────────────────

class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True, default=new_uuid)
    name = Column(String(200), default="")
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    owner = Column(String(64), default="")
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "task_id": self.task_id,
            "owner": self.owner,
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


# ── Audit ─────────────────────────────────────────────────

class AuditModel(Base):
    __tablename__ = "audit_records"

    id = Column(String(64), primary_key=True, default=new_uuid)
    actor = Column(String(128), nullable=False, index=True)
    action = Column(String(128), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(String(128), nullable=False)
    task_id = Column(String(64), nullable=True, index=True)
    request_id = Column(String(128), nullable=True)
    before = Column(JSON, default=dict)
    after = Column(JSON, default=dict)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.created_at.isoformat() if self.created_at else "",
            "actor": self.actor,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "task_id": self.task_id,
            "request_id": self.request_id,
            "before": self.before or {},
            "after": self.after or {},
            "metadata": self.metadata_ or {},
        }


# ── Execution History ─────────────────────────────────────

class ExecutionModel(Base):
    __tablename__ = "executions"

    id = Column(String(64), primary_key=True, default=new_uuid)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    iteration = Column(Integer, default=0)
    status = Column(String(32), default="pending")
    plan = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    feedback = Column(JSON, nullable=True)
    duration_ms = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    task = relationship("TaskModel", backref="executions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "iteration": self.iteration,
            "status": self.status,
            "plan": self.plan,
            "result": self.result,
            "feedback": self.feedback,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


# ── Experience ────────────────────────────────────────────

class ExperienceModel(Base):
    __tablename__ = "experiences"

    id = Column(String(64), primary_key=True, default=new_uuid)
    task_pattern = Column(String(300), nullable=False, index=True)
    agents = Column(JSON, default=list)
    success = Column(Boolean, default=False)
    score = Column(Float, default=0.0)
    duration_ms = Column(Float, default=0.0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_pattern": self.task_pattern,
            "agents": self.agents or [],
            "success": self.success,
            "score": self.score,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


# ���� Command ������������������������������������������������������������������������������������������������������������������������������������

class CommandModel(Base):
    __tablename__ = "commands"

    id = Column(String(64), primary_key=True, default=new_uuid)
    user_id = Column(String(64), default="", index=True)
    prompt = Column(Text, nullable=False)
    intent = Column(JSON, default=dict)
    task_id = Column(String(64), default="", index=True)
    classification = Column(JSON, default=dict)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "prompt": self.prompt,
            "intent": self.intent or {},
            "task_id": self.task_id,
            "classification": self.classification or {},
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }



# ���� Memory ������������������������������������������������������������������������������������������������������������������������������������

class MemoryModel(Base):
    __tablename__ = "memories"

    id = Column(String(64), primary_key=True, default=new_uuid)
    user_id = Column(String(64), default="", index=True)
    memory_type = Column(String(32), nullable=False, index=True)
    content = Column(Text, nullable=False)
    importance = Column(Float, default=0.5)
    embedding_id = Column(String(128), default="")
    tags = Column(JSON, default=list)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "importance": self.importance,
            "embedding_id": self.embedding_id,
            "tags": self.tags or [],
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }




# ── Knowledge Documents ──────────────────────────────────────────────────────

class ImprovementRecordModel(Base):
    """Phase 5.8 - Self Improvement records."""
    __tablename__ = "improvement_records"

    id = Column(String(64), primary_key=True, default=new_uuid)
    recommendation_id = Column(String(64), default="", index=True)
    category = Column(String(64), default="")
    title = Column(String(300), default="")
    action = Column(JSON, default=dict)
    status = Column(String(32), default="applied")
    applied_at = Column(DateTime(timezone=True), default=utcnow)
    result = Column(JSON, default=dict)
    user_id = Column(String(64), default="", index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recommendation_id": self.recommendation_id,
            "category": self.category,
            "title": self.title,
            "action": self.action or {},
            "status": self.status,
            "applied_at": self.applied_at.isoformat() if self.applied_at else "",
            "result": self.result or {},
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class KnowledgeDocumentModel(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(64), primary_key=True, default=new_uuid)
    title = Column(String(300), nullable=False, index=True)
    doc_type = Column(String(32), nullable=False, index=True)
    content = Column(Text, nullable=False)
    filename = Column(String(300), default="")
    source_url = Column(String(500), default="")
    tags = Column(JSON, default=list)
    summary = Column(Text, default="")
    metadata_ = Column("metadata", JSON, default=dict)
    chunk_count = Column(Integer, default=0)
    user_id = Column(String(64), default="", index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "doc_type": self.doc_type,
            "filename": self.filename, "source_url": self.source_url,
            "tags": self.tags or [], "summary": self.summary,
            "metadata": self.metadata_ or {}, "chunk_count": self.chunk_count,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(64), primary_key=True, default=new_uuid)
    document_id = Column(String(64), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    document = relationship("KnowledgeDocumentModel", backref="chunks")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "document_id": self.document_id,
            "chunk_index": self.chunk_index, "content": self.content,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }




# ── Automation ──────────────────────────────────────────────────────────────

class AutomationModel(Base):
    __tablename__ = "automations"

    id = Column(String(64), primary_key=True, default=new_uuid)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, default="")
    trigger = Column(JSON, default=dict)
    action = Column(JSON, default=dict)
    status = Column(String(32), default="active")
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, default=0)
    user_id = Column(String(64), default="", index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "trigger": self.trigger or {}, "action": self.action or {},
            "status": self.status, "last_run_at": self.last_run_at.isoformat() if self.last_run_at else "",
            "run_count": self.run_count, "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }

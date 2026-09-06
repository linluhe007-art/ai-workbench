"""initial schema

Revision ID: 001
Revises: None
Create Date: 2026-08-12

Phase 4.20: Production-ready initial migration.
Creates all core tables: users, roles, tenants, tasks,
artifacts, workspaces, audit_records, executions, experiences.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(256), default=""),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("tenant_ids", sa.JSON(), default=list),
        sa.Column("roles", sa.JSON(), default=list),
        sa.Column("metadata", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # Roles
    op.create_table(
        "roles",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, index=True),
        sa.Column("description", sa.String(500), default=""),
        sa.Column("permissions", sa.JSON(), default=list),
        sa.Column("tenant_id", sa.String(64), default=""),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), unique=True, nullable=False, index=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("metadata", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # Tasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("task", sa.Text(), default=""),
        sa.Column("status", sa.String(32), default="pending", index=True),
        sa.Column("tenant_id", sa.String(64), default="", index=True),
        sa.Column("user_id", sa.String(64), default=""),
        sa.Column("max_iterations", sa.Integer(), default=3),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("attempt", sa.Integer(), default=0),
        sa.Column("error_message", sa.Text(), default=""),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # Artifacts
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(300), default=""),
        sa.Column("type", sa.String(50), default="text", index=True),
        sa.Column("content", sa.Text(), default=""),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("workspace_id", sa.String(64), nullable=True),
        sa.Column("tenant_id", sa.String(64), default="", index=True),
        sa.Column("agent_id", sa.String(64), default=""),
        sa.Column("step_id", sa.String(64), default=""),
        sa.Column("metadata", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # Workspaces
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), default=""),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("owner", sa.String(64), default=""),
        sa.Column("tenant_id", sa.String(64), default=""),
        sa.Column("metadata", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # Audit Records
    op.create_table(
        "audit_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("actor", sa.String(128), nullable=False, index=True),
        sa.Column("action", sa.String(128), nullable=False, index=True),
        sa.Column("resource_type", sa.String(64), nullable=False, index=True),
        sa.Column("resource_id", sa.String(128), nullable=False),
        sa.Column("task_id", sa.String(64), nullable=True, index=True),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("tenant_id", sa.String(64), default="", index=True),
        sa.Column("before", sa.JSON(), default=dict),
        sa.Column("after", sa.JSON(), default=dict),
        sa.Column("metadata", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), index=True),
    )

    # Executions
    op.create_table(
        "executions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("iteration", sa.Integer(), default=0),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("plan", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("feedback", sa.JSON(), nullable=True),
        sa.Column("duration_ms", sa.Float(), default=0.0),
        sa.Column("tenant_id", sa.String(64), default=""),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # Experiences
    op.create_table(
        "experiences",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("task_pattern", sa.String(300), nullable=False, index=True),
        sa.Column("agents", sa.JSON(), default=list),
        sa.Column("success", sa.Boolean(), default=False),
        sa.Column("score", sa.Float(), default=0.0),
        sa.Column("duration_ms", sa.Float(), default=0.0),
        sa.Column("tenant_id", sa.String(64), default=""),
        sa.Column("metadata", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # Create composite indexes for common queries
    op.create_index("idx_tasks_tenant_status", "tasks", ["tenant_id", "status"])
    op.create_index("idx_artifacts_tenant_type", "artifacts", ["tenant_id", "type"])
    op.create_index("idx_audit_tenant_actor", "audit_records", ["tenant_id", "actor"])
    op.create_index("idx_audit_task_action", "audit_records", ["task_id", "action"])


def downgrade() -> None:
    op.drop_table("experiences")
    op.drop_table("executions")
    op.drop_table("audit_records")
    op.drop_table("workspaces")
    op.drop_table("artifacts")
    op.drop_table("tasks")
    op.drop_table("tenants")
    op.drop_table("roles")
    op.drop_table("users")

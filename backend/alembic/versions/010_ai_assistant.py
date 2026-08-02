"""AI Assistant tables

Revision ID: 010
Revises: 009
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="openai"),
        sa.Column("base_url", sa.String(500), nullable=False, server_default="https://api.openai.com/v1"),
        sa.Column("model_name", sa.String(100), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("embedding_model", sa.String(100), nullable=False, server_default="text-embedding-3-small"),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("tenant_id", name="uq_ai_configs_tenant"),
    )
    op.create_index("ix_ai_configs_tenant_id", "ai_configs", ["tenant_id"])

    op.create_table(
        "ai_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_ai_documents_tenant_id", "ai_documents", ["tenant_id"])

    op.create_table(
        "ai_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_ai_chunks_tenant_id", "ai_chunks", ["tenant_id"])
    op.create_index("ix_ai_chunks_document_id", "ai_chunks", ["document_id"])

    op.create_table(
        "ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default="New chat"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_ai_conversations_tenant_id", "ai_conversations", ["tenant_id"])
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])

    op.create_table(
        "ai_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
    op.drop_table("ai_chunks")
    op.drop_table("ai_documents")
    op.drop_table("ai_configs")

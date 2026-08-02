"""AI Assistant — tenant LLM config, knowledge docs, chat history."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.platform import TenantScopedMixin


class AiConfig(Base, TenantScopedMixin):
    """Per-tenant LLM settings (API key stored encrypted)."""

    __tablename__ = "ai_configs"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_ai_configs_tenant"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), default="groq", nullable=False)
    base_url: Mapped[str] = mapped_column(
        String(500), default="https://api.groq.com/openai/v1", nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), default="llama-3.3-70b-versatile", nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), default="local", nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AiDocument(Base, TenantScopedMixin):
    """Knowledge document (policy text or synced HR data)."""

    __tablename__ = "ai_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    chunks: Mapped[list["AiChunk"]] = relationship(
        "AiChunk", back_populates="document", cascade="all, delete-orphan"
    )


class AiChunk(Base, TenantScopedMixin):
    """Embedded text chunk for RAG retrieval (embedding stored as float JSON array)."""

    __tablename__ = "ai_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    document: Mapped["AiDocument"] = relationship("AiDocument", back_populates="chunks")


class AiConversation(Base, TenantScopedMixin):
    __tablename__ = "ai_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="New chat", nullable=False)

    messages: Mapped[list["AiMessage"]] = relationship(
        "AiMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AiMessage.created_at",
    )


class AiMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["AiConversation"] = relationship("AiConversation", back_populates="messages")

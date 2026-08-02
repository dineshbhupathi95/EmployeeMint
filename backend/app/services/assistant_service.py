"""Company AI Assistant — config, ingest, RAG chat."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.crypto import decrypt_secret, encrypt_secret, mask_api_key
from app.models import (
    AiChunk,
    AiConfig,
    AiConversation,
    AiDocument,
    AiMessage,
    Announcement,
    Employee,
    Holiday,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
)
from app.services.llm_client import (
    chat_completion,
    chunk_text,
    cosine_similarity,
    embed_texts,
    keyword_score,
)


class AssistantService:
    async def get_or_create_config(self, db: AsyncSession, tenant_id: uuid.UUID) -> AiConfig:
        result = await db.execute(
            select(AiConfig).where(AiConfig.tenant_id == tenant_id, AiConfig.is_deleted.is_(False))
        )
        cfg = result.scalar_one_or_none()
        if cfg:
            return cfg
        cfg = AiConfig(tenant_id=tenant_id)
        db.add(cfg)
        await db.flush()
        return cfg

    def config_public(self, cfg: AiConfig) -> dict:
        plain = None
        if cfg.api_key_encrypted:
            try:
                plain = decrypt_secret(cfg.api_key_encrypted)
            except ValueError:
                plain = None
        return {
            "provider": cfg.provider,
            "base_url": cfg.base_url,
            "model_name": cfg.model_name,
            "embedding_model": cfg.embedding_model,
            "is_enabled": cfg.is_enabled,
            "has_api_key": bool(cfg.api_key_encrypted),
            "api_key_masked": mask_api_key(plain),
        }

    async def update_config(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        provider: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        embedding_model: str | None = None,
        api_key: str | None = None,
        is_enabled: bool | None = None,
    ) -> AiConfig:
        cfg = await self.get_or_create_config(db, tenant_id)
        if provider is not None:
            cfg.provider = provider
        if base_url is not None:
            cfg.base_url = base_url.rstrip("/")
        if model_name is not None:
            cfg.model_name = model_name
        if embedding_model is not None:
            cfg.embedding_model = embedding_model
        if api_key is not None and api_key.strip() and not api_key.startswith("••••") and "…" not in api_key:
            cfg.api_key_encrypted = encrypt_secret(api_key.strip())
        if is_enabled is not None:
            cfg.is_enabled = is_enabled
        # Auto-enable when a key is present and caller didn't explicitly disable
        if cfg.api_key_encrypted and is_enabled is None:
            cfg.is_enabled = True
        if cfg.api_key_encrypted and is_enabled is True:
            cfg.is_enabled = True
        await db.flush()
        return cfg

    def _require_key(self, cfg: AiConfig) -> str:
        if not cfg.api_key_encrypted:
            raise ValueError("API key is not configured. Set it in Settings → AI Assistant.")
        return decrypt_secret(cfg.api_key_encrypted)

    async def test_connection(self, db: AsyncSession, tenant_id: uuid.UUID) -> dict:
        cfg = await self.get_or_create_config(db, tenant_id)
        key = self._require_key(cfg)
        reply = await chat_completion(
            api_key=key,
            base_url=cfg.base_url,
            model=cfg.model_name,
            messages=[
                {"role": "system", "content": "Reply with exactly: OK"},
                {"role": "user", "content": "ping"},
            ],
        )
        return {"ok": True, "reply": reply[:200]}

    async def list_documents(self, db: AsyncSession, tenant_id: uuid.UUID) -> list[AiDocument]:
        result = await db.execute(
            select(AiDocument)
            .where(AiDocument.tenant_id == tenant_id, AiDocument.is_deleted.is_(False))
            .order_by(AiDocument.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create_document(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        title: str,
        content: str,
        source_type: str = "manual",
    ) -> AiDocument:
        doc = AiDocument(
            tenant_id=tenant_id,
            title=title.strip(),
            content=content.strip(),
            source_type=source_type,
            status="pending",
        )
        db.add(doc)
        await db.flush()
        await self.reindex_document(db, tenant_id, doc.id)
        return doc

    async def delete_document(self, db: AsyncSession, tenant_id: uuid.UUID, doc_id: uuid.UUID) -> None:
        result = await db.execute(
            select(AiDocument).where(
                AiDocument.id == doc_id,
                AiDocument.tenant_id == tenant_id,
                AiDocument.is_deleted.is_(False),
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError("Document not found")
        doc.is_deleted = True
        await db.execute(delete(AiChunk).where(AiChunk.document_id == doc_id))

    def _uses_local_rag(self, cfg: AiConfig) -> bool:
        emb = (cfg.embedding_model or "").strip().lower()
        return cfg.provider in ("groq",) or emb in ("local", "none", "keyword", "")

    async def reindex_document(
        self, db: AsyncSession, tenant_id: uuid.UUID, doc_id: uuid.UUID
    ) -> AiDocument:
        cfg = await self.get_or_create_config(db, tenant_id)

        result = await db.execute(
            select(AiDocument).where(
                AiDocument.id == doc_id,
                AiDocument.tenant_id == tenant_id,
                AiDocument.is_deleted.is_(False),
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError("Document not found")

        await db.execute(delete(AiChunk).where(AiChunk.document_id == doc.id))
        pieces = chunk_text(doc.content)
        if not pieces:
            doc.status = "empty"
            doc.chunk_count = 0
            await db.flush()
            return doc

        if self._uses_local_rag(cfg):
            embeddings: list[list[float]] = [[] for _ in pieces]
        else:
            key = self._require_key(cfg)
            embeddings = await embed_texts(
                api_key=key,
                base_url=cfg.base_url,
                model=cfg.embedding_model,
                texts=pieces,
            )
        for i, (text, emb) in enumerate(zip(pieces, embeddings)):
            db.add(
                AiChunk(
                    tenant_id=tenant_id,
                    document_id=doc.id,
                    content=text,
                    embedding=emb,
                    chunk_index=i,
                    meta={"title": doc.title, "source_type": doc.source_type},
                )
            )
        doc.chunk_count = len(pieces)
        doc.status = "indexed"
        await db.flush()
        return doc

    async def sync_company_data(self, db: AsyncSession, tenant_id: uuid.UUID) -> dict:
        """Rebuild synced knowledge docs from holidays, leave types, announcements."""
        year = date.today().year

        holidays = (
            await db.execute(
                select(Holiday).where(
                    Holiday.tenant_id == tenant_id,
                    Holiday.is_deleted.is_(False),
                ).order_by(Holiday.date)
            )
        ).scalars().all()

        holiday_lines = [
            f"- {h.name}: {h.date.isoformat()}"
            + (" (optional)" if h.is_optional else "")
            for h in holidays
        ]
        holiday_body = (
            f"Company holidays ({year} and all configured):\n"
            f"Total holidays configured: {len(holidays)}\n"
            + ("\n".join(holiday_lines) if holiday_lines else "No holidays configured.")
        )
        await self._upsert_synced_doc(
            db, tenant_id, title="Company Holidays", source_type="holiday", content=holiday_body
        )

        leave_types = (
            await db.execute(
                select(LeaveType).where(
                    LeaveType.tenant_id == tenant_id,
                    LeaveType.is_deleted.is_(False),
                    LeaveType.is_active.is_(True),
                )
            )
        ).scalars().all()
        lt_lines = [
            f"- {lt.name} ({lt.code}): annual quota {float(lt.annual_quota)} days"
            + (", paid" if lt.is_paid else ", unpaid")
            for lt in leave_types
        ]
        leave_body = "Leave policy / leave types:\n" + (
            "\n".join(lt_lines) if lt_lines else "No leave types configured."
        )
        await self._upsert_synced_doc(
            db, tenant_id, title="Leave Types & Quotas", source_type="leave_policy", content=leave_body
        )

        anns = (
            await db.execute(
                select(Announcement).where(
                    Announcement.tenant_id == tenant_id,
                    Announcement.is_deleted.is_(False),
                ).order_by(Announcement.created_at.desc()).limit(20)
            )
        ).scalars().all()
        ann_lines = [f"- {a.title}: {a.body}" for a in anns]
        ann_body = "Company announcements:\n" + (
            "\n".join(ann_lines) if ann_lines else "No announcements."
        )
        await self._upsert_synced_doc(
            db, tenant_id, title="Announcements", source_type="announcement", content=ann_body
        )

        return {"synced": 3, "holidays": len(holidays), "leave_types": len(leave_types)}

    async def _upsert_synced_doc(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        title: str,
        source_type: str,
        content: str,
    ) -> None:
        result = await db.execute(
            select(AiDocument).where(
                AiDocument.tenant_id == tenant_id,
                AiDocument.source_type == source_type,
                AiDocument.is_deleted.is_(False),
            )
        )
        doc = result.scalar_one_or_none()
        if doc:
            doc.title = title
            doc.content = content
            doc.status = "pending"
        else:
            doc = AiDocument(
                tenant_id=tenant_id,
                title=title,
                content=content,
                source_type=source_type,
                status="pending",
            )
            db.add(doc)
            await db.flush()
        await self.reindex_document(db, tenant_id, doc.id)

    async def build_live_context(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
        employee_id: uuid.UUID | None,
        permissions: list[str],
    ) -> str:
        parts: list[str] = [f"Today's date: {date.today().isoformat()}"]

        # Resolve employee record for the logged-in user if needed
        emp: Employee | None = None
        if employee_id:
            emp = (
                await db.execute(
                    select(Employee).where(
                        Employee.id == employee_id,
                        Employee.tenant_id == tenant_id,
                        Employee.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
        elif user_id:
            emp = (
                await db.execute(
                    select(Employee).where(
                        Employee.user_id == user_id,
                        Employee.tenant_id == tenant_id,
                        Employee.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if emp:
                employee_id = emp.id

        holiday_count = await db.execute(
            select(func.count()).select_from(Holiday).where(
                Holiday.tenant_id == tenant_id, Holiday.is_deleted.is_(False)
            )
        )
        parts.append(f"Total company holidays configured: {holiday_count.scalar_one()}")

        upcoming = (
            await db.execute(
                select(Holiday)
                .where(
                    Holiday.tenant_id == tenant_id,
                    Holiday.is_deleted.is_(False),
                    Holiday.date >= date.today(),
                )
                .order_by(Holiday.date)
                .limit(10)
            )
        ).scalars().all()
        if upcoming:
            parts.append(
                "Upcoming holidays:\n"
                + "\n".join(f"- {h.name} on {h.date.isoformat()}" for h in upcoming)
            )
        else:
            parts.append("Upcoming holidays: none from today onward.")

        types = {
            lt.id: lt
            for lt in (
                await db.execute(
                    select(LeaveType).where(
                        LeaveType.tenant_id == tenant_id,
                        LeaveType.is_deleted.is_(False),
                        LeaveType.is_active.is_(True),
                    )
                )
            ).scalars().all()
        }
        if types:
            parts.append(
                "Active leave types:\n"
                + "\n".join(
                    f"- {lt.name} ({lt.code}): annual quota {float(lt.annual_quota)} days"
                    for lt in types.values()
                )
            )

        if emp and employee_id:
            parts.append(
                f"Current employee: {emp.first_name} {emp.last_name} "
                f"(code {emp.employee_code}, status {emp.employment_status})"
            )

            year = date.today().year
            balances = (
                await db.execute(
                    select(LeaveBalance).where(
                        LeaveBalance.tenant_id == tenant_id,
                        LeaveBalance.employee_id == employee_id,
                        LeaveBalance.year == year,
                        LeaveBalance.is_deleted.is_(False),
                    )
                )
            ).scalars().all()

            if balances:
                lines = []
                total_remaining = 0.0
                for b in balances:
                    lt = types.get(b.leave_type_id)
                    name = lt.name if lt else "Leave"
                    remaining = float(b.allocated) - float(b.used) - float(b.pending)
                    total_remaining += remaining
                    lines.append(
                        f"- {name}: allocated {float(b.allocated)}, used {float(b.used)}, "
                        f"pending {float(b.pending)}, remaining {remaining}"
                    )
                parts.append(
                    f"CURRENT USER LEAVE BALANCE ({year}) — use these numbers to answer leave questions:\n"
                    + "\n".join(lines)
                    + f"\nTotal remaining leave days: {total_remaining}"
                )
            else:
                parts.append(
                    f"CURRENT USER LEAVE BALANCE ({year}): no leave_balance rows found for this employee. "
                    "Tell the user their leave quotas may not be assigned yet (HR should assign leave types "
                    "on the employee profile). Do not invent numbers."
                )

            pending = await db.execute(
                select(func.count()).select_from(LeaveRequest).where(
                    LeaveRequest.tenant_id == tenant_id,
                    LeaveRequest.employee_id == employee_id,
                    LeaveRequest.status == "pending",
                    LeaveRequest.is_deleted.is_(False),
                )
            )
            parts.append(f"Current user's pending leave requests: {pending.scalar_one()}")
        else:
            parts.append(
                "Current user has no linked employee profile, so personal leave balances are unavailable."
            )

        return "\n".join(parts)

    async def retrieve_chunks(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        query: str,
        query_embedding: list[float] | None,
        top_k: int = 5,
    ) -> list[tuple[AiChunk, float]]:
        result = await db.execute(
            select(AiChunk).where(AiChunk.tenant_id == tenant_id, AiChunk.is_deleted.is_(False))
        )
        chunks = list(result.scalars().all())
        scored: list[tuple[AiChunk, float]] = []
        for ch in chunks:
            emb = ch.embedding or []
            if query_embedding and isinstance(emb, list) and emb:
                score = cosine_similarity(query_embedding, emb)
            else:
                score = keyword_score(query, ch.content)
            if score > 0:
                scored.append((ch, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    async def list_conversations(
        self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[AiConversation]:
        result = await db.execute(
            select(AiConversation)
            .where(
                AiConversation.tenant_id == tenant_id,
                AiConversation.user_id == user_id,
                AiConversation.is_deleted.is_(False),
            )
            .order_by(AiConversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_conversation(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> AiConversation | None:
        result = await db.execute(
            select(AiConversation)
            .options(selectinload(AiConversation.messages))
            .where(
                AiConversation.id == conversation_id,
                AiConversation.tenant_id == tenant_id,
                AiConversation.user_id == user_id,
                AiConversation.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def delete_conversation(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> None:
        conv = await self.get_conversation(db, tenant_id, user_id, conversation_id)
        if not conv:
            raise ValueError("Conversation not found")
        conv.is_deleted = True

    async def chat(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        employee_id: uuid.UUID | None,
        permissions: list[str],
        message: str,
        conversation_id: uuid.UUID | None = None,
    ) -> dict:
        cfg = await self.get_or_create_config(db, tenant_id)
        if not cfg.is_enabled:
            raise ValueError("AI Assistant is disabled. Enable it in Settings → AI Assistant.")
        key = self._require_key(cfg)
        message = message.strip()
        if not message:
            raise ValueError("Message is empty")

        if conversation_id:
            conv = await self.get_conversation(db, tenant_id, user_id, conversation_id)
            if not conv:
                raise ValueError("Conversation not found")
            prior_result = await db.execute(
                select(AiMessage)
                .where(AiMessage.conversation_id == conv.id)
                .order_by(AiMessage.created_at.asc())
            )
            prior_messages = list(prior_result.scalars().all())
        else:
            title = message[:60] + ("…" if len(message) > 60 else "")
            conv = AiConversation(tenant_id=tenant_id, user_id=user_id, title=title)
            db.add(conv)
            await db.flush()
            prior_messages = []

        live = await self.build_live_context(
            db,
            tenant_id,
            user_id=user_id,
            employee_id=employee_id,
            permissions=permissions,
        )

        sources: list[dict] = []
        rag_block = ""
        try:
            q_emb: list[float] | None = None
            if not self._uses_local_rag(cfg):
                [q_emb] = await embed_texts(
                    api_key=key,
                    base_url=cfg.base_url,
                    model=cfg.embedding_model,
                    texts=[message],
                )
            hits = await self.retrieve_chunks(db, tenant_id, message, q_emb, top_k=5)
            if hits:
                rag_parts = []
                for ch, score in hits:
                    if score < 0.05:
                        continue
                    # Prefer meta title — avoid lazy-loading ch.document in async
                    title = (ch.meta or {}).get("title") or "Knowledge"
                    sources.append({"title": title, "score": round(score, 3)})
                    rag_parts.append(f"[{title}]\n{ch.content}")
                rag_block = "\n\n---\n\n".join(rag_parts)
        except Exception:
            # Embeddings may fail on some providers; still answer with live context
            rag_block = ""

        history_msgs = [
            {"role": m.role, "content": m.content}
            for m in prior_messages[-12:]
            if m.role in ("user", "assistant")
        ]

        system = (
            "You are the Company Assistant for an HRMS product (EmployeeMint). "
            "Answer clearly using the LIVE EMPLOYEE / ORG FACTS and COMPANY KNOWLEDGE sections. "
            "The LIVE FACTS section is authoritative for the current user's leave balances, "
            "holidays, and profile. If it lists remaining leave days, report those numbers directly. "
            "If it says no leave_balance rows exist, say quotas may not be assigned yet. "
            "Never invent leave numbers. Do not claim you lack access when LIVE FACTS already contain the answer."
        )
        context_msg = (
            "=== LIVE EMPLOYEE / ORG FACTS ===\n"
            f"{live}\n\n"
            "=== COMPANY KNOWLEDGE (RAG) ===\n"
            f"{rag_block or '(No indexed documents matched. Rely on live facts or ask admin to Sync company data.)'}"
        )

        llm_messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": context_msg},
            *history_msgs,
            {"role": "user", "content": message},
        ]

        answer = await chat_completion(
            api_key=key,
            base_url=cfg.base_url,
            model=cfg.model_name,
            messages=llm_messages,
        )

        user_msg = AiMessage(conversation_id=conv.id, role="user", content=message, sources=[])
        asst_msg = AiMessage(
            conversation_id=conv.id, role="assistant", content=answer, sources=sources
        )
        db.add(user_msg)
        db.add(asst_msg)
        await db.flush()
        await db.refresh(user_msg)
        await db.refresh(asst_msg)

        return {
            "conversation_id": str(conv.id),
            "title": conv.title,
            "message": {
                "id": str(asst_msg.id),
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "created_at": asst_msg.created_at.isoformat() if asst_msg.created_at else None,
            },
            "user_message": {
                "id": str(user_msg.id),
                "role": "user",
                "content": message,
                "sources": [],
                "created_at": user_msg.created_at.isoformat() if user_msg.created_at else None,
            },
        }


assistant_service = AssistantService()

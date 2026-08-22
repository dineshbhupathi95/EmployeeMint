"""Candidate CRUD, resume handling, offer linking, accept-offer → hire."""

import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Candidate, OfferLetter, Role
from app.schemas.candidate import AcceptOfferRequest, CandidateCreate, CandidateUpdate
from app.schemas.employee import EmployeeCreate
from app.services.resume_extract_service import extract_resume_text
from app.services.resume_parse_service import parse_resume_text

CANDIDATE_STATUSES = {
    "new",
    "screening",
    "interview",
    "selected",
    "offer_draft",
    "offer_sent",
    "offer_accepted",
    "offer_declined",
    "rejected",
    "withdrawn",
    "hired",
}

RESUME_MAX_BYTES = 8 * 1024 * 1024
ALLOWED_RESUME_EXT = (".pdf", ".docx", ".txt", ".md")


class CandidateService:
    async def get(
        self, db: AsyncSession, tenant_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Candidate | None:
        result = await db.execute(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.tenant_id == tenant_id,
                Candidate.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_candidates(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Candidate], int]:
        q = select(Candidate).where(Candidate.tenant_id == tenant_id, Candidate.is_deleted.is_(False))
        if status:
            q = q.where(Candidate.status == status)
        count = await db.execute(select(func.count()).select_from(q.subquery()))
        total = count.scalar_one()
        result = await db.execute(
            q.order_by(Candidate.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def create(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        data: CandidateCreate,
    ) -> Candidate:
        existing = await db.execute(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                func.lower(Candidate.email) == data.email.lower().strip(),
                Candidate.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("A candidate with this email already exists")

        candidate = Candidate(
            tenant_id=tenant_id,
            created_by=user_id,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            email=data.email.lower().strip(),
            phone=data.phone,
            status=data.status or "new",
            source=data.source,
            applied_for_designation=data.applied_for_designation,
            expected_ctc=data.expected_ctc,
            notice_period_days=data.notice_period_days,
            current_company=data.current_company,
            current_designation=data.current_designation,
            total_experience_years=data.total_experience_years,
            applied_at=data.applied_at or date.today(),
            notes=data.notes,
            parsed_profile=data.parsed_profile or {},
        )
        db.add(candidate)
        await db.flush()
        return candidate

    async def update(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        data: CandidateUpdate,
    ) -> Candidate:
        candidate = await self.get(db, tenant_id, candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")
        if candidate.status == "hired":
            raise ValueError("Cannot edit a hired candidate")

        updates = data.model_dump(exclude_unset=True)
        if "status" in updates and updates["status"] not in CANDIDATE_STATUSES:
            raise ValueError("Invalid status")
        if "email" in updates:
            updates["email"] = updates["email"].lower().strip()

        for key, value in updates.items():
            setattr(candidate, key, value)
        await db.flush()
        return candidate

    async def parse_resume_preview(self, filename: str, content: bytes) -> dict:
        if len(content) > RESUME_MAX_BYTES:
            raise ValueError("Resume too large (max 8MB)")
        text = extract_resume_text(filename, content)
        return {**parse_resume_text(text), "resume_text_length": len(text)}

    async def upload_resume(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        *,
        filename: str,
        content: bytes,
        content_type: str | None,
        auto_fill: bool = True,
    ) -> tuple[Candidate, dict]:
        if len(content) > RESUME_MAX_BYTES:
            raise ValueError("Resume too large (max 8MB)")
        lower = (filename or "").lower()
        if lower.endswith(".doc"):
            raise ValueError(
                "Legacy .doc files are not supported. Save as .docx or .pdf and upload again."
            )
        if not any(lower.endswith(ext) for ext in ALLOWED_RESUME_EXT):
            raise ValueError("Use PDF, DOCX, TXT, or MD resume files")

        candidate = await self.get(db, tenant_id, candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")

        text = extract_resume_text(filename, content)
        parsed = parse_resume_text(text)

        upload_dir = os.path.join("uploads", "candidates", str(tenant_id), str(candidate_id))
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{os.path.basename(filename)}"
        filepath = os.path.join(upload_dir, safe_name)
        with open(filepath, "wb") as f:
            f.write(content)

        candidate.resume_file_path = filepath
        candidate.resume_file_name = filename
        candidate.resume_content_type = content_type
        candidate.resume_text = text[:50000]
        candidate.resume_parsed_at = datetime.now(timezone.utc)
        candidate.parsed_profile = parsed.get("parsed_profile", {})

        if auto_fill:
            if parsed.get("first_name"):
                candidate.first_name = parsed["first_name"]
            if parsed.get("last_name"):
                candidate.last_name = parsed["last_name"]
            if parsed.get("email"):
                candidate.email = parsed["email"].lower().strip()
            if parsed.get("phone"):
                candidate.phone = parsed["phone"]
            if parsed.get("current_company"):
                candidate.current_company = parsed["current_company"]
            if parsed.get("current_designation"):
                candidate.current_designation = parsed["current_designation"]
            if parsed.get("total_experience_years") is not None:
                candidate.total_experience_years = Decimal(str(parsed["total_experience_years"]))

        await db.flush()
        return candidate, parsed

    async def list_offers(
        self, db: AsyncSession, tenant_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> list[OfferLetter]:
        result = await db.execute(
            select(OfferLetter)
            .where(
                OfferLetter.tenant_id == tenant_id,
                OfferLetter.candidate_id == candidate_id,
                OfferLetter.is_deleted.is_(False),
            )
            .order_by(OfferLetter.created_at.desc())
        )
        return list(result.scalars().all())

    async def _get_employee_role_id(self, db: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID | None:
        result = await db.execute(
            select(Role.id).where(
                Role.tenant_id == tenant_id,
                Role.name == "Employee",
                Role.is_deleted.is_(False),
            )
        )
        row = result.scalar_one_or_none()
        return row

    async def create_offer_for_candidate(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        candidate_id: uuid.UUID,
        *,
        template_id: uuid.UUID,
        designation: str | None = None,
        ctc: str | None = None,
        joining_date: date | None = None,
    ) -> OfferLetter:
        candidate = await self.get(db, tenant_id, candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")
        if candidate.status in ("hired", "withdrawn", "rejected"):
            raise ValueError("Cannot create offer for this candidate status")

        from app.services.lifecycle_service import LifecycleService

        letter = await LifecycleService().create_offer(
            db,
            tenant_id,
            user_id,
            template_id=template_id,
            candidate_id=candidate.id,
            candidate_name=f"{candidate.first_name} {candidate.last_name}",
            candidate_email=candidate.email,
            designation=designation or candidate.applied_for_designation or candidate.current_designation,
            ctc=ctc or candidate.expected_ctc,
            joining_date=joining_date,
        )
        candidate.status = "offer_draft"
        await db.flush()
        return letter

    async def accept_offer(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        offer_id: uuid.UUID,
        user_id: uuid.UUID,
        data: AcceptOfferRequest,
    ) -> dict:
        candidate = await self.get(db, tenant_id, candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")
        if candidate.employee_id:
            raise ValueError("Candidate is already hired")

        result = await db.execute(
            select(OfferLetter).where(
                OfferLetter.id == offer_id,
                OfferLetter.tenant_id == tenant_id,
                OfferLetter.candidate_id == candidate_id,
                OfferLetter.is_deleted.is_(False),
            )
        )
        offer = result.scalar_one_or_none()
        if not offer:
            raise ValueError("Offer not found for this candidate")
        if offer.status != "released":
            raise ValueError("Offer must be released before acceptance")
        if offer.status == "accepted":
            raise ValueError("Offer already accepted")

        role_ids = list(data.role_ids)
        if not role_ids:
            employee_role = await self._get_employee_role_id(db, tenant_id)
            if employee_role:
                role_ids = [employee_role]

        from app.services.employee_service import EmployeeService

        emp_data = EmployeeCreate(
            first_name=candidate.first_name,
            last_name=candidate.last_name,
            email=candidate.email,
            password=data.password,
            work_email=candidate.email,
            phone=candidate.phone,
            date_of_joining=offer.joining_date or data.date_of_joining,
            department_id=data.department_id,
            designation_id=data.designation_id,
            location_id=data.location_id,
            reports_to_employee_id=data.reports_to_employee_id,
            role_ids=role_ids,
            leave_type_ids=data.leave_type_ids,
        )
        employee = await EmployeeService().create(db, tenant_id, emp_data, user_id)

        now = datetime.now(timezone.utc)
        offer.status = "accepted"
        offer.employee_id = employee.id
        offer.accepted_at = now

        candidate.status = "hired"
        candidate.employee_id = employee.id
        candidate.hired_at = now

        from app.services.finance_service import FinanceService

        compensation = await FinanceService().sync_compensation_from_offer(
            db, tenant_id, offer, user_id
        )

        onboarding_count = 0
        if data.start_onboarding:
            from app.services.lifecycle_service import LifecycleService

            try:
                tasks = await LifecycleService().start_onboarding(
                    db, tenant_id, user_id, employee.id
                )
                onboarding_count = len(tasks)
            except ValueError:
                onboarding_count = 0

        await db.flush()
        return {
            "employee_id": str(employee.id),
            "employee_code": employee.employee_code,
            "offer_id": str(offer.id),
            "compensation_configured": compensation is not None,
            "onboarding_tasks_created": onboarding_count,
        }

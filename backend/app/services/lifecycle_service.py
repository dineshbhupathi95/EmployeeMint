"""HR lifecycle: offer letters, onboarding."""

import html
import re
import uuid
from datetime import date, timedelta

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Employee, OfferLetter, OfferLetterTemplate, OnboardingChecklist, OnboardingTask, Tenant

DEFAULT_ONBOARDING_TASKS = [
    ("Submit identity documents", "Upload ID / address proof in Profile → Documents"),
    ("Complete bank & tax forms", "Upload bank details and tax forms in Profile → Documents"),
    ("IT account & laptop setup", "Coordinate with IT for email, systems access, and equipment"),
    ("HR orientation session", "Attend policies, benefits, and company introduction"),
]

DEFAULT_TEMPLATE_BODY = """Dear {{candidate_name}},

We are pleased to offer you the position of {{designation}} at {{company_name}}.

Date: {{date}}
Compensation (CTC): {{ctc}}
Proposed Joining Date: {{joining_date}}

This offer is subject to successful verification of documents and background checks.
Please confirm your acceptance by replying to this letter.

We look forward to welcoming you aboard.

Sincerely,
Human Resources
{{company_name}}
"""


class LifecycleService:
    async def _get_offer(
        self, db: AsyncSession, tenant_id: uuid.UUID, offer_id: uuid.UUID
    ) -> OfferLetter | None:
        result = await db.execute(
            select(OfferLetter).where(
                OfferLetter.id == offer_id,
                OfferLetter.tenant_id == tenant_id,
                OfferLetter.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def _get_template(
        self, db: AsyncSession, tenant_id: uuid.UUID, template_id: uuid.UUID
    ) -> OfferLetterTemplate | None:
        result = await db.execute(
            select(OfferLetterTemplate).where(
                OfferLetterTemplate.id == template_id,
                OfferLetterTemplate.tenant_id == tenant_id,
                OfferLetterTemplate.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    def _html_to_text(self, content: str) -> str:
        text = content.replace("\r\n", "\n")
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</p>", "\n\n", text)
        text = re.sub(r"(?i)</div>", "\n", text)
        text = re.sub(r"(?i)</li>", "\n", text)
        text = re.sub(r"(?i)<li[^>]*>", "• ", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _render_template(
        self, body: str, letter: OfferLetter, company_name: str
    ) -> str:
        values = {
            "candidate_name": letter.candidate_name or "",
            "candidate_email": letter.candidate_email or "",
            "designation": letter.designation or "the applied role",
            "ctc": letter.ctc or "As discussed",
            "joining_date": letter.joining_date.strftime("%d %B %Y") if letter.joining_date else "To be confirmed",
            "company_name": company_name,
            "date": date.today().strftime("%d %B %Y"),
        }
        rendered = body
        for key, value in values.items():
            rendered = rendered.replace("{{" + key + "}}", value)
        return rendered

    def _build_offer_pdf(
        self,
        letter: OfferLetter,
        company_name: str,
        template_body: str | None = None,
        template_name: str | None = None,
    ) -> bytes:
        body = template_body or DEFAULT_TEMPLATE_BODY
        rendered = self._render_template(body, letter, company_name)
        text = self._html_to_text(rendered)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        title = template_name or "Offer of Employment"
        pdf.multi_cell(0, 10, title, align="C")
        pdf.ln(6)
        pdf.set_font("Helvetica", size=11)
        # FPDF latin-1 only — replace common unicode chars
        safe = (
            text.replace("•", "-")
            .replace("–", "-")
            .replace("—", "-")
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
        )
        try:
            pdf.multi_cell(0, 6, safe)
        except Exception:
            pdf.multi_cell(0, 6, safe.encode("latin-1", "replace").decode("latin-1"))
        return bytes(pdf.output())

    async def list_templates(self, db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
        result = await db.execute(
            select(OfferLetterTemplate)
            .where(
                OfferLetterTemplate.tenant_id == tenant_id,
                OfferLetterTemplate.is_deleted.is_(False),
            )
            .order_by(OfferLetterTemplate.name)
        )
        return [
            {
                "id": str(t.id),
                "name": t.name,
                "body_html": t.body_html,
                "is_active": t.is_active,
            }
            for t in result.scalars().all()
        ]

    async def create_template(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        name: str,
        body_html: str,
        is_active: bool = True,
    ) -> OfferLetterTemplate:
        if not name.strip():
            raise ValueError("Template name is required")
        if not body_html.strip():
            raise ValueError("Template body is required")
        template = OfferLetterTemplate(
            tenant_id=tenant_id,
            created_by=user_id,
            name=name.strip(),
            body_html=body_html.strip(),
            is_active=is_active,
        )
        db.add(template)
        await db.flush()
        return template

    async def update_template(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        *,
        name: str | None = None,
        body_html: str | None = None,
        is_active: bool | None = None,
    ) -> OfferLetterTemplate:
        template = await self._get_template(db, tenant_id, template_id)
        if not template:
            raise ValueError("Template not found")
        if name is not None:
            template.name = name.strip()
        if body_html is not None:
            template.body_html = body_html.strip()
        if is_active is not None:
            template.is_active = is_active
        await db.flush()
        return template

    async def delete_template(
        self, db: AsyncSession, tenant_id: uuid.UUID, template_id: uuid.UUID
    ) -> None:
        template = await self._get_template(db, tenant_id, template_id)
        if not template:
            raise ValueError("Template not found")
        template.is_deleted = True
        template.is_active = False
        await db.flush()

    async def generate_offer_pdf(
        self, db: AsyncSession, tenant_id: uuid.UUID, offer_id: uuid.UUID
    ) -> tuple[OfferLetter, bytes]:
        letter = await self._get_offer(db, tenant_id, offer_id)
        if not letter:
            raise ValueError("Offer letter not found")
        if letter.status == "released":
            raise ValueError("Cannot regenerate a released offer letter")
        if not letter.template_id:
            raise ValueError("Offer has no template. Recreate the offer with a selected template.")

        template = await self._get_template(db, tenant_id, letter.template_id)
        if not template:
            raise ValueError("Offer template not found or was deleted")

        tenant = await db.get(Tenant, tenant_id)
        company_name = tenant.name if tenant else "Your Company"
        pdf_bytes = self._build_offer_pdf(
            letter, company_name, template.body_html, template.name
        )

        letter.status = "pdf_ready"
        letter.file_url = f"/api/v1/offer-letters/{letter.id}/pdf"
        await db.flush()
        return letter, pdf_bytes

    async def release_offer(
        self, db: AsyncSession, tenant_id: uuid.UUID, offer_id: uuid.UUID
    ) -> OfferLetter:
        letter = await self._get_offer(db, tenant_id, offer_id)
        if not letter:
            raise ValueError("Offer letter not found")
        if letter.status == "draft":
            raise ValueError("Generate the offer PDF before releasing")
        if letter.status == "released":
            raise ValueError("Offer letter already released")

        letter.status = "released"
        await db.flush()

        from app.services.finance_service import FinanceService

        await FinanceService().sync_compensation_from_offer(db, tenant_id, letter)
        await db.flush()
        return letter

    async def list_offers(self, db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
        result = await db.execute(
            select(OfferLetter, OfferLetterTemplate)
            .outerjoin(OfferLetterTemplate, OfferLetter.template_id == OfferLetterTemplate.id)
            .where(OfferLetter.tenant_id == tenant_id, OfferLetter.is_deleted.is_(False))
            .order_by(OfferLetter.created_at.desc())
        )
        return [
            {
                "id": str(o.id),
                "candidate_name": o.candidate_name,
                "candidate_email": o.candidate_email,
                "designation": o.designation,
                "ctc": o.ctc,
                "joining_date": str(o.joining_date) if o.joining_date else None,
                "status": o.status,
                "has_pdf": o.status in ("pdf_ready", "released"),
                "file_url": o.file_url,
                "template_id": str(o.template_id) if o.template_id else None,
                "template_name": t.name if t else None,
            }
            for o, t in result.all()
        ]

    async def create_offer(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        template_id: uuid.UUID,
        candidate_name: str,
        candidate_email: str,
        designation: str | None,
        ctc: str | None,
        joining_date: date | None,
    ) -> OfferLetter:
        template = await self._get_template(db, tenant_id, template_id)
        if not template:
            raise ValueError("Selected template not found")
        if not template.is_active:
            raise ValueError("Selected template is inactive")

        letter = OfferLetter(
            tenant_id=tenant_id,
            created_by=user_id,
            template_id=template.id,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            designation=designation,
            ctc=ctc,
            joining_date=joining_date,
            status="draft",
        )
        db.add(letter)
        await db.flush()
        return letter

    async def list_onboarding_tasks(self, db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
        result = await db.execute(
            select(OnboardingTask, Employee)
            .join(Employee, OnboardingTask.employee_id == Employee.id)
            .where(
                OnboardingTask.tenant_id == tenant_id,
                OnboardingTask.is_deleted.is_(False),
                Employee.is_deleted.is_(False),
            )
            .order_by(Employee.first_name, OnboardingTask.due_date.nulls_last())
        )
        rows = result.all()
        return [
            {
                "id": str(task.id),
                "employee_id": str(task.employee_id),
                "employee_name": f"{emp.first_name} {emp.last_name}",
                "employee_code": emp.employee_code,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "due_date": str(task.due_date) if task.due_date else None,
            }
            for task, emp in rows
        ]

    async def start_onboarding(
        self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, employee_id: uuid.UUID
    ) -> list[OnboardingTask]:
        employee = await db.get(Employee, employee_id)
        if not employee or employee.tenant_id != tenant_id or employee.is_deleted:
            raise ValueError("Employee not found")

        existing = await db.execute(
            select(OnboardingTask.id).where(
                OnboardingTask.tenant_id == tenant_id,
                OnboardingTask.employee_id == employee_id,
                OnboardingTask.is_deleted.is_(False),
            )
        )
        if existing.first():
            raise ValueError("Onboarding already started for this employee")

        checklist_result = await db.execute(
            select(OnboardingChecklist).where(
                OnboardingChecklist.tenant_id == tenant_id,
                OnboardingChecklist.is_active.is_(True),
                OnboardingChecklist.is_deleted.is_(False),
            )
        )
        checklist = checklist_result.scalar_one_or_none()

        tasks: list[OnboardingTask] = []
        for idx, (title, description) in enumerate(DEFAULT_ONBOARDING_TASKS):
            task = OnboardingTask(
                tenant_id=tenant_id,
                created_by=user_id,
                employee_id=employee_id,
                checklist_id=checklist.id if checklist else None,
                title=title,
                description=description,
                status="pending",
                assigned_to_user_id=employee.user_id,
                due_date=date.today() + timedelta(days=idx * 2 + 3),
            )
            db.add(task)
            tasks.append(task)
        await db.flush()

        if employee.user_id:
            from app.services.dashboard_service import NotificationService

            await NotificationService().notify_onboarding_assigned(
                db,
                tenant_id=tenant_id,
                employee_user_id=employee.user_id,
                employee_name=f"{employee.first_name} {employee.last_name}",
                task_count=len(tasks),
                created_by=user_id,
            )
        return tasks

    async def create_onboarding_task(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        employee_id: uuid.UUID,
        title: str,
        description: str | None,
        due_date: date | None,
    ) -> OnboardingTask:
        employee = await db.get(Employee, employee_id)
        if not employee or employee.tenant_id != tenant_id or employee.is_deleted:
            raise ValueError("Employee not found")

        task = OnboardingTask(
            tenant_id=tenant_id,
            created_by=user_id,
            employee_id=employee_id,
            title=title,
            description=description,
            due_date=due_date,
            status="pending",
            assigned_to_user_id=employee.user_id,
        )
        db.add(task)
        await db.flush()

        if employee.user_id:
            from app.services.dashboard_service import NotificationService

            await NotificationService().notify_onboarding_assigned(
                db,
                tenant_id=tenant_id,
                employee_user_id=employee.user_id,
                employee_name=f"{employee.first_name} {employee.last_name}",
                task_count=1,
                task_title=title,
                created_by=user_id,
            )
        return task

    async def list_my_onboarding_tasks(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID
    ) -> list[dict]:
        result = await db.execute(
            select(OnboardingTask).where(
                OnboardingTask.tenant_id == tenant_id,
                OnboardingTask.employee_id == employee_id,
                OnboardingTask.is_deleted.is_(False),
            ).order_by(OnboardingTask.due_date.nulls_last(), OnboardingTask.created_at)
        )
        return [
            {
                "id": str(task.id),
                "employee_id": str(task.employee_id),
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "due_date": str(task.due_date) if task.due_date else None,
            }
            for task in result.scalars().all()
        ]

    async def update_my_onboarding_task(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        task_id: uuid.UUID,
        *,
        status: str,
    ) -> OnboardingTask:
        result = await db.execute(
            select(OnboardingTask).where(
                OnboardingTask.id == task_id,
                OnboardingTask.tenant_id == tenant_id,
                OnboardingTask.employee_id == employee_id,
                OnboardingTask.is_deleted.is_(False),
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError("Task not found")
        if status not in ("pending", "in_progress", "completed"):
            raise ValueError("Invalid status")
        task.status = status
        await db.flush()
        return task

    async def update_onboarding_task(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        task_id: uuid.UUID,
        *,
        status: str | None = None,
        title: str | None = None,
        due_date: date | None = None,
    ) -> OnboardingTask:
        result = await db.execute(
            select(OnboardingTask).where(
                OnboardingTask.id == task_id,
                OnboardingTask.tenant_id == tenant_id,
                OnboardingTask.is_deleted.is_(False),
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError("Task not found")
        if status is not None:
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError("Invalid status")
            task.status = status
        if title is not None:
            task.title = title
        if due_date is not None:
            task.due_date = due_date
        await db.flush()
        return task

"""Employee document uploads for profile / onboarding."""

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Employee, EmployeeDocument, OnboardingTask

DOCUMENT_TYPES = {
    "identity_proof": {
        "label": "Identity Proof",
        "description": "Aadhaar, PAN, Passport, or Driving License",
        "task_keywords": ("identity", "id proof", "documents"),
    },
    "address_proof": {
        "label": "Address Proof",
        "description": "Utility bill, rental agreement, or passport",
        "task_keywords": ("address",),
    },
    "bank_details": {
        "label": "Bank Details",
        "description": "Cancelled cheque or bank passbook first page",
        "task_keywords": ("bank", "payroll"),
    },
    "tax_forms": {
        "label": "Tax Forms",
        "description": "Tax declaration / Form 12BB / investment proofs",
        "task_keywords": ("tax", "bank & tax", "payroll"),
    },
    "photo": {
        "label": "Passport Photo",
        "description": "Recent passport-size photograph",
        "task_keywords": ("photo",),
    },
    "education": {
        "label": "Education Certificates",
        "description": "Degree / marksheets",
        "task_keywords": ("education", "certificate"),
    },
    "other": {
        "label": "Other Documents",
        "description": "Any additional required documents",
        "task_keywords": (),
    },
}

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"


class DocumentService:
    def list_required_types(self) -> list[dict]:
        return [
            {"code": code, "label": meta["label"], "description": meta["description"]}
            for code, meta in DOCUMENT_TYPES.items()
        ]

    async def list_documents(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID
    ) -> list[EmployeeDocument]:
        result = await db.execute(
            select(EmployeeDocument)
            .where(
                EmployeeDocument.tenant_id == tenant_id,
                EmployeeDocument.employee_id == employee_id,
                EmployeeDocument.is_deleted.is_(False),
            )
            .order_by(EmployeeDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def upload(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        user_id: uuid.UUID,
        document_type: str,
        title: str | None,
        file_name: str,
        content_type: str | None,
        content: bytes,
    ) -> EmployeeDocument:
        if document_type not in DOCUMENT_TYPES:
            raise ValueError(f"Invalid document type. Choose from: {', '.join(DOCUMENT_TYPES)}")
        if not content:
            raise ValueError("Empty file")
        if len(content) > 8 * 1024 * 1024:
            raise ValueError("File too large (max 8MB)")

        employee = await db.get(Employee, employee_id)
        if not employee or employee.tenant_id != tenant_id or employee.is_deleted:
            raise ValueError("Employee not found")

        safe_name = file_name.replace("/", "_").replace("\\", "_")
        doc_id = uuid.uuid4()
        rel_dir = Path(str(tenant_id)) / str(employee_id)
        abs_dir = UPLOAD_ROOT / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{doc_id}_{safe_name}"
        abs_path = abs_dir / stored_name
        abs_path.write_bytes(content)

        meta = DOCUMENT_TYPES[document_type]
        doc = EmployeeDocument(
            id=doc_id,
            tenant_id=tenant_id,
            employee_id=employee_id,
            created_by=user_id,
            document_type=document_type,
            title=title or meta["label"],
            file_name=safe_name,
            content_type=content_type,
            file_path=str(rel_dir / stored_name),
            file_size=len(content),
            status="uploaded",
        )
        db.add(doc)
        await db.flush()

        await self._auto_complete_related_tasks(db, tenant_id, employee_id, document_type)
        return doc

    async def _auto_complete_related_tasks(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        document_type: str,
    ) -> None:
        keywords = DOCUMENT_TYPES.get(document_type, {}).get("task_keywords") or ()
        if not keywords:
            return
        result = await db.execute(
            select(OnboardingTask).where(
                OnboardingTask.tenant_id == tenant_id,
                OnboardingTask.employee_id == employee_id,
                OnboardingTask.is_deleted.is_(False),
                OnboardingTask.status != "completed",
            )
        )
        for task in result.scalars().all():
            hay = f"{task.title} {task.description or ''}".lower()
            if any(k in hay for k in keywords):
                task.status = "completed"
        await db.flush()

    async def get_document(
        self, db: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> EmployeeDocument | None:
        result = await db.execute(
            select(EmployeeDocument).where(
                EmployeeDocument.id == document_id,
                EmployeeDocument.tenant_id == tenant_id,
                EmployeeDocument.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def delete_document(
        self, db: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> None:
        doc = await self.get_document(db, tenant_id, document_id)
        if not doc:
            raise ValueError("Document not found")
        doc.is_deleted = True
        await db.flush()

    def absolute_path(self, doc: EmployeeDocument) -> Path:
        return UPLOAD_ROOT / doc.file_path

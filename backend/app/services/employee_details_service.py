"""Employee personal, academic, and prior work history."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.organization import Employee, EmployeeEducation, EmployeeWorkExperience
from app.schemas.employee_details import (
    BackgroundVerificationUpdate,
    EducationCreate,
    EducationUpdate,
    EmployeeDetailsResponse,
    EducationResponse,
    PersonalDetailsUpdate,
    WorkExperienceCreate,
    WorkExperienceResponse,
    WorkExperienceUpdate,
)
from app.services.document_service import DocumentService


class EmployeeDetailsService:
    async def get_employee(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID
    ) -> Employee | None:
        result = await db.execute(
            select(Employee)
            .options(
                selectinload(Employee.educations),
                selectinload(Employee.work_experiences),
            )
            .where(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
                Employee.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def to_response(
        self,
        db: AsyncSession,
        employee: Employee,
        *,
        include_documents: bool = True,
    ) -> EmployeeDetailsResponse:
        educations = [
            EducationResponse.model_validate(e)
            for e in sorted(
                (x for x in employee.educations if not x.is_deleted),
                key=lambda x: (x.year_of_passing or 0, x.degree),
                reverse=True,
            )
        ]
        experiences = [
            WorkExperienceResponse.model_validate(e)
            for e in sorted(
                (x for x in employee.work_experiences if not x.is_deleted),
                key=lambda x: x.start_date or date.min,
                reverse=True,
            )
        ]
        documents: list[dict] = []
        if include_documents:
            docs = await DocumentService().list_documents(db, employee.tenant_id, employee.id)
            documents = [
                {
                    "id": str(d.id),
                    "document_type": d.document_type,
                    "title": d.title,
                    "file_name": d.file_name,
                    "content_type": d.content_type,
                    "file_size": d.file_size,
                    "status": d.status,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in docs
            ]
        return EmployeeDetailsResponse(
            employee_id=employee.id,
            employee_code=employee.employee_code,
            first_name=employee.first_name,
            last_name=employee.last_name,
            work_email=employee.work_email,
            phone=employee.phone,
            date_of_joining=employee.date_of_joining,
            date_of_birth=employee.date_of_birth,
            gender=employee.gender,
            marital_status=employee.marital_status,
            blood_group=employee.blood_group,
            nationality=employee.nationality,
            personal_email=employee.personal_email,
            father_name=employee.father_name,
            emergency_contact_name=employee.emergency_contact_name,
            emergency_contact_phone=employee.emergency_contact_phone,
            emergency_contact_relation=employee.emergency_contact_relation,
            current_address=employee.current_address,
            permanent_address=employee.permanent_address,
            pan_number=employee.pan_number,
            aadhaar_number=employee.aadhaar_number,
            passport_number=employee.passport_number,
            background_verification_status=employee.background_verification_status,
            background_verification_notes=employee.background_verification_notes,
            educations=educations,
            work_experiences=experiences,
            documents=documents,
        )

    async def update_personal(
        self, db: AsyncSession, employee: Employee, data: PersonalDetailsUpdate
    ) -> Employee:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(employee, field, value)
        await db.flush()
        return employee

    async def update_verification(
        self, db: AsyncSession, employee: Employee, data: BackgroundVerificationUpdate
    ) -> Employee:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(employee, field, value)
        await db.flush()
        return employee

    async def add_education(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        data: EducationCreate,
        created_by: uuid.UUID | None,
    ) -> EmployeeEducation:
        row = EmployeeEducation(
            tenant_id=tenant_id,
            employee_id=employee_id,
            created_by=created_by,
            **data.model_dump(),
        )
        db.add(row)
        await db.flush()
        return row

    async def update_education(
        self, db: AsyncSession, row: EmployeeEducation, data: EducationUpdate
    ) -> EmployeeEducation:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        await db.flush()
        return row

    async def soft_delete_education(self, db: AsyncSession, row: EmployeeEducation) -> None:
        row.is_deleted = True
        await db.flush()

    async def get_education(
        self, db: AsyncSession, tenant_id: uuid.UUID, education_id: uuid.UUID
    ) -> EmployeeEducation | None:
        result = await db.execute(
            select(EmployeeEducation).where(
                EmployeeEducation.id == education_id,
                EmployeeEducation.tenant_id == tenant_id,
                EmployeeEducation.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def add_experience(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        data: WorkExperienceCreate,
        created_by: uuid.UUID | None,
    ) -> EmployeeWorkExperience:
        payload = data.model_dump()
        if payload.get("is_current"):
            payload["end_date"] = None
        row = EmployeeWorkExperience(
            tenant_id=tenant_id,
            employee_id=employee_id,
            created_by=created_by,
            **payload,
        )
        db.add(row)
        await db.flush()
        return row

    async def update_experience(
        self, db: AsyncSession, row: EmployeeWorkExperience, data: WorkExperienceUpdate
    ) -> EmployeeWorkExperience:
        payload = data.model_dump(exclude_unset=True)
        if payload.get("is_current"):
            payload["end_date"] = None
        for field, value in payload.items():
            setattr(row, field, value)
        await db.flush()
        return row

    async def soft_delete_experience(self, db: AsyncSession, row: EmployeeWorkExperience) -> None:
        row.is_deleted = True
        await db.flush()

    async def get_experience(
        self, db: AsyncSession, tenant_id: uuid.UUID, experience_id: uuid.UUID
    ) -> EmployeeWorkExperience | None:
        result = await db.execute(
            select(EmployeeWorkExperience).where(
                EmployeeWorkExperience.id == experience_id,
                EmployeeWorkExperience.tenant_id == tenant_id,
                EmployeeWorkExperience.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

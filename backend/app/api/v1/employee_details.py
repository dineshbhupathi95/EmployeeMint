"""Employee personal / academic / work history APIs for profile + HR background checks."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, _has_permission, get_current_user, require_permission
from app.core.database import get_db
from app.schemas.employee_details import (
    BackgroundVerificationUpdate,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    EmployeeDetailsResponse,
    PersonalDetailsUpdate,
    WorkExperienceCreate,
    WorkExperienceResponse,
    WorkExperienceUpdate,
)
from app.services.document_service import DocumentService
from app.services.employee_details_service import EmployeeDetailsService

router = APIRouter(prefix="/employee-details", tags=["employee-details"])
service = EmployeeDetailsService()
document_service = DocumentService()


def _ensure_tenant(user: CurrentUser) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_TENANT", "message": "No tenant"}})
    return user.tenant_id


def _can_view(user: CurrentUser, employee_id: uuid.UUID) -> bool:
    if user.employee_id == employee_id and _has_permission(user, "employee.view.own"):
        return True
    if _has_permission(user, "employee.view.all"):
        return True
    return False


def _can_edit(user: CurrentUser, employee_id: uuid.UUID) -> bool:
    if user.employee_id == employee_id and _has_permission(user, "employee.edit.own"):
        return True
    if _has_permission(user, "employee.edit.all"):
        return True
    return False


async def _load_for_view(
    db: AsyncSession, user: CurrentUser, employee_id: uuid.UUID
):
    tenant_id = _ensure_tenant(user)
    if not _can_view(user, employee_id):
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Cannot view employee details"}},
        )
    emp = await service.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found"}})
    return emp


async def _load_for_edit(
    db: AsyncSession, user: CurrentUser, employee_id: uuid.UUID
):
    tenant_id = _ensure_tenant(user)
    if not _can_edit(user, employee_id):
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Cannot edit employee details"}},
        )
    emp = await service.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found"}})
    return emp


@router.get("/my", response_model=EmployeeDetailsResponse)
async def get_my_details(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.view.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    emp = await _load_for_view(db, current_user, current_user.employee_id)
    return await service.to_response(db, emp)


@router.put("/my/personal", response_model=EmployeeDetailsResponse)
async def update_my_personal(
    data: PersonalDetailsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    emp = await _load_for_edit(db, current_user, current_user.employee_id)
    await service.update_personal(db, emp, data)
    await db.commit()
    emp = await service.get_employee(db, current_user.tenant_id, emp.id)  # type: ignore[arg-type]
    return await service.to_response(db, emp)  # type: ignore[arg-type]


@router.post("/my/education", response_model=EducationResponse, status_code=201)
async def add_my_education(
    data: EducationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    await _load_for_edit(db, current_user, current_user.employee_id)
    row = await service.add_education(
        db,
        tenant_id=current_user.tenant_id,  # type: ignore[arg-type]
        employee_id=current_user.employee_id,
        data=data,
        created_by=current_user.id,
    )
    await db.commit()
    await db.refresh(row)
    return EducationResponse.model_validate(row)


@router.put("/my/education/{education_id}", response_model=EducationResponse)
async def update_my_education(
    education_id: uuid.UUID,
    data: EducationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    row = await service.get_education(db, current_user.tenant_id, education_id)  # type: ignore[arg-type]
    if not row or row.employee_id != current_user.employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Education not found"}})
    await service.update_education(db, row, data)
    await db.commit()
    await db.refresh(row)
    return EducationResponse.model_validate(row)


@router.delete("/my/education/{education_id}", status_code=204)
async def delete_my_education(
    education_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    row = await service.get_education(db, current_user.tenant_id, education_id)  # type: ignore[arg-type]
    if not row or row.employee_id != current_user.employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Education not found"}})
    await service.soft_delete_education(db, row)
    await db.commit()


@router.post("/my/experience", response_model=WorkExperienceResponse, status_code=201)
async def add_my_experience(
    data: WorkExperienceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    await _load_for_edit(db, current_user, current_user.employee_id)
    row = await service.add_experience(
        db,
        tenant_id=current_user.tenant_id,  # type: ignore[arg-type]
        employee_id=current_user.employee_id,
        data=data,
        created_by=current_user.id,
    )
    await db.commit()
    await db.refresh(row)
    return WorkExperienceResponse.model_validate(row)


@router.put("/my/experience/{experience_id}", response_model=WorkExperienceResponse)
async def update_my_experience(
    experience_id: uuid.UUID,
    data: WorkExperienceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    row = await service.get_experience(db, current_user.tenant_id, experience_id)  # type: ignore[arg-type]
    if not row or row.employee_id != current_user.employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Experience not found"}})
    await service.update_experience(db, row, data)
    await db.commit()
    await db.refresh(row)
    return WorkExperienceResponse.model_validate(row)


@router.delete("/my/experience/{experience_id}", status_code=204)
async def delete_my_experience(
    experience_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    row = await service.get_experience(db, current_user.tenant_id, experience_id)  # type: ignore[arg-type]
    if not row or row.employee_id != current_user.employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Experience not found"}})
    await service.soft_delete_experience(db, row)
    await db.commit()


# ── HR / Admin: any employee ───────────────────────────────────────────────


@router.get("/employee/{employee_id}", response_model=EmployeeDetailsResponse)
async def get_employee_details(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    emp = await _load_for_view(db, current_user, employee_id)
    return await service.to_response(db, emp)


@router.put("/employee/{employee_id}/personal", response_model=EmployeeDetailsResponse)
async def update_employee_personal(
    employee_id: uuid.UUID,
    data: PersonalDetailsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.all")),
):
    emp = await _load_for_edit(db, current_user, employee_id)
    await service.update_personal(db, emp, data)
    await db.commit()
    emp = await service.get_employee(db, current_user.tenant_id, employee_id)  # type: ignore[arg-type]
    return await service.to_response(db, emp)  # type: ignore[arg-type]


@router.put("/employee/{employee_id}/verification", response_model=EmployeeDetailsResponse)
async def update_background_verification(
    employee_id: uuid.UUID,
    data: BackgroundVerificationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.all")),
):
    """HR-only: mark background verification status / notes."""
    emp = await _load_for_edit(db, current_user, employee_id)
    await service.update_verification(db, emp, data)
    await db.commit()
    emp = await service.get_employee(db, current_user.tenant_id, employee_id)  # type: ignore[arg-type]
    return await service.to_response(db, emp)  # type: ignore[arg-type]


@router.post("/employee/{employee_id}/education", response_model=EducationResponse, status_code=201)
async def add_employee_education(
    employee_id: uuid.UUID,
    data: EducationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.all")),
):
    await _load_for_edit(db, current_user, employee_id)
    row = await service.add_education(
        db,
        tenant_id=current_user.tenant_id,  # type: ignore[arg-type]
        employee_id=employee_id,
        data=data,
        created_by=current_user.id,
    )
    await db.commit()
    await db.refresh(row)
    return EducationResponse.model_validate(row)


@router.put("/employee/{employee_id}/education/{education_id}", response_model=EducationResponse)
async def update_employee_education(
    employee_id: uuid.UUID,
    education_id: uuid.UUID,
    data: EducationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.all")),
):
    row = await service.get_education(db, current_user.tenant_id, education_id)  # type: ignore[arg-type]
    if not row or row.employee_id != employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Education not found"}})
    await service.update_education(db, row, data)
    await db.commit()
    await db.refresh(row)
    return EducationResponse.model_validate(row)


@router.delete("/employee/{employee_id}/education/{education_id}", status_code=204)
async def delete_employee_education(
    employee_id: uuid.UUID,
    education_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.all")),
):
    row = await service.get_education(db, current_user.tenant_id, education_id)  # type: ignore[arg-type]
    if not row or row.employee_id != employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Education not found"}})
    await service.soft_delete_education(db, row)
    await db.commit()


@router.post("/employee/{employee_id}/experience", response_model=WorkExperienceResponse, status_code=201)
async def add_employee_experience(
    employee_id: uuid.UUID,
    data: WorkExperienceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.all")),
):
    await _load_for_edit(db, current_user, employee_id)
    row = await service.add_experience(
        db,
        tenant_id=current_user.tenant_id,  # type: ignore[arg-type]
        employee_id=employee_id,
        data=data,
        created_by=current_user.id,
    )
    await db.commit()
    await db.refresh(row)
    return WorkExperienceResponse.model_validate(row)


@router.put("/employee/{employee_id}/experience/{experience_id}", response_model=WorkExperienceResponse)
async def update_employee_experience(
    employee_id: uuid.UUID,
    experience_id: uuid.UUID,
    data: WorkExperienceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.all")),
):
    row = await service.get_experience(db, current_user.tenant_id, experience_id)  # type: ignore[arg-type]
    if not row or row.employee_id != employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Experience not found"}})
    await service.update_experience(db, row, data)
    await db.commit()
    await db.refresh(row)
    return WorkExperienceResponse.model_validate(row)


@router.delete("/employee/{employee_id}/experience/{experience_id}", status_code=204)
async def delete_employee_experience(
    employee_id: uuid.UUID,
    experience_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.all")),
):
    row = await service.get_experience(db, current_user.tenant_id, experience_id)  # type: ignore[arg-type]
    if not row or row.employee_id != employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Experience not found"}})
    await service.soft_delete_experience(db, row)
    await db.commit()


@router.get("/employee/{employee_id}/documents/{document_id}/download")
async def download_employee_document(
    employee_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.view.all")),
):
    """HR/Admin download of employee documents for background verification."""
    tenant_id = _ensure_tenant(current_user)
    doc = await document_service.get_document(db, tenant_id, document_id)
    if not doc or doc.employee_id != employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Document not found"}})
    path = document_service.absolute_path(doc)
    if not path.exists():
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "File missing on server"}})
    return FileResponse(
        path,
        filename=doc.file_name,
        media_type=doc.content_type or "application/octet-stream",
        content_disposition_type="inline",
    )

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TimesheetEntry
from app.services.workflow_service import WorkflowService


class TimesheetService:
    def __init__(self) -> None:
        self.workflow = WorkflowService()

    async def list_entries(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[TimesheetEntry], int]:
        base = select(TimesheetEntry).where(
            TimesheetEntry.tenant_id == tenant_id,
            TimesheetEntry.employee_id == employee_id,
            TimesheetEntry.is_deleted.is_(False),
        )
        count = await db.execute(select(func.count()).select_from(base.subquery()))
        total = count.scalar_one()
        result = await db.execute(
            base.order_by(TimesheetEntry.work_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def create_entry(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        user_id: uuid.UUID,
        work_date: date,
        hours: Decimal,
        description: str,
    ) -> TimesheetEntry:
        entry = TimesheetEntry(
            tenant_id=tenant_id,
            employee_id=employee_id,
            work_date=work_date,
            hours=hours,
            description=description,
            status="draft",
            created_by=user_id,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def update_entry(
        self, db: AsyncSession, entry: TimesheetEntry, **fields
    ) -> TimesheetEntry:
        if entry.status not in ("draft", "rejected"):
            raise ValueError("Only draft or rejected entries can be edited")
        for key, value in fields.items():
            if value is not None:
                setattr(entry, key, value)
        await db.flush()
        return entry

    async def submit_entry(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        user_id: uuid.UUID,
        entry_id: uuid.UUID,
    ) -> TimesheetEntry:
        result = await db.execute(
            select(TimesheetEntry).where(
                TimesheetEntry.id == entry_id,
                TimesheetEntry.tenant_id == tenant_id,
                TimesheetEntry.employee_id == employee_id,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError("Timesheet entry not found")
        if entry.status not in ("draft", "rejected"):
            raise ValueError("Entry already submitted")
        entry.status = "pending"
        await db.flush()
        try:
            approval = await self.workflow.submit_request(
                db,
                tenant_id=tenant_id,
                request_type="timesheet",
                requester_user_id=user_id,
                requester_employee_id=employee_id,
                payload={
                    "hours": float(entry.hours),
                    "date": str(entry.work_date),
                    "description": entry.description,
                },
                reference_id=entry.id,
                created_by=user_id,
            )
        except ValueError:
            entry.status = "draft"
            await db.flush()
            raise

        if approval.status == "approved":
            entry.status = "approved"
        elif approval.status == "pending":
            entry.status = "pending"
        await db.flush()
        return entry

    async def update_status_on_approval(self, db: AsyncSession, entry_id: uuid.UUID, approved: bool) -> None:
        result = await db.execute(select(TimesheetEntry).where(TimesheetEntry.id == entry_id))
        entry = result.scalar_one_or_none()
        if not entry:
            return
        entry.status = "approved" if approved else "rejected"
        await db.flush()

    async def get_by_id(
        self, db: AsyncSession, tenant_id: uuid.UUID, entry_id: uuid.UUID
    ) -> TimesheetEntry | None:
        result = await db.execute(
            select(TimesheetEntry).where(
                TimesheetEntry.id == entry_id,
                TimesheetEntry.tenant_id == tenant_id,
                TimesheetEntry.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

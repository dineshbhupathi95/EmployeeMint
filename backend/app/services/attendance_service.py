import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AttendanceRecord, WfhRequest


class AttendanceService:
    MODES = ("in_office", "remote", "wfh")

    async def check_in(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        mode: str,
        user_id: uuid.UUID,
    ) -> AttendanceRecord:
        if mode not in self.MODES:
            raise ValueError(f"Invalid mode. Choose from: {', '.join(self.MODES)}")
        today = date.today()
        if mode == "wfh":
            wfh = await self._get_approved_wfh(db, tenant_id, employee_id, today)
            if not wfh:
                raise ValueError("WFH requires manager approval. Submit a WFH request first.")
        result = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date == today,
            )
        )
        record = result.scalar_one_or_none()
        if record and record.check_in:
            raise ValueError("Already checked in today")
        if not record:
            record = AttendanceRecord(
                tenant_id=tenant_id,
                employee_id=employee_id,
                date=today,
                mode=mode,
                created_by=user_id,
            )
            db.add(record)
        record.check_in = datetime.now(UTC)
        record.mode = mode
        record.status = "present"
        await db.flush()
        return record

    async def _get_approved_wfh(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID, target_date: date
    ) -> WfhRequest | None:
        result = await db.execute(
            select(WfhRequest).where(
                WfhRequest.tenant_id == tenant_id,
                WfhRequest.employee_id == employee_id,
                WfhRequest.request_date == target_date,
                WfhRequest.status == "approved",
                WfhRequest.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def request_wfh(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        user_id: uuid.UUID,
        request_date: date,
        reason: str | None,
    ) -> WfhRequest:
        if request_date < date.today():
            raise ValueError("Cannot request WFH for past dates")
        existing = await db.execute(
            select(WfhRequest).where(
                WfhRequest.tenant_id == tenant_id,
                WfhRequest.employee_id == employee_id,
                WfhRequest.request_date == request_date,
                WfhRequest.is_deleted.is_(False),
            )
        )
        wfh = existing.scalar_one_or_none()
        if wfh and wfh.status in ("pending", "approved"):
            raise ValueError(f"WFH request already {wfh.status} for this date")
        if not wfh:
            wfh = WfhRequest(
                tenant_id=tenant_id,
                employee_id=employee_id,
                request_date=request_date,
                reason=reason,
                status="pending",
                created_by=user_id,
            )
            db.add(wfh)
        else:
            wfh.reason = reason
            wfh.status = "pending"
        await db.flush()

        from app.services.workflow_service import WorkflowService

        workflow = WorkflowService()
        await workflow.submit_request(
            db,
            tenant_id=tenant_id,
            request_type="wfh",
            requester_user_id=user_id,
            requester_employee_id=employee_id,
            payload={"date": str(request_date), "reason": reason or ""},
            reference_id=wfh.id,
            created_by=user_id,
        )
        await db.flush()
        return wfh

    async def list_wfh_requests(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID
    ) -> list[WfhRequest]:
        result = await db.execute(
            select(WfhRequest).where(
                WfhRequest.tenant_id == tenant_id,
                WfhRequest.employee_id == employee_id,
                WfhRequest.is_deleted.is_(False),
            ).order_by(WfhRequest.request_date.desc())
        )
        return list(result.scalars().all())

    async def update_wfh_status(self, db: AsyncSession, wfh_id: uuid.UUID, approved: bool) -> None:
        result = await db.execute(select(WfhRequest).where(WfhRequest.id == wfh_id))
        wfh = result.scalar_one_or_none()
        if not wfh:
            return
        wfh.status = "approved" if approved else "rejected"
        await db.flush()

    async def check_out(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID
    ) -> AttendanceRecord:
        today = date.today()
        result = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date == today,
            )
        )
        record = result.scalar_one_or_none()
        if not record or not record.check_in:
            raise ValueError("No check-in found for today")
        if record.check_out:
            raise ValueError("Already checked out today")
        record.check_out = datetime.now(UTC)
        await db.flush()
        return record

    async def get_month(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID, year: int, month: int
    ) -> list[AttendanceRecord]:
        from datetime import date as dt

        start = dt(year, month, 1)
        end = dt(year, month + 1, 1) if month < 12 else dt(year + 1, 1, 1)
        result = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date >= start,
                AttendanceRecord.date < end,
            ).order_by(AttendanceRecord.date)
        )
        return list(result.scalars().all())

    async def team_today(
        self, db: AsyncSession, tenant_id: uuid.UUID, manager_employee_id: uuid.UUID
    ) -> list[AttendanceRecord]:
        from app.services.employee_service import EmployeeService

        members = await EmployeeService().get_all_reportees(db, tenant_id, manager_employee_id)
        team_ids = [m.id for m in members]
        if not team_ids:
            return []
        today = date.today()
        result = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.employee_id.in_(team_ids),
                AttendanceRecord.date == today,
            )
        )
        return list(result.scalars().all())

    async def regularize(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        user_id: uuid.UUID,
        target_date: date,
        mode: str,
        check_in_time,
        check_out_time,
        reason: str,
    ) -> AttendanceRecord:
        if target_date > date.today():
            raise ValueError("Cannot regularize future dates")
        if mode not in self.MODES:
            raise ValueError(f"Invalid mode. Choose from: {', '.join(self.MODES)}")

        result = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date == target_date,
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            record = AttendanceRecord(
                tenant_id=tenant_id,
                employee_id=employee_id,
                date=target_date,
                mode=mode,
                status="regularized",
                notes=reason,
                created_by=user_id,
            )
            db.add(record)
        else:
            record.status = "regularized"
            record.notes = reason

        if check_in_time:
            record.check_in = datetime.combine(target_date, check_in_time, tzinfo=UTC)
        if check_out_time:
            record.check_out = datetime.combine(target_date, check_out_time, tzinfo=UTC)
        record.mode = mode
        await db.flush()

        from app.services.workflow_service import WorkflowService

        workflow = WorkflowService()
        await workflow.submit_request(
            db,
            tenant_id=tenant_id,
            request_type="regularization",
            requester_user_id=user_id,
            requester_employee_id=employee_id,
            payload={"date": str(target_date), "reason": reason},
            reference_id=record.id,
            created_by=user_id,
        )
        await db.flush()
        return record

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LeaveBalance, LeaveRequest, LeaveType
from app.services.workflow_service import WorkflowService


class LeaveService:
    def __init__(self) -> None:
        self.workflow = WorkflowService()

    async def list_types(self, db: AsyncSession, tenant_id: uuid.UUID) -> list[LeaveType]:
        result = await db.execute(
            select(LeaveType).where(
                LeaveType.tenant_id == tenant_id, LeaveType.is_active.is_(True), LeaveType.is_deleted.is_(False)
            )
        )
        return list(result.scalars().all())

    async def get_balances(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID, year: int | None = None
    ) -> list[LeaveBalance]:
        yr = year or date.today().year
        result = await db.execute(
            select(LeaveBalance).where(
                LeaveBalance.tenant_id == tenant_id,
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == yr,
                LeaveBalance.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def ensure_balances(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID, year: int | None = None
    ) -> list[LeaveBalance]:
        """Return existing leave balances only (assigned via employee create/update)."""
        return await self.get_balances(db, tenant_id, employee_id, year)

    async def sync_employee_leave_types(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        leave_type_ids: list[uuid.UUID],
        created_by: uuid.UUID | None = None,
        year: int | None = None,
    ) -> list[LeaveBalance]:
        """Assign selected leave types and allocate annual quotas for the year."""
        yr = year or date.today().year
        selected = list(dict.fromkeys(leave_type_ids))  # preserve order, unique

        types = await self.list_types(db, tenant_id)
        type_map = {t.id: t for t in types}
        for lt_id in selected:
            if lt_id not in type_map:
                raise ValueError("One or more leave types are invalid or inactive")

        result = await db.execute(
            select(LeaveBalance).where(
                LeaveBalance.tenant_id == tenant_id,
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == yr,
            )
        )
        existing = {b.leave_type_id: b for b in result.scalars().all()}
        selected_set = set(selected)
        balances: list[LeaveBalance] = []

        for lt_id in selected:
            lt = type_map[lt_id]
            bal = existing.get(lt_id)
            if bal:
                bal.is_deleted = False
                # Keep used/pending; refresh allocated from leave type when not already used beyond quota
                if bal.used + bal.pending <= lt.annual_quota:
                    bal.allocated = lt.annual_quota
                elif bal.allocated < bal.used + bal.pending:
                    bal.allocated = bal.used + bal.pending
            else:
                bal = LeaveBalance(
                    tenant_id=tenant_id,
                    employee_id=employee_id,
                    leave_type_id=lt_id,
                    year=yr,
                    allocated=lt.annual_quota,
                    created_by=created_by,
                )
                db.add(bal)
            balances.append(bal)

        for lt_id, bal in existing.items():
            if lt_id not in selected_set:
                bal.is_deleted = True

        await db.flush()
        return balances

    async def get_assigned_leave_type_ids(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID, year: int | None = None
    ) -> list[uuid.UUID]:
        balances = await self.get_balances(db, tenant_id, employee_id, year)
        return [b.leave_type_id for b in balances]

    def _calc_days(self, start: date, end: date, is_half_day: bool) -> Decimal:
        days = (end - start).days + 1
        if days < 1:
            raise ValueError("End date must be on or after start date")
        total = Decimal(str(days))
        if is_half_day:
            total = Decimal("0.5")
        return total

    async def apply_leave(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        user_id: uuid.UUID,
        leave_type_id: uuid.UUID,
        start_date: date,
        end_date: date,
        is_half_day: bool,
        half_day_period: str | None,
        reason: str | None,
    ) -> LeaveRequest:
        days = self._calc_days(start_date, end_date, is_half_day)
        balances = await self.ensure_balances(db, tenant_id, employee_id)
        bal = next((b for b in balances if b.leave_type_id == leave_type_id), None)
        if not bal:
            raise ValueError("Leave type is not assigned to this employee")
        available = bal.allocated - bal.used - bal.pending
        if days > available:
            raise ValueError(f"Insufficient balance. Available: {available} days")

        leave_req = LeaveRequest(
            tenant_id=tenant_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            is_half_day=is_half_day,
            half_day_period=half_day_period,
            days=days,
            reason=reason,
            status="pending",
            created_by=user_id,
        )
        db.add(leave_req)
        await db.flush()

        bal.pending += days
        await self.workflow.submit_request(
            db,
            tenant_id=tenant_id,
            request_type="leave",
            requester_user_id=user_id,
            requester_employee_id=employee_id,
            payload={
                "days": float(days),
                "leave_type_id": str(leave_type_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            reference_id=leave_req.id,
            created_by=user_id,
        )
        await db.flush()
        return leave_req

    async def update_request(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: uuid.UUID,
        leave_type_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        is_half_day: bool | None = None,
        half_day_period: str | None = None,
        reason: str | None = None,
    ) -> LeaveRequest:
        result = await db.execute(
            select(LeaveRequest).where(
                LeaveRequest.id == request_id,
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.employee_id == employee_id,
            )
        )
        req = result.scalar_one_or_none()
        if not req:
            raise ValueError("Leave request not found")
        if req.status not in ("pending", "rejected"):
            raise ValueError("Only pending or rejected requests can be edited")

        old_days = req.days
        old_type_id = req.leave_type_id

        if leave_type_id is not None:
            req.leave_type_id = leave_type_id
        if start_date is not None:
            req.start_date = start_date
        if end_date is not None:
            req.end_date = end_date
        if is_half_day is not None:
            req.is_half_day = is_half_day
        if half_day_period is not None:
            req.half_day_period = half_day_period
        if reason is not None:
            req.reason = reason

        new_days = self._calc_days(req.start_date, req.end_date, req.is_half_day)
        req.days = new_days

        if req.status == "pending":
            bal_result = await db.execute(
                select(LeaveBalance).where(
                    LeaveBalance.employee_id == employee_id,
                    LeaveBalance.leave_type_id == old_type_id,
                    LeaveBalance.year == req.start_date.year,
                )
            )
            old_bal = bal_result.scalar_one_or_none()
            if old_bal:
                old_bal.pending -= old_days

            balances = await self.ensure_balances(db, tenant_id, employee_id)
            new_bal = next((b for b in balances if b.leave_type_id == req.leave_type_id), None)
            if not new_bal:
                raise ValueError("Leave type is not assigned to this employee")
            available = new_bal.allocated - new_bal.used - new_bal.pending
            if new_days > available:
                raise ValueError(f"Insufficient balance. Available: {available} days")
            new_bal.pending += new_days
        elif req.status == "rejected":
            req.status = "pending"
            balances = await self.ensure_balances(db, tenant_id, employee_id)
            bal = next((b for b in balances if b.leave_type_id == req.leave_type_id), None)
            if not bal:
                raise ValueError("Leave type is not assigned to this employee")
            available = bal.allocated - bal.used - bal.pending
            if new_days > available:
                raise ValueError(f"Insufficient balance. Available: {available} days")
            bal.pending += new_days
            await self.workflow.submit_request(
                db,
                tenant_id=tenant_id,
                request_type="leave",
                requester_user_id=user_id,
                requester_employee_id=employee_id,
                payload={
                    "days": float(new_days),
                    "leave_type_id": str(req.leave_type_id),
                    "start_date": req.start_date.isoformat(),
                    "end_date": req.end_date.isoformat(),
                },
                reference_id=req.id,
                created_by=user_id,
            )

        await db.flush()
        return req

    async def list_requests(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LeaveRequest], int]:
        q = select(LeaveRequest).where(
            LeaveRequest.tenant_id == tenant_id, LeaveRequest.is_deleted.is_(False)
        )
        if employee_id:
            q = q.where(LeaveRequest.employee_id == employee_id)
        if status:
            q = q.where(LeaveRequest.status == status)

        count = await db.execute(select(func.count()).select_from(q.subquery()))
        total = count.scalar_one()
        result = await db.execute(
            q.order_by(LeaveRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def update_status_on_approval(
        self, db: AsyncSession, leave_request_id: uuid.UUID, approved: bool
    ) -> None:
        result = await db.execute(select(LeaveRequest).where(LeaveRequest.id == leave_request_id))
        req = result.scalar_one_or_none()
        if not req:
            return
        bal_result = await db.execute(
            select(LeaveBalance).where(
                LeaveBalance.employee_id == req.employee_id,
                LeaveBalance.leave_type_id == req.leave_type_id,
                LeaveBalance.year == req.start_date.year,
            )
        )
        bal = bal_result.scalar_one_or_none()
        if approved:
            req.status = "approved"
            if bal:
                bal.pending -= req.days
                bal.used += req.days
        else:
            req.status = "rejected"
            if bal:
                bal.pending -= req.days
        await db.flush()

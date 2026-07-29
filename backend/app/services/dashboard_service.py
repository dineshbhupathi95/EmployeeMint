import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Announcement, Employee, Holiday, Notification
from app.services.finance_service import FinanceService
from app.services.leave_service import LeaveService
from app.services.workflow_service import WorkflowService


class DashboardService:
    def __init__(self) -> None:
        self.leave = LeaveService()
        self.workflow = WorkflowService()

    async def get_summary(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        employee_id: uuid.UUID | None,
        permissions: list[str],
    ) -> dict:
        from app.models import AttendanceRecord, LeaveRequest, TimesheetEntry
        from datetime import date, timedelta

        today = date.today()
        data: dict = {
            "pending_approvals": 0,
            "leave_balances": [],
            "attendance_today": None,
            "team_present": 0,
            "team_total": 0,
            "announcements": [],
            "upcoming_holidays": [],
            "upcoming_birthdays": [],
            "my_pending_leave": 0,
            "my_approved_leave_this_year": 0,
            "unread_notifications": 0,
            "timesheet_drafts": 0,
            "timesheet_pending": 0,
            "headcount": 0,
            "present_today_org": 0,
        }

        # Unread notifications
        data["unread_notifications"] = await NotificationService().unread_count(db, tenant_id, user_id)

        # Upcoming holidays (next 90 days, include today)
        holiday_end = today + timedelta(days=90)
        hol = await db.execute(
            select(Holiday)
            .where(
                Holiday.tenant_id == tenant_id,
                Holiday.is_deleted.is_(False),
                Holiday.date >= today,
                Holiday.date <= holiday_end,
            )
            .order_by(Holiday.date)
            .limit(8)
        )
        data["upcoming_holidays"] = [
            {
                "id": str(h.id),
                "name": h.name,
                "date": str(h.date),
                "is_optional": h.is_optional,
                "weekday": h.date.strftime("%a"),
            }
            for h in hol.scalars().all()
        ]

        if "approvals.view" in permissions or "approvals.action" in permissions:
            pending = await self.workflow.get_pending_for_user(db, user_id, tenant_id)
            data["pending_approvals"] = len(pending)

        if employee_id and ("leave.view.own" in permissions or "leave.apply" in permissions):
            types = await self.leave.list_types(db, tenant_id)
            type_map = {t.id: t.name for t in types}
            balances = await self.leave.get_balances(db, tenant_id, employee_id)
            data["leave_balances"] = [
                {
                    "leave_type_id": str(b.leave_type_id),
                    "leave_type_name": type_map.get(b.leave_type_id, "Leave"),
                    "allocated": float(b.allocated),
                    "used": float(b.used),
                    "pending": float(b.pending),
                    "available": float(b.allocated - b.used - b.pending),
                }
                for b in balances
            ]

            pending_leave = await db.execute(
                select(func.count())
                .select_from(LeaveRequest)
                .where(
                    LeaveRequest.tenant_id == tenant_id,
                    LeaveRequest.employee_id == employee_id,
                    LeaveRequest.status == "pending",
                    LeaveRequest.is_deleted.is_(False),
                )
            )
            data["my_pending_leave"] = pending_leave.scalar_one()

            approved_leave = await db.execute(
                select(func.count())
                .select_from(LeaveRequest)
                .where(
                    LeaveRequest.tenant_id == tenant_id,
                    LeaveRequest.employee_id == employee_id,
                    LeaveRequest.status == "approved",
                    LeaveRequest.is_deleted.is_(False),
                    LeaveRequest.start_date >= date(today.year, 1, 1),
                )
            )
            data["my_approved_leave_this_year"] = approved_leave.scalar_one()

        if employee_id and "attendance.mark.own" in permissions:
            att = await db.execute(
                select(AttendanceRecord).where(
                    AttendanceRecord.employee_id == employee_id,
                    AttendanceRecord.date == today,
                )
            )
            record = att.scalar_one_or_none()
            if record:
                data["attendance_today"] = {
                    "checked_in": record.check_in is not None,
                    "checked_out": record.check_out is not None,
                    "mode": record.mode,
                    "check_in": record.check_in.isoformat() if record.check_in else None,
                    "check_out": record.check_out.isoformat() if record.check_out else None,
                }

        if employee_id and "timesheet.submit" in permissions:
            drafts = await db.execute(
                select(func.count())
                .select_from(TimesheetEntry)
                .where(
                    TimesheetEntry.tenant_id == tenant_id,
                    TimesheetEntry.employee_id == employee_id,
                    TimesheetEntry.status == "draft",
                    TimesheetEntry.is_deleted.is_(False),
                )
            )
            data["timesheet_drafts"] = drafts.scalar_one()
            pending_ts = await db.execute(
                select(func.count())
                .select_from(TimesheetEntry)
                .where(
                    TimesheetEntry.tenant_id == tenant_id,
                    TimesheetEntry.employee_id == employee_id,
                    TimesheetEntry.status == "pending",
                    TimesheetEntry.is_deleted.is_(False),
                )
            )
            data["timesheet_pending"] = pending_ts.scalar_one()

        if employee_id and "employee.view.team" in permissions:
            from app.services.employee_service import EmployeeService

            members, _scope = await EmployeeService().get_my_team(db, tenant_id, employee_id)
            data["team_total"] = len(members)
            if members:
                att = await db.execute(
                    select(func.count())
                    .select_from(AttendanceRecord)
                    .where(
                        AttendanceRecord.employee_id.in_([m.id for m in members]),
                        AttendanceRecord.date == today,
                        AttendanceRecord.check_in.isnot(None),
                    )
                )
                data["team_present"] = att.scalar_one()

        if "employee.view.all" in permissions or "reports.view" in permissions:
            hc = await db.execute(
                select(func.count())
                .select_from(Employee)
                .where(
                    Employee.tenant_id == tenant_id,
                    Employee.is_deleted.is_(False),
                    Employee.employment_status == "active",
                )
            )
            data["headcount"] = hc.scalar_one()
            present = await db.execute(
                select(func.count())
                .select_from(AttendanceRecord)
                .join(Employee, Employee.id == AttendanceRecord.employee_id)
                .where(
                    AttendanceRecord.tenant_id == tenant_id,
                    AttendanceRecord.date == today,
                    AttendanceRecord.check_in.isnot(None),
                    Employee.is_deleted.is_(False),
                )
            )
            data["present_today_org"] = present.scalar_one()

        # Upcoming birthdays (next 30 days) among active employees
        birthday_emps = await db.execute(
            select(Employee).where(
                Employee.tenant_id == tenant_id,
                Employee.is_deleted.is_(False),
                Employee.employment_status == "active",
                Employee.date_of_birth.isnot(None),
            )
        )
        birthdays = []
        for emp in birthday_emps.scalars().all():
            if not emp.date_of_birth:
                continue
            next_bday = emp.date_of_birth.replace(year=today.year)
            if next_bday < today:
                next_bday = emp.date_of_birth.replace(year=today.year + 1)
            if (next_bday - today).days <= 30:
                birthdays.append(
                    {
                        "id": str(emp.id),
                        "name": f"{emp.first_name} {emp.last_name}",
                        "date": str(next_bday),
                        "days_until": (next_bday - today).days,
                    }
                )
        birthdays.sort(key=lambda b: b["days_until"])
        data["upcoming_birthdays"] = birthdays[:6]

        ann = await db.execute(
            select(Announcement)
            .where(
                Announcement.tenant_id == tenant_id,
                Announcement.is_deleted.is_(False),
                Announcement.show_on_dashboard.is_(True),
            )
            .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
            .limit(5)
        )
        data["announcements"] = [
            {"id": str(a.id), "title": a.title, "body": a.body, "is_pinned": a.is_pinned}
            for a in ann.scalars().all()
        ]

        return data


class NotificationService:
    REQUEST_LABELS = {
        "leave": "Leave",
        "wfh": "WFH",
        "regularization": "Attendance regularization",
        "reimbursement": "Reimbursement",
        "timesheet": "Timesheet",
    }

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        body: str,
        notification_type: str,
        metadata: dict | None = None,
        created_by: uuid.UUID | None = None,
    ) -> Notification:
        note = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            metadata_=metadata or {},
            created_by=created_by,
        )
        db.add(note)
        await db.flush()
        return note

    async def unread_count(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
                Notification.is_deleted.is_(False),
            )
        )
        return result.scalar_one()

    async def notify_approval_submitted(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        request: "ApprovalRequest",
        approver_user_id: uuid.UUID | None,
    ) -> None:
        if not approver_user_id:
            return
        from app.models import Employee

        label = self.REQUEST_LABELS.get(request.request_type, request.request_type)
        requester_name = "An employee"
        if request.requester_employee_id:
            result = await db.execute(select(Employee).where(Employee.id == request.requester_employee_id))
            emp = result.scalar_one_or_none()
            if emp:
                requester_name = f"{emp.first_name} {emp.last_name}"

        detail = ""
        if request.request_type == "leave":
            detail = f" from {request.payload.get('start_date', '')} to {request.payload.get('end_date', '')}"
        elif request.request_type == "wfh":
            detail = f" for {request.payload.get('date', '')}"
        elif request.request_type == "timesheet":
            detail = f" — {request.payload.get('hours', '')}h on {request.payload.get('date', '')}"

        await self.create(
            db,
            tenant_id=tenant_id,
            user_id=approver_user_id,
            title=f"New {label} request",
            body=f"{requester_name} submitted a {label.lower()} request{detail} awaiting your approval.",
            notification_type="approval_pending",
            metadata={"request_id": str(request.id), "request_type": request.request_type},
            created_by=request.requester_user_id,
        )

    async def notify_approval_result(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        request: "ApprovalRequest",
        comments: str | None = None,
    ) -> None:
        label = self.REQUEST_LABELS.get(request.request_type, request.request_type)
        if request.status == "approved":
            title = f"{label} request approved"
            body = f"Your {label.lower()} request has been approved."
        else:
            title = f"{label} request rejected"
            body = f"Your {label.lower()} request was rejected."
            if comments:
                body += f" Reason: {comments}"

        await self.create(
            db,
            tenant_id=tenant_id,
            user_id=request.requester_user_id,
            title=title,
            body=body,
            notification_type=f"approval_{request.status}",
            metadata={"request_id": str(request.id), "request_type": request.request_type},
        )

    async def notify_onboarding_assigned(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_user_id: uuid.UUID,
        employee_name: str,
        task_count: int,
        created_by: uuid.UUID | None = None,
        task_title: str | None = None,
    ) -> None:
        if task_title:
            title = "New onboarding task"
            body = f"You have a new onboarding task: {task_title}. Complete it from Profile → Documents / Onboarding."
        else:
            title = "Onboarding checklist assigned"
            body = (
                f"Hi {employee_name.split()[0]}, {task_count} onboarding task"
                f"{'s' if task_count != 1 else ''} assigned. "
                "Upload identity, bank & tax documents in Profile and mark tasks complete."
            )
        await self.create(
            db,
            tenant_id=tenant_id,
            user_id=employee_user_id,
            title=title,
            body=body,
            notification_type="onboarding_assigned",
            metadata={"task_count": task_count},
            created_by=created_by,
        )

    async def list_for_user(
        self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, unread_only: bool = False
    ) -> list[Notification]:
        q = select(Notification).where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
            Notification.is_deleted.is_(False),
        )
        if unread_only:
            q = q.where(Notification.is_read.is_(False))
        result = await db.execute(q.order_by(Notification.created_at.desc()).limit(50))
        return list(result.scalars().all())

    async def mark_read(self, db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> None:
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        n = result.scalar_one_or_none()
        if n:
            n.is_read = True
            n.read_at = datetime.now(UTC)
            await db.flush()


class OrganizationService:
    async def get_org_tree(self, db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
        result = await db.execute(
            select(Employee)
            .options(
                selectinload(Employee.department),
                selectinload(Employee.designation),
            )
            .where(Employee.tenant_id == tenant_id, Employee.is_deleted.is_(False))
            .order_by(Employee.first_name)
        )
        employees = result.scalars().all()
        nodes = {}
        for e in employees:
            nodes[str(e.id)] = {
                "id": str(e.id),
                "name": f"{e.first_name} {e.last_name}",
                "employee_code": e.employee_code,
                "designation": e.designation.name if e.designation else None,
                "department": e.department.name if e.department else None,
                "reports_to": str(e.reports_to_employee_id) if e.reports_to_employee_id else None,
                "children": [],
            }
        roots = []
        for node in nodes.values():
            parent_id = node["reports_to"]
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(node)
            else:
                roots.append(node)
        return roots

    async def list_holidays(self, db: AsyncSession, tenant_id: uuid.UUID, year: int) -> list[Holiday]:
        from datetime import date as dt

        start = dt(year, 1, 1)
        end = dt(year + 1, 1, 1)
        result = await db.execute(
            select(Holiday).where(
                Holiday.tenant_id == tenant_id,
                Holiday.date >= start,
                Holiday.date < end,
                Holiday.is_deleted.is_(False),
            ).order_by(Holiday.date)
        )
        return list(result.scalars().all())

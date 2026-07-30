import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, require_permission
from app.core.database import get_db
from app.models import AttendanceRecord, Department, Employee, LeaveRequest, LeaveType

router = APIRouter(prefix="/reports", tags=["reports"])


async def _get_summary(db: AsyncSession, tenant_id) -> dict:
    headcount = await db.execute(
        select(func.count()).select_from(Employee).where(
            Employee.tenant_id == tenant_id, Employee.is_deleted.is_(False), Employee.employment_status == "active"
        )
    )
    pending_leave = await db.execute(
        select(func.count()).select_from(LeaveRequest).where(
            LeaveRequest.tenant_id == tenant_id, LeaveRequest.status == "pending", LeaveRequest.is_deleted.is_(False)
        )
    )
    today = date.today()
    present_today = await db.execute(
        select(func.count()).select_from(AttendanceRecord).where(
            AttendanceRecord.tenant_id == tenant_id,
            AttendanceRecord.date == today,
            AttendanceRecord.check_in.isnot(None),
        )
    )
    approved_leave = await db.execute(
        select(func.count()).select_from(LeaveRequest).where(
            LeaveRequest.tenant_id == tenant_id, LeaveRequest.status == "approved", LeaveRequest.is_deleted.is_(False)
        )
    )
    return {
        "headcount": headcount.scalar_one(),
        "pending_leave_requests": pending_leave.scalar_one(),
        "present_today": present_today.scalar_one(),
        "approved_leave_requests": approved_leave.scalar_one(),
    }


async def _get_analytics(db: AsyncSession, tenant_id) -> dict:
    today = date.today()
    start_14 = today - timedelta(days=13)

    # Headcount by department (active employees)
    dept_rows = await db.execute(
        select(
            func.coalesce(Department.name, "Unassigned").label("name"),
            func.count(Employee.id).label("count"),
        )
        .select_from(Employee)
        .outerjoin(Department, Employee.department_id == Department.id)
        .where(
            Employee.tenant_id == tenant_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == "active",
        )
        .group_by(Department.name)
        .order_by(func.count(Employee.id).desc())
    )
    headcount_by_department = [
        {"name": row.name, "value": row.count} for row in dept_rows.all()
    ]

    # Employment status breakdown
    status_rows = await db.execute(
        select(Employee.employment_status, func.count(Employee.id))
        .where(Employee.tenant_id == tenant_id, Employee.is_deleted.is_(False))
        .group_by(Employee.employment_status)
        .order_by(func.count(Employee.id).desc())
    )
    employment_status = [
        {"name": (row[0] or "unknown").replace("_", " ").title(), "value": row[1]}
        for row in status_rows.all()
    ]

    # Leave requests by status
    leave_status_rows = await db.execute(
        select(LeaveRequest.status, func.count(LeaveRequest.id))
        .where(LeaveRequest.tenant_id == tenant_id, LeaveRequest.is_deleted.is_(False))
        .group_by(LeaveRequest.status)
        .order_by(func.count(LeaveRequest.id).desc())
    )
    leave_by_status = [
        {"name": (row[0] or "unknown").replace("_", " ").title(), "value": row[1]}
        for row in leave_status_rows.all()
    ]

    # Leave requests by type
    leave_type_rows = await db.execute(
        select(LeaveType.name, func.count(LeaveRequest.id))
        .select_from(LeaveRequest)
        .join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)
        .where(LeaveRequest.tenant_id == tenant_id, LeaveRequest.is_deleted.is_(False))
        .group_by(LeaveType.name)
        .order_by(func.count(LeaveRequest.id).desc())
    )
    leave_by_type = [
        {"name": row[0], "value": row[1]} for row in leave_type_rows.all()
    ]

    # Attendance trend — last 14 days (checked-in count per day)
    att_trend_rows = await db.execute(
        select(
            AttendanceRecord.date,
            func.count(
                case((AttendanceRecord.check_in.isnot(None), 1))
            ).label("present"),
            func.count(AttendanceRecord.id).label("records"),
        )
        .where(
            AttendanceRecord.tenant_id == tenant_id,
            AttendanceRecord.date >= start_14,
            AttendanceRecord.date <= today,
        )
        .group_by(AttendanceRecord.date)
        .order_by(AttendanceRecord.date)
    )
    by_date = {row.date: {"present": row.present, "records": row.records} for row in att_trend_rows.all()}
    attendance_trend = []
    for i in range(14):
        d = start_14 + timedelta(days=i)
        day = by_date.get(d, {"present": 0, "records": 0})
        attendance_trend.append(
            {
                "date": d.isoformat(),
                "label": d.strftime("%b %d"),
                "present": day["present"],
                "records": day["records"],
            }
        )

    # Attendance mode (last 14 days)
    mode_rows = await db.execute(
        select(AttendanceRecord.mode, func.count(AttendanceRecord.id))
        .where(
            AttendanceRecord.tenant_id == tenant_id,
            AttendanceRecord.date >= start_14,
            AttendanceRecord.date <= today,
        )
        .group_by(AttendanceRecord.mode)
        .order_by(func.count(AttendanceRecord.id).desc())
    )
    attendance_by_mode = [
        {"name": (row[0] or "unknown").replace("_", " ").title(), "value": row[1]}
        for row in mode_rows.all()
    ]

    summary = await _get_summary(db, tenant_id)
    absent_today = max(summary["headcount"] - summary["present_today"], 0)

    return {
        "summary": {
            **summary,
            "absent_today": absent_today,
        },
        "headcount_by_department": headcount_by_department,
        "employment_status": employment_status,
        "leave_by_status": leave_by_status,
        "leave_by_type": leave_by_type,
        "attendance_trend": attendance_trend,
        "attendance_by_mode": attendance_by_mode,
        "attendance_today": [
            {"name": "Present", "value": summary["present_today"]},
            {"name": "Not checked in", "value": absent_today},
        ],
    }


@router.get("/summary")
async def reports_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports.view")),
):
    return await _get_summary(db, current_user.tenant_id)


@router.get("/analytics")
async def reports_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports.view")),
):
    return await _get_analytics(db, current_user.tenant_id)


@router.get("/export")
async def export_report(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports.view")),
):
    tenant_id = current_user.tenant_id
    today = date.today()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["EmployeeMint HR Report"])
    writer.writerow(["Generated", today.isoformat()])
    writer.writerow([])

    writer.writerow(["SUMMARY"])
    summary = await _get_summary(db, tenant_id)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Active Headcount", summary["headcount"]])
    writer.writerow(["Present Today", summary["present_today"]])
    writer.writerow(["Pending Leave Requests", summary["pending_leave_requests"]])
    writer.writerow(["Approved Leave Requests", summary["approved_leave_requests"]])
    writer.writerow([])

    writer.writerow(["EMPLOYEES"])
    writer.writerow(["Employee ID", "First Name", "Last Name", "Work Email", "Status", "Department"])
    emp_result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.department))
        .where(Employee.tenant_id == tenant_id, Employee.is_deleted.is_(False))
        .order_by(Employee.employee_code)
    )
    for e in emp_result.scalars().all():
        writer.writerow([
            e.employee_code,
            e.first_name,
            e.last_name,
            e.work_email or "",
            e.employment_status,
            e.department.name if e.department else "",
        ])
    writer.writerow([])

    writer.writerow(["LEAVE REQUESTS"])
    writer.writerow(["Employee Code", "Leave Type", "Start", "End", "Days", "Status", "Reason"])
    leave_types_result = await db.execute(select(LeaveType).where(LeaveType.tenant_id == tenant_id))
    leave_type_map = {lt.id: lt.name for lt in leave_types_result.scalars().all()}

    leave_result = await db.execute(
        select(LeaveRequest, Employee)
        .join(Employee, LeaveRequest.employee_id == Employee.id)
        .where(LeaveRequest.tenant_id == tenant_id, LeaveRequest.is_deleted.is_(False))
        .order_by(LeaveRequest.created_at.desc())
    )
    for req, emp in leave_result.all():
        writer.writerow([
            emp.employee_code,
            leave_type_map.get(req.leave_type_id, ""),
            req.start_date.isoformat(),
            req.end_date.isoformat(),
            float(req.days),
            req.status,
            req.reason or "",
        ])
    writer.writerow([])

    writer.writerow(["ATTENDANCE TODAY"])
    writer.writerow(["Employee ID", "Name", "Mode", "Check In", "Check Out", "Status"])
    att_result = await db.execute(
        select(AttendanceRecord, Employee)
        .join(Employee, AttendanceRecord.employee_id == Employee.id)
        .where(AttendanceRecord.tenant_id == tenant_id, AttendanceRecord.date == today)
        .order_by(Employee.first_name)
    )
    for rec, emp in att_result.all():
        writer.writerow([
            emp.employee_code,
            f"{emp.first_name} {emp.last_name}",
            rec.mode,
            rec.check_in.isoformat() if rec.check_in else "",
            rec.check_out.isoformat() if rec.check_out else "",
            rec.status,
        ])

    output.seek(0)
    filename = f"employeemint-report-{today.isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

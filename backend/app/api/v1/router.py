from fastapi import APIRouter

from app.api.v1 import (
    approvals,
    attendance,
    auth,
    dashboard,
    documents,
    employees,
    finance,
    leave,
    lifecycle,
    platform,
    reports,
    settings,
    setup,
    timesheets,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(platform.router)
api_router.include_router(setup.router)
api_router.include_router(employees.router)
api_router.include_router(leave.router)
api_router.include_router(attendance.router)
api_router.include_router(finance.router)
api_router.include_router(approvals.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(settings.router)
api_router.include_router(lifecycle.router)
api_router.include_router(timesheets.router)
api_router.include_router(documents.router)

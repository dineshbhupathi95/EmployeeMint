"""Seed default tenant configuration on provisioning."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ApprovalWorkflow,
    ApprovalWorkflowStep,
    LeaveType,
    OnboardingChecklist,
    OfferLetterTemplate,
    ReimbursementCategory,
)

DEFAULT_LEAVE_TYPES = [
    {"name": "Casual Leave", "code": "CL", "annual_quota": Decimal("12"), "is_paid": True},
    {"name": "Sick Leave", "code": "SL", "annual_quota": Decimal("10"), "is_paid": True, "requires_document": True},
    {"name": "Earned Leave", "code": "EL", "annual_quota": Decimal("15"), "is_paid": True},
]

DEFAULT_REIMBURSEMENT_CATEGORIES = [
    {"name": "Travel", "description": "Local and outstation travel"},
    {"name": "Meals", "description": "Business meals and refreshments"},
    {"name": "Office Supplies", "description": "Stationery and supplies"},
]

DEFAULT_WORKFLOWS = [
    {
        "name": "Leave Approval",
        "request_type": "leave",
        "steps": [{"step_order": 1, "approver_rule": "direct_manager"}],
    },
    {
        "name": "Reimbursement Approval",
        "request_type": "reimbursement",
        "steps": [{"step_order": 1, "approver_rule": "direct_manager"}],
    },
    {
        "name": "Attendance Regularization",
        "request_type": "regularization",
        "steps": [{"step_order": 1, "approver_rule": "direct_manager"}],
    },
    {
        "name": "WFH Approval",
        "request_type": "wfh",
        "steps": [{"step_order": 1, "approver_rule": "direct_manager"}],
    },
    {
        "name": "Timesheet Approval",
        "request_type": "timesheet",
        "steps": [{"step_order": 1, "approver_rule": "direct_manager"}],
    },
]

DEFAULT_ONBOARDING_CHECKLIST = {
    "name": "Standard Onboarding",
    "description": "Default new hire checklist",
}

DEFAULT_OFFER_TEMPLATE = {
    "name": "Standard Offer Letter",
    "body_html": (
        "<p>Dear {{candidate_name}},</p>"
        "<p>We are pleased to offer you the position of {{designation}} at {{company_name}}.</p>"
        "<p>CTC: {{ctc}} | Joining: {{joining_date}}</p>"
    ),
}


async def ensure_missing_workflows(
    db: AsyncSession, tenant_id: uuid.UUID, created_by: uuid.UUID | None = None
) -> list[str]:
    """Add any DEFAULT_WORKFLOWS that are missing for this tenant (e.g. timesheet for older tenants)."""
    from sqlalchemy import select

    result = await db.execute(
        select(ApprovalWorkflow.request_type).where(
            ApprovalWorkflow.tenant_id == tenant_id,
            ApprovalWorkflow.is_deleted.is_(False),
        )
    )
    existing = {row[0] for row in result.all()}
    added: list[str] = []
    for wf_template in DEFAULT_WORKFLOWS:
        if wf_template["request_type"] in existing:
            continue
        wf = ApprovalWorkflow(
            tenant_id=tenant_id,
            created_by=created_by,
            name=wf_template["name"],
            request_type=wf_template["request_type"],
            is_active=True,
        )
        db.add(wf)
        await db.flush()
        for step in wf_template["steps"]:
            db.add(ApprovalWorkflowStep(workflow_id=wf.id, **step))
        added.append(wf_template["request_type"])
    if added:
        await db.flush()
    return added


async def seed_tenant_defaults(db: AsyncSession, tenant_id: uuid.UUID, created_by: uuid.UUID | None) -> None:
    for lt in DEFAULT_LEAVE_TYPES:
        db.add(LeaveType(tenant_id=tenant_id, created_by=created_by, **lt))

    for cat in DEFAULT_REIMBURSEMENT_CATEGORIES:
        db.add(ReimbursementCategory(tenant_id=tenant_id, created_by=created_by, **cat))

    await ensure_missing_workflows(db, tenant_id, created_by)

    db.add(
        OnboardingChecklist(
            tenant_id=tenant_id,
            created_by=created_by,
            **DEFAULT_ONBOARDING_CHECKLIST,
        )
    )
    db.add(
        OfferLetterTemplate(
            tenant_id=tenant_id,
            created_by=created_by,
            **DEFAULT_OFFER_TEMPLATE,
        )
    )
    await db.flush()

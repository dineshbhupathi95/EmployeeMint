import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ApprovalRequest,
    ApprovalRequestStep,
    ApprovalWorkflow,
    ApprovalWorkflowStep,
    Employee,
    User,
)


class WorkflowService:
    async def _resolve_approver(
        self,
        db: AsyncSession,
        rule: str,
        rule_value: str | None,
        requester_employee_id: uuid.UUID | None,
        tenant_id: uuid.UUID,
    ) -> uuid.UUID | None:
        if not requester_employee_id:
            return None

        result = await db.execute(
            select(Employee).where(Employee.id == requester_employee_id, Employee.tenant_id == tenant_id)
        )
        requester = result.scalar_one_or_none()
        if not requester:
            return None

        if rule == "direct_manager":
            if requester.reports_to_employee_id:
                mgr = await db.execute(
                    select(Employee).where(Employee.id == requester.reports_to_employee_id)
                )
                manager = mgr.scalar_one_or_none()
                return manager.user_id if manager else None

        elif rule == "specific_user" and rule_value:
            user_result = await db.execute(
                select(User).where(User.id == uuid.UUID(rule_value), User.tenant_id == tenant_id)
            )
            user = user_result.scalar_one_or_none()
            return user.id if user else None

        elif rule == "department_head" and requester.department_id:
            from app.models import Department

            dept_result = await db.execute(
                select(Department).where(Department.id == requester.department_id)
            )
            dept = dept_result.scalar_one_or_none()
            if dept and dept.head_employee_id:
                head = await db.execute(select(Employee).where(Employee.id == dept.head_employee_id))
                head_emp = head.scalar_one_or_none()
                return head_emp.user_id if head_emp else None

        elif rule == "role" and rule_value:
            from app.models import Role, UserRole

            role_result = await db.execute(
                select(Role).where(Role.tenant_id == tenant_id, Role.name == rule_value)
            )
            role = role_result.scalar_one_or_none()
            if role:
                ur_result = await db.execute(
                    select(UserRole).where(UserRole.role_id == role.id).limit(1)
                )
                ur = ur_result.scalar_one_or_none()
                return ur.user_id if ur else None

        return None

    def _evaluate_condition(self, step: ApprovalWorkflowStep, payload: dict) -> bool:
        if not step.condition_field:
            return True
        value = payload.get(step.condition_field)
        if value is None:
            return True
        op = step.condition_operator
        target = step.condition_value
        if op == "gt":
            return float(value) > float(target)
        if op == "gte":
            return float(value) >= float(target)
        if op == "eq":
            return str(value) == str(target)
        return True

    async def submit_request(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        request_type: str,
        requester_user_id: uuid.UUID,
        requester_employee_id: uuid.UUID | None,
        payload: dict[str, Any],
        reference_id: uuid.UUID | None = None,
        created_by: uuid.UUID | None = None,
    ) -> ApprovalRequest:
        # Ensure newer workflow types (timesheet, wfh) exist for older tenants
        from app.core.tenant_defaults import ensure_missing_workflows

        await ensure_missing_workflows(db, tenant_id, created_by)

        wf_result = await db.execute(
            select(ApprovalWorkflow)
            .options(selectinload(ApprovalWorkflow.steps))
            .where(
                ApprovalWorkflow.tenant_id == tenant_id,
                ApprovalWorkflow.request_type == request_type,
                ApprovalWorkflow.is_active.is_(True),
                ApprovalWorkflow.is_deleted.is_(False),
            )
        )
        workflow = wf_result.scalar_one_or_none()
        if not workflow or not workflow.steps:
            raise ValueError(
                f"No approval workflow configured for '{request_type}'. "
                "Ask an admin to enable it under Settings → Workflows."
            )

        applicable_steps = [
            s for s in workflow.steps if self._evaluate_condition(s, payload)
        ]
        if not applicable_steps:
            applicable_steps = list(workflow.steps)

        request = ApprovalRequest(
            tenant_id=tenant_id,
            request_type=request_type,
            requester_user_id=requester_user_id,
            requester_employee_id=requester_employee_id,
            payload=payload,
            reference_id=reference_id,
            status="pending",
            current_step_order=1,
            created_by=created_by,
        )
        db.add(request)
        await db.flush()

        for step in applicable_steps:
            approver_id = await self._resolve_approver(
                db, step.approver_rule, step.approver_value, requester_employee_id, tenant_id
            )
            if step.approver_rule == "direct_manager" and not approver_id:
                raise ValueError(
                    "No reporting manager assigned. Ask HR to set your manager on the employee profile "
                    "before submitting for approval."
                )
            if not approver_id:
                raise ValueError(
                    f"Could not resolve approver for rule '{step.approver_rule}'. "
                    "Check workflow configuration."
                )
            db.add(
                ApprovalRequestStep(
                    request_id=request.id,
                    step_order=step.step_order,
                    approver_user_id=approver_id,
                    status="pending",
                )
            )
        await db.flush()

        from app.services.dashboard_service import NotificationService

        notifier = NotificationService()
        step_result = await db.execute(
            select(ApprovalRequestStep).where(
                ApprovalRequestStep.request_id == request.id,
                ApprovalRequestStep.step_order == request.current_step_order,
            )
        )
        first_step = step_result.scalar_one_or_none()
        if first_step:
            await notifier.notify_approval_submitted(
                db,
                tenant_id=tenant_id,
                request=request,
                approver_user_id=first_step.approver_user_id,
            )

        return request

    async def act_on_step(
        self,
        db: AsyncSession,
        *,
        step_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        action: str,
        comments: str | None = None,
    ) -> ApprovalRequest:
        result = await db.execute(
            select(ApprovalRequestStep)
            .options(selectinload(ApprovalRequestStep.request).selectinload(ApprovalRequest.steps))
            .where(ApprovalRequestStep.id == step_id)
        )
        step = result.scalar_one_or_none()
        if not step:
            raise ValueError("Approval step not found")
        if step.status != "pending":
            raise ValueError("Step already actioned")
        if step.approver_user_id and step.approver_user_id != actor_user_id:
            raise ValueError("Not authorized to act on this step")

        step.status = action
        step.comments = comments
        step.acted_at = datetime.now(UTC)
        request = step.request

        if action == "rejected":
            request.status = "rejected"
        else:
            pending = [s for s in request.steps if s.status == "pending" and s.id != step.id]
            if not pending:
                request.status = "approved"
            else:
                next_step = min(s.step_order for s in pending)
                request.current_step_order = next_step

        await db.flush()

        from app.services.dashboard_service import NotificationService

        notifier = NotificationService()
        if request.status in ("approved", "rejected"):
            await notifier.notify_approval_result(
                db,
                tenant_id=request.tenant_id,
                request=request,
                comments=comments,
            )
        elif request.status == "pending":
            next_step = next(
                (s for s in request.steps if s.status == "pending" and s.step_order == request.current_step_order),
                None,
            )
            if next_step:
                await notifier.notify_approval_submitted(
                    db,
                    tenant_id=request.tenant_id,
                    request=request,
                    approver_user_id=next_step.approver_user_id,
                )

        return request

    async def get_pending_for_user(
        self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[ApprovalRequest]:
        result = await db.execute(
            select(ApprovalRequest)
            .join(ApprovalRequestStep)
            .options(selectinload(ApprovalRequest.steps))
            .where(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.status == "pending",
                ApprovalRequestStep.approver_user_id == user_id,
                ApprovalRequestStep.status == "pending",
                ApprovalRequestStep.step_order == ApprovalRequest.current_step_order,
            )
            .order_by(ApprovalRequest.created_at.desc())
        )
        return list(result.scalars().unique().all())

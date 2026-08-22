import re
import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Employee, EmployeeCompensation, OfferLetter, Payslip, ReimbursementCategory, ReimbursementClaim, User
from app.services.tax_service import compute_income_tax, compute_professional_tax_monthly
from app.services.workflow_service import WorkflowService


def parse_ctc_annual(ctc: str | None) -> Decimal | None:
    if not ctc or not ctc.strip():
        return None
    text = ctc.lower().replace(",", "").replace("₹", "").replace("inr", "").strip()
    match = re.search(r"[\d.]+", text)
    if not match:
        return None
    value = Decimal(match.group())
    if "lpa" in text or "lac" in text or "lakh" in text:
        return (value * Decimal("100000")).quantize(Decimal("0.01"))
    if "cr" in text or "crore" in text:
        return (value * Decimal("10000000")).quantize(Decimal("0.01"))
    if value < Decimal("1000"):
        return (value * Decimal("100000")).quantize(Decimal("0.01"))
    return value.quantize(Decimal("0.01"))


def build_salary_breakdown(
    ctc_annual: Decimal | None,
    *,
    tax_regime: str = "new",
) -> tuple[dict, dict, Decimal | None, Decimal | None, dict | None]:
    if not ctc_annual or ctc_annual <= 0:
        return {}, {}, None, None, None

    basic_annual = (ctc_annual * Decimal("0.40")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    hra_annual = (ctc_annual * Decimal("0.20")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    special_annual = ctc_annual - basic_annual - hra_annual

    basic_monthly = (basic_annual / 12).quantize(Decimal("0.01"), ROUND_HALF_UP)
    hra_monthly = (hra_annual / 12).quantize(Decimal("0.01"), ROUND_HALF_UP)
    special_monthly = (special_annual / 12).quantize(Decimal("0.01"), ROUND_HALF_UP)
    gross_monthly = (ctc_annual / 12).quantize(Decimal("0.01"), ROUND_HALF_UP)

    pf = (basic_monthly * Decimal("0.12")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    pf_annual = (pf * 12).quantize(Decimal("0.01"), ROUND_HALF_UP)
    professional_tax = compute_professional_tax_monthly(gross_monthly)

    regime = "old" if tax_regime == "old" else "new"
    tax = compute_income_tax(
        annual_gross=ctc_annual,
        employee_pf_annual=pf_annual,
        regime=regime,
    )
    tax_estimate = Decimal(str(tax["monthly_tds"]))

    net_monthly = gross_monthly - pf - professional_tax - tax_estimate

    earnings = {
        "basic": float(basic_monthly),
        "hra": float(hra_monthly),
        "special_allowance": float(special_monthly),
    }
    deductions = {
        "pf": float(pf),
        "professional_tax": float(professional_tax),
        "income_tax_tds": float(tax_estimate),
    }
    return earnings, deductions, gross_monthly, net_monthly, tax


class FinanceService:
    def __init__(self) -> None:
        self.workflow = WorkflowService()

    def compute_pay_from_ctc(self, ctc: str | None, tax_regime: str = "new") -> dict:
        ctc_annual = parse_ctc_annual(ctc)
        earnings, deductions, gross, net, tax = build_salary_breakdown(
            ctc_annual, tax_regime=tax_regime
        )
        return {
            "ctc_annual": float(ctc_annual) if ctc_annual is not None else None,
            "gross_monthly": float(gross) if gross is not None else None,
            "net_monthly": float(net) if net is not None else None,
            "earnings": earnings,
            "deductions": deductions,
            "tax_computation": tax,
        }

    async def _find_employee_by_email(
        self, db: AsyncSession, tenant_id: uuid.UUID, email: str
    ) -> Employee | None:
        normalized = email.lower().strip()
        result = await db.execute(
            select(Employee)
            .outerjoin(User, Employee.user_id == User.id)
            .where(
                Employee.tenant_id == tenant_id,
                Employee.is_deleted.is_(False),
                or_(
                    func.lower(Employee.work_email) == normalized,
                    func.lower(User.email) == normalized,
                ),
            )
        )
        return result.scalar_one_or_none()

    async def get_compensation(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID
    ) -> EmployeeCompensation | None:
        result = await db.execute(
            select(EmployeeCompensation).where(
                EmployeeCompensation.tenant_id == tenant_id,
                EmployeeCompensation.employee_id == employee_id,
                EmployeeCompensation.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    def enrichment_for_compensation(
        self, comp: EmployeeCompensation, tax_regime: str | None = None
    ) -> dict:
        """Recompute tax/net from CTC so My Pay always shows current automatic tax rules."""
        regime = tax_regime or (comp.deductions or {}).get("tax_regime") or "new"
        if isinstance(regime, str) and regime not in ("new", "old"):
            regime = "new"
        earnings, deductions, gross, net, tax = build_salary_breakdown(
            comp.ctc_annual, tax_regime=str(regime)
        )
        if not tax:
            return {
                "earnings": comp.earnings or {},
                "deductions": comp.deductions or {},
                "gross_monthly": comp.gross_monthly,
                "net_monthly": comp.net_monthly,
                "tax_computation": None,
            }
        deductions_out = {**deductions, "tax_regime": regime}
        return {
            "earnings": earnings,
            "deductions": deductions_out,
            "gross_monthly": gross,
            "net_monthly": net,
            "tax_computation": tax,
        }

    async def upsert_compensation(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        user_id: uuid.UUID | None,
        ctc: str | None,
        designation: str | None = None,
        joining_date: date | None = None,
        source: str = "admin",
        offer_letter_id: uuid.UUID | None = None,
        tax_regime: str = "new",
        earnings: dict | None = None,
        deductions: dict | None = None,
        gross_monthly: Decimal | None = None,
        net_monthly: Decimal | None = None,
    ) -> EmployeeCompensation:
        ctc_annual = parse_ctc_annual(ctc)
        regime = "old" if tax_regime == "old" else "new"
        if earnings is None or deductions is None:
            calc_earnings, calc_deductions, calc_gross, calc_net, _tax = build_salary_breakdown(
                ctc_annual, tax_regime=regime
            )
            earnings = earnings or calc_earnings
            deductions = {**(deductions or calc_deductions), "tax_regime": regime}
            gross_monthly = gross_monthly or calc_gross
            net_monthly = net_monthly or calc_net
        else:
            deductions = {**deductions, "tax_regime": regime}

        existing = await self.get_compensation(db, tenant_id, employee_id)
        if existing:
            existing.ctc = ctc
            existing.ctc_annual = ctc_annual
            existing.designation = designation
            existing.joining_date = joining_date
            existing.earnings = earnings
            existing.deductions = deductions
            existing.gross_monthly = gross_monthly
            existing.net_monthly = net_monthly
            existing.source = source
            existing.offer_letter_id = offer_letter_id
            await db.flush()
            return existing

        comp = EmployeeCompensation(
            tenant_id=tenant_id,
            employee_id=employee_id,
            created_by=user_id,
            ctc=ctc,
            ctc_annual=ctc_annual,
            designation=designation,
            joining_date=joining_date,
            earnings=earnings,
            deductions=deductions,
            gross_monthly=gross_monthly,
            net_monthly=net_monthly,
            source=source,
            offer_letter_id=offer_letter_id,
        )
        db.add(comp)
        await db.flush()
        return comp

    async def sync_compensation_from_offer(
        self, db: AsyncSession, tenant_id: uuid.UUID, offer: OfferLetter, user_id: uuid.UUID | None = None
    ) -> EmployeeCompensation | None:
        employee = None
        if offer.employee_id:
            employee = await db.get(Employee, offer.employee_id)
        if not employee:
            employee = await self._find_employee_by_email(db, tenant_id, offer.candidate_email)
        if not employee:
            return None
        return await self.upsert_compensation(
            db,
            tenant_id=tenant_id,
            employee_id=employee.id,
            user_id=user_id,
            ctc=offer.ctc,
            designation=offer.designation,
            joining_date=offer.joining_date,
            source="offer_letter",
            offer_letter_id=offer.id,
            tax_regime="new",
        )

    async def try_sync_offer_for_new_employee(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee: Employee, user_id: uuid.UUID | None = None
    ) -> EmployeeCompensation | None:
        emails: list[str] = []
        if employee.work_email:
            emails.append(employee.work_email)
        if employee.user_id:
            user = await db.get(User, employee.user_id)
            if user and user.email:
                emails.append(user.email)
        for email in emails:
            result = await db.execute(
                select(OfferLetter)
                .where(
                    OfferLetter.tenant_id == tenant_id,
                    OfferLetter.is_deleted.is_(False),
                    OfferLetter.status.in_(["released", "accepted"]),
                    func.lower(OfferLetter.candidate_email) == email.lower().strip(),
                )
                .order_by(OfferLetter.updated_at.desc())
            )
            offer = result.scalar_one_or_none()
            if offer:
                return await self.sync_compensation_from_offer(db, tenant_id, offer, user_id)
        return None

    async def list_payslips(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID
    ) -> list[Payslip]:
        result = await db.execute(
            select(Payslip)
            .where(Payslip.tenant_id == tenant_id, Payslip.employee_id == employee_id)
            .order_by(Payslip.year.desc(), Payslip.month.desc())
        )
        return list(result.scalars().all())

    async def list_categories(self, db: AsyncSession, tenant_id: uuid.UUID) -> list[ReimbursementCategory]:
        result = await db.execute(
            select(ReimbursementCategory).where(
                ReimbursementCategory.tenant_id == tenant_id,
                ReimbursementCategory.is_active.is_(True),
                ReimbursementCategory.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def submit_reimbursement(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        amount: Decimal,
        expense_date: date,
        description: str | None,
    ) -> ReimbursementClaim:
        claim = ReimbursementClaim(
            tenant_id=tenant_id,
            employee_id=employee_id,
            category_id=category_id,
            amount=amount,
            expense_date=expense_date,
            description=description,
            status="pending",
            created_by=user_id,
        )
        db.add(claim)
        await db.flush()
        await self.workflow.submit_request(
            db,
            tenant_id=tenant_id,
            request_type="reimbursement",
            requester_user_id=user_id,
            requester_employee_id=employee_id,
            payload={"amount": float(amount), "category_id": str(category_id)},
            reference_id=claim.id,
            created_by=user_id,
        )
        await db.flush()
        return claim

    async def list_claims(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReimbursementClaim], int]:
        q = select(ReimbursementClaim).where(
            ReimbursementClaim.tenant_id == tenant_id, ReimbursementClaim.is_deleted.is_(False)
        )
        if employee_id:
            q = q.where(ReimbursementClaim.employee_id == employee_id)
        count = await db.execute(select(func.count()).select_from(q.subquery()))
        total = count.scalar_one()
        result = await db.execute(
            q.order_by(ReimbursementClaim.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def update_claim_status(
        self, db: AsyncSession, claim_id: uuid.UUID, approved: bool
    ) -> None:
        result = await db.execute(select(ReimbursementClaim).where(ReimbursementClaim.id == claim_id))
        claim = result.scalar_one_or_none()
        if claim:
            claim.status = "approved" if approved else "rejected"
            await db.flush()

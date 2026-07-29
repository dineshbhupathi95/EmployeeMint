"""India income-tax estimate for payroll TDS (simplified)."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

Regime = Literal["new", "old"]

Q = Decimal("0.01")
ZERO = Decimal("0")


def _q(value: Decimal) -> Decimal:
    return value.quantize(Q, rounding=ROUND_HALF_UP)


def _apply_slabs(taxable: Decimal, slabs: list[tuple[Decimal, Decimal]]) -> tuple[Decimal, list[dict]]:
    """slabs: list of (upper_limit, rate). last upper can be None-like huge."""
    tax = ZERO
    breakdown: list[dict] = []
    lower = ZERO
    remaining = max(taxable, ZERO)

    for upper, rate in slabs:
        if remaining <= 0:
            break
        span = upper - lower if upper is not None else remaining
        band = min(remaining, span)
        if band > 0:
            band_tax = _q(band * rate)
            tax += band_tax
            breakdown.append(
                {
                    "from": float(lower),
                    "to": float(upper) if upper is not None else None,
                    "rate_percent": float(rate * 100),
                    "taxable_in_slab": float(band),
                    "tax": float(band_tax),
                }
            )
            remaining -= band
        lower = upper if upper is not None else lower

    return _q(tax), breakdown


# FY 2025-26 new regime (Budget 2025) — used as default for FY 2026-27 estimates
NEW_REGIME_SLABS: list[tuple[Decimal | None, Decimal]] = [
    (Decimal("400000"), Decimal("0")),
    (Decimal("800000"), Decimal("0.05")),
    (Decimal("1200000"), Decimal("0.10")),
    (Decimal("1600000"), Decimal("0.15")),
    (Decimal("2000000"), Decimal("0.20")),
    (Decimal("2400000"), Decimal("0.25")),
    (None, Decimal("0.30")),
]

# Classic old regime slabs (simplified)
OLD_REGIME_SLABS: list[tuple[Decimal | None, Decimal]] = [
    (Decimal("250000"), Decimal("0")),
    (Decimal("500000"), Decimal("0.05")),
    (Decimal("1000000"), Decimal("0.20")),
    (None, Decimal("0.30")),
]


def compute_income_tax(
    *,
    annual_gross: Decimal,
    employee_pf_annual: Decimal = ZERO,
    regime: Regime = "new",
    financial_year: str = "2025-26",
) -> dict:
    """
    Estimate annual income tax + monthly TDS from taxable salary.

    Uses standard deduction and section 87A rebate rules for the selected regime.
    Old regime also applies a simple 80C estimate capped at employee PF (max ₹1.5L).
    """
    if annual_gross <= 0:
        return {
            "regime": regime,
            "financial_year": financial_year,
            "annual_gross": 0.0,
            "standard_deduction": 0.0,
            "chapter_via_deductions": 0.0,
            "taxable_income": 0.0,
            "tax_before_rebate": 0.0,
            "rebate_87a": 0.0,
            "tax_before_cess": 0.0,
            "cess": 0.0,
            "annual_tax": 0.0,
            "monthly_tds": 0.0,
            "slab_breakdown": [],
            "notes": "No taxable income.",
        }

    if regime == "new":
        standard_deduction = Decimal("75000")
        chapter_via = ZERO
        slabs = NEW_REGIME_SLABS
        # Budget 2025: income up to ₹12L effectively nil tax via rebate (after std deduction framing)
        rebate_limit_income = Decimal("1200000")
        max_rebate = Decimal("60000")  # practical cap for estimate
        notes = (
            f"New tax regime FY {financial_year}: standard deduction ₹75,000; "
            "section 87A rebate applied when eligible. Employer contributions / exemptions not itemized."
        )
    else:
        standard_deduction = Decimal("50000")
        chapter_via = min(max(employee_pf_annual, ZERO), Decimal("150000"))
        slabs = OLD_REGIME_SLABS
        rebate_limit_income = Decimal("500000")
        max_rebate = Decimal("12500")
        notes = (
            f"Old tax regime FY {financial_year}: standard deduction ₹50,000; "
            "80C estimated from employee PF (max ₹1.5L). HRA/other exemptions not applied."
        )

    taxable = _q(max(annual_gross - standard_deduction - chapter_via, ZERO))
    tax_before_rebate, slab_breakdown = _apply_slabs(taxable, slabs)

    rebate = ZERO
    if taxable <= rebate_limit_income:
        rebate = min(tax_before_rebate, max_rebate)
        # For new regime Budget 2025, taxable income ≤ 12L → full rebate to nil
        if regime == "new" and taxable <= Decimal("1200000"):
            rebate = tax_before_rebate

    tax_before_cess = _q(max(tax_before_rebate - rebate, ZERO))
    cess = _q(tax_before_cess * Decimal("0.04"))
    annual_tax = _q(tax_before_cess + cess)
    monthly_tds = _q(annual_tax / 12)

    return {
        "regime": regime,
        "financial_year": financial_year,
        "annual_gross": float(_q(annual_gross)),
        "standard_deduction": float(standard_deduction),
        "chapter_via_deductions": float(_q(chapter_via)),
        "taxable_income": float(taxable),
        "tax_before_rebate": float(tax_before_rebate),
        "rebate_87a": float(_q(rebate)),
        "tax_before_cess": float(tax_before_cess),
        "cess": float(cess),
        "annual_tax": float(annual_tax),
        "monthly_tds": float(monthly_tds),
        "slab_breakdown": slab_breakdown,
        "notes": notes,
    }


def compute_professional_tax_monthly(gross_monthly: Decimal) -> Decimal:
    """Simplified professional tax (Maharashtra-style monthly estimate)."""
    if gross_monthly <= Decimal("7500"):
        return ZERO
    if gross_monthly <= Decimal("10000"):
        return Decimal("175.00")
    return Decimal("200.00")

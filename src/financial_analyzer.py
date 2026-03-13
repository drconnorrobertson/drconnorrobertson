"""Financial underwriting engine for STR deals.

Calculates all expenses, mortgage payments, and cash-on-cash returns.
"""

import math
from typing import Any

from src.models import (
    Deal,
    ExpenseBreakdown,
    PermitInfo,
    Property,
    RevenueEstimate,
)


def calculate_monthly_mortgage(
    loan_amount: float, annual_rate: float, term_years: int
) -> float:
    """Calculate monthly P&I payment using standard amortization formula."""
    if loan_amount <= 0 or annual_rate <= 0:
        return 0.0
    monthly_rate = annual_rate / 12
    n_payments = term_years * 12
    payment = loan_amount * (
        (monthly_rate * math.pow(1 + monthly_rate, n_payments))
        / (math.pow(1 + monthly_rate, n_payments) - 1)
    )
    return payment


def calculate_cash_invested(price: float, config: dict[str, Any]) -> float:
    """Calculate total cash required to close and prepare the property."""
    fa = config["financial_assumptions"]
    down_payment = price * fa["down_payment_pct"]
    closing_costs = price * fa["closing_cost_pct"]
    improvements = fa["improvement_budget"]
    furnishing = fa["furnishing_budget"]
    return down_payment + closing_costs + improvements + furnishing


def calculate_expenses(
    prop: Property,
    revenue: RevenueEstimate,
    config: dict[str, Any],
) -> ExpenseBreakdown:
    """Calculate all annual operating expenses."""
    fa = config["financial_assumptions"]
    exp = config["expenses"]

    loan_amount = prop.price * (1 - fa["down_payment_pct"])
    monthly_mortgage = calculate_monthly_mortgage(
        loan_amount, fa["interest_rate"], fa["loan_term_years"]
    )

    # Property tax: use Zillow data if available, else estimate 1% of price
    property_tax = prop.property_tax_annual if prop.property_tax_annual else prop.price * 0.01

    # HOA: use Zillow data if available
    hoa_annual = (prop.hoa_monthly * 12) if prop.hoa_monthly else 0.0

    # Cleaning: number of turnovers per year based on occupancy and avg stay
    occupied_nights = revenue.occupancy_rate * 365
    turnovers = occupied_nights / exp["avg_stay_nights"]
    cleaning = turnovers * exp["cleaning_per_turnover"]

    return ExpenseBreakdown(
        mortgage_annual=monthly_mortgage * 12,
        property_tax=property_tax,
        insurance=exp["insurance_annual"],
        hoa_annual=hoa_annual,
        property_management=revenue.annual_revenue * exp["property_management_pct"],
        utilities=exp["utilities_monthly"] * 12,
        maintenance=prop.price * exp["maintenance_pct"],
        cleaning=cleaning,
        platform_fees=revenue.annual_revenue * exp["platform_fee_pct"],
        supplies=exp["supplies_monthly"] * 12,
        str_permit=exp["str_permit_annual"],
        accounting=exp["accounting_annual"],
        furniture_reserve=revenue.annual_revenue * exp["furniture_reserve_pct"],
        landscaping=exp["landscaping_monthly"] * 12,
    )


def analyze_deal(
    prop: Property,
    revenue: RevenueEstimate,
    permit: PermitInfo,
    config: dict[str, Any],
) -> Deal:
    """Perform full financial analysis and return a Deal."""
    expenses = calculate_expenses(prop, revenue, config)
    cash_invested = calculate_cash_invested(prop.price, config)
    annual_cash_flow = revenue.annual_revenue - expenses.total
    cash_on_cash = annual_cash_flow / cash_invested if cash_invested > 0 else 0.0

    return Deal(
        property=prop,
        revenue=revenue,
        expenses=expenses,
        permit=permit,
        cash_invested=cash_invested,
        annual_cash_flow=annual_cash_flow,
        cash_on_cash_return=cash_on_cash,
    )

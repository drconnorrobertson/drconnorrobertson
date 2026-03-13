"""Tests for the financial analyzer module."""

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.financial_analyzer import (
    analyze_deal,
    calculate_cash_invested,
    calculate_expenses,
    calculate_monthly_mortgage,
)
from src.models import (
    Confidence,
    ExpenseBreakdown,
    PermitInfo,
    PermitStatus,
    Property,
    RevenueEstimate,
    RevenueSource,
)

SAMPLE_CONFIG = {
    "financial_assumptions": {
        "down_payment_pct": 0.10,
        "loan_term_years": 30,
        "interest_rate": 0.07,
        "closing_cost_pct": 0.03,
        "improvement_budget": 25000,
        "furnishing_budget": 15000,
    },
    "expenses": {
        "insurance_annual": 4000,
        "property_management_pct": 0.22,
        "utilities_monthly": 400,
        "maintenance_pct": 0.015,
        "cleaning_per_turnover": 150,
        "avg_stay_nights": 3.5,
        "platform_fee_pct": 0.03,
        "supplies_monthly": 100,
        "str_permit_annual": 500,
        "accounting_annual": 1500,
        "furniture_reserve_pct": 0.03,
        "landscaping_monthly": 150,
    },
}


def make_property(price=500000, tax=5000, hoa=None, bedrooms=3):
    return Property(
        zpid="123",
        address="123 Main St",
        city="Gatlinburg",
        state="TN",
        zipcode="37738",
        price=price,
        bedrooms=bedrooms,
        bathrooms=2.0,
        property_tax_annual=tax,
        hoa_monthly=hoa,
        market="Gatlinburg, TN",
    )


def make_revenue(annual=70000, nightly=275, occupancy=0.70):
    return RevenueEstimate(
        annual_revenue=annual,
        nightly_rate=nightly,
        occupancy_rate=occupancy,
    )


class TestMonthlyMortgage:
    def test_basic_calculation(self):
        # $450k loan at 7% for 30 years -> ~$2,994/mo
        payment = calculate_monthly_mortgage(450000, 0.07, 30)
        assert 2990 < payment < 3000

    def test_zero_loan(self):
        assert calculate_monthly_mortgage(0, 0.07, 30) == 0.0

    def test_zero_rate(self):
        assert calculate_monthly_mortgage(100000, 0, 30) == 0.0

    def test_known_value(self):
        # $200k at 6% for 30yr -> $1,199.10
        payment = calculate_monthly_mortgage(200000, 0.06, 30)
        assert abs(payment - 1199.10) < 1.0


class TestCashInvested:
    def test_basic(self):
        # $500k: 10% down ($50k) + 3% closing ($15k) + $25k improve + $15k furnish = $105k
        result = calculate_cash_invested(500000, SAMPLE_CONFIG)
        assert result == 105000

    def test_max_price(self):
        # $900k: $90k + $27k + $25k + $15k = $157k
        result = calculate_cash_invested(900000, SAMPLE_CONFIG)
        assert result == 157000


class TestExpenses:
    def test_all_expenses_included(self):
        prop = make_property()
        rev = make_revenue()
        expenses = calculate_expenses(prop, rev, SAMPLE_CONFIG)

        assert expenses.mortgage_annual > 0
        assert expenses.property_tax == 5000
        assert expenses.insurance == 4000
        assert expenses.hoa_annual == 0
        assert expenses.property_management == 70000 * 0.22
        assert expenses.utilities == 400 * 12
        assert expenses.maintenance == 500000 * 0.015
        assert expenses.cleaning > 0
        assert expenses.platform_fees == 70000 * 0.03
        assert expenses.supplies == 100 * 12
        assert expenses.str_permit == 500
        assert expenses.accounting == 1500
        assert expenses.furniture_reserve == 70000 * 0.03
        assert expenses.landscaping == 150 * 12

    def test_hoa_included_when_present(self):
        prop = make_property(hoa=300)
        rev = make_revenue()
        expenses = calculate_expenses(prop, rev, SAMPLE_CONFIG)
        assert expenses.hoa_annual == 3600

    def test_property_tax_fallback(self):
        prop = make_property(tax=None)
        rev = make_revenue()
        expenses = calculate_expenses(prop, rev, SAMPLE_CONFIG)
        assert expenses.property_tax == 500000 * 0.01

    def test_total_is_sum(self):
        prop = make_property()
        rev = make_revenue()
        expenses = calculate_expenses(prop, rev, SAMPLE_CONFIG)
        manual_total = (
            expenses.mortgage_annual
            + expenses.property_tax
            + expenses.insurance
            + expenses.hoa_annual
            + expenses.property_management
            + expenses.utilities
            + expenses.maintenance
            + expenses.cleaning
            + expenses.platform_fees
            + expenses.supplies
            + expenses.str_permit
            + expenses.accounting
            + expenses.furniture_reserve
            + expenses.landscaping
        )
        assert abs(expenses.total - manual_total) < 0.01


class TestAnalyzeDeal:
    def test_deal_assembly(self):
        prop = make_property()
        rev = make_revenue()
        permit = PermitInfo(status=PermitStatus.ALLOWED)
        deal = analyze_deal(prop, rev, permit, SAMPLE_CONFIG)

        assert deal.cash_invested == 105000
        assert deal.annual_cash_flow == rev.annual_revenue - deal.expenses.total
        assert deal.cash_on_cash_return == deal.annual_cash_flow / deal.cash_invested

    def test_good_deal_flag(self):
        # High revenue relative to price — needs strong revenue to beat all expenses
        prop = make_property(price=200000, tax=2000)
        rev = make_revenue(annual=120000, nightly=450, occupancy=0.73)
        permit = PermitInfo(status=PermitStatus.ALLOWED)
        deal = analyze_deal(prop, rev, permit, SAMPLE_CONFIG)
        assert deal.cash_on_cash_return > 0.10
        assert deal.is_good_deal is True

    def test_banned_permit_not_good_deal(self):
        prop = make_property(price=300000)
        rev = make_revenue(annual=80000, occupancy=0.75)
        permit = PermitInfo(status=PermitStatus.BANNED)
        deal = analyze_deal(prop, rev, permit, SAMPLE_CONFIG)
        assert deal.is_good_deal is False

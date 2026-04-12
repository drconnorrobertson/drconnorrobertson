"""MACRS depreciation calculation engine."""

import math
from datetime import date

# MACRS half-year convention depreciation rates (200% declining balance)
MACRS_RATES = {
    5: [0.2000, 0.3200, 0.1920, 0.1152, 0.1152, 0.0576],
    7: [0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446],
    15: [
        0.0500, 0.0950, 0.0855, 0.0770, 0.0693, 0.0623, 0.0590, 0.0590,
        0.0591, 0.0590, 0.0591, 0.0590, 0.0591, 0.0590, 0.0591, 0.0295,
    ],
}

# Straight-line rates for real property (mid-month convention)
# Month placed in service -> first year percentage
SL_FIRST_YEAR_27_5 = {
    1: 3.485, 2: 3.182, 3: 2.879, 4: 2.576, 5: 2.273, 6: 1.970,
    7: 1.667, 8: 1.364, 9: 1.061, 10: 0.758, 11: 0.455, 12: 0.152,
}

SL_FIRST_YEAR_39 = {
    1: 2.461, 2: 2.247, 3: 2.033, 4: 1.819, 5: 1.605, 6: 1.391,
    7: 1.177, 8: 0.963, 9: 0.749, 10: 0.535, 11: 0.321, 12: 0.107,
}


def calculate_macrs_depreciation(cost, recovery_period, placed_in_service_date, years=None):
    """Calculate MACRS depreciation schedule for an asset.

    Args:
        cost: Cost basis of the asset.
        recovery_period: IRS recovery period (5, 7, 15, 27.5, or 39).
        placed_in_service_date: Date the asset was placed in service.
        years: Number of years to calculate (defaults to recovery_period + 1).

    Returns:
        List of dicts with year, depreciation, accumulated, and remaining book value.
    """
    if isinstance(placed_in_service_date, str):
        placed_in_service_date = date.fromisoformat(placed_in_service_date)

    month_placed = placed_in_service_date.month
    start_year = placed_in_service_date.year

    schedule = []
    accumulated = 0.0

    if recovery_period in MACRS_RATES:
        rates = MACRS_RATES[recovery_period]
        calc_years = years or len(rates)
        for i in range(min(calc_years, len(rates))):
            depreciation = round(cost * rates[i], 2)
            accumulated = round(accumulated + depreciation, 2)
            remaining = round(cost - accumulated, 2)
            schedule.append({
                "year": start_year + i,
                "year_number": i + 1,
                "depreciation": depreciation,
                "accumulated": accumulated,
                "book_value": max(remaining, 0),
            })
    elif recovery_period == 27.5:
        annual_rate = 100.0 / 27.5  # ~3.636%
        first_year_pct = SL_FIRST_YEAR_27_5.get(month_placed, 3.485)
        calc_years = years or 29
        for i in range(calc_years):
            if i == 0:
                pct = first_year_pct
            elif i < 28:
                pct = annual_rate
            elif i == 28:
                pct = annual_rate * (12 - month_placed + 0.5) / 12
            else:
                pct = 0
            depreciation = round(cost * pct / 100.0, 2)
            accumulated = round(accumulated + depreciation, 2)
            if accumulated > cost:
                depreciation = round(depreciation - (accumulated - cost), 2)
                accumulated = cost
            remaining = round(cost - accumulated, 2)
            schedule.append({
                "year": start_year + i,
                "year_number": i + 1,
                "depreciation": depreciation,
                "accumulated": accumulated,
                "book_value": max(remaining, 0),
            })
    elif recovery_period == 39:
        annual_rate = 100.0 / 39.0  # ~2.564%
        first_year_pct = SL_FIRST_YEAR_39.get(month_placed, 2.461)
        calc_years = years or 40
        for i in range(calc_years):
            if i == 0:
                pct = first_year_pct
            elif i < 39:
                pct = annual_rate
            elif i == 39:
                pct = annual_rate * (12 - month_placed + 0.5) / 12
            else:
                pct = 0
            depreciation = round(cost * pct / 100.0, 2)
            accumulated = round(accumulated + depreciation, 2)
            if accumulated > cost:
                depreciation = round(depreciation - (accumulated - cost), 2)
                accumulated = cost
            remaining = round(cost - accumulated, 2)
            schedule.append({
                "year": start_year + i,
                "year_number": i + 1,
                "depreciation": depreciation,
                "accumulated": accumulated,
                "book_value": max(remaining, 0),
            })

    return schedule


def calculate_bonus_depreciation(cost, bonus_rate):
    """Calculate first-year bonus depreciation.

    Args:
        cost: Cost basis eligible for bonus depreciation.
        bonus_rate: Bonus depreciation rate (e.g. 1.0 for 100%, 0.60 for 60%).

    Returns:
        Bonus depreciation amount.
    """
    return round(cost * bonus_rate, 2)


def get_bonus_rate_for_year(year):
    """Get the applicable bonus depreciation rate for a given tax year.

    Based on Tax Cuts and Jobs Act phase-down schedule.

    Args:
        year: Tax year.

    Returns:
        Bonus depreciation rate as a decimal.
    """
    if year <= 2022:
        return 1.00
    elif year == 2023:
        return 0.80
    elif year == 2024:
        return 0.60
    elif year == 2025:
        return 0.40
    elif year == 2026:
        return 0.20
    else:
        return 0.00

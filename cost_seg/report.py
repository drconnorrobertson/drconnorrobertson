"""Cost Segregation Report Generator.

Generates detailed cost segregation study reports for commercial
and residential rental properties.
"""

import json
import os
from datetime import date, datetime

from .classifications import ASSET_CLASSES, DEFAULT_ALLOCATIONS
from .depreciation import (
    calculate_bonus_depreciation,
    calculate_macrs_depreciation,
    get_bonus_rate_for_year,
)


def load_property(path):
    """Load property data from a JSON file."""
    with open(path) as f:
        return json.load(f)


def classify_property(property_data):
    """Classify property components into IRS depreciation categories.

    Args:
        property_data: Dict with property details. Required keys:
            - property_name: Name/address of the property
            - property_type: Type (office, retail, restaurant, etc.)
            - cost_basis: Total depreciable cost basis (excluding land)
            - placed_in_service: Date placed in service (YYYY-MM-DD)
            Optional keys:
            - allocations: Custom dict of asset class -> percentage
            - components: List of dicts with category, description, cost
            - land_value: Value of land (excluded from depreciation)
            - tax_rate: Combined federal+state tax rate (default 0.37)

    Returns:
        Dict with classified components and summary.
    """
    property_type = property_data.get("property_type", "office").lower()
    cost_basis = property_data["cost_basis"]
    land_value = property_data.get("land_value", 0)

    # Use custom allocations if provided, otherwise use defaults
    if "allocations" in property_data:
        allocations = property_data["allocations"]
    elif "components" in property_data:
        # Build allocations from explicit component list
        allocations = {}
        for comp in property_data["components"]:
            cat = comp["category"]
            allocations[cat] = allocations.get(cat, 0) + comp["cost"]
        # Convert to percentages
        total = sum(allocations.values())
        allocations = {k: v / total for k, v in allocations.items()}
    else:
        allocations = DEFAULT_ALLOCATIONS.get(property_type)
        if not allocations:
            allocations = DEFAULT_ALLOCATIONS["office"]

    # Calculate cost for each category
    classified = {}
    allocated_total = 0
    for category, pct in allocations.items():
        amount = round(cost_basis * pct, 2)
        allocated_total += amount
        classified[category] = {
            "category": category,
            "description": ASSET_CLASSES[category]["description"],
            "recovery_period": ASSET_CLASSES[category]["recovery_period"],
            "percentage": round(pct * 100, 2),
            "cost": amount,
            "components": ASSET_CLASSES[category]["components"],
        }

    # Adjust rounding difference on the largest category
    diff = round(cost_basis - allocated_total, 2)
    if diff != 0:
        largest = max(classified.keys(), key=lambda k: classified[k]["cost"])
        classified[largest]["cost"] = round(classified[largest]["cost"] + diff, 2)

    return {
        "property": property_data,
        "land_value": land_value,
        "depreciable_basis": cost_basis,
        "classified": classified,
    }


def generate_depreciation_schedules(classification, years=10):
    """Generate depreciation schedules for all classified components.

    Args:
        classification: Output from classify_property().
        years: Number of years to show in the schedule.

    Returns:
        Dict with depreciation schedules and tax savings analysis.
    """
    placed_in_service = classification["property"]["placed_in_service"]
    pis_date = date.fromisoformat(placed_in_service)
    tax_year = pis_date.year
    tax_rate = classification["property"].get("tax_rate", 0.37)
    bonus_rate = get_bonus_rate_for_year(tax_year)

    schedules = {}
    total_first_year_deduction = 0.0
    total_standard_first_year = 0.0

    for category, info in classification["classified"].items():
        cost = info["cost"]
        recovery = info["recovery_period"]

        # Bonus depreciation applies to 5, 7, and 15-year property
        if recovery in (5, 7, 15) and bonus_rate > 0:
            bonus = calculate_bonus_depreciation(cost, bonus_rate)
            remaining_basis = cost - bonus
        else:
            bonus = 0
            remaining_basis = cost

        schedule = calculate_macrs_depreciation(
            remaining_basis, recovery, placed_in_service, years=years
        )

        # First year deduction = bonus + first year regular depreciation
        first_year_regular = schedule[0]["depreciation"] if schedule else 0
        first_year_total = bonus + first_year_regular
        total_first_year_deduction += first_year_total

        # Standard depreciation (without cost seg) assumes all 39-year
        standard_schedule = calculate_macrs_depreciation(
            cost, 39, placed_in_service, years=1
        )
        standard_first = standard_schedule[0]["depreciation"] if standard_schedule else 0
        total_standard_first_year += standard_first

        schedules[category] = {
            "category": category,
            "cost": cost,
            "bonus_depreciation": bonus,
            "bonus_rate": bonus_rate,
            "remaining_basis": remaining_basis,
            "schedule": schedule,
            "first_year_total": round(first_year_total, 2),
            "standard_first_year": round(standard_first, 2),
        }

    # For standard comparison, calculate as if everything is 39-year
    total_cost = classification["depreciable_basis"]
    standard_all = calculate_macrs_depreciation(total_cost, 39, placed_in_service, years=1)
    standard_first_year_total = standard_all[0]["depreciation"] if standard_all else 0

    additional_first_year = round(total_first_year_deduction - standard_first_year_total, 2)
    tax_savings = round(additional_first_year * tax_rate, 2)

    return {
        "schedules": schedules,
        "summary": {
            "total_cost_basis": total_cost,
            "bonus_rate": bonus_rate,
            "tax_rate": tax_rate,
            "accelerated_first_year": round(total_first_year_deduction, 2),
            "standard_first_year": round(standard_first_year_total, 2),
            "additional_deductions": additional_first_year,
            "estimated_tax_savings": tax_savings,
        },
    }


def format_currency(amount):
    """Format a number as currency."""
    return f"${amount:,.2f}"


def format_percentage(pct):
    """Format a number as a percentage."""
    return f"{pct:.1f}%"


def generate_report(property_data, output_dir="reports", years=10):
    """Generate a full cost segregation report.

    Args:
        property_data: Property dict or path to JSON file.
        output_dir: Directory for output files.
        years: Number of years for depreciation schedule.

    Returns:
        Path to the generated report file.
    """
    if isinstance(property_data, str):
        property_data = load_property(property_data)

    classification = classify_property(property_data)
    depreciation = generate_depreciation_schedules(classification, years=years)
    summary = depreciation["summary"]

    prop = property_data
    pis = prop["placed_in_service"]
    report_date = datetime.now().strftime("%B %d, %Y")

    lines = []
    w = lines.append

    # Header
    w("=" * 78)
    w("                    AE COST SEGREGATION STUDY REPORT")
    w("=" * 78)
    w("")
    w(f"  Report Date:          {report_date}")
    w(f"  Property:             {prop['property_name']}")
    if prop.get("address"):
        w(f"  Address:              {prop['address']}")
    w(f"  Property Type:        {prop.get('property_type', 'N/A').title()}")
    w(f"  Placed in Service:    {pis}")
    w(f"  Total Cost Basis:     {format_currency(prop['cost_basis'])}")
    if prop.get("land_value"):
        w(f"  Land Value:           {format_currency(prop['land_value'])}")
        w(f"  Depreciable Basis:    {format_currency(classification['depreciable_basis'])}")
    w(f"  Tax Rate (assumed):   {format_percentage(summary['tax_rate'] * 100)}")
    w(f"  Bonus Depr. Rate:     {format_percentage(summary['bonus_rate'] * 100)}")
    w("")

    # Executive Summary
    w("-" * 78)
    w("  EXECUTIVE SUMMARY")
    w("-" * 78)
    w("")
    w(f"  Accelerated First-Year Depreciation:    {format_currency(summary['accelerated_first_year'])}")
    w(f"  Standard First-Year Depreciation:       {format_currency(summary['standard_first_year'])}")
    w(f"  Additional First-Year Deductions:       {format_currency(summary['additional_deductions'])}")
    w("")
    w(f"  >>> ESTIMATED FIRST-YEAR TAX SAVINGS:   {format_currency(summary['estimated_tax_savings'])} <<<")
    w("")

    # Asset Classification Summary
    w("-" * 78)
    w("  ASSET CLASSIFICATION SUMMARY")
    w("-" * 78)
    w("")
    w(f"  {'Category':<30} {'% of Basis':>12} {'Cost':>18}")
    w(f"  {'-'*30} {'-'*12} {'-'*18}")

    for category in ["5-year", "7-year", "15-year", "27.5-year", "39-year"]:
        if category in classification["classified"]:
            info = classification["classified"][category]
            w(f"  {info['description']:<30} {format_percentage(info['percentage']):>12} {format_currency(info['cost']):>18}")

    w(f"  {'-'*30} {'-'*12} {'-'*18}")
    w(f"  {'TOTAL':<30} {'100.0%':>12} {format_currency(classification['depreciable_basis']):>18}")
    w("")

    # Reclassified Assets Detail
    accelerated_total = 0
    w("-" * 78)
    w("  RECLASSIFIED ASSETS (Accelerated Depreciation)")
    w("-" * 78)
    w("")

    for category in ["5-year", "7-year", "15-year"]:
        if category not in classification["classified"]:
            continue
        info = classification["classified"][category]
        sched = depreciation["schedules"][category]
        accelerated_total += info["cost"]

        w(f"  {info['description']}")
        w(f"  Cost: {format_currency(info['cost'])}  |  "
          f"Bonus Depr: {format_currency(sched['bonus_depreciation'])}  |  "
          f"First-Year Total: {format_currency(sched['first_year_total'])}")
        w("")
        w(f"  Typical components:")
        for comp in info["components"][:5]:
            w(f"    - {comp}")
        w("")

    w(f"  Total Reclassified: {format_currency(accelerated_total)} "
      f"({format_percentage(accelerated_total / classification['depreciable_basis'] * 100)} of basis)")
    w("")

    # Depreciation Comparison Table
    w("-" * 78)
    w("  DEPRECIATION SCHEDULE COMPARISON (First 10 Years)")
    w("-" * 78)
    w("")
    w(f"  {'Year':<6} {'Accelerated':>16} {'Standard (39-yr)':>18} {'Difference':>16}")
    w(f"  {'-'*6} {'-'*16} {'-'*18} {'-'*16}")

    standard_schedule = calculate_macrs_depreciation(
        classification["depreciable_basis"], 39, pis, years=years
    )

    for yr_idx in range(min(years, len(standard_schedule))):
        std_depr = standard_schedule[yr_idx]["depreciation"]
        accel_depr = 0.0
        for cat_sched in depreciation["schedules"].values():
            if yr_idx == 0:
                accel_depr += cat_sched["bonus_depreciation"]
            if yr_idx < len(cat_sched["schedule"]):
                accel_depr += cat_sched["schedule"][yr_idx]["depreciation"]
        accel_depr = round(accel_depr, 2)
        diff = round(accel_depr - std_depr, 2)
        year_num = standard_schedule[yr_idx]["year"]
        w(f"  {year_num:<6} {format_currency(accel_depr):>16} {format_currency(std_depr):>18} {format_currency(diff):>16}")

    w("")

    # Disclaimer
    w("-" * 78)
    w("  DISCLAIMER")
    w("-" * 78)
    w("")
    w("  This cost segregation study is prepared for estimation purposes. Actual")
    w("  results may vary based on detailed engineering analysis, IRS audit, and")
    w("  specific property conditions. This report should be reviewed by a")
    w("  qualified tax professional before filing. AE Cost Seg recommends")
    w("  engaging a licensed engineer for the formal engineering-based study.")
    w("")
    w("=" * 78)
    w(f"  Generated by AE Cost Seg Report Generator")
    w("=" * 78)

    report_text = "\n".join(lines)

    # Write report to file
    os.makedirs(output_dir, exist_ok=True)
    safe_name = prop["property_name"].replace(" ", "_").replace("/", "-")
    filename = f"CostSeg_{safe_name}_{pis}.txt"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        f.write(report_text)

    # Also write a JSON summary
    json_path = os.path.join(output_dir, f"CostSeg_{safe_name}_{pis}.json")
    json_output = {
        "property": prop,
        "classification": {
            k: {kk: vv for kk, vv in v.items() if kk != "components"}
            for k, v in classification["classified"].items()
        },
        "summary": summary,
        "report_file": filepath,
        "generated": report_date,
    }
    with open(json_path, "w") as f:
        json.dump(json_output, f, indent=2)

    return filepath, report_text

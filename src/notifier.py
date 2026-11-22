"""Output formatting and CSV export for STR deals."""

import csv
import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.models import Deal

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")
console = Console()


class Notifier:
    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def print_deal(self, deal: Deal) -> None:
        """Print a formatted deal summary to the terminal."""
        prop = deal.property
        rev = deal.revenue
        exp = deal.expenses

        quality = "[bold green]GOOD DEAL[/]" if deal.is_good_deal else "[yellow]MARGINAL[/]"

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Label", style="bold")
        table.add_column("Value")

        table.add_row("Address", prop.full_address)
        table.add_row("Price", f"${prop.price:,.0f}")
        table.add_row("Bed/Bath", f"{prop.bedrooms}bd / {prop.bathrooms}ba")
        table.add_row("Sqft", f"{prop.sqft:,}" if prop.sqft else "N/A")
        table.add_row("", "")
        table.add_row("Est. Annual Revenue", f"${rev.annual_revenue:,.0f}")
        table.add_row("  Nightly Rate", f"${rev.nightly_rate:,.0f}")
        table.add_row("  Occupancy", f"{rev.occupancy_rate:.0%}")
        table.add_row("  Data Source", f"{rev.source.value} ({rev.confidence.value})")
        table.add_row("", "")
        table.add_row("EXPENSES", "")
        table.add_row("  Mortgage (P&I)", f"${exp.mortgage_annual:,.0f}")
        table.add_row("  Property Tax", f"${exp.property_tax:,.0f}")
        table.add_row("  Insurance", f"${exp.insurance:,.0f}")
        if exp.hoa_annual > 0:
            table.add_row("  HOA", f"${exp.hoa_annual:,.0f}")
        table.add_row("  Property Mgmt", f"${exp.property_management:,.0f}")
        table.add_row("  Utilities", f"${exp.utilities:,.0f}")
        table.add_row("  Maintenance", f"${exp.maintenance:,.0f}")
        table.add_row("  Cleaning", f"${exp.cleaning:,.0f}")
        table.add_row("  Platform Fees", f"${exp.platform_fees:,.0f}")
        table.add_row("  Supplies", f"${exp.supplies:,.0f}")
        table.add_row("  STR Permit", f"${exp.str_permit:,.0f}")
        table.add_row("  Accounting", f"${exp.accounting:,.0f}")
        table.add_row("  Furniture Reserve", f"${exp.furniture_reserve:,.0f}")
        table.add_row("  Landscaping", f"${exp.landscaping:,.0f}")
        table.add_row("  [bold]Total Expenses[/]", f"[bold]${exp.total:,.0f}[/]")
        table.add_row("", "")
        table.add_row("IMPROVEMENTS", "")
        imp = deal.improvements
        table.add_row("  Furnishing", f"${imp.furnishing_cost:,.0f}")
        for amenity_name, amenity_cost in imp.amenity_details:
            table.add_row(f"  Add {amenity_name}", f"${amenity_cost:,.0f}")
        if imp.cosmetic_rehab > 0:
            table.add_row("  Cosmetic Rehab", f"${imp.cosmetic_rehab:,.0f}")
        table.add_row("  [bold]Total Improvements[/]", f"[bold]${imp.total:,.0f}[/]")
        table.add_row("", "")
        table.add_row("Cash Invested", f"${deal.cash_invested:,.0f}")
        table.add_row("Annual Cash Flow", f"${deal.annual_cash_flow:,.0f}")
        table.add_row("Cash-on-Cash Return", f"{deal.cash_on_cash_return:.1%}")
        table.add_row("Permit Status", deal.permit.status.value)
        table.add_row("Listing", prop.listing_url or "N/A")

        color = "green" if deal.is_good_deal else "yellow"
        console.print(Panel(table, title=f"{quality} | {prop.market}", border_style=color))

    def print_scan_summary(self, market: str, total: int, new: int, deals: int) -> None:
        """Print a one-line scan summary."""
        console.print(
            f"[dim]{datetime.now():%H:%M:%S}[/] "
            f"[bold]{market}[/]: {total} listings, {new} new, "
            f"[green]{deals} deals[/]"
        )

    def export_csv(self, deals: list[Deal]) -> str | None:
        """Export deals to a dated CSV file and append to the running log."""
        if not deals:
            return None

        date_str = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.output_dir / f"deals_{date_str}.csv"
        log_file = self.output_dir / "deal_log.csv"

        fieldnames = [
            "timestamp", "address", "city", "state", "zip", "market",
            "price", "bedrooms", "bathrooms", "sqft",
            "nightly_rate", "occupancy", "annual_revenue", "revenue_source",
            "mortgage", "property_tax", "insurance", "hoa", "prop_mgmt",
            "utilities", "maintenance", "cleaning", "platform_fees",
            "supplies", "permit_fee", "accounting", "furniture_reserve",
            "landscaping", "total_expenses",
            "furnishing_cost", "amenity_cost", "cosmetic_rehab", "total_improvements",
            "cash_invested", "annual_cash_flow", "cash_on_cash",
            "permit_status", "listing_url",
        ]

        rows = []
        for deal in deals:
            rows.append({
                "timestamp": datetime.now().isoformat(),
                "address": deal.property.address,
                "city": deal.property.city,
                "state": deal.property.state,
                "zip": deal.property.zipcode,
                "market": deal.property.market,
                "price": deal.property.price,
                "bedrooms": deal.property.bedrooms,
                "bathrooms": deal.property.bathrooms,
                "sqft": deal.property.sqft or "",
                "nightly_rate": deal.revenue.nightly_rate,
                "occupancy": f"{deal.revenue.occupancy_rate:.2%}",
                "annual_revenue": deal.revenue.annual_revenue,
                "revenue_source": deal.revenue.source.value,
                "mortgage": deal.expenses.mortgage_annual,
                "property_tax": deal.expenses.property_tax,
                "insurance": deal.expenses.insurance,
                "hoa": deal.expenses.hoa_annual,
                "prop_mgmt": deal.expenses.property_management,
                "utilities": deal.expenses.utilities,
                "maintenance": deal.expenses.maintenance,
                "cleaning": deal.expenses.cleaning,
                "platform_fees": deal.expenses.platform_fees,
                "supplies": deal.expenses.supplies,
                "permit_fee": deal.expenses.str_permit,
                "accounting": deal.expenses.accounting,
                "furniture_reserve": deal.expenses.furniture_reserve,
                "landscaping": deal.expenses.landscaping,
                "total_expenses": deal.expenses.total,
                "furnishing_cost": deal.improvements.furnishing_cost,
                "amenity_cost": deal.improvements.amenity_cost,
                "cosmetic_rehab": deal.improvements.cosmetic_rehab,
                "total_improvements": deal.improvements.total,
                "cash_invested": deal.cash_invested,
                "annual_cash_flow": deal.annual_cash_flow,
                "cash_on_cash": f"{deal.cash_on_cash_return:.2%}",
                "permit_status": deal.permit.status.value,
                "listing_url": deal.property.listing_url,
            })

        # Write daily file
        write_header = not daily_file.exists()
        with open(daily_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerows(rows)

        # Append to running log
        write_header = not log_file.exists()
        with open(log_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerows(rows)

        logger.info("Exported %d deals to %s", len(rows), daily_file)
        return str(daily_file)

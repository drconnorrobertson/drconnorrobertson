"""Run a sample STR deal analysis and print results to terminal."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.financial_analyzer import analyze_deal
from src.improvement_estimator import MARKET_COMP_AMENITIES, ImprovementEstimator
from src.models import (
    Confidence,
    PermitInfo,
    PermitStatus,
    Property,
    RevenueEstimate,
    RevenueSource,
)
from src.notifier import Notifier
from src.permit_checker import PermitChecker
from src.revenue_estimator import MARKET_DEFAULTS, RevenueEstimator

console = Console()


def load_config():
    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)


def analyze_sample_property(config, market, price, bedrooms, bathrooms, sqft, year_built, existing_amenities=None):
    """Analyze a single property and print full results."""
    city_parts = market.split(", ")
    city = city_parts[0]
    state = city_parts[1] if len(city_parts) > 1 else ""

    prop = Property(
        zpid="demo",
        address="Sample Property",
        city=city,
        state=state,
        zipcode="00000",
        price=price,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        sqft=sqft,
        year_built=year_built,
        market=market,
    )

    # Revenue from market heuristics
    estimator = RevenueEstimator()
    revenue = estimator.estimate(prop)

    # Improvements
    improvement_estimator = ImprovementEstimator(config)
    imp_estimate = improvement_estimator.estimate(prop, existing_amenities=existing_amenities or [])

    # Permit
    permit_checker = PermitChecker()
    permit = permit_checker.check(prop)

    # Full analysis
    deal = analyze_deal(prop, revenue, permit, config, imp_estimate)

    # Print with notifier
    notifier = Notifier()
    notifier.print_deal(deal)

    return deal


def market_comparison(config, bedrooms=3, ref_price=450000):
    """Compare all markets side-by-side."""
    console.print()
    console.print(Panel(f"[bold]Market Comparison — {bedrooms}BR at ${ref_price:,}[/bold]", border_style="blue"))

    table = Table(show_header=True)
    table.add_column("Market", style="bold", min_width=22)
    table.add_column("Nightly", justify="right")
    table.add_column("Occ%", justify="right")
    table.add_column("Revenue", justify="right")
    table.add_column("Improvements", justify="right")
    table.add_column("Cash In", justify="right")
    table.add_column("Cash Flow", justify="right")
    table.add_column("CoC%", justify="right")
    table.add_column("Permit", justify="center")

    results = []

    for market_cfg in config["markets"]:
        market_name = market_cfg["name"]
        city_parts = market_name.split(", ")

        prop = Property(
            zpid="cmp", address="", city=city_parts[0],
            state=city_parts[1] if len(city_parts) > 1 else "",
            zipcode="00000", price=ref_price, bedrooms=bedrooms,
            bathrooms=2.0, sqft=1800, year_built=2010, market=market_name,
        )

        estimator = RevenueEstimator()
        revenue = estimator.estimate(prop)

        improvement_estimator = ImprovementEstimator(config)
        imp_est = improvement_estimator.estimate(prop, existing_amenities=[])

        permit_checker = PermitChecker()
        permit = permit_checker.check(prop)

        deal = analyze_deal(prop, revenue, permit, config, imp_est)
        results.append((market_name, revenue, imp_est, deal, permit))

    # Sort by CoC
    results.sort(key=lambda x: x[3].cash_on_cash_return, reverse=True)

    for market_name, rev, imp_est, deal, permit in results:
        coc = deal.cash_on_cash_return
        coc_style = "green" if coc >= 0.10 else "yellow" if coc >= 0.07 else "red"
        cf_style = "green" if deal.annual_cash_flow > 0 else "red"
        permit_emoji = {"ALLOWED": "✅", "CONDITIONAL": "⚠️ ", "RESTRICTED": "🚫", "BANNED": "❌", "UNKNOWN": "❓"}.get(permit.status.value, "❓")

        table.add_row(
            market_name,
            f"${rev.nightly_rate:,.0f}",
            f"{rev.occupancy_rate:.0%}",
            f"${rev.annual_revenue:,.0f}",
            f"${imp_est.total:,.0f}",
            f"${deal.cash_invested:,.0f}",
            f"[{cf_style}]${deal.annual_cash_flow:,.0f}[/]",
            f"[{coc_style}]{coc:.1%}[/]",
            f"{permit_emoji}",
        )

    console.print(table)


if __name__ == "__main__":
    config = load_config()

    console.print()
    console.print(Panel("[bold cyan]STR DEAL FINDER — Sample Analysis[/bold cyan]", border_style="cyan"))

    # === Property 1: Gatlinburg cabin — good entry price, has hot tub ===
    console.print()
    console.print("[bold]SCENARIO 1: Gatlinburg 3BR cabin — $325K, has hot tub[/bold]")
    console.print("[dim]Realistic entry price for a cabin that already has the #1 amenity[/dim]")
    analyze_sample_property(config, "Gatlinburg, TN", 325000, 3, 2.0, 1600, 2015, ["hot tub"])

    # === Property 2: Scottsdale — strong revenue market ===
    console.print()
    console.print("[bold]SCENARIO 2: Scottsdale 4BR — $500K, has pool + hot tub[/bold]")
    console.print("[dim]Premium market, property already has the big-ticket amenities[/dim]")
    analyze_sample_property(config, "Scottsdale, AZ", 500000, 4, 3.0, 2200, 2012, ["private pool", "hot tub"])

    # === Property 3: Kissimmee near Disney, turnkey ===
    console.print()
    console.print("[bold]SCENARIO 3: Kissimmee 5BR — $425K, has pool + game room + themed rooms[/bold]")
    console.print("[dim]Turnkey Disney rental — already has what comps have[/dim]")
    analyze_sample_property(config, "Kissimmee, FL", 425000, 5, 3.0, 2800, 2018, ["private pool", "game room", "themed rooms"])

    # === Property 4: Branson budget deal ===
    console.print()
    console.print("[bold]SCENARIO 4: Branson 3BR — $225K, needs hot tub + game room[/bold]")
    console.print("[dim]Low entry price, needs work but affordable[/dim]")
    analyze_sample_property(config, "Branson, MO", 225000, 3, 2.0, 1400, 2008, [])

    # === Property 5: Destin beach house ===
    console.print()
    console.print("[bold]SCENARIO 5: Destin 3BR — $375K, already has outdoor kitchen[/bold]")
    analyze_sample_property(config, "Destin, FL", 375000, 3, 2.0, 1700, 2016, ["outdoor kitchen/grill"])

    # === Market Comparison at lower price ===
    console.print()
    console.print("[bold]ALL MARKETS COMPARISON[/bold]")
    market_comparison(config, bedrooms=3, ref_price=350000)

"""STR Deal Finder — Main entry point.

Continuously scans Zillow for short-term rental investment opportunities,
analyzes financials, checks permit feasibility, and outputs qualifying deals.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml

from src.airdna_client import AirDNAClient
from src.financial_analyzer import analyze_deal
from src.improvement_estimator import ImprovementEstimator
from src.models import PermitStatus
from src.notifier import Notifier
from src.permit_checker import PermitChecker
from src.revenue_estimator import RevenueEstimator
from src.zillow_client import ZillowClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config/settings.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run_scan(config: dict, dry_run: bool = False) -> None:
    """Run a single scan across all configured markets."""
    api_key = config["api_keys"]["zillow_rapidapi"]
    if api_key == "YOUR_RAPIDAPI_KEY":
        logger.error(
            "Please set your RapidAPI key in config/settings.yaml "
            "(api_keys.zillow_rapidapi)"
        )
        sys.exit(1)

    zillow = ZillowClient(api_key)
    estimator = RevenueEstimator(config["api_keys"].get("mashvisor", ""))

    # Set up AirDNA client for comp-driven improvement analysis
    airdna_key = config["api_keys"].get("airdna_rapidapi", "")
    airdna_client = AirDNAClient(airdna_key) if airdna_key else None
    if airdna_client:
        logger.info("AirDNA integration enabled — fetching comp amenities from live data")
    improvement_estimator = ImprovementEstimator(config, airdna_client=airdna_client)

    permit_checker = PermitChecker()
    notifier = Notifier()

    filters = config["filters"]
    thresholds = config["thresholds"]
    min_coc = thresholds["min_cash_on_cash"]
    min_occ = thresholds["min_occupancy"]

    total_deals_found = 0

    for market_cfg in config["markets"]:
        market_name = market_cfg["name"]
        location = market_cfg["location"]

        logger.info("Scanning: %s", market_name)

        listings = zillow.search_listings(
            location=location,
            max_price=filters["max_price"],
            min_bedrooms=filters["min_bedrooms"],
            home_types=filters.get("property_types"),
        )

        new_listings = [p for p in listings if zillow.is_new(p.zpid)]
        qualifying_deals = []

        for prop in new_listings:
            # Enrich with detailed data (taxes, HOA)
            prop = zillow.enrich_property(prop)
            prop.market = market_name

            # Estimate revenue
            revenue = estimator.estimate(prop)

            # Skip low-occupancy estimates
            if revenue.occupancy_rate < min_occ:
                logger.debug(
                    "Skipping %s: low occupancy %.0f%%",
                    prop.address,
                    revenue.occupancy_rate * 100,
                )
                zillow.mark_seen(prop.zpid)
                continue

            # Check permit
            permit = permit_checker.check(prop)

            # Estimate improvements based on market comps
            improvements = improvement_estimator.estimate(prop)

            # Analyze financials
            deal = analyze_deal(prop, revenue, permit, config, improvements)

            # Mark as seen regardless of outcome
            zillow.mark_seen(prop.zpid)

            # Filter on cash-on-cash and permit
            if deal.cash_on_cash_return >= min_coc and permit.status != PermitStatus.BANNED:
                qualifying_deals.append(deal)
                notifier.print_deal(deal)

        notifier.print_scan_summary(
            market=market_name,
            total=len(listings),
            new=len(new_listings),
            deals=len(qualifying_deals),
        )

        if qualifying_deals:
            notifier.export_csv(qualifying_deals)
            total_deals_found += len(qualifying_deals)

        # Rate limiting between markets
        if not dry_run:
            time.sleep(2)

    logger.info(
        "Scan complete. Found %d qualifying deals across %d markets.",
        total_deals_found,
        len(config["markets"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="STR Deal Finder")
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to config file (default: config/settings.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run once and exit (don't loop)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    if args.dry_run:
        logger.info("Dry run mode — scanning once and exiting.")
        run_scan(config, dry_run=True)
        return

    interval_hours = config.get("scan_interval_hours", 4)
    interval_seconds = interval_hours * 3600

    logger.info(
        "STR Deal Finder started. Scanning every %d hours across %d markets.",
        interval_hours,
        len(config["markets"]),
    )

    while True:
        try:
            run_scan(config)
        except KeyboardInterrupt:
            logger.info("Shutting down.")
            break
        except Exception:
            logger.exception("Error during scan")

        logger.info("Next scan in %d hours.", interval_hours)
        try:
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Shutting down.")
            break


if __name__ == "__main__":
    main()

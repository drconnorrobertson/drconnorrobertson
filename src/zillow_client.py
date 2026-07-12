"""Zillow RapidAPI client for property search and details.

Uses the Real-Time Zillow Data API on RapidAPI.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

from src.models import Property

logger = logging.getLogger(__name__)

RAPIDAPI_HOST = "zillow-com1.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}"

SEEN_FILE = Path("output/seen_zpids.json")


class ZillowClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": RAPIDAPI_HOST,
        }
        self.seen_zpids: set[str] = self._load_seen()

    def _load_seen(self) -> set[str]:
        if SEEN_FILE.exists():
            with open(SEEN_FILE) as f:
                return set(json.load(f))
        return set()

    def _save_seen(self) -> None:
        SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SEEN_FILE, "w") as f:
            json.dump(list(self.seen_zpids), f)

    def mark_seen(self, zpid: str) -> None:
        self.seen_zpids.add(zpid)
        self._save_seen()

    def is_new(self, zpid: str) -> bool:
        return zpid not in self.seen_zpids

    def search_listings(
        self,
        location: str,
        max_price: int = 900000,
        min_bedrooms: int = 1,
        home_types: list[str] | None = None,
    ) -> list[Property]:
        """Search Zillow for listings in a location matching filters."""
        params: dict[str, Any] = {
            "location": location,
            "status_type": "ForSale",
            "price_max": str(max_price),
            "beds_min": str(min_bedrooms),
            "sort": "Newest",
        }
        if home_types:
            params["home_type"] = ",".join(home_types)

        logger.info("Searching Zillow: %s (max $%s)", location, f"{max_price:,}")

        try:
            resp = requests.get(
                f"{BASE_URL}/propertyExtendedSearch",
                headers=self.headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Zillow API error for %s: %s", location, e)
            return []

        results = data.get("props", [])
        logger.info("Found %d listings in %s", len(results), location)

        properties = []
        for item in results:
            try:
                prop = self._parse_listing(item, location)
                if prop:
                    properties.append(prop)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("Failed to parse listing: %s", e)
                continue

        return properties

    def get_details(self, zpid: str) -> dict[str, Any] | None:
        """Fetch detailed property data by zpid."""
        try:
            resp = requests.get(
                f"{BASE_URL}/property",
                headers=self.headers,
                params={"zpid": zpid},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error("Zillow detail fetch error for zpid %s: %s", zpid, e)
            return None

    def enrich_property(self, prop: Property) -> Property:
        """Enrich a property with detailed data (taxes, HOA, etc.)."""
        details = self.get_details(prop.zpid)
        if not details:
            return prop

        if prop.property_tax_annual is None:
            tax_history = details.get("taxHistory", [])
            if tax_history:
                prop.property_tax_annual = tax_history[0].get("taxPaid")

        if prop.hoa_monthly is None:
            hoa = details.get("monthlyHoaFee")
            if hoa:
                prop.hoa_monthly = float(hoa)

        if prop.year_built is None:
            prop.year_built = details.get("yearBuilt")

        return prop

    def _parse_listing(self, item: dict, market: str) -> Property | None:
        zpid = str(item.get("zpid", ""))
        if not zpid:
            return None

        price = item.get("price")
        if not price or price <= 0:
            return None

        bedrooms = item.get("bedrooms")
        if not bedrooms or bedrooms < 1:
            return None

        address = item.get("address", "")
        if isinstance(address, dict):
            street = address.get("streetAddress", "")
            city = address.get("city", "")
            state = address.get("state", "")
            zipcode = address.get("zipcode", "")
        else:
            street = str(address)
            city = ""
            state = ""
            zipcode = ""

        return Property(
            zpid=zpid,
            address=street,
            city=city,
            state=state,
            zipcode=zipcode,
            price=float(price),
            bedrooms=int(bedrooms),
            bathrooms=float(item.get("bathrooms", 1)),
            sqft=item.get("livingArea"),
            lot_size=item.get("lotAreaValue"),
            property_tax_annual=item.get("propertyTaxRate"),
            hoa_monthly=None,
            listing_url=item.get("detailUrl", ""),
            market=market,
            property_type=item.get("propertyType", ""),
        )

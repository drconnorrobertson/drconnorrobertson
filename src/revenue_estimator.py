"""STR revenue estimation using Mashvisor API with heuristic fallback.

Estimates annual revenue based on nightly rate and occupancy for a given
property's market and bedroom count.
"""

import logging
from typing import Any

import requests

from src.models import Confidence, Property, RevenueEstimate, RevenueSource

logger = logging.getLogger(__name__)

# Market defaults: {market: {bedrooms: (nightly_rate, occupancy)}}
# Based on publicly available STR market data and post-2020 professional operator
# performance. Occupancy reflects well-managed listings with good amenities.
MARKET_DEFAULTS: dict[str, dict[int, tuple[float, float]]] = {
    "Gatlinburg, TN": {
        1: (150, 0.67),
        2: (200, 0.70),
        3: (275, 0.72),
        4: (375, 0.70),
        5: (475, 0.65),
        6: (575, 0.60),
    },
    "Pigeon Forge, TN": {
        1: (140, 0.65),
        2: (185, 0.68),
        3: (250, 0.70),
        4: (350, 0.68),
        5: (450, 0.63),
        6: (550, 0.58),
    },
    "Destin, FL": {
        1: (175, 0.63),
        2: (225, 0.67),
        3: (300, 0.70),
        4: (400, 0.65),
        5: (500, 0.60),
        6: (600, 0.55),
    },
    "Panama City Beach, FL": {
        1: (150, 0.60),
        2: (200, 0.65),
        3: (275, 0.68),
        4: (350, 0.63),
        5: (425, 0.58),
        6: (500, 0.53),
    },
    "Kissimmee, FL": {
        1: (125, 0.70),
        2: (175, 0.73),
        3: (225, 0.75),
        4: (300, 0.73),
        5: (400, 0.70),
        6: (500, 0.65),
    },
    "Gulf Shores, AL": {
        1: (150, 0.60),
        2: (200, 0.63),
        3: (275, 0.67),
        4: (350, 0.63),
        5: (425, 0.58),
        6: (500, 0.53),
    },
    "Scottsdale, AZ": {
        1: (150, 0.65),
        2: (225, 0.68),
        3: (325, 0.70),
        4: (450, 0.65),
        5: (575, 0.60),
        6: (700, 0.55),
    },
    "Joshua Tree, CA": {
        1: (150, 0.60),
        2: (200, 0.63),
        3: (275, 0.65),
        4: (375, 0.60),
        5: (450, 0.55),
        6: (525, 0.50),
    },
    "Big Bear Lake, CA": {
        1: (150, 0.55),
        2: (200, 0.60),
        3: (275, 0.63),
        4: (375, 0.60),
        5: (475, 0.55),
        6: (575, 0.50),
    },
    "Mount Pocono, PA": {
        1: (125, 0.55),
        2: (175, 0.60),
        3: (250, 0.63),
        4: (350, 0.60),
        5: (425, 0.55),
        6: (500, 0.50),
    },
    "Kill Devil Hills, NC": {
        1: (150, 0.55),
        2: (225, 0.60),
        3: (325, 0.65),
        4: (450, 0.63),
        5: (575, 0.60),
        6: (700, 0.55),
    },
    "Branson, MO": {
        1: (100, 0.60),
        2: (150, 0.63),
        3: (200, 0.67),
        4: (275, 0.63),
        5: (350, 0.58),
        6: (425, 0.53),
    },
    "Myrtle Beach, SC": {
        1: (125, 0.60),
        2: (175, 0.65),
        3: (250, 0.68),
        4: (325, 0.63),
        5: (400, 0.58),
        6: (475, 0.53),
    },
}

MASHVISOR_BASE = "https://api.mashvisor.com/v1.1/client"


class RevenueEstimator:
    def __init__(self, mashvisor_key: str = ""):
        self.mashvisor_key = mashvisor_key

    def estimate(self, prop: Property) -> RevenueEstimate:
        """Estimate STR revenue. Tries Mashvisor first, falls back to heuristics."""
        if self.mashvisor_key:
            result = self._estimate_mashvisor(prop)
            if result:
                return result

        return self._estimate_heuristic(prop)

    def _estimate_mashvisor(self, prop: Property) -> RevenueEstimate | None:
        """Query Mashvisor API for rental revenue data."""
        try:
            resp = requests.get(
                f"{MASHVISOR_BASE}/rental-rates",
                params={
                    "zip_code": prop.zipcode,
                    "bedrooms": prop.bedrooms,
                    "source": "airbnb",
                },
                headers={"x-api-key": self.mashvisor_key},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            content = data.get("content", {})
            nightly_rate = content.get("airbnb_rental_rates", {}).get("average_rate")
            occupancy = content.get("airbnb_rental_rates", {}).get("occupancy")

            if nightly_rate and occupancy:
                occupancy_pct = occupancy / 100 if occupancy > 1 else occupancy
                annual = nightly_rate * occupancy_pct * 365
                return RevenueEstimate(
                    annual_revenue=annual,
                    nightly_rate=nightly_rate,
                    occupancy_rate=occupancy_pct,
                    source=RevenueSource.MASHVISOR,
                    confidence=Confidence.HIGH,
                )
        except requests.RequestException as e:
            logger.warning("Mashvisor API error: %s", e)

        return None

    def _estimate_heuristic(self, prop: Property) -> RevenueEstimate:
        """Estimate revenue using market-specific lookup table."""
        market_data = MARKET_DEFAULTS.get(prop.market, {})

        bedrooms = min(prop.bedrooms, 6)

        if bedrooms in market_data:
            nightly_rate, occupancy = market_data[bedrooms]
        else:
            # Extrapolate: use the closest available bedroom count
            available = sorted(market_data.keys())
            if available:
                closest = min(available, key=lambda x: abs(x - bedrooms))
                nightly_rate, occupancy = market_data[closest]
            else:
                # No market data at all — very conservative generic estimate
                nightly_rate = 150 + (bedrooms - 1) * 50
                occupancy = 0.55

        annual = nightly_rate * occupancy * 365

        return RevenueEstimate(
            annual_revenue=annual,
            nightly_rate=nightly_rate,
            occupancy_rate=occupancy,
            source=RevenueSource.HEURISTIC,
            confidence=Confidence.MEDIUM if market_data else Confidence.LOW,
        )

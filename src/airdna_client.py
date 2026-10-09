"""AirDNA RapidAPI client for fetching STR comp data and amenities.

Queries AirDNA via RapidAPI to find top-performing comparable properties
in a market and extract their amenities. This data drives the improvement
estimator to calculate what amenities a property needs to compete.
"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

AIRDNA_RAPIDAPI_HOST = "airdna1.p.rapidapi.com"
AIRDNA_BASE_URL = f"https://{AIRDNA_RAPIDAPI_HOST}"


class AirDNAClient:
    def __init__(self, rapidapi_key: str):
        self.api_key = rapidapi_key
        self.headers = {
            "x-rapidapi-key": rapidapi_key,
            "x-rapidapi-host": AIRDNA_RAPIDAPI_HOST,
        }

    def get_market_comps(
        self,
        location: str,
        bedrooms: int,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Fetch top-performing STR listings in a market from AirDNA.

        Returns a list of property dicts with amenities, revenue, and ratings.
        """
        try:
            resp = requests.get(
                f"{AIRDNA_BASE_URL}/properties",
                params={
                    "location": location,
                    "bedrooms": bedrooms,
                    "currency": "USD",
                    "room_type": "entire_home",
                    "sort_by": "revenue",
                    "sort_order": "desc",
                    "limit": limit,
                },
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            properties = data.get("properties", data.get("results", []))
            if isinstance(properties, list):
                return properties

            return []

        except requests.RequestException as e:
            logger.warning("AirDNA properties search failed: %s", e)
            return []

    def get_property_details(self, property_id: str) -> dict[str, Any] | None:
        """Fetch detailed property info including amenities from AirDNA."""
        try:
            resp = requests.get(
                f"{AIRDNA_BASE_URL}/properties/{property_id}",
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()

        except requests.RequestException as e:
            logger.warning("AirDNA property detail failed for %s: %s", property_id, e)
            return None

    def get_rentalizer_estimate(
        self,
        address: str,
        bedrooms: int,
        bathrooms: float,
    ) -> dict[str, Any] | None:
        """Get AirDNA Rentalizer estimate with comps for an address."""
        try:
            resp = requests.get(
                f"{AIRDNA_BASE_URL}/rentalizer",
                params={
                    "address": address,
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "currency": "USD",
                },
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()

        except requests.RequestException as e:
            logger.warning("AirDNA Rentalizer failed for %s: %s", address, e)
            return None

    def extract_comp_amenities(
        self,
        location: str,
        bedrooms: int,
        top_n: int = 10,
    ) -> list[str]:
        """Get the most common amenities among top-performing comps.

        Fetches the top revenue-generating listings in a market and
        extracts which amenities appear most frequently. Returns a list
        of amenity names sorted by frequency (most common first).
        """
        properties = self.get_market_comps(location, bedrooms, limit=top_n)
        if not properties:
            return []

        amenity_counts: dict[str, int] = {}

        for prop in properties:
            amenities = self._extract_amenities_from_listing(prop)
            for amenity in amenities:
                amenity_counts[amenity] = amenity_counts.get(amenity, 0) + 1

        # Sort by frequency, return amenities present in at least 30% of comps
        threshold = max(1, int(len(properties) * 0.3))
        common = [
            name
            for name, count in sorted(
                amenity_counts.items(), key=lambda x: x[1], reverse=True
            )
            if count >= threshold
        ]
        return common

    def _extract_amenities_from_listing(
        self, listing: dict[str, Any]
    ) -> list[str]:
        """Extract and normalize amenity names from a listing response.

        AirDNA returns amenities in various formats depending on the endpoint.
        This normalizes them to lowercase strings that match our amenity catalog.
        """
        amenities = []

        # Try different response formats
        raw_amenities = (
            listing.get("amenities", [])
            or listing.get("listing_amenities", [])
            or listing.get("details", {}).get("amenities", [])
        )

        for item in raw_amenities:
            if isinstance(item, str):
                amenities.append(item.lower().strip())
            elif isinstance(item, dict):
                name = item.get("name", item.get("amenity", ""))
                if name:
                    amenities.append(name.lower().strip())

        return amenities


# Mapping from AirDNA amenity names to our internal amenity catalog names.
# AirDNA uses various naming conventions; this normalizes them.
AIRDNA_AMENITY_MAP: dict[str, str] = {
    # Hot tub variants
    "hot tub": "hot tub",
    "hottub": "hot tub",
    "jacuzzi": "hot tub",
    "spa": "hot tub",
    # Pool variants
    "pool": "private pool",
    "private pool": "private pool",
    "swimming pool": "private pool",
    "indoor pool": "indoor pool",
    "heated pool": "private pool",
    # Game room variants
    "game room": "game room",
    "games room": "game room",
    "arcade": "game room",
    "pool table": "game room",
    "foosball": "game room",
    "ping pong": "game room",
    # Theater variants
    "theater room": "theater room",
    "home theater": "theater room",
    "movie room": "theater room",
    "projector": "theater room",
    # Fireplace
    "fireplace": "fireplace",
    "wood burning fireplace": "fireplace",
    "gas fireplace": "fireplace",
    # Outdoor
    "fire pit": "fire pit",
    "firepit": "fire pit",
    "outdoor kitchen": "outdoor kitchen/grill",
    "bbq grill": "outdoor kitchen/grill",
    "grill": "outdoor kitchen/grill",
    "bbq": "outdoor kitchen/grill",
    "ev charger": "EV charger",
    "ev charging": "EV charger",
    "outdoor shower": "outdoor shower",
    # Water gear
    "kayak": "kayaks/paddleboards",
    "kayaks": "kayaks/paddleboards",
    "paddleboard": "kayaks/paddleboards",
    "paddle board": "kayaks/paddleboards",
    # Specialty
    "sauna": "sauna",
    "putting green": "putting green",
    "dock": "dock/lake access",
    "lake access": "dock/lake access",
    "beach gear": "beach gear",
    "beach equipment": "beach gear",
    # Deck/patio
    "deck": "mountain view deck",
    "patio": "mountain view deck",
    "balcony": "mountain view deck",
}


def normalize_airdna_amenities(raw_amenities: list[str]) -> set[str]:
    """Map AirDNA amenity names to our internal catalog names."""
    normalized = set()
    for raw in raw_amenities:
        key = raw.lower().strip()
        if key in AIRDNA_AMENITY_MAP:
            normalized.add(AIRDNA_AMENITY_MAP[key])
        else:
            # Check if any map pattern is contained in this amenity name.
            # Only match pattern-in-key (e.g., "fire pit" in "outdoor firepit area"),
            # not key-in-pattern (avoids "kitchen" matching "outdoor kitchen").
            for pattern, canonical in AIRDNA_AMENITY_MAP.items():
                if len(pattern) >= 4 and pattern in key:
                    normalized.add(canonical)
                    break
    return normalized

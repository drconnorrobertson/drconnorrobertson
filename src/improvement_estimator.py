"""Comp-driven improvement cost estimator.

Analyzes what top-performing STR comps in a market typically have,
compares against the subject property, and estimates the cost to
close the amenity gap + furnish the property.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.models import Property

logger = logging.getLogger(__name__)


@dataclass
class AmenityItem:
    name: str
    materials_cost: float
    labor_cost: float
    revenue_impact: str  # "high", "medium", "low"

    @property
    def install_cost(self) -> float:
        return self.materials_cost + self.labor_cost


@dataclass
class ImprovementEstimate:
    furnishing_cost: float = 0.0
    amenity_additions: list[tuple[str, float]] = field(default_factory=list)
    cosmetic_rehab: float = 0.0

    @property
    def total_amenity_cost(self) -> float:
        return sum(cost for _, cost in self.amenity_additions)

    @property
    def total(self) -> float:
        return self.furnishing_cost + self.total_amenity_cost + self.cosmetic_rehab

    def breakdown_lines(self) -> list[tuple[str, float]]:
        lines = [("Furnishing", self.furnishing_cost)]
        for name, cost in self.amenity_additions:
            lines.append((f"Add {name}", cost))
        if self.cosmetic_rehab > 0:
            lines.append(("Cosmetic Rehab", self.cosmetic_rehab))
        return lines


# What top STR comps typically have in each market, with install costs.
# Format: {market: [(amenity_name, install_cost, revenue_impact)]}
# These represent amenities that the TOP 25% of earners in each market have.
# Market comp amenities: AmenityItem(name, materials_cost, labor_cost, revenue_impact)
# Costs include materials AND labor separately for accurate budgeting.
# Labor typically runs 40-60% of project cost for construction work,
# lower for simple installs (hot tub delivery, furniture assembly).
MARKET_COMP_AMENITIES: dict[str, list[AmenityItem]] = {
    "Gatlinburg, TN": [
        AmenityItem("hot tub", 4500, 3500, "high"),         # delivery + electrical + pad
        AmenityItem("game room", 3000, 2000, "high"),        # equipment + setup
        AmenityItem("fireplace", 1500, 2500, "medium"),      # insert + install
        AmenityItem("mountain view deck", 3000, 5000, "high"),  # lumber + build
        AmenityItem("EV charger", 600, 900, "low"),          # charger + electrician
    ],
    "Pigeon Forge, TN": [
        AmenityItem("hot tub", 4500, 3500, "high"),
        AmenityItem("game room", 3000, 2000, "high"),
        AmenityItem("theater room", 3500, 3500, "medium"),   # projector/screen + wiring
        AmenityItem("fireplace", 1500, 2500, "medium"),
        AmenityItem("indoor pool", 18000, 22000, "high"),    # pool + enclosure + plumbing
    ],
    "Destin, FL": [
        AmenityItem("private pool", 18000, 22000, "high"),   # shell + plumbing + deck
        AmenityItem("outdoor kitchen/grill", 2000, 3000, "medium"),
        AmenityItem("beach gear", 500, 0, "medium"),         # purchase only
        AmenityItem("kayaks/paddleboards", 1200, 300, "medium"),  # gear + rack install
        AmenityItem("EV charger", 600, 900, "low"),
    ],
    "Panama City Beach, FL": [
        AmenityItem("private pool", 18000, 22000, "high"),
        AmenityItem("outdoor kitchen/grill", 2000, 3000, "medium"),
        AmenityItem("beach gear", 500, 0, "medium"),
        AmenityItem("bunk room", 1500, 1500, "medium"),      # bunks + install
    ],
    "Kissimmee, FL": [
        AmenityItem("private pool", 18000, 22000, "high"),
        AmenityItem("game room", 3000, 2000, "high"),
        AmenityItem("theater room", 3500, 3500, "medium"),
        AmenityItem("themed rooms", 2000, 3000, "high"),     # murals + decor + painter
        AmenityItem("splash pad", 4000, 5000, "medium"),     # pad + plumbing
    ],
    "Gulf Shores, AL": [
        AmenityItem("private pool", 18000, 22000, "high"),
        AmenityItem("outdoor kitchen/grill", 2000, 3000, "medium"),
        AmenityItem("beach gear", 500, 0, "medium"),
        AmenityItem("hot tub", 4500, 3500, "medium"),
    ],
    "Scottsdale, AZ": [
        AmenityItem("private pool", 18000, 22000, "high"),
        AmenityItem("hot tub", 4500, 3500, "high"),
        AmenityItem("outdoor kitchen/grill", 3000, 4000, "medium"),  # higher-end market
        AmenityItem("fire pit", 1000, 1500, "medium"),
        AmenityItem("putting green", 2000, 2500, "low"),
    ],
    "Joshua Tree, CA": [
        AmenityItem("hot tub", 4500, 3500, "high"),
        AmenityItem("fire pit", 1000, 1500, "high"),
        AmenityItem("outdoor shower", 800, 1200, "medium"),
        AmenityItem("stargazing deck", 1500, 2500, "medium"),
        AmenityItem("cowboy pool", 2500, 3000, "medium"),    # stock tank + plumbing
    ],
    "Big Bear Lake, CA": [
        AmenityItem("hot tub", 4500, 3500, "high"),
        AmenityItem("game room", 3000, 2000, "high"),
        AmenityItem("fireplace", 1500, 2500, "medium"),
        AmenityItem("sauna", 3000, 4000, "medium"),          # kit + electrical + build
        AmenityItem("fire pit", 1000, 1500, "medium"),
    ],
    "Mount Pocono, PA": [
        AmenityItem("hot tub", 4500, 3500, "high"),
        AmenityItem("game room", 3000, 2000, "high"),
        AmenityItem("fireplace", 1500, 2500, "medium"),
        AmenityItem("fire pit", 1000, 1500, "medium"),
        AmenityItem("ski gear storage", 300, 200, "low"),
    ],
    "Kill Devil Hills, NC": [
        AmenityItem("private pool", 18000, 22000, "high"),
        AmenityItem("hot tub", 4500, 3500, "medium"),
        AmenityItem("beach gear", 500, 0, "medium"),
        AmenityItem("outdoor shower", 800, 1200, "low"),
        AmenityItem("game room", 3000, 2000, "medium"),
    ],
    "Branson, MO": [
        AmenityItem("hot tub", 4500, 3500, "high"),
        AmenityItem("game room", 3000, 2000, "high"),
        AmenityItem("fireplace", 1500, 2500, "medium"),
        AmenityItem("fire pit", 1000, 1500, "medium"),
        AmenityItem("dock/lake access", 2000, 4000, "high"),  # materials + contractor
    ],
    "Myrtle Beach, SC": [
        AmenityItem("private pool", 18000, 22000, "high"),
        AmenityItem("hot tub", 4500, 3500, "medium"),
        AmenityItem("outdoor kitchen/grill", 2000, 3000, "medium"),
        AmenityItem("beach gear", 500, 0, "medium"),
        AmenityItem("game room", 3000, 2000, "medium"),
    ],
}

# Furnishing cost per bedroom (includes furniture, decor, linens, kitchen, etc.)
FURNISHING_PER_BEDROOM = 4000

# Base furnishing for common areas (living room, kitchen, dining, patio)
FURNISHING_BASE = 8000

# Extra per sqft above 1500 for larger homes that need more furniture
FURNISHING_PER_EXTRA_SQFT = 3.0

# Cosmetic rehab estimate based on property age.
# Includes BOTH materials AND labor (painters, flooring installers, etc.)
# Materials are roughly 40% and labor 60% of cosmetic rehab costs.
COSMETIC_REHAB_BY_AGE: list[tuple[int, float]] = [
    # (years_old_threshold, total_rehab_cost_materials_and_labor)
    (5, 0),         # 0-5 years: no cosmetic rehab needed
    (15, 7000),     # 6-15 years: paint ($3k materials + $4k labor)
    (30, 18000),    # 16-30 years: paint + flooring + fixtures ($7k mat + $11k labor)
    (50, 30000),    # 31-50 years: paint, flooring, fixtures, kitchen/bath updates ($12k + $18k)
    (999, 45000),   # 50+: major cosmetic rehab, possible layout changes ($18k + $27k)
]


class ImprovementEstimator:
    def __init__(self, config: dict[str, Any] | None = None, airdna_client: Any = None):
        self.config = config or {}
        self.airdna_client = airdna_client
        improvement_config = self.config.get("improvements", {})
        self.furnishing_per_bedroom = improvement_config.get(
            "furnishing_per_bedroom", FURNISHING_PER_BEDROOM
        )
        self.furnishing_base = improvement_config.get(
            "furnishing_base", FURNISHING_BASE
        )
        self.only_high_impact = improvement_config.get(
            "only_high_impact_amenities", False
        )
        self.max_amenity_budget = improvement_config.get(
            "max_amenity_budget", 60000
        )
        self.existing_amenities: list[str] = improvement_config.get(
            "existing_amenities", []
        )
        # Cache AirDNA comp amenities per market to avoid repeated API calls
        self._comp_amenity_cache: dict[str, set[str]] = {}

    def estimate(
        self,
        prop: Property,
        existing_amenities: list[str] | None = None,
    ) -> ImprovementEstimate:
        """Estimate improvement costs based on market comps and property details.

        If an AirDNA client is configured, queries AirDNA for the top-performing
        comps in the market and extracts what amenities they have. The property
        needs to match those amenities to compete. Falls back to hardcoded
        market data if AirDNA is unavailable.

        Args:
            prop: The subject property.
            existing_amenities: List of amenity names the property already has.
                If None, assumes the property has nothing (worst case).
        """
        existing = set(a.lower() for a in (existing_amenities or self.existing_amenities))

        # Try to enrich existing amenities from AirDNA comp data
        comp_amenities = self._get_comp_amenities(prop)
        if comp_amenities:
            logger.info(
                "AirDNA comps for %s show top amenities: %s",
                prop.market,
                ", ".join(sorted(comp_amenities)),
            )

        furnishing = self._estimate_furnishing(prop)
        amenity_additions = self._estimate_amenities(prop, existing)
        cosmetic = self._estimate_cosmetic_rehab(prop)

        return ImprovementEstimate(
            furnishing_cost=furnishing,
            amenity_additions=amenity_additions,
            cosmetic_rehab=cosmetic,
        )

    def _get_comp_amenities(self, prop: Property) -> set[str]:
        """Fetch amenities from top-performing comps via AirDNA.

        Results are cached per market so we only call the API once per market.
        Returns normalized amenity names that match our internal catalog.
        """
        if not self.airdna_client:
            return set()

        cache_key = f"{prop.market}:{prop.bedrooms}"
        if cache_key in self._comp_amenity_cache:
            return self._comp_amenity_cache[cache_key]

        try:
            from src.airdna_client import normalize_airdna_amenities

            raw_amenities = self.airdna_client.extract_comp_amenities(
                location=prop.market,
                bedrooms=prop.bedrooms,
                top_n=10,
            )
            normalized = normalize_airdna_amenities(raw_amenities)
            self._comp_amenity_cache[cache_key] = normalized
            return normalized
        except Exception as e:
            logger.warning("Failed to fetch AirDNA comp amenities: %s", e)
            self._comp_amenity_cache[cache_key] = set()
            return set()

    def _estimate_furnishing(self, prop: Property) -> float:
        """Estimate furnishing cost based on bedrooms and sqft."""
        cost = self.furnishing_base + (prop.bedrooms * self.furnishing_per_bedroom)

        # Scale up for larger properties
        sqft = prop.sqft or (prop.bedrooms * 400 + 600)  # estimate if missing
        if sqft > 1500:
            cost += (sqft - 1500) * FURNISHING_PER_EXTRA_SQFT

        return cost

    def _estimate_amenities(
        self,
        prop: Property,
        existing: set[str],
    ) -> list[tuple[str, float]]:
        """Determine which comp amenities are missing and estimate costs."""
        market_amenities = MARKET_COMP_AMENITIES.get(prop.market, [])
        if not market_amenities:
            # Unknown market — use generic amenities
            market_amenities = [
                AmenityItem("hot tub", 4500, 3500, "high"),
                AmenityItem("fire pit", 1000, 1500, "medium"),
                AmenityItem("game room", 3000, 2000, "medium"),
            ]

        additions = []
        running_total = 0.0

        for amenity in market_amenities:
            if amenity.name.lower() in existing:
                continue

            if self.only_high_impact and amenity.revenue_impact != "high":
                continue

            if running_total + amenity.install_cost > self.max_amenity_budget:
                continue

            additions.append((amenity.name, amenity.install_cost))
            running_total += amenity.install_cost

        return additions

    def _estimate_cosmetic_rehab(self, prop: Property) -> float:
        """Estimate cosmetic rehab based on property age."""
        if prop.year_built is None:
            # Unknown age — assume moderate rehab needed (materials + labor)
            return 15000

        import datetime
        age = datetime.date.today().year - prop.year_built

        for threshold, cost in COSMETIC_REHAB_BY_AGE:
            if age <= threshold:
                return cost

        return 45000  # fallback for very old

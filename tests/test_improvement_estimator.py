"""Tests for the improvement estimator module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.improvement_estimator import (
    MARKET_COMP_AMENITIES,
    AmenityItem,
    ImprovementEstimator,
)
from src.models import Property


def make_property(
    market="Gatlinburg, TN",
    bedrooms=3,
    sqft=1800,
    year_built=2015,
):
    return Property(
        zpid="123",
        address="123 Main St",
        city="Gatlinburg",
        state="TN",
        zipcode="37738",
        price=500000,
        bedrooms=bedrooms,
        bathrooms=2.0,
        sqft=sqft,
        year_built=year_built,
        market=market,
    )


class TestFurnishingCost:
    def test_scales_with_bedrooms(self):
        estimator = ImprovementEstimator()
        prop2 = make_property(bedrooms=2, sqft=1200)
        prop5 = make_property(bedrooms=5, sqft=1200)
        est2 = estimator.estimate(prop2, existing_amenities=["hot tub", "game room", "fireplace", "mountain view deck", "EV charger"])
        est5 = estimator.estimate(prop5, existing_amenities=["hot tub", "game room", "fireplace", "mountain view deck", "EV charger"])
        assert est5.furnishing_cost > est2.furnishing_cost

    def test_scales_with_sqft(self):
        estimator = ImprovementEstimator()
        amenities = ["hot tub", "game room", "fireplace", "mountain view deck", "EV charger"]
        prop_small = make_property(sqft=1200)
        prop_large = make_property(sqft=3000)
        est_small = estimator.estimate(prop_small, existing_amenities=amenities)
        est_large = estimator.estimate(prop_large, existing_amenities=amenities)
        assert est_large.furnishing_cost > est_small.furnishing_cost

    def test_base_plus_per_bedroom(self):
        estimator = ImprovementEstimator()
        prop = make_property(bedrooms=3, sqft=1400)
        est = estimator.estimate(prop, existing_amenities=["hot tub", "game room", "fireplace", "mountain view deck", "EV charger"])
        # base $8000 + 3 * $4000 = $20,000 (no sqft premium under 1500)
        assert est.furnishing_cost == 20000

    def test_sqft_premium(self):
        estimator = ImprovementEstimator()
        prop = make_property(bedrooms=3, sqft=2000)
        est = estimator.estimate(prop, existing_amenities=["hot tub", "game room", "fireplace", "mountain view deck", "EV charger"])
        # base $8000 + 3*$4000 + (2000-1500)*$3.0 = $20,000 + $1,500 = $21,500
        assert est.furnishing_cost == 21500


class TestAmenityCosts:
    def test_all_amenities_when_none_exist(self):
        estimator = ImprovementEstimator()
        prop = make_property()
        est = estimator.estimate(prop, existing_amenities=[])
        # Should include all Gatlinburg amenities
        assert len(est.amenity_additions) > 0
        assert est.total_amenity_cost > 0

    def test_skips_existing_amenities(self):
        estimator = ImprovementEstimator()
        prop = make_property()
        est_none = estimator.estimate(prop, existing_amenities=[])
        est_some = estimator.estimate(prop, existing_amenities=["hot tub", "game room"])
        assert est_some.total_amenity_cost < est_none.total_amenity_cost

    def test_has_everything(self):
        estimator = ImprovementEstimator()
        prop = make_property()
        all_names = [a.name for a in MARKET_COMP_AMENITIES["Gatlinburg, TN"]]
        est = estimator.estimate(prop, existing_amenities=all_names)
        assert est.total_amenity_cost == 0
        assert len(est.amenity_additions) == 0

    def test_only_high_impact(self):
        estimator = ImprovementEstimator({"improvements": {"only_high_impact_amenities": True}})
        prop = make_property()
        est = estimator.estimate(prop, existing_amenities=[])
        for name, _ in est.amenity_additions:
            amenity = next(a for a in MARKET_COMP_AMENITIES["Gatlinburg, TN"] if a.name == name)
            assert amenity.revenue_impact == "high"

    def test_max_budget_cap(self):
        estimator = ImprovementEstimator({"improvements": {"max_amenity_budget": 10000}})
        prop = make_property()
        est = estimator.estimate(prop, existing_amenities=[])
        assert est.total_amenity_cost <= 10000

    def test_amenity_costs_include_labor(self):
        """Every amenity should have materials + labor = install_cost."""
        for market, amenities in MARKET_COMP_AMENITIES.items():
            for a in amenities:
                assert a.install_cost == a.materials_cost + a.labor_cost, (
                    f"{market}/{a.name}: {a.install_cost} != {a.materials_cost} + {a.labor_cost}"
                )
                # Non-zero materials for everything
                assert a.materials_cost > 0, f"{market}/{a.name} has zero materials cost"
                # Labor can be 0 (e.g., beach gear is just a purchase)


class TestCosmeticRehab:
    def test_new_home_no_rehab(self):
        estimator = ImprovementEstimator()
        prop = make_property(year_built=2024)
        est = estimator.estimate(prop, existing_amenities=["hot tub", "game room", "fireplace", "mountain view deck", "EV charger"])
        assert est.cosmetic_rehab == 0

    def test_older_home_needs_rehab(self):
        estimator = ImprovementEstimator()
        prop = make_property(year_built=1990)
        est = estimator.estimate(prop, existing_amenities=["hot tub", "game room", "fireplace", "mountain view deck", "EV charger"])
        assert est.cosmetic_rehab > 0

    def test_very_old_home_expensive(self):
        estimator = ImprovementEstimator()
        prop_new = make_property(year_built=2020)
        prop_old = make_property(year_built=1960)
        amenities = ["hot tub", "game room", "fireplace", "mountain view deck", "EV charger"]
        est_new = estimator.estimate(prop_new, existing_amenities=amenities)
        est_old = estimator.estimate(prop_old, existing_amenities=amenities)
        assert est_old.cosmetic_rehab > est_new.cosmetic_rehab

    def test_unknown_age_moderate_estimate(self):
        estimator = ImprovementEstimator()
        prop = make_property(year_built=None)
        amenities = ["hot tub", "game room", "fireplace", "mountain view deck", "EV charger"]
        est = estimator.estimate(prop, existing_amenities=amenities)
        assert est.cosmetic_rehab == 15000  # conservative default


class TestTotalEstimate:
    def test_total_is_sum_of_parts(self):
        estimator = ImprovementEstimator()
        prop = make_property()
        est = estimator.estimate(prop, existing_amenities=[])
        assert est.total == est.furnishing_cost + est.total_amenity_cost + est.cosmetic_rehab

    def test_all_markets_produce_estimates(self):
        estimator = ImprovementEstimator()
        for market in MARKET_COMP_AMENITIES:
            prop = make_property(market=market)
            est = estimator.estimate(prop, existing_amenities=[])
            assert est.total > 0, f"No improvement estimate for {market}"
            assert est.furnishing_cost > 0

    def test_unknown_market_still_works(self):
        estimator = ImprovementEstimator()
        prop = make_property(market="Unknown City, XX")
        est = estimator.estimate(prop, existing_amenities=[])
        assert est.total > 0
        assert est.furnishing_cost > 0
        # Should have generic amenity suggestions
        assert len(est.amenity_additions) > 0

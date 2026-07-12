"""Tests for the revenue estimator module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import Confidence, Property, RevenueSource
from src.revenue_estimator import RevenueEstimator


def make_property(market="Gatlinburg, TN", bedrooms=3, zipcode="37738"):
    return Property(
        zpid="123",
        address="123 Main St",
        city="Gatlinburg",
        state="TN",
        zipcode=zipcode,
        price=500000,
        bedrooms=bedrooms,
        bathrooms=2.0,
        market=market,
    )


class TestHeuristicEstimation:
    def test_known_market(self):
        estimator = RevenueEstimator()
        prop = make_property(market="Gatlinburg, TN", bedrooms=3)
        result = estimator.estimate(prop)

        assert result.nightly_rate == 275
        assert result.occupancy_rate == 0.72
        assert result.annual_revenue == 275 * 0.72 * 365
        assert result.source == RevenueSource.HEURISTIC
        assert result.confidence == Confidence.MEDIUM

    def test_different_bedroom_count(self):
        estimator = RevenueEstimator()
        prop1 = make_property(bedrooms=1)
        prop4 = make_property(bedrooms=4)
        r1 = estimator.estimate(prop1)
        r4 = estimator.estimate(prop4)

        assert r4.nightly_rate > r1.nightly_rate
        assert r4.annual_revenue > r1.annual_revenue

    def test_unknown_market_fallback(self):
        estimator = RevenueEstimator()
        prop = make_property(market="Somewhere Unknown", bedrooms=3)
        result = estimator.estimate(prop)

        assert result.annual_revenue > 0
        assert result.confidence == Confidence.LOW
        assert result.source == RevenueSource.HEURISTIC

    def test_capped_at_six_bedrooms(self):
        estimator = RevenueEstimator()
        prop = make_property(bedrooms=8)
        result = estimator.estimate(prop)
        # Should use 6-bedroom data (capped)
        assert result.nightly_rate > 0

    def test_all_markets_have_data(self):
        estimator = RevenueEstimator()
        markets = [
            "Gatlinburg, TN", "Pigeon Forge, TN", "Destin, FL",
            "Panama City Beach, FL", "Kissimmee, FL", "Gulf Shores, AL",
            "Scottsdale, AZ", "Joshua Tree, CA", "Big Bear Lake, CA",
            "Mount Pocono, PA", "Kill Devil Hills, NC", "Branson, MO",
            "Myrtle Beach, SC",
        ]
        for market in markets:
            prop = make_property(market=market, bedrooms=3)
            result = estimator.estimate(prop)
            assert result.annual_revenue > 0, f"No revenue for {market}"
            assert result.confidence == Confidence.MEDIUM

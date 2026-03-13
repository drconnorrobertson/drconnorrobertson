"""Tests for the AirDNA client module."""

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.airdna_client import (
    AIRDNA_AMENITY_MAP,
    AirDNAClient,
    normalize_airdna_amenities,
)


class TestNormalizeAmenities:
    def test_exact_match(self):
        result = normalize_airdna_amenities(["hot tub", "pool", "game room"])
        assert "hot tub" in result
        assert "private pool" in result
        assert "game room" in result

    def test_case_insensitive(self):
        result = normalize_airdna_amenities(["Hot Tub", "POOL", "Game Room"])
        assert "hot tub" in result
        assert "private pool" in result
        assert "game room" in result

    def test_variant_names(self):
        result = normalize_airdna_amenities(["jacuzzi", "swimming pool", "home theater"])
        assert "hot tub" in result
        assert "private pool" in result
        assert "theater room" in result

    def test_partial_match(self):
        result = normalize_airdna_amenities(["outdoor wood-burning firepit area"])
        assert "fire pit" in result

    def test_unknown_amenity_ignored(self):
        result = normalize_airdna_amenities(["wifi", "air conditioning", "kitchen"])
        assert len(result) == 0

    def test_empty_list(self):
        result = normalize_airdna_amenities([])
        assert len(result) == 0

    def test_deduplicates(self):
        result = normalize_airdna_amenities(["hot tub", "jacuzzi", "spa"])
        assert result == {"hot tub"}


class TestExtractAmenitiesFromListing:
    def test_list_of_strings(self):
        client = AirDNAClient("fake-key")
        listing = {"amenities": ["Hot Tub", "Pool", "WiFi"]}
        result = client._extract_amenities_from_listing(listing)
        assert "hot tub" in result
        assert "pool" in result
        assert "wifi" in result

    def test_list_of_dicts(self):
        client = AirDNAClient("fake-key")
        listing = {
            "amenities": [
                {"name": "Hot Tub"},
                {"amenity": "Pool"},
                {"name": "Game Room"},
            ]
        }
        result = client._extract_amenities_from_listing(listing)
        assert "hot tub" in result
        assert "pool" in result
        assert "game room" in result

    def test_nested_details(self):
        client = AirDNAClient("fake-key")
        listing = {"details": {"amenities": ["Fire Pit", "Grill"]}}
        result = client._extract_amenities_from_listing(listing)
        assert "fire pit" in result
        assert "grill" in result

    def test_listing_amenities_key(self):
        client = AirDNAClient("fake-key")
        listing = {"listing_amenities": ["Sauna", "EV Charger"]}
        result = client._extract_amenities_from_listing(listing)
        assert "sauna" in result
        assert "ev charger" in result

    def test_empty_listing(self):
        client = AirDNAClient("fake-key")
        result = client._extract_amenities_from_listing({})
        assert result == []


class TestExtractCompAmenities:
    def test_extracts_common_amenities(self):
        client = AirDNAClient("fake-key")

        mock_properties = [
            {"amenities": ["Hot Tub", "Game Room", "Fireplace"]},
            {"amenities": ["Hot Tub", "Game Room", "Pool"]},
            {"amenities": ["Hot Tub", "Pool", "Fireplace"]},
            {"amenities": ["Hot Tub", "Game Room", "Grill"]},
        ]

        with patch.object(client, "get_market_comps", return_value=mock_properties):
            result = client.extract_comp_amenities("Gatlinburg, TN", 3)

        # hot tub appears in 4/4, should be first
        assert "hot tub" in result
        # game room in 3/4 (75%), should be included
        assert "game room" in result

    def test_empty_when_api_fails(self):
        client = AirDNAClient("fake-key")
        with patch.object(client, "get_market_comps", return_value=[]):
            result = client.extract_comp_amenities("Gatlinburg, TN", 3)
        assert result == []

    def test_threshold_filters_rare(self):
        client = AirDNAClient("fake-key")

        # 10 properties, "rare amenity" only in 1 (10% < 30% threshold)
        mock_properties = [{"amenities": ["Hot Tub"]} for _ in range(9)]
        mock_properties.append({"amenities": ["Hot Tub", "Rare Amenity"]})

        with patch.object(client, "get_market_comps", return_value=mock_properties):
            result = client.extract_comp_amenities("Test Market", 3)

        assert "hot tub" in result
        assert "rare amenity" not in result


class TestImprovementEstimatorWithAirDNA:
    def test_uses_airdna_when_available(self):
        from src.improvement_estimator import ImprovementEstimator
        from src.models import Property

        mock_client = MagicMock()
        mock_client.extract_comp_amenities.return_value = [
            "hot tub", "game room", "fire pit", "pool"
        ]

        estimator = ImprovementEstimator(airdna_client=mock_client)
        prop = Property(
            zpid="123", address="123 Main", city="Gatlinburg", state="TN",
            zipcode="37738", price=500000, bedrooms=3, bathrooms=2.0,
            market="Gatlinburg, TN",
        )
        est = estimator.estimate(prop, existing_amenities=[])

        # Should have called AirDNA
        mock_client.extract_comp_amenities.assert_called_once()
        assert est.total > 0

    def test_falls_back_without_airdna(self):
        from src.improvement_estimator import ImprovementEstimator
        from src.models import Property

        estimator = ImprovementEstimator()  # no AirDNA client
        prop = Property(
            zpid="123", address="123 Main", city="Gatlinburg", state="TN",
            zipcode="37738", price=500000, bedrooms=3, bathrooms=2.0,
            market="Gatlinburg, TN",
        )
        est = estimator.estimate(prop, existing_amenities=[])

        # Should still produce an estimate from hardcoded data
        assert est.total > 0
        assert len(est.amenity_additions) > 0

    def test_caches_airdna_results(self):
        from src.improvement_estimator import ImprovementEstimator
        from src.models import Property

        mock_client = MagicMock()
        mock_client.extract_comp_amenities.return_value = ["hot tub"]

        estimator = ImprovementEstimator(airdna_client=mock_client)
        prop = Property(
            zpid="123", address="123 Main", city="Gatlinburg", state="TN",
            zipcode="37738", price=500000, bedrooms=3, bathrooms=2.0,
            market="Gatlinburg, TN",
        )

        # Call twice with same market/bedrooms
        estimator.estimate(prop, existing_amenities=[])
        estimator.estimate(prop, existing_amenities=[])

        # AirDNA should only be called once (cached)
        assert mock_client.extract_comp_amenities.call_count == 1

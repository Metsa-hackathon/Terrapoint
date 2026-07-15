import unittest

from calculators.valuation import (
    calculate_property_estimate,
    calculate_stand_value,
    valuation_reliability,
)


class StandValuationTests(unittest.TestCase):
    def test_pine_uses_published_q1_stumpage_range(self):
        result = calculate_stand_value("MA", stock_per_ha=100, area_ha=1)

        self.assertEqual(result["low_eur"], 7610)
        self.assertEqual(result["base_eur"], 7860)
        self.assertEqual(result["high_eur"], 8110)
        self.assertEqual(result["price_source_quality"], "published")

    def test_species_elements_improve_mixed_stand_estimate(self):
        result = calculate_stand_value(
            "MA",
            stock_per_ha=100,
            area_ha=1,
            elements=[
                {"puuliik_kood": "MA", "tagavara_y_ha": 50},
                {"puuliik_kood": "LV", "tagavara_y_ha": 50},
            ],
        )

        self.assertEqual(result["base_eur"], 4985)
        self.assertTrue(result["composition_used"])

    def test_unknown_species_uses_conservative_firewood_range_not_pine(self):
        result = calculate_stand_value("XX", stock_per_ha=100, area_ha=1)

        self.assertEqual(result["low_eur"], 1060)
        self.assertEqual(result["high_eur"], 1560)
        self.assertEqual(result["price_source_quality"], "fallback")

    def test_partial_elements_price_unexplained_volume_conservatively(self):
        result = calculate_stand_value(
            "MA",
            stock_per_ha=200,
            area_ha=1,
            elements=[{"puuliik_kood": "MA", "tagavara_y_ha": 100}],
        )

        self.assertEqual(result["base_eur"], 9170)
        self.assertEqual(result["composition_coverage"], 0.5)
        self.assertEqual(result["price_source_quality"], "fallback")

    def test_small_estimated_component_reports_proportional_share(self):
        result = calculate_stand_value(
            "MA",
            stock_per_ha=100,
            area_ha=1,
            elements=[
                {"puuliik_kood": "MA", "tagavara_y_ha": 99},
                {"puuliik_kood": "LH", "tagavara_y_ha": 1},
            ],
        )

        self.assertLess(result["estimated_value_share"], 0.02)

    def test_estimated_element_stock_reports_composition_uncertainty(self):
        result = calculate_stand_value(
            "MA",
            stock_per_ha=100,
            area_ha=1,
            elements=[
                {"puuliik_kood": "MA", "tagavara_y_ha": 50, "tagavara_provenance": "official"},
                {"puuliik_kood": "LV", "tagavara_y_ha": 50, "tagavara_provenance": "estimated"},
            ],
        )

        self.assertEqual(result["estimated_composition_share"], 0.5)


class ValuationReliabilityTests(unittest.TestCase):
    def test_old_inventory_widens_range_and_reduces_reliability(self):
        result = valuation_reliability(
            inventory={"vanim_inventuur_a": 11, "staatus": "kriitiline"},
            composition_coverage=1.0,
            estimated_price_share=0,
            post_inventory_notices=0,
            details_complete=True,
        )

        self.assertLessEqual(result["score"], 45)
        self.assertEqual(result["level"], "madal")
        self.assertEqual(result["range_low_factor"], 0.7)
        self.assertEqual(result["range_high_factor"], 1.3)
        self.assertTrue(any("11" in reason for reason in result["reasons"]))

    def test_property_estimate_separates_land_reference_and_timber(self):
        result = calculate_property_estimate(
            land_tax_value=100_000,
            timber={"low_eur": 70_000, "base_eur": 80_000, "high_eur": 90_000},
        )

        self.assertEqual(result["base_eur"], 180_000)
        self.assertEqual(result["low_eur"], 140_000)
        self.assertEqual(result["high_eur"], 220_000)
        self.assertEqual(result["land_method"], "tax_value_sensitivity")
        self.assertFalse(result["has_transaction_comparables"])

    def test_missing_land_reference_does_not_masquerade_as_property_value(self):
        result = calculate_property_estimate(
            land_tax_value=None,
            timber={"low_eur": 70_000, "base_eur": 80_000, "high_eur": 90_000},
        )

        self.assertFalse(result["land_reference_available"])
        self.assertIsNone(result["low_eur"])
        self.assertIsNone(result["base_eur"])
        self.assertIsNone(result["high_eur"])

    def test_missing_inventory_dates_reduce_reliability_even_with_fresh_known_date(self):
        result = valuation_reliability(
            inventory={
                "inventuuri_vanus_max_a": 0,
                "staatus": "hoiatus",
                "kuupaev_puudub_eraldisi": 1,
                "registrikande_kuupaev_puudub_eraldisi": 1,
            },
            composition_coverage=1,
            estimated_price_share=0,
            post_inventory_notices=0,
            details_complete=True,
        )

        self.assertLessEqual(result["score"], 60)
        self.assertLessEqual(result["range_low_factor"], 0.7)
        self.assertTrue(any("puudub" in reason.lower() for reason in result["reasons"]))

    def test_post_inventory_volume_widens_low_end_and_caps_reliability(self):
        result = valuation_reliability(
            inventory={"inventuuri_vanus_max_a": 1, "staatus": "hoiatus"},
            composition_coverage=1,
            estimated_price_share=0,
            post_inventory_notices=1,
            details_complete=True,
            post_inventory_volume_ratio=1,
        )

        self.assertEqual(result["level"], "keskmine")
        self.assertLessEqual(result["range_low_factor"], 0.4)

    def test_unavailable_notice_source_reduces_reliability(self):
        result = valuation_reliability(
            inventory={"inventuuri_vanus_max_a": 1},
            composition_coverage=1,
            estimated_price_share=0,
            post_inventory_notices=0,
            details_complete=True,
            notices_complete=False,
        )

        self.assertEqual(result["level"], "keskmine")
        self.assertLessEqual(result["range_low_factor"], 0.7)
        self.assertTrue(any("teatis" in reason.lower() for reason in result["reasons"]))

    def test_estimated_volume_and_composition_widen_range_and_reduce_reliability(self):
        result = valuation_reliability(
            inventory={"inventuuri_vanus_max_a": 1},
            composition_coverage=1,
            estimated_price_share=0,
            post_inventory_notices=0,
            details_complete=True,
            estimated_volume_share=1,
            estimated_composition_share=0.5,
        )

        self.assertEqual(result["level"], "madal")
        self.assertLessEqual(result["range_low_factor"], 0.6)
        self.assertGreaterEqual(result["range_high_factor"], 1.4)
        self.assertTrue(any("tagavara" in reason.lower() for reason in result["reasons"]))
        self.assertTrue(any("koosseisu" in reason.lower() for reason in result["reasons"]))

    def test_unavailable_stock_area_caps_confidence_and_widens_range(self):
        result = valuation_reliability(
            inventory={"inventuuri_vanus_max_a": 1},
            composition_coverage=1,
            estimated_price_share=0,
            post_inventory_notices=0,
            details_complete=True,
            unavailable_stock_area_share=0.6,
        )

        self.assertEqual(result["level"], "madal")
        self.assertLessEqual(result["range_low_factor"], 0.6)
        self.assertGreaterEqual(result["range_high_factor"], 1.4)
        self.assertTrue(any("puudub" in reason.lower() for reason in result["reasons"]))

    def test_unknown_notice_chronology_reduces_reliability(self):
        result = valuation_reliability(
            inventory={"inventuuri_vanus_max_a": 1},
            composition_coverage=1,
            estimated_price_share=0,
            post_inventory_notices=0,
            details_complete=True,
            unknown_notice_chronology_count=1,
        )

        self.assertEqual(result["level"], "keskmine")
        self.assertTrue(any("seostada" in reason.lower() for reason in result["reasons"]))


if __name__ == "__main__":
    unittest.main()

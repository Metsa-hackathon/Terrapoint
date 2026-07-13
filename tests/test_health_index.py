import unittest

from calculators.health_index import calculate_beetle_risk, calculate_health_assessment, spruce_context


class BeetleRiskTests(unittest.TestCase):
    def test_beetle_layers_do_not_raise_parcel_risk_without_spruce(self):
        result = calculate_beetle_risk(
            has_spruce=False,
            max_spruce_age=0,
            in_mke_zone=True,
            has_eelis_observation=True,
        )

        self.assertEqual(result["score"], 0)
        self.assertFalse(result["official_zone"])

    def test_mke_zone_is_critical_only_for_spruce(self):
        result = calculate_beetle_risk(
            has_spruce=True,
            max_spruce_age=70,
            in_mke_zone=True,
            has_eelis_observation=False,
        )

        self.assertEqual(result["score"], 3)
        self.assertTrue(result["official_zone"])

    def test_secondary_spruce_elements_drive_beetle_context(self):
        result = spruce_context(
            stands=[{"puuliik_kood": "MA", "vanus": 80}],
            elements_by_stand=[[{"puuliik_kood": "KU", "vanus": 70, "tagavara_y_ha": 80}]],
        )

        self.assertTrue(result["has_spruce"])
        self.assertEqual(result["max_spruce_age"], 70)


class HealthAssessmentTests(unittest.TestCase):
    def test_score_is_explained_by_detected_risk_components(self):
        result = calculate_health_assessment(
            beetle_score=2,
            damage_count=2,
            has_hogweed=True,
            inventory={"staatus": "värske", "vanim_inventuur_a": 2},
            details_complete=True,
            risk_layers_complete=True,
        )

        self.assertEqual(result["score"], 64)
        self.assertEqual([item["delta"] for item in result["components"]], [-16, -10, -10])
        self.assertEqual(result["methodology"], "Terrapoint remote risk signal v2")
        self.assertLessEqual(result["confidence"]["score"], 80)

    def test_stale_inventory_reduces_confidence_not_health_score(self):
        fresh = calculate_health_assessment(
            beetle_score=0,
            damage_count=0,
            has_hogweed=False,
            inventory={"staatus": "värske", "vanim_inventuur_a": 2},
            details_complete=True,
            risk_layers_complete=True,
        )
        stale = calculate_health_assessment(
            beetle_score=0,
            damage_count=0,
            has_hogweed=False,
            inventory={"staatus": "kriitiline", "vanim_inventuur_a": 11},
            details_complete=True,
            risk_layers_complete=True,
        )

        self.assertEqual(fresh["score"], stale["score"])
        self.assertLess(stale["confidence"]["score"], fresh["confidence"]["score"])
        self.assertEqual(stale["confidence"]["level"], "madal")

    def test_missing_inventory_dates_reduce_health_confidence(self):
        result = calculate_health_assessment(
            beetle_score=0,
            damage_count=0,
            has_hogweed=False,
            inventory={
                "inventuuri_vanus_max_a": 0,
                "kuupaev_puudub_eraldisi": 1,
                "registrikande_kuupaev_puudub_eraldisi": 1,
            },
            details_complete=True,
            risk_layers_complete=True,
        )

        self.assertLessEqual(result["confidence"]["score"], 50)
        self.assertTrue(any("puudub" in reason.lower() for reason in result["confidence"]["reasons"]))

    def test_incomplete_element_or_damage_details_reduce_confidence(self):
        result = calculate_health_assessment(
            beetle_score=0,
            damage_count=0,
            has_hogweed=False,
            inventory={"inventuuri_vanus_max_a": 1},
            details_complete=False,
            risk_layers_complete=True,
        )

        self.assertEqual(result["confidence"]["score"], 60)
        self.assertTrue(any("detailid" in reason.lower() for reason in result["confidence"]["reasons"]))


if __name__ == "__main__":
    unittest.main()

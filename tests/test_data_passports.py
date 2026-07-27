import unittest

from services.data_passports import build_asset_passports


class AssetPassportTests(unittest.TestCase):
    def test_builds_ordered_volume_and_value_passports(self):
        passports = build_asset_passports(
            stands=[
                {"eraldis_nr": 1, "tagavara_provenance": "official", "tagavara_y_ha": 100},
                {"eraldis_nr": 2, "tagavara_provenance": "official", "tagavara_y_ha": 124},
            ],
            inventory={
                "staatus": "värske",
                "vanim_invent_kp": "2024-01-15",
                "uusim_invent_kp": "2025-02-01",
                "inventuuri_vanus_max_a": 2,
            },
            reliability={"score": 82, "level": "kõrge", "reasons": ["Inventuur on värske."]},
            timber_estimate={"low_eur": 16_000, "base_eur": 18_500, "high_eur": 21_000},
            property_estimate={
                "land_reference_available": True,
                "land_reference_eur": 4_200,
                "low_eur": 18_800,
                "base_eur": None,
                "high_eur": 25_200,
                "has_transaction_comparables": False,
            },
            total_volume_m3=224,
        )

        self.assertEqual(
            [passport["id"] for passport in passports],
            ["forest_volume", "timber_value", "land_reference", "property_estimate"],
        )
        volume = passports[0]
        self.assertEqual(volume["value"], 224)
        self.assertEqual(volume["unit"], "m³")
        self.assertEqual(volume["provenance"], "derived")
        self.assertEqual(volume["label"], "Kasvava metsa kogumaht")
        self.assertEqual(volume["provenance_label"], "Arvutatud Metsaregistri andmetest")
        self.assertEqual(volume["source"]["name"], "Metsaregister")
        self.assertEqual(volume["source"]["oldest_as_of"], "2024-01-15")
        self.assertIn("m³/ha × pindala", volume["derivation"])
        self.assertIn("ei ole automaatselt raiutav", " ".join(volume["limitations"]).lower())
        self.assertTrue(volume["ai_question"])

        timber = passports[1]
        self.assertEqual(timber["range"], {"low": 16_000, "base": 18_500, "high": 21_000})
        self.assertEqual(timber["label"], "Kasvava puidu indikatiivne hinnavahemik")
        self.assertEqual(timber["confidence"]["score"], 82)
        self.assertEqual(timber["confidence"]["label"], "Kõrge lähteandmete usaldus")
        self.assertEqual(timber["provenance"], "estimate")
        self.assertEqual(timber["provenance_label"], "Arvutuslik hinnavahemik")

        land = passports[2]
        self.assertTrue(land["available"])
        self.assertEqual(land["value"], 4_200)
        self.assertEqual(land["provenance"], "official")
        self.assertEqual(land["label"], "Maa maksustamishind")
        self.assertEqual(land["provenance_label"], "Maa- ja Ruumiamet")
        self.assertIn("maksustamishind", " ".join(land["limitations"]).lower())

        property_value = passports[3]
        self.assertEqual(property_value["label"], "Kogu kinnistu indikatiivne hinnavahemik")
        self.assertEqual(
            property_value["provenance_label"],
            "Maa maksustamishind + puidu hinnavahemik",
        )
        self.assertIsNone(property_value["range"]["base"])
        self.assertIn("tehing", " ".join(property_value["limitations"]).lower())
        combined_limitations = " ".join(property_value["limitations"]).lower()
        for factor in ("raievalmidust", "ülestöötamise", "transpordi", "kahjustusi", "likviidsust"):
            self.assertIn(factor, combined_limitations)

    def test_land_reference_keeps_assessment_year_and_validity_semantics_separate(self):
        passports = build_asset_passports(
            stands=[{"eraldis_nr": 1, "tagavara_provenance": "official", "tagavara_y_ha": 100}],
            inventory={"staatus": "värske"},
            reliability={"score": 80, "level": "kõrge", "reasons": []},
            timber_estimate={"low_eur": 1_000, "base_eur": 1_500, "high_eur": 2_000},
            property_estimate={
                "land_reference_available": True,
                "land_reference_eur": 4_200,
                "low_eur": 3_940,
                "base_eur": None,
                "high_eur": 7_460,
            },
            total_volume_m3=100,
            land_reference_meta={
                "state": "available",
                "total_value": 4_200,
                "assessment_year": 2022,
                "assessment_time": "2025-12-17",
                "valid_from": "2025-12-17",
                "valid_until": None,
                "basis": "Alusandmete uuendamine",
            },
        )

        land = next(passport for passport in passports if passport["id"] == "land_reference")
        self.assertEqual(land["source"]["assessment_year"], 2022)
        self.assertEqual(land["source"]["valid_from"], "2025-12-17")
        self.assertEqual(land["source"]["assessed_at"], "2025-12-17")
        self.assertEqual(land["source"]["basis"], "Alusandmete uuendamine")
        self.assertNotIn("as_of", land["source"])

    def test_marks_volume_as_mixed_when_any_stand_stock_is_estimated(self):
        passports = build_asset_passports(
            stands=[
                {"eraldis_nr": 1, "tagavara_provenance": "official", "tagavara_y_ha": 100},
                {"eraldis_nr": 2, "tagavara_provenance": "estimated", "tagavara_y_ha": 80},
            ],
            inventory={"staatus": "hoiatus", "inventuuri_vanus_max_a": 7},
            reliability={"score": 54, "level": "keskmine", "reasons": []},
            timber_estimate={"low_eur": 10_000, "base_eur": 12_000, "high_eur": 16_000},
            property_estimate={"land_reference_available": False},
            total_volume_m3=180,
        )

        volume = passports[0]
        self.assertEqual(volume["provenance"], "mixed")
        self.assertEqual(volume["provenance_label"], "Registriandmed + Terrapointi hinnang")
        self.assertEqual(volume["quality"]["official_stands"], 1)
        self.assertEqual(volume["quality"]["estimated_stands"], 1)
        self.assertTrue(any("hinnanguline" in item.lower() for item in volume["limitations"]))

        land = passports[2]
        property_value = passports[3]
        self.assertFalse(land["available"])
        self.assertFalse(property_value["available"])
        self.assertEqual(property_value["unavailable_label"], "Maa maksustamishind puudub")

    def test_all_estimated_volume_never_claims_official_stock_inputs(self):
        passports = build_asset_passports(
            stands=[{"eraldis_nr": 1, "tagavara_provenance": "estimated", "tagavara_y_ha": 150}],
            inventory={"staatus": "värske", "inventuuri_vanus_max_a": 1},
            reliability={
                "score": 45,
                "level": "madal",
                "reasons": ["Kogu tagavara on hinnanguline."],
            },
            timber_estimate={"low_eur": 6_000, "base_eur": 10_000, "high_eur": 14_000},
            property_estimate={"land_reference_available": False},
            total_volume_m3=150,
        )

        volume, timber = passports[:2]
        self.assertEqual(volume["provenance"], "estimate")
        self.assertEqual(volume["provenance_label"], "Hinnatud Metsaregistri andmete põhjal")
        self.assertEqual(volume["quality"]["official_stands"], 0)
        self.assertEqual(volume["confidence"]["level"], "madal")
        self.assertIn("hinnang", volume["confidence"]["label"].lower())
        self.assertTrue(any("hinnanguline" in item.lower() for item in timber["limitations"]))

    def test_missing_stock_is_unavailable_even_if_provenance_label_is_inconsistent(self):
        passports = build_asset_passports(
            stands=[{
                "eraldis_nr": 1,
                "tagavara_provenance": "official",
                "tagavara_y_ha": None,
            }],
            inventory={"staatus": "värske"},
            reliability={"score": 80, "level": "kõrge", "reasons": []},
            timber_estimate={"low_eur": 1_000, "base_eur": 1_500, "high_eur": 2_000},
            property_estimate={"land_reference_available": False},
            total_volume_m3=0,
        )

        volume = passports[0]
        self.assertFalse(volume["available"])
        self.assertEqual(volume["quality"]["official_stands"], 0)
        self.assertEqual(volume["quality"]["unavailable_stands"], 1)

    def test_unsupported_stock_is_unavailable_and_notice_outage_caps_confidence(self):
        passports = build_asset_passports(
            stands=[{"eraldis_nr": 1, "tagavara_provenance": "unavailable"}],
            inventory={"staatus": "värske", "inventuuri_vanus_max_a": 1},
            reliability={
                "score": 65,
                "level": "keskmine",
                "reasons": ["Metsateatiste allikas ei vastanud; inventuurijärgset raiet ei saanud kontrollida"],
            },
            timber_estimate={"low_eur": 0, "base_eur": 0, "high_eur": 0},
            property_estimate={"land_reference_available": False},
            total_volume_m3=0,
        )

        volume = passports[0]
        self.assertFalse(volume["available"])
        self.assertEqual(volume["unavailable_label"], "Eraldiste tagavara lähteandmed puuduvad")
        self.assertEqual(volume["provenance"], "unknown")
        self.assertNotEqual(volume["confidence"]["level"], "kõrge")
        self.assertTrue(any("teatis" in reason.lower() for reason in volume["confidence"]["reasons"]))

    def test_estimated_and_unavailable_stock_is_incomplete_not_a_complete_estimate(self):
        passports = build_asset_passports(
            stands=[
                {"eraldis_nr": 1, "tagavara_provenance": "estimated", "tagavara_y_ha": 150},
                {"eraldis_nr": 2, "tagavara_provenance": "unavailable", "tagavara_y_ha": None},
            ],
            inventory={"staatus": "värske", "inventuuri_vanus_max_a": 1},
            reliability={
                "score": 40,
                "level": "madal",
                "reasons": ["Osal eraldistel puudub tagavara."],
            },
            timber_estimate={"low_eur": 6_000, "base_eur": 10_000, "high_eur": 14_000},
            property_estimate={
                "land_reference_available": True,
                "land_reference_eur": 4_200,
                "low_eur": 8_940,
                "base_eur": 14_200,
                "high_eur": 19_460,
            },
            total_volume_m3=150,
        )

        volume, timber, land, property_value = passports
        self.assertFalse(volume["available"])
        self.assertEqual(volume["provenance"], "mixed")
        self.assertIn("puud", volume["provenance_label"].lower())
        self.assertFalse(timber["available"])
        self.assertEqual(timber["unavailable_label"], "Puidu hinnangut ei saa tagavaraandmeteta arvutada")
        self.assertTrue(land["available"])
        self.assertFalse(property_value["available"])
        self.assertEqual(property_value["unavailable_label"], "Puidu tagavaraandmed puuduvad")

    def test_rejects_incomplete_or_invalid_timber_ranges(self):
        invalid_ranges = [
            {"low_eur": None, "base_eur": 1_000, "high_eur": None},
            {"low_eur": 2_000, "base_eur": 1_500, "high_eur": 1_000},
            {"low_eur": 1_000, "base_eur": float("nan"), "high_eur": 2_000},
        ]

        for timber_estimate in invalid_ranges:
            with self.subTest(timber_estimate=timber_estimate):
                passports = build_asset_passports(
                    stands=[{"eraldis_nr": 1, "tagavara_provenance": "official", "tagavara_y_ha": 100}],
                    inventory={"staatus": "värske"},
                    reliability={"score": 82, "level": "kõrge", "reasons": []},
                    timber_estimate=timber_estimate,
                    property_estimate={
                        "land_reference_available": True,
                        "land_reference_eur": 4_200,
                        "low_eur": 5_000,
                        "base_eur": None,
                        "high_eur": 8_000,
                    },
                    total_volume_m3=100,
                )

                timber = passports[1]
                self.assertFalse(timber["available"])
                self.assertEqual(
                    timber["unavailable_label"],
                    "Puidu hinnavahemiku lähteandmed puuduvad",
                )
                self.assertEqual(timber["range"], {"low": None, "base": None, "high": None})
                self.assertEqual(
                    passports[3]["unavailable_label"],
                    "Puidu hinnavahemiku lähteandmed puuduvad",
                )

    def test_combines_missing_land_and_timber_reasons(self):
        passports = build_asset_passports(
            stands=[{"eraldis_nr": 1, "tagavara_provenance": "unavailable"}],
            inventory={"staatus": "kriitiline"},
            reliability={"score": 20, "level": "madal", "reasons": []},
            timber_estimate={"low_eur": None, "base_eur": None, "high_eur": None},
            property_estimate={"land_reference_available": False},
            total_volume_m3=0,
        )

        property_value = passports[3]
        self.assertFalse(property_value["available"])
        self.assertEqual(
            property_value["unavailable_label"],
            "Maa maksustamishind ja puidu tagavaraandmed puuduvad",
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from api.index import _forest_area_ha, build_system_prompt


class AreaDataTests(unittest.TestCase):
    def test_forest_area_is_sum_of_all_eraldised_not_last_eraldis(self):
        eraldised = [
            {"id": 1, "pindala_ha": 2.62},
            {"id": 2, "pindala_ha": 1.32},
            {"id": 3, "pindala_ha": 0.46},
        ]

        self.assertAlmostEqual(_forest_area_ha(eraldised), 4.40)
        self.assertNotEqual(_forest_area_ha(eraldised), eraldised[-1]["pindala_ha"])

    def test_ai_prompt_uses_kataster_forest_area_field(self):
        prompt = build_system_prompt({
            "kataster": {
                "number": "78404:409:0113",
                "pindala_ha": 21.65,
                "mets_pindala_ha": 20.17,
            },
            "mets": {
                "puuliik": "Mänd",
                "vanus": 65,
                "tagavara_y_ha": 180,
                "pindala_ha": 20.17,
            },
        })

        self.assertIn("Metsamaa pindala: 20.17 ha", prompt)
        self.assertNotIn("Metsamaa pindala: 1.28 ha", prompt)

    def test_ai_prompt_describes_freshness_and_historical_cutting_without_claiming_execution(self):
        prompt = build_system_prompt({
            "kataster": {"number": "78404:409:0113", "pindala_ha": 2},
            "mets": {
                "puuliik": "kask",
                "elus_tagavara_ha": 120,
                "inventuur": {
                    "staatus": "hoiatus",
                    "vanim_invent_kp": "2018-01-01",
                    "inventuuri_vanus_max_a": 8,
                    "inventuurijargsed_teatised": 1,
                },
            },
            "riskid": {
                "ajaloolised_lageraiealad": [{
                    "periood_algus": 2013,
                    "periood_lopp": 2015,
                    "vanus_vahemalt_a": 10,
                }],
            },
            "teatised": [{
                "tyyp": "Lageraie",
                "maht": 50,
                "otsus_kinnitatud_kp": "2024-01-10",
                "parast_inventuuri": True,
                "active": False,
            }],
        })

        self.assertIn("Elus puistutagavara: 120 m³/ha", prompt)
        self.assertIn("Inventuuri andmekvaliteet: hoiatus", prompt)
        self.assertIn("Ajalooline lageraie satelliidituvastus: 2013–2015", prompt)
        self.assertIn("kavandatud maht 50 m³", prompt)
        self.assertNotIn("Hiljutine lageraieala", prompt)

    def test_ai_prompt_preserves_valuation_range_and_health_caveat(self):
        prompt = build_system_prompt({
            "kataster": {"number": "78404:409:0113", "pindala_ha": 2},
            "vaartus": {
                "total_value_eur": 80_000,
                "range_low_eur": 70_000,
                "range_high_eur": 90_000,
                "property_estimate": {"low_eur": 140_000, "base_eur": 180_000, "high_eur": 220_000},
                "reliability": {"score": 55, "level": "keskmine"},
            },
            "riskid": {
                "terviseindeks": 84,
                "terviseindeks_selgitus": {
                    "methodology": "Terrapoint remote risk signal v2",
                    "confidence": {"score": 60, "level": "keskmine"},
                    "components": [{"label": "Üraskirisk", "delta": -16}],
                },
            },
        })

        self.assertIn("Kinnistu automaatne vahemik: 140000–220000 EUR", prompt)
        self.assertIn("Puidu hinnavahemik: 70000–90000 EUR", prompt)
        self.assertIn("Hinnangu usaldus: 55/100 (keskmine)", prompt)
        self.assertIn("Kaugandmete terviseskoor: 84/100", prompt)
        self.assertIn("ei ole ametlik terviseindeks", prompt)

    def test_ai_prompt_prefers_corrected_beetle_assessment(self):
        prompt = build_system_prompt({
            "kataster": {"number": "78404:409:0113", "pindala_ha": 2},
            "riskid": {
                "yrask": {"score": 3, "label": "Kriitiline — MKE tsoonis"},
                "yrask_hinnang": {"score": 0, "label": "Madal — kuuske ei tuvastatud"},
            },
        })

        self.assertIn("Üraski risk: Madal — kuuske ei tuvastatud", prompt)
        self.assertNotIn("Üraski risk: Kriitiline — MKE tsoonis", prompt)

    def test_ai_prompt_prefers_new_stand_and_unit_values(self):
        prompt = build_system_prompt({
            "kataster": {"number": "78404:409:0113", "pindala_ha": 1},
            "mets": {"eraldised": [{
                "eraldis_nr": 1,
                "puuliik": "mänd",
                "vaartus_eur": 7_800,
                "vaartus_hinnang_eur": 1_310,
            }]},
            "vaartus": {
                "total_value_eur": 7_800,
                "base_value_eur": 1_310,
                "value_per_ha": 7_800,
                "base_value_per_ha": 1_310,
                "price_per_m3": 78,
                "base_price_per_m3": 13.1,
            },
        })

        self.assertIn("väärtus 1310 EUR", prompt)
        self.assertIn("Väärtus ha kohta: 1310 EUR/ha", prompt)
        self.assertIn("Keskmine hind: 13.1 EUR/m³", prompt)
        self.assertNotIn("väärtus 7800 EUR", prompt)

    def test_ai_prompt_includes_all_subsidy_states_and_audit_fields(self):
        prompt = build_system_prompt({
            "kataster": {"number": "78404:409:0113", "pindala_ha": 2},
            "toetused": [
                {
                    "name": "Inventeerimise toetus",
                    "eligibility_status": "Vajab kontrolli",
                    "eligibility_reason": "Seitsme aasta piirang vajab kontrolli.",
                    "application_status": "upcoming",
                    "application_period": "01.12–15.12.2026",
                    "application_channel": "e-PRIA",
                    "amount": "20 €/ha",
                    "verification_items": ["metsaühistu liikmesus"],
                    "source_name": "Riigi Teataja",
                    "source_url": "https://www.riigiteataja.ee/akt/110032026007",
                    "verified_at": "2026-07-13",
                    "source_as_of": "2026-03-10",
                    "catalog_valid_through": "2026-12-31",
                    "disclaimer": "Lõpliku otsuse teeb toetuse andja.",
                    "match_scope": "compartment",
                    "eraldised_match_count": 6,
                    "eraldised_match_ha": 4.2,
                    "eraldised_match": [
                        {"eraldis_nr": nr, "pindala_ha": 0.7, "match_reason": "Metsaregistri eraldis."}
                        for nr in range(1, 7)
                    ],
                },
                {
                    "name": "Looduskaitse hüvitis",
                    "eligibility_status": "Ei sobi teadaolevate andmete põhjal",
                    "eligibility_reason": "Kattuvust ei leitud.",
                    "application_status": "closed",
                    "application_period": "04.04–30.04.2026",
                    "application_channel": "e-PRIA",
                    "amount": "kuni 160 €/ha",
                    "verification_items": ["ametlik kaart"],
                    "source_name": "PRIA",
                    "source_url": "https://www.pria.ee/toetused/example",
                    "verified_at": "2026-07-13",
                    "disclaimer": "Lõpliku otsuse teeb toetuse andja.",
                },
            ],
        })

        self.assertIn("--- METSATOETUSTE HINNANG ---", prompt)
        self.assertIn("Inventeerimise toetus: Vajab kontrolli", prompt)
        self.assertIn("Looduskaitse hüvitis: Ei sobi teadaolevate andmete põhjal", prompt)
        self.assertIn("Seitsme aasta piirang vajab kontrolli.", prompt)
        self.assertIn("01.12–15.12.2026", prompt)
        self.assertIn("metsaühistu liikmesus", prompt)
        self.assertIn("https://www.riigiteataja.ee/akt/110032026007", prompt)
        self.assertIn("Eraldised: 6 tk, 4.2 ha, ulatus compartment", prompt)
        self.assertIn("Näidatud 5/6 eraldist", prompt)
        self.assertIn("allika seis 2026-03-10", prompt)
        self.assertIn("kataloog kehtib kuni 2026-12-31", prompt)
        self.assertIn("Lõpliku otsuse teeb toetuse andja.", prompt)


if __name__ == "__main__":
    unittest.main()

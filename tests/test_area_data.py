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


if __name__ == "__main__":
    unittest.main()

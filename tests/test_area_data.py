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


if __name__ == "__main__":
    unittest.main()

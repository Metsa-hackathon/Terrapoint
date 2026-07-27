import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from api import index as api


PARCEL = "78404:409:0113"
PARCEL_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
}
INTERSECTING_FEATURE = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[24.01, 59.01], [24.02, 59.01], [24.02, 59.02], [24.01, 59.01]]],
    },
    "properties": {},
}


class EudrContractTests(unittest.TestCase):
    def setUp(self):
        api._rate_limit_buckets.clear()
        self.client = TestClient(api.app)
        self.kataster = {
            "number": PARCEL,
            "geometry": PARCEL_GEOMETRY,
            "pindala_ha": 1.5,
            "sihtotstarve": "MAATULUNDUSMAA",
            "mk_nimi": "Harju maakond",
            "ov_nimi": "Tallinn",
            "l_aadress": "Testi kinnistu",
        }
        self.eraldised = [{
            "pindala_ha": 1.2,
            "puuliik_kood": "MA",
            "vanus": 60,
        }]

    def request(self, layers, unavailable=None, truncated=None):
        self.layer_query = AsyncMock(
            return_value=(layers, unavailable or [], truncated or [])
        )
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=self.kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=self.eraldised)),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
            patch("api.index.query_layers", new=self.layer_query),
        ):
            return self.client.get(f"/api/export/eudr/{PARCEL}")

    def test_export_queries_only_the_relevant_spatial_sources(self):
        response = self.request({"kaitsealad": [], "sood": []})

        self.assertEqual(response.status_code, 200)
        self.layer_query.assert_awaited_once()
        self.assertEqual(self.layer_query.await_args.args[1], ("kaitsealad", "sood"))

    def test_adaptest_activity_model_is_not_exported_as_an_official_protected_area(self):
        response = self.request({
            "kaitsealad": [],
            "katsealad": [INTERSECTING_FEATURE],
            "sood": [],
        })

        self.assertEqual(response.status_code, 200)
        properties = response.json()["features"][0]["properties"]
        self.assertFalse(properties["kaitseala"])
        self.assertEqual(properties["spatial_status"]["kaitseala"], {
            "intersects": False,
            "sources_complete": True,
        })

    def test_export_uses_dominant_volume_species_instead_of_first_stand(self):
        self.eraldised = [
            {"pindala_ha": 1, "puuliik_kood": "KS", "vanus": 60, "tagavara_y_ha": 10},
            {"pindala_ha": 2, "puuliik_kood": "MA", "vanus": 70, "tagavara_y_ha": 100},
        ]

        response = self.request({"kaitsealad": [], "sood": []})

        self.assertEqual(response.status_code, 200)
        properties = response.json()["features"][0]["properties"]
        self.assertEqual(properties["peapuuliik"], "MA")

    def test_export_does_not_guess_missing_forest_species_or_age(self):
        self.eraldised = [{
            "pindala_ha": 1.2,
            "puuliik_kood": "MA",
            "puuliik_kood_raw": None,
            "vanus": 0,
            "vanus_raw": None,
            "tagavara_y_ha": 100,
        }]

        response = self.request({"kaitsealad": [], "sood": []})

        self.assertEqual(response.status_code, 200)
        properties = response.json()["features"][0]["properties"]
        self.assertIsNone(properties["peapuuliik"])
        self.assertFalse(properties["metsa_liigiandmed_taielikud"])
        self.assertIsNone(properties["keskmine_vanus"])
        self.assertFalse(properties["metsa_vanuseandmed_taielikud"])

    def test_export_does_not_choose_a_dominant_species_with_missing_stock(self):
        self.eraldised = [
            {
                "pindala_ha": 1,
                "puuliik_kood": "MA",
                "puuliik_kood_raw": "MA",
                "vanus": 20,
                "vanus_raw": 20,
                "tagavara_y_ha": 100,
            },
            {
                "pindala_ha": 10,
                "puuliik_kood": "KU",
                "puuliik_kood_raw": "KU",
                "vanus": 30,
                "vanus_raw": 30,
                "tagavara_y_ha": None,
            },
        ]

        response = self.request({"kaitsealad": [], "sood": []})

        properties = response.json()["features"][0]["properties"]
        self.assertTrue(properties["metsa_liigiandmed_taielikud"])
        self.assertFalse(properties["metsa_tagavaraandmed_taielikud"])
        self.assertIsNone(properties["peapuuliik"])

    def test_export_preserves_a_valid_zero_age(self):
        self.eraldised = [{
            "pindala_ha": 1.2,
            "puuliik_kood": "MA",
            "puuliik_kood_raw": "MA",
            "vanus": 0,
            "vanus_raw": 0,
            "tagavara_y_ha": 0,
        }]

        response = self.request({"kaitsealad": [], "sood": []})

        properties = response.json()["features"][0]["properties"]
        self.assertEqual(properties["keskmine_vanus"], 0)
        self.assertTrue(properties["metsa_vanuseandmed_taielikud"])

    def test_export_is_explicitly_a_geolocation_reference_not_due_diligence_declaration(self):
        response = self.request({"kaitsealad": [], "sood": []})

        self.assertEqual(response.status_code, 200)
        properties = response.json()["features"][0]["properties"]
        self.assertEqual(properties["eudr_export_scope"], "geolocation_reference")
        self.assertFalse(properties["eudr_due_diligence_complete"])
        self.assertTrue(properties["eudr_limitations"])
        self.assertTrue(any("raadamis" in item.lower() for item in properties["eudr_limitations"]))

    def test_export_fails_closed_when_relevant_status_is_unknown(self):
        response = self.request(
            {"kaitsealad": [], "katsealad": [], "sood": []},
            unavailable=["sood"],
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("täielike ruumiandmeteta", response.json()["error"])

    def test_unrelated_truncated_layer_does_not_block_export(self):
        response = self.request(
            {"kaitsealad": [], "katsealad": [], "sood": []},
            truncated=["veekogud"],
        )

        self.assertEqual(response.status_code, 200)
        properties = response.json()["features"][0]["properties"]
        self.assertFalse(properties["kaitseala"])
        self.assertFalse(properties["natura_2000"])
        self.assertFalse(properties["soode_ala"])

    def test_malformed_relevant_geometry_fails_closed(self):
        malformed = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": "bad"},
            "properties": {},
        }

        response = self.request({
            "kaitsealad": [malformed],
            "katsealad": [],
            "sood": [],
        })

        self.assertEqual(response.status_code, 503)

    def test_empty_relevant_geometry_fails_closed(self):
        empty = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": []},
            "properties": {},
        }

        response = self.request({
            "kaitsealad": [empty],
            "katsealad": [],
            "sood": [],
        })

        self.assertEqual(response.status_code, 503)

    def test_missing_required_protection_layer_fails_closed(self):
        response = self.request({
            "katsealad": [INTERSECTING_FEATURE],
            "sood": [],
        })

        self.assertEqual(response.status_code, 503)

    def test_self_intersecting_relevant_geometry_fails_closed(self):
        invalid = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[23.9, 58.9], [24.2, 59.2], [23.9, 59.2], [24.2, 58.9], [23.9, 58.9]]],
            },
            "properties": {},
        }

        response = self.request({
            "kaitsealad": [invalid],
            "katsealad": [],
            "sood": [],
        })

        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()

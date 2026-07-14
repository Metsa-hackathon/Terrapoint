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
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=self.kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=self.eraldised)),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
            patch(
                "api.index.query_all_layers",
                new=AsyncMock(return_value=(layers, unavailable or [], truncated or [])),
            ),
        ):
            return self.client.get(f"/api/export/eudr/{PARCEL}")

    def test_export_uses_metsaregister_protected_area_in_canonical_status(self):
        response = self.request({
            "kaitsealad": [],
            "katsealad": [INTERSECTING_FEATURE],
            "sood": [],
        })

        self.assertEqual(response.status_code, 200)
        properties = response.json()["features"][0]["properties"]
        self.assertTrue(properties["kaitseala"])
        self.assertEqual(properties["spatial_status"]["kaitseala"], {
            "intersects": True,
            "sources_complete": True,
        })

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
            "kaitsealad": [],
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

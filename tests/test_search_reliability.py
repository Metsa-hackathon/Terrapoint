import asyncio
import copy
import unittest
from unittest.mock import AsyncMock, patch

import orjson

from api import index as api


class SearchReliabilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        api.search_cache.clear()

    async def test_timeout_is_a_retryable_gateway_timeout(self):
        with patch("api.index._search_core", new=AsyncMock(side_effect=asyncio.TimeoutError)):
            response = await api._search("78404:409:0113")

        self.assertEqual(response.status_code, 504)
        self.assertEqual(orjson.loads(response.body)["code"], "SEARCH_TIMEOUT")

    async def test_partial_response_is_not_cached(self):
        result = {
            "kataster": {"number": "78404:409:0113"},
            "meta": {
                "partial": True,
                "unavailable_sources": ["metsaregister.eraldised"],
            },
        }
        search_core = AsyncMock(side_effect=[copy.deepcopy(result), copy.deepcopy(result)])

        with patch("api.index._search_core", new=search_core):
            first = await api._search("78404:409:0113")
            second = await api._search("78404:409:0113")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(search_core.await_count, 2)

    async def test_subordinate_source_failure_is_reported_as_partial_data(self):
        kataster = {
            "number": "78404:409:0113",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
            },
            "pindala_ha": 1,
        }

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(side_effect=RuntimeError("WFS unavailable"))),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", 0)

        self.assertTrue(result["meta"]["partial"])
        self.assertIn("metsaregister.eraldised", result["meta"]["unavailable_sources"])
        self.assertIsNone(result["mets"])

    async def test_layer_features_outside_the_parcel_do_not_create_restrictions(self):
        kataster = {
            "number": "78404:409:0113",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
            },
            "pindala_ha": 1,
        }
        nearby_but_not_intersecting = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.2, 59.2], [24.3, 59.2], [24.3, 59.3], [24.2, 59.2]]],
            },
            "properties": {"nimi": "Naaberkinnistu kaitseala"},
        }

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({"kaitsealad": [nearby_but_not_intersecting]}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", 0)

        self.assertEqual(result["kitsendused"], [])

    async def test_layer_truncation_is_not_reported_as_partial(self):
        # Suur mets → kihid jooksevad 100 feature piirile (truncated), kuid
        # see ei halvenda analüüsi: _filter_features_by_geometry jätab krundi
        # andmed alles. Osaline staatus blokeerib AI analüüsi ja näitab
        # hirmusõnumit, seega truncation ei tohi partial=True pärida.
        kataster = {
            "number": "78404:409:0113",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
            },
            "pindala_ha": 50,
        }
        truncated_layers = ["kaitsealad", "sood", "veekogud", "vooluveed", "natura_elupaik"]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], truncated_layers))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", 0)

        self.assertFalse(result["meta"]["partial"])
        self.assertEqual(result["meta"]["truncated_layers"], sorted(truncated_layers))
        self.assertEqual(result["meta"]["unavailable_sources"], [])

    async def test_layer_failure_still_reports_partial(self):
        # Reaalne WFS katke (vigane kiht) peab jääma osaliseks — see on
        # andmete puudumine, mitte mahupiir.
        kataster = {
            "number": "78404:409:0113",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
            },
            "pindala_ha": 1,
        }

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({"kaitsealad": []}, ["kaitsealad"], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", 0)

        self.assertTrue(result["meta"]["partial"])
        self.assertIn("layers.kaitsealad", result["meta"]["unavailable_sources"])
        self.assertEqual(result["meta"]["truncated_layers"], [])

    async def test_intentional_detail_skip_is_not_reported_as_source_failure(self):
        kataster = {
            "number": "78404:409:0113",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
            },
            "pindala_ha": 31,
        }
        eraldised = [
            {"id": index, "pindala_ha": 1, "puuliik_kood": "MA", "puuliik": "Mänd", "vanus": 40, "tagavara_y_ha": 100}
            for index in range(31)
        ]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=eraldised)),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", 0)

        self.assertFalse(result["meta"]["partial"])
        self.assertTrue(result["meta"]["details_skipped"])


if __name__ == "__main__":
    unittest.main()

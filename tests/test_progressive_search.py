"""Progressiivne otsingu laadimine: kiire põhiandmed + eraldi detailid.

Leht laeb kinnistu kahes etapis: kiire variant annab põhiandmed kiiremini,
täielik variant lisab eraldiste detailid (liikide koosseis ja kahjustused).
Mõlemad kasutavad serveris ühist allikavahemälu, et upstreami päringuid ei
dubleerita.
"""

import contextlib
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from api import index as api

KATASTER_NR = "78404:409:0113"
GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
}


class ProgressiveSearchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        api._rate_limit_buckets.clear()
        self.client = TestClient(api.app)
        self.kataster = {
            "number": KATASTER_NR,
            "geometry": GEOMETRY,
            "pindala_ha": 1,
        }
        self.stands = [
            {
                "id": 1,
                "eraldis_nr": 1,
                "geometry": GEOMETRY,
                "pindala_ha": 1,
                "puuliik_kood": "MA",
                "puuliik_kood_raw": None,
                "puuliik": "mänd",
                "vanus": 40,
                "tagavara_y_ha": 100,
                "tagavara_provenance": "official",
                "boniteedi_kood": 2,
            }
        ]

    @contextlib.contextmanager
    def _patches(self, element_mock, kahjustus_mock):
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=self.kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=self.stands)),
            patch("api.index.query_eraldis_element", new=element_mock),
            patch("api.index.query_kahjustused", new=kahjustus_mock),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            yield

    async def test_fast_variant_skips_the_details_phase(self):
        element_mock = AsyncMock(return_value=[])
        kahjustus_mock = AsyncMock(return_value=[])
        with self._patches(element_mock, kahjustus_mock):
            result = await api._search_core(
                KATASTER_NR,
                time.time(),
                include_map_layers=False,
                include_details=False,
            )

        element_mock.assert_not_awaited()
        kahjustus_mock.assert_not_awaited()
        meta = result["meta"]
        self.assertTrue(meta["details_pending"])
        self.assertTrue(meta["details_skipped"])
        self.assertFalse(meta["partial"])
        self.assertEqual(meta["unavailable_sources"], [])

    async def test_full_variant_fetches_the_details(self):
        element_mock = AsyncMock(return_value=[])
        kahjustus_mock = AsyncMock(return_value=[])
        with self._patches(element_mock, kahjustus_mock):
            result = await api._search_core(
                KATASTER_NR,
                time.time(),
                include_map_layers=False,
            )

        element_mock.assert_awaited()
        meta = result["meta"]
        self.assertFalse(meta["details_pending"])
        self.assertFalse(meta["details_skipped"])

    def test_fast_and_full_variants_use_separate_cache_keys(self):
        fast_key = api._search_cache_key(KATASTER_NR, False, False)
        full_key = api._search_cache_key(KATASTER_NR, False, True)
        self.assertNotEqual(fast_key, full_key)
        self.assertNotEqual(fast_key, api._search_cache_key(KATASTER_NR, True, False))
        self.assertEqual(full_key, api._search_cache_key(KATASTER_NR, False))

    async def test_cached_fast_result_is_not_served_for_the_full_variant(self):
        element_mock = AsyncMock(return_value=[])
        kahjustus_mock = AsyncMock(return_value=[])
        with self._patches(element_mock, kahjustus_mock):
            fast, fast_status = await api._search_uncached(
                KATASTER_NR, include_map_layers=False, include_details=False
            )
            full, full_status = await api._search_uncached(
                KATASTER_NR, include_map_layers=False
            )

        self.assertEqual(fast_status, 200)
        self.assertEqual(full_status, 200)
        self.assertTrue(fast["meta"]["details_pending"])
        self.assertFalse(full["meta"]["details_pending"])
        # Kiire variant jääb oma vahemälupositsiooni, mitte ei tõrju täielikku.
        cached_fast = api.search_cache.get(api._search_cache_key(KATASTER_NR, False, False))
        cached_full = api.search_cache.get(api._search_cache_key(KATASTER_NR, False, True))
        self.assertTrue(cached_fast["meta"]["details_pending"])
        self.assertFalse(cached_full["meta"]["details_pending"])

    def test_endpoint_forwards_the_details_flag(self):
        payload = {
            "kataster": {"number": KATASTER_NR},
            "mets": {},
            "meta": {"partial": False, "unavailable_sources": []},
        }
        search_core = AsyncMock(return_value=payload)
        with patch("api.index._search_core", new=search_core):
            response = self.client.get(
                f"/api/search/{KATASTER_NR}?include_map_layers=false&include_details=false"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search_core.await_args.kwargs["include_details"], False)

        search_core = AsyncMock(return_value=payload)
        with patch("api.index._search_core", new=search_core):
            response = self.client.get(f"/api/search/{KATASTER_NR}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search_core.await_args.kwargs["include_details"], True)


if __name__ == "__main__":
    unittest.main()

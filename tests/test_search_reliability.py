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

    async def test_large_forest_fetches_element_data_not_just_peapuuliik(self):
        # Suure metsaga (>30 eraldist) peab liikide koosseis baseeruma
        # element-tasandi andmetel (mitmekesisus), mitte ainult iga eraldise
        # peapuuliigil (~100% ühte liiki kõigi jaoks). Vana kood skipetas
        # kõik üle 30 eraldise ja näitas suurtele metsadele alati ~100% ühte
        # liiki — see nägi välja nagu koosseis korduks igal metsal.
        import time as _time
        kataster = {
            "number": "21401:001:0123",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
            },
            "pindala_ha": 100,
        }
        # 50 eraldised — vana lävend 30 oleks skipemas, uus lävend 200 ei
        eraldised = [
            {"id": 100 + i, "pindala_ha": 1, "puuliik_kood": "MA", "puuliik": "Mänd",
             "vanus": 60, "tagavara_y_ha": 200, "boniteedi_kood": 3, "eraldis_nr": i + 1}
            for i in range(50)
        ]
        # Element-tasandil on segatud liike (KA, KU) — see on täpsem kui
        # eraldise peapuuliik MA
        async def fake_element(eraldis_id):
            return [
                {"eraldis_id": eraldis_id, "puuliik_kood": "MA", "puuliik": "Mänd",
                 "vanus": 60, "tagavara_y_ha": 150, "taius": 8},
                {"eraldis_id": eraldis_id, "puuliik_kood": "KU", "puuliik": "Kuusk",
                 "vanus": 55, "tagavara_y_ha": 50, "taius": 2},
            ]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=eraldised)),
            patch("api.index.query_eraldis_element", new=AsyncMock(side_effect=fake_element)),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("21401:001:0123", _time.time())

        mets = result["mets"] or {}
        koos = mets.get("liikide_koosseis", [])
        # Koosseis peab sisaldama nii MA kui KU — vana kood annaks ainult MA
        codes = {s.get("puuliik_kood") for s in koos}
        self.assertIn("MA", codes)
        self.assertIn("KU", codes, "Kuusk puudub koosseisust — element-andmeid ei laetud")
        # Ei tohiks olla details_skipped=True (eraldiseid 50 on alla lävendi 200)
        self.assertFalse(result["meta"]["details_skipped"])
        self.assertFalse(result["meta"]["sampled_eraldised"])

    async def test_gather_in_batches_respects_batch_size(self):
        # Veendu, et _gather_in_batches jookseb batch-kaupa ja ei ürita
        # kõiki korraga. 60 ülesannet batch=20 peab jagunema 3 batch'i.
        call_log = []
        current_running = 0
        max_concurrent = 0

        async def task(i):
            nonlocal current_running, max_concurrent
            current_running += 1
            max_concurrent = max(max_concurrent, current_running)
            call_log.append(i)
            await asyncio.sleep(0.01)
            current_running -= 1
            return i * 2

        tasks = [task(i) for i in range(60)]
        results = await api._gather_in_batches(tasks, batch_size=20, overall_timeout=5.0)
        self.assertEqual(results, [i * 2 for i in range(60)])
        # Batch=20 → korraga max 20 (mitte 60)
        self.assertLessEqual(max_concurrent, 20)
        self.assertGreater(max_concurrent, 1)

    async def test_gather_in_batches_handles_overall_timeout(self):
        # Overall timeout peab katkestama ja tagastama fallback'i järelejäänutele
        async def slow_task(i):
            await asyncio.sleep(10)
            return i

        tasks = [slow_task(i) for i in range(10)]
        results = await api._gather_in_batches(tasks, batch_size=5, overall_timeout=0.2,
                                              fallback_per_task=list)
        # Kõik peaksid saama fallback[] (esimene batch ei jõua kunagi valmida 10s sleepiga)
        self.assertEqual(results, [[]] * 10)

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

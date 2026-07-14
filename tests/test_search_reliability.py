import asyncio
import copy
import inspect
import unittest
from unittest.mock import AsyncMock, patch

import orjson

from api import index as api


class SearchReliabilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        api.search_cache.clear()
        api._search_in_flight.clear()
        api._search_waiters.clear()

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

    async def test_concurrent_same_key_cold_searches_share_in_flight_result(self):
        result = {
            "kataster": {"number": "78404:409:0113"},
            "meta": {"partial": False, "unavailable_sources": []},
        }
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow_search_core(*args):
            started.set()
            await release.wait()
            return copy.deepcopy(result)

        search_core = AsyncMock(side_effect=slow_search_core)
        with patch("api.index._search_core", new=search_core):
            first_task = asyncio.create_task(api._search("78404:409:0113"))
            await asyncio.wait_for(started.wait(), timeout=1)
            second_task = asyncio.create_task(api._search("78404:409:0113"))
            await asyncio.sleep(0)
            release.set()
            first, second = await asyncio.gather(first_task, second_task)

        self.assertEqual(search_core.await_count, 1)
        self.assertEqual(orjson.loads(first.body), result)
        self.assertEqual(orjson.loads(second.body), result)

    async def test_cancelling_one_waiter_does_not_cancel_shared_search(self):
        result = {
            "kataster": {"number": "78404:409:0113"},
            "meta": {"partial": False, "unavailable_sources": []},
        }
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow_search_core(*args):
            started.set()
            await release.wait()
            return copy.deepcopy(result)

        search_core = AsyncMock(side_effect=slow_search_core)
        with patch("api.index._search_core", new=search_core):
            first_task = asyncio.create_task(api._search("78404:409:0113"))
            await asyncio.wait_for(started.wait(), timeout=1)
            second_task = asyncio.create_task(api._search("78404:409:0113"))
            await asyncio.sleep(0)
            first_task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first_task
            release.set()
            second = await second_task

        self.assertEqual(search_core.await_count, 1)
        self.assertEqual(orjson.loads(second.body), result)

    async def test_cancelling_final_waiter_cancels_underlying_search(self):
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def slow_search_core(*args):
            started.set()
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.set()

        with patch("api.index._search_core", new=AsyncMock(side_effect=slow_search_core)):
            waiter = asyncio.create_task(api._search("78404:409:0113"))
            await asyncio.wait_for(started.wait(), timeout=1)
            waiter.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await waiter
            self.assertNotIn("78404:409:0113", api._search_in_flight)
            await asyncio.wait_for(cancelled.wait(), timeout=1)

        self.assertNotIn("78404:409:0113", api._search_in_flight)

    async def test_concurrent_different_keys_do_not_share_results(self):
        async def search_core(kataster_nr, *args):
            await asyncio.sleep(0)
            return {
                "kataster": {"number": kataster_nr},
                "meta": {"partial": False, "unavailable_sources": []},
            }

        search_core_mock = AsyncMock(side_effect=search_core)
        with patch("api.index._search_core", new=search_core_mock):
            first, second = await asyncio.gather(
                api._search("78404:409:0113"),
                api._search("17501:002:0490"),
            )

        self.assertEqual(search_core_mock.await_count, 2)
        self.assertEqual(orjson.loads(first.body)["kataster"]["number"], "78404:409:0113")
        self.assertEqual(orjson.loads(second.body)["kataster"]["number"], "17501:002:0490")

    async def test_failed_in_flight_search_is_removed_for_retry(self):
        result = {
            "kataster": {"number": "78404:409:0113"},
            "meta": {"partial": False, "unavailable_sources": []},
        }
        search_core = AsyncMock(side_effect=[RuntimeError("unexpected"), copy.deepcopy(result)])

        with patch("api.index._search_core", new=search_core):
            with self.assertRaises(RuntimeError):
                await api._search("78404:409:0113")
            await asyncio.sleep(0)
            response = await api._search("78404:409:0113")

        self.assertEqual(search_core.await_count, 2)
        self.assertEqual(orjson.loads(response.body), result)

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
        self.assertFalse(result["meta"]["ai_analysis_available"])
        self.assertIsNone(result["mets"])
        climate = next(item for item in result["toetused"] if item["id"] == "kliimakindla-metsa-kujundamine")
        self.assertEqual(climate["eligibility_status"], "Vajab kontrolli")

    async def test_slow_primary_source_degrades_to_partial_data_within_budget(self):
        kataster = {
            "number": "78404:409:0113",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
            },
            "pindala_ha": 1,
        }

        cancelled = asyncio.Event()

        async def slow_eraldis(*args):
            try:
                await asyncio.sleep(1)
                return []
            finally:
                cancelled.set()

        with (
            patch("api.index.PRIMARY_SOURCE_TIMEOUT_SECONDS", 0.01),
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(side_effect=slow_eraldis)),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertTrue(result["meta"]["partial"])
        self.assertIn("metsaregister.eraldised", result["meta"]["unavailable_sources"])
        self.assertTrue(cancelled.is_set())

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
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({
                "kaitsealad": [nearby_but_not_intersecting],
                "katsealad": [],
                "sood": [],
            }, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", 0)

        self.assertEqual(result["kitsendused"], [])
        self.assertEqual(result["spatial_status"]["kaitseala"], {
            "intersects": False,
            "sources_complete": True,
        })

    async def test_empty_feature_geometry_makes_spatial_evidence_incomplete(self):
        empty_geometry = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": []},
            "properties": {},
        }
        parcel_geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }

        filtered, incomplete = api._filter_features_by_geometry_with_status(
            [empty_geometry],
            parcel_geometry,
        )

        self.assertEqual(filtered, [])
        self.assertTrue(incomplete)

    async def test_non_list_features_and_empty_parcel_are_incomplete(self):
        parcel_geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }

        self.assertEqual(
            api._filter_features_by_geometry_with_status({}, parcel_geometry),
            ([], True),
        )
        self.assertEqual(
            api._filter_features_by_geometry_with_status([], {"type": "Polygon", "coordinates": []}),
            ([], True),
        )

    async def test_self_intersecting_geometries_are_incomplete(self):
        valid_parcel = {
            "type": "Polygon",
            "coordinates": [[[0.2, 1.4], [0.6, 1.4], [0.6, 1.8], [0.2, 1.4]]],
        }
        bow_tie = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
        }
        feature = {"type": "Feature", "geometry": bow_tie, "properties": {}}

        self.assertEqual(
            api._filter_features_by_geometry_with_status([feature], valid_parcel)[1],
            True,
        )
        self.assertEqual(
            api._filter_features_by_geometry_with_status([], bow_tie),
            ([], True),
        )

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
        self.assertIsNone(result["spatial_status"]["kaitseala"]["intersects"])
        self.assertFalse(result["spatial_status"]["kaitseala"]["sources_complete"])
        self.assertIsNone(result["spatial_status"]["sood"]["intersects"])
        self.assertFalse(result["spatial_status"]["sood"]["sources_complete"])
        protection = next(item for item in result["toetused"] if item["id"] == "looduskaitse-piirangute-huvitis")
        self.assertEqual(protection["eligibility_status"], "Vajab kontrolli")

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
        self.assertIsNone(result["spatial_status"]["kaitseala"]["intersects"])
        self.assertFalse(result["spatial_status"]["kaitseala"]["sources_complete"])
        protection = next(item for item in result["toetused"] if item["id"] == "looduskaitse-piirangute-huvitis")
        self.assertEqual(protection["eligibility_status"], "Vajab kontrolli")

    def test_spatial_status_keeps_positive_evidence_when_other_sources_are_incomplete(self):
        status = api._build_spatial_status(
            {
                "kaitsealad": [{"type": "Feature"}],
                "katsealad": [],
                "sood": [],
            },
            [],
            ["layers.katsealad"],
            [],
        )

        self.assertEqual(status["kaitseala"], {
            "intersects": True,
            "sources_complete": False,
        })
        self.assertEqual(status["sood"], {
            "intersects": False,
            "sources_complete": True,
        })
        self.assertEqual(status["natura_2000"], {
            "intersects": False,
            "sources_complete": True,
        })

    def test_malformed_relevant_geometry_marks_source_incomplete(self):
        parcel = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        malformed = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": "bad"}}

        filtered, incomplete = api._filter_features_by_geometry_with_status([malformed], parcel)

        self.assertEqual(filtered, [])
        self.assertTrue(incomplete)

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
        try:
            results = await api._gather_in_batches(tasks, batch_size=5, overall_timeout=0.2,
                                                   fallback_per_task=list)
            # Kõik peaksid saama fallback[] (esimene batch ei jõua kunagi valmida 10s sleepiga)
            self.assertEqual(results, [[]] * 10)
            states = [inspect.getcoroutinestate(task) for task in tasks]
            self.assertEqual(states, [inspect.CORO_CLOSED] * len(tasks))
        finally:
            # Hoia katkine produktsioonikood testijooksus RuntimeWarning'ut tekitamast.
            for task in tasks:
                if inspect.getcoroutinestate(task) != inspect.CORO_CLOSED:
                    task.close()

    async def test_detail_task_failures_mark_both_sources_unavailable(self):
        kataster = {
            "number": "78404:409:0113",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
            },
            "pindala_ha": 1,
        }
        eraldised = [{
            "id": 1,
            "pindala_ha": 1,
            "puuliik_kood": "MA",
            "puuliik": "Mänd",
            "vanus": 60,
            "tagavara_y_ha": 200,
            "boniteedi_kood": 3,
            "eraldis_nr": 1,
        }]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=eraldised)),
            patch("api.index.query_eraldis_element", new=AsyncMock(side_effect=RuntimeError("element unavailable"))),
            patch("api.index.query_kahjustused", new=AsyncMock(side_effect=RuntimeError("kahjustused unavailable"))),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertEqual(
            result["meta"]["unavailable_sources"],
            ["metsaregister.eraldis_element", "metsaregister.kahjustused"],
        )
        self.assertTrue(result["meta"]["partial"])
        self.assertTrue(result["meta"]["ai_analysis_available"])

    async def test_detail_failure_marks_only_the_failed_source(self):
        kataster = {
            "number": "78404:409:0113",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
            },
            "pindala_ha": 1,
        }
        eraldised = [{
            "id": 1,
            "pindala_ha": 1,
            "puuliik_kood": "MA",
            "puuliik": "Mänd",
            "vanus": 60,
            "tagavara_y_ha": 200,
            "boniteedi_kood": 3,
            "eraldis_nr": 1,
        }]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=eraldised)),
            patch("api.index.query_eraldis_element", new=AsyncMock(side_effect=RuntimeError("element unavailable"))),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[{"eraldis_id": 1}])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertEqual(result["meta"]["unavailable_sources"], ["metsaregister.eraldis_element"])
        self.assertTrue(result["meta"]["ai_analysis_available"])
        self.assertEqual(len(result["kahjustused"]), 1)

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

    async def test_historical_clearcut_is_not_health_penalty_and_notice_does_not_reduce_stock(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {"number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1}
        eraldised = [{
            "id": 1,
            "pindala_ha": 1,
            "puuliik_kood": "MA",
            "puuliik": "mänd",
            "vanus": 60,
            "tagavara_y_ha": 200,
            "boniteedi_kood": 3,
            "eraldis_nr": 1,
            "invent_kp": "2020-01-01Z",
            "registreerimise_kp": "2021-01-01T10:00:00Z",
        }]
        clearcut = {"geometry": geometry, "properties": {"periood_a": 2013, "periood_o": 2015}}
        notice = {"properties": {
            "teatise_nr": "A",
            "too_kood": "LR",
            "otsus": "JAH",
            "otsus_kinnitatud_kp": "2024-02-10T10:00:00Z",
            "kehtiv_kuni": "2027-02-09Z",
            "raiutav_maht": 50,
            "eraldise_nr": 1,
            "pindala": 1,
        }}
        notice_without_volume = {"properties": {
            "teatise_nr": "B",
            "too_kood": "SR",
            "otsus": "JAH",
            "otsus_kinnitatud_kp": "2025-02-10T10:00:00Z",
            "eraldise_nr": 1,
            "pindala": 1,
            "arhiiv": True,
            "otsuse_pojendus": "Arhiivi põhjendus",
        }}
        notice_second_row = {"properties": {
            "teatise_nr": "A",
            "too_kood": "LR",
            "otsus": "JAH",
            "otsus_kinnitatud_kp": "2024-02-10T10:00:00Z",
            "kehtiv_kuni": "2027-02-09Z",
            "raiutav_maht": 20,
            "eraldise_nr": 1,
            "pindala": 0.5,
        }}
        unmatched_notice = {"properties": {
            "teatise_nr": "C",
            "too_kood": "LR",
            "otsus": "JAH",
            "otsus_kinnitatud_kp": "2025-03-10T10:00:00Z",
            "raiutav_maht": 30,
            "eraldise_nr": 2026,
            "pindala": 0.4,
        }}

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=eraldised)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({"lageraiealad": [clearcut]}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[notice, notice_second_row, notice_without_volume, unmatched_notice])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertEqual(result["riskid"]["terviseindeks"], 98)
        self.assertEqual(result["riskid"]["terviseskoor"], 100)
        self.assertEqual(result["riskid"]["terviseskoor_selgitus"]["components"], [])
        self.assertEqual(result["riskid"]["terviseskoor_selgitus"]["confidence"]["level"], "keskmine")
        self.assertEqual(result["vaartus"]["reliability"]["level"], "madal")
        self.assertTrue(any("teatist" in reason for reason in result["vaartus"]["reliability"]["reasons"]))
        self.assertEqual(result["riskid"]["ajaloolised_lageraiealad"][0]["periood_lopp"], 2015)
        self.assertEqual(result["vaartus"]["tagavara_m3"], 200)
        notices = {notice["number"]: notice for notice in result["teatised"]}
        self.assertTrue(notices["A"]["parast_inventuuri"])
        self.assertIsNone(notices["C"]["parast_inventuuri"])
        self.assertEqual(notices["B"]["otsuse_pohjendus"], "Arhiivi põhjendus")
        self.assertEqual(result["mets"]["inventuur"]["inventuurijargsed_teatised"], 2)
        self.assertEqual(result["mets"]["inventuur"]["inventuurijargsed_teatise_read"], 3)
        self.assertEqual(result["mets"]["inventuur"]["inventuurijargne_kavandatud_maht_m3"], 70)
        self.assertEqual(result["mets"]["inventuur"]["inventuurijargse_teatise_maht_puudub"], 1)
        self.assertEqual(result["mets"]["inventuur"]["inventuuri_seos_teadmata_teatised"], 1)
        self.assertEqual(result["teatised_meta"]["teatisi_kokku"], 3)
        self.assertEqual(result["teatised_meta"]["ridu_kokku"], 4)

    async def test_partial_notice_layers_preserve_rows_and_mark_search_partial(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {"number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1}
        notices = [{"properties": {"teatise_nr": "A", "too_kood": "LR"}}]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=(notices, ["metsaregister.teatis_arhiiv"]))),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertEqual(len(result["teatised"]), 1)
        self.assertTrue(result["meta"]["partial"])
        self.assertIn("metsaregister.teatis_arhiiv", result["meta"]["unavailable_sources"])


if __name__ == "__main__":
    unittest.main()

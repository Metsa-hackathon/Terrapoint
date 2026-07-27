import asyncio
import copy
import inspect
import unittest
from unittest.mock import AsyncMock, patch

import orjson
from shapely.geometry import Point, shape

from api import index as api


class SearchReliabilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        api.search_cache.clear()
        api._search_in_flight.clear()
        api._search_waiters.clear()

    def test_compartment_display_sort_uses_official_number_not_internal_id(self):
        stands = [
            {"id": 11108251, "eraldis_nr": 16},
            {"id": 9543691, "eraldis_nr": 1},
            {"id": 9397257, "eraldis_nr": 5},
            {"id": 12345678, "eraldis_nr": None},
        ]

        ordered = sorted(stands, key=lambda stand: api._eraldis_sort_key(stand["eraldis_nr"]))

        self.assertEqual([stand["eraldis_nr"] for stand in ordered], [1, 5, 16, None])
        self.assertEqual([stand["id"] for stand in ordered], [9543691, 9397257, 11108251, 12345678])

    def test_official_compartment_number_normalization_accepts_only_javascript_safe_integers(self):
        javascript_safe_max = 9_007_199_254_740_991
        accepted = [
            (0, 0),
            (16, 16),
            (16.0, 16),
            ("16", 16),
            (" 16.0 ", 16),
            ("1e2", 100),
            (javascript_safe_max, javascript_safe_max),
            (float(javascript_safe_max), javascript_safe_max),
            (str(javascript_safe_max), javascript_safe_max),
        ]
        for value, expected in accepted:
            with self.subTest(value=value):
                self.assertEqual(api._normalize_eraldis_nr(value), expected)

        rejected = [
            None,
            True,
            False,
            "",
            "   ",
            "not-a-number",
            -1,
            -1.0,
            "-1",
            16.5,
            "16.5",
            float("inf"),
            float("-inf"),
            float("nan"),
            "inf",
            "NaN",
            javascript_safe_max + 1,
            float(javascript_safe_max + 1),
            str(javascript_safe_max + 1),
            "1e20",
            [16],
            {"number": 16},
        ]
        for value in rejected:
            with self.subTest(value=value):
                self.assertIsNone(api._normalize_eraldis_nr(value))

    def test_geometry_label_point_is_covered_by_concave_polygon(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [20, 58], [24, 58], [24, 59], [21, 59],
                [21, 62], [20, 62], [20, 58],
            ]],
        }

        label_point = api._geometry_label_point(geometry)

        self.assertIsNotNone(label_point)
        self.assertTrue(shape(geometry).covers(Point(*label_point)))
        self.assertFalse(shape(geometry).covers(Point(22, 60)))

    def test_geometry_label_point_is_covered_by_multipolygon(self):
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[20, 58], [21, 58], [21, 59], [20, 59], [20, 58]]],
                [[[30, 60], [34, 60], [34, 64], [30, 64], [30, 60]]],
            ],
        }

        label_point = api._geometry_label_point(geometry)

        self.assertIsNotNone(label_point)
        self.assertTrue(shape(geometry).covers(Point(*label_point)))
        self.assertFalse(shape(geometry).covers(Point(27, 61)))

    def test_geometry_label_point_rejects_invalid_or_empty_geometry(self):
        invalid_geometries = [
            None,
            {},
            {"type": "Polygon", "coordinates": []},
            {"type": "Polygon", "coordinates": "invalid"},
            {
                "type": "Polygon",
                "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
            },
        ]

        for geometry in invalid_geometries:
            with self.subTest(geometry=geometry):
                self.assertIsNone(api._geometry_label_point(geometry))

    async def test_search_sorts_official_numbers_without_mispairing_calculated_prices(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {
            "number": "78404:409:0113",
            "geometry": geometry,
            "pindala_ha": 6,
        }
        stands = [
            {
                "id": 11108251,
                "eraldis_nr": 16,
                "geometry": geometry,
                "pindala_ha": 1,
                "puuliik_kood": "MA",
                "puuliik": "mänd",
                "vanus": 60,
                "tagavara_y_ha": 10,
                "boniteedi_kood": 2,
            },
            {
                "id": 9543691,
                "eraldis_nr": 1,
                "geometry": geometry,
                "pindala_ha": 2,
                "puuliik_kood": "LV",
                "puuliik": "hall lepp",
                "vanus": 40,
                "tagavara_y_ha": 100,
                "boniteedi_kood": 3,
            },
            {
                "id": 9397257,
                "eraldis_nr": 5,
                "geometry": geometry,
                "pindala_ha": 3,
                "puuliik_kood": "KU",
                "puuliik": "kuusk",
                "vanus": 80,
                "tagavara_y_ha": 50,
                "boniteedi_kood": 1,
            },
        ]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        summaries = result["mets"]["eraldised"]
        map_features = result["map_layers"]["eraldised"]["features"]
        self.assertEqual([stand["eraldis_nr"] for stand in summaries], [1, 5, 16])
        self.assertEqual([stand["hinnang_seisuhind"] for stand in summaries], [17.1, 47.6, 45.85])
        self.assertEqual([feature["properties"]["eraldis_nr"] for feature in map_features], [1, 5, 16])
        summaries_by_number = {stand["eraldis_nr"]: stand for stand in summaries}
        for feature in map_features:
            properties = feature["properties"]
            summary = summaries_by_number[properties["eraldis_nr"]]
            label_point = feature["properties"]["label_point"]
            self.assertTrue(shape(feature["geometry"]).covers(Point(*label_point)))
            expected_legacy_color = {
                "unknown": "#6b7280",
                "green": "#28a745",
                "yellow": "#ffc107",
                "red": "#e63946",
            }[feature["properties"]["raie_status"]]
            self.assertEqual(feature["properties"]["color"], expected_legacy_color)
            self.assertEqual(feature["properties"]["age_class_provenance"], "Terrapointi tuletis")
            self.assertIn("age_class_color", feature["properties"])
            self.assertEqual(properties["vaartus_min_eur"], summary["vaartus_min_eur"])
            self.assertEqual(properties["vaartus_hinnang_eur"], summary["vaartus_hinnang_eur"])
            self.assertEqual(properties["vaartus_max_eur"], summary["vaartus_max_eur"])
        for stand in summaries:
            self.assertIn("age_class", stand)
            self.assertIn("age_class_label", stand)
            self.assertIn("age_class_color", stand)
            self.assertEqual(stand["age_class_provenance"], "Terrapointi tuletis")
        expected_weighted_price = round((45.85 * 10 + 17.1 * 200 + 47.6 * 150) / 360, 2)
        self.assertEqual(result["vaartus"]["base_price_per_m3"], expected_weighted_price)

    async def test_missing_species_does_not_inherit_pine_assortment_prices(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {"number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1}
        stands = [{
            "id": 1, "eraldis_nr": 1, "geometry": geometry, "pindala_ha": 1,
            "puuliik_kood": "MA", "puuliik_kood_raw": None, "puuliik": "mänd", "vanus": 40,
            "tagavara_y_ha": 100, "tagavara_provenance": "official", "boniteedi_kood": 2,
        }]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        value = result["vaartus"]
        self.assertEqual(value["range_low_eur"], 1060)
        self.assertEqual(value["range_high_eur"], 1560)
        self.assertEqual(value["base_price_per_m3"], 13.1)
        self.assertIsNone(value["log_price"])
        self.assertIsNone(value["pulp_price"])

    async def test_zero_stock_has_no_per_cubic_metre_scenario(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {"number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1}
        stands = [{
            "id": 1, "eraldis_nr": 1, "geometry": geometry, "pindala_ha": 1,
            "puuliik_kood": "MA", "puuliik": "mänd", "vanus": 5,
            "tagavara_y_ha": 0, "tagavara_provenance": "official", "boniteedi_kood": 2,
        }]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        value = result["vaartus"]
        self.assertEqual(value["tagavara_m3"], 0)
        self.assertIsNone(value["price_per_m3"])
        self.assertIsNone(value["base_price_per_m3"])
        self.assertIsNone(value["log_price"])
        self.assertIsNone(value["pulp_price"])

    async def test_unavailable_stock_area_suppresses_partial_financial_passports(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {
            "number": "78404:409:0113",
            "geometry": geometry,
            "pindala_ha": 10,
            "maks_hind": 4_200,
        }
        stands = [
            {
                "id": 1,
                "eraldis_nr": 1,
                "geometry": geometry,
                "pindala_ha": 1,
                "puuliik_kood": "MA",
                "puuliik": "mänd",
                "vanus": 60,
                "tagavara_y_ha": 100,
                "tagavara_provenance": "official",
                "boniteedi_kood": 2,
                "invent_kp": "2025-01-01",
                "registreerimise_kp": "2025-01-01",
            },
            {
                "id": 2,
                "eraldis_nr": 2,
                "geometry": geometry,
                "pindala_ha": 9,
                "puuliik_kood": "KU",
                "puuliik": "kuusk",
                "vanus": 0,
                "tagavara_y_ha": None,
                "tagavara_provenance": "unavailable",
                "boniteedi_kood": 2,
                "invent_kp": "2025-01-01",
                "registreerimise_kp": "2025-01-01",
            },
        ]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertEqual(result["vaartus"]["reliability"]["level"], "madal")
        self.assertTrue(any("puudub" in reason.lower() for reason in result["vaartus"]["reliability"]["reasons"]))
        unavailable_stand = next(stand for stand in result["mets"]["eraldised"] if stand["eraldis_nr"] == 2)
        self.assertIsNone(unavailable_stand["tagavara_y_ha"])
        self.assertIsNone(unavailable_stand["vaartus_hinnang_eur"])
        self.assertIsNone(result["mets"]["tagavara_y_ha"])
        self.assertFalse(result["mets"]["peapuuliigi_andmed_taielikud"])
        self.assertIsNone(result["vaartus"]["tagavara_m3"])
        self.assertIsNone(result["vaartus"]["base_value_eur"])
        self.assertIsNone(result["sinik"]["co2_tons_total"])
        map_stand = next(
            feature["properties"]
            for feature in result["map_layers"]["eraldised"]["features"]
            if feature["properties"]["eraldis_nr"] == 2
        )
        self.assertIsNone(map_stand["tagavara_y_ha"])
        self.assertEqual(map_stand["tagavara_provenance"], "unavailable")
        passports = {passport["id"]: passport for passport in result["vaartus"]["andmepassid"]}
        self.assertFalse(passports["forest_volume"]["available"])
        self.assertFalse(passports["timber_value"]["available"])
        self.assertTrue(passports["land_reference"]["available"])
        self.assertFalse(passports["property_estimate"]["available"])

    async def test_search_normalizes_invalid_official_numbers_and_serializes_without_internal_ids(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {
            "number": "78404:409:0113",
            "geometry": geometry,
            "pindala_ha": 1,
        }
        stands = [
            {
                "id": 11108251,
                "eraldis_nr": [16],
                "geometry": geometry,
                "pindala_ha": 1,
                "puuliik_kood": "MA",
                "puuliik": "mänd",
                "vanus": 60,
                "tagavara_y_ha": 100,
                "boniteedi_kood": 2,
            },
            {
                "id": 9543691,
                "eraldis_nr": "1e20",
                "geometry": geometry,
                "pindala_ha": 1,
                "puuliik_kood": "LV",
                "puuliik": "hall lepp",
                "vanus": 40,
                "tagavara_y_ha": 50,
                "boniteedi_kood": 3,
            },
        ]
        element_query = AsyncMock(return_value=[])

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=element_query),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        response = api.json_response(result)
        serialized = orjson.loads(response.body)
        self.assertEqual([stand["eraldis_nr"] for stand in serialized["mets"]["eraldised"]], [None, None])
        self.assertEqual(
            [feature["properties"]["eraldis_nr"] for feature in serialized["map_layers"]["eraldised"]["features"]],
            [None, None],
        )
        self.assertNotIn(b"11108251", response.body)
        self.assertNotIn(b"9543691", response.body)
        self.assertEqual(
            [awaited.args[0] for awaited in element_query.await_args_list],
            [11108251, 9543691],
        )

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

    async def test_search_without_map_layers_queries_only_analytical_sources(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {
            "number": "78404:409:0113",
            "geometry": geometry,
            "pindala_ha": 1,
        }
        stands = [{
            "id": 1,
            "eraldis_nr": 1,
            "geometry": geometry,
            "pindala_ha": 1,
            "puuliik_kood": "MA",
            "puuliik": "mänd",
            "vanus": 60,
            "tagavara_y_ha": 100,
            "boniteedi_kood": 3,
        }]
        all_layers = AsyncMock(return_value=({}, [], []))
        selected_layers = AsyncMock(return_value=({}, [], []))
        expected_keys = (
            "kaitsealad", "yrask_eelis", "yrask_mke", "piirang", "karuputk",
            "sood", "lageraiealad", "malestised", "piirangukeelualad",
            "kaitsevoondid", "uleujutus", "veekaitse", "ranna_piirang",
            "vaetiste_keeld", "kma_kitsendused", "katsealad",
        )

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=all_layers),
            patch("api.index.query_layers", new=selected_layers),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core(
                "78404:409:0113", api.time.time(), include_map_layers=False
            )

        all_layers.assert_not_awaited()
        selected_layers.assert_awaited_once()
        self.assertEqual(selected_layers.await_args.args[1], expected_keys)
        self.assertEqual(set(result["map_layers"]), {"eraldised"})
        self.assertIsNotNone(result["mets"])
        self.assertIn("toetused", result)
        self.assertIn("teatised", result)

    async def test_search_without_map_layers_preserves_every_non_map_field(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {
            "number": "78404:409:0113",
            "geometry": geometry,
            "pindala_ha": 1,
            "maks_hind": 4_200,
        }
        stands = [{
            "id": 1,
            "eraldis_nr": 1,
            "geometry": geometry,
            "pindala_ha": 1,
            "puuliik_kood": "KU",
            "puuliik": "kuusk",
            "vanus": 60,
            "vanus_raw": 60,
            "tagavara_y_ha": 100,
            "boniteedi_kood": 3,
        }]
        feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": {"nimi": "Analüütiline vaste", "periood_a": 2011, "periood_o": 2015},
        }
        all_layer_data = {
            key: ([copy.deepcopy(feature)] if key in {
                "kaitsealad", "yrask_eelis", "yrask_mke", "piirang", "karuputk",
                "sood", "lageraiealad", "malestised", "piirangukeelualad",
                "kaitsevoondid", "uleujutus", "veekaitse", "ranna_piirang",
                "vaetiste_keeld", "kma_kitsendused", "katsealad",
            } else [])
            for key, _workspace, _typename in api.LAYER_CONFIGS
        }

        async def run(include_map_layers):
            with (
                patch("api.index.time.time", return_value=100.0),
                patch("api.index.query_kataster", new=AsyncMock(return_value=copy.deepcopy(kataster))),
                patch("api.index.query_eraldis", new=AsyncMock(return_value=copy.deepcopy(stands))),
                patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
                patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
                patch("api.index.query_all_layers", new=AsyncMock(return_value=(copy.deepcopy(all_layer_data), [], []))),
                patch(
                    "api.index.query_layers",
                    new=AsyncMock(side_effect=lambda _bbox, keys: (
                        {key: copy.deepcopy(all_layer_data[key]) for key in keys}, [], []
                    )),
                ),
                patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
                patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
            ):
                return await api._search_core(
                    "78404:409:0113", 100.0, include_map_layers=include_map_layers
                )

        with_layers = await run(True)
        without_layers = await run(False)
        with_map = with_layers.pop("map_layers")
        without_map = without_layers.pop("map_layers")

        self.assertEqual(without_layers, with_layers)
        self.assertEqual(set(without_map), {"eraldised"})
        self.assertGreater(len(with_map), len(without_map))

    async def test_search_defaults_to_legacy_eager_layer_query(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        all_layers = AsyncMock(return_value=({}, [], []))
        parcel_query = AsyncMock(return_value={
            "number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1,
        })
        with (
            patch("api.index.query_kataster", new=parcel_query),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=all_layers),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            await api._search_core("78404:409:0113", api.time.time())

        all_layers.assert_awaited_once()
        parcel_query.assert_awaited_once_with(
            "78404:409:0113",
            include_valuation_metadata=True,
        )

    async def test_search_marks_truncated_clearcut_archive_as_partial(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        cut = {
            "type": "Feature",
            "geometry": geometry,
            "properties": {"periood_a": 2013, "periood_o": 2015},
        }
        for features, expected_state in (([cut], "matches_partial"), ([], "incomplete")):
            with self.subTest(expected_state=expected_state):
                with (
                    patch("api.index.query_kataster", new=AsyncMock(return_value={
                        "number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1,
                    })),
                    patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
                    patch(
                        "api.index.query_all_layers",
                        new=AsyncMock(return_value=({"lageraiealad": features}, [], ["lageraiealad"])),
                    ),
                    patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
                    patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
                ):
                    result = await api._search_core("78404:409:0113", api.time.time())

                status = result["riskid"]["ajaloolise_lageraide_kontroll"]
                self.assertEqual(status["state"], expected_state)

    async def test_missing_source_age_and_species_keep_legacy_display_but_unknown_class(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        stands = [{
            "id": 1,
            "eraldis_nr": 1,
            "geometry": geometry,
            "pindala_ha": 1,
            "puuliik_kood": "MA",
            "puuliik_kood_raw": None,
            "puuliik": "mänd",
            "vanus": 0,
            "vanus_raw": None,
            "tagavara_y_ha": 0,
            "boniteedi_kood": 3,
        }]
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value={
                "number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1,
            })),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        summary = result["mets"]["eraldised"][0]
        feature = result["map_layers"]["eraldised"]["features"][0]["properties"]
        self.assertEqual(summary["vanus"], 0)
        self.assertEqual(summary["puuliik_kood"], "MA")
        self.assertFalse(result["mets"]["vanuseandmed_taielikud"])
        self.assertFalse(result["mets"]["liigiandmed_taielikud"])
        self.assertEqual(summary["age_class_label"], "Määramata")
        self.assertEqual(feature["age_class_label"], "Määramata")
        self.assertEqual(result["raie"]["status"], "unknown")
        self.assertIsNone(result["raie"]["raievanus"])
        climate = next(
            item for item in result["toetused"]
            if item["id"] == "kliimakindla-metsa-kujundamine"
        )
        self.assertEqual(climate["eligibility_status"], "Vajab kontrolli")
        self.assertTrue(climate["andmed_piiratud"])

    async def test_invalid_stand_geometry_is_omitted_and_marked_partial(self):
        parcel_geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        stands = [{
            "id": 1,
            "eraldis_nr": 1,
            "geometry": {"type": "Point", "coordinates": [24.05, 59.05]},
            "pindala_ha": 1,
            "puuliik_kood": "MA",
            "puuliik_kood_raw": "MA",
            "puuliik": "mänd",
            "vanus": 40,
            "vanus_raw": 40,
            "tagavara_y_ha": 100,
            "tagavara_provenance": "official",
            "boniteedi_kood": 2,
        }]
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value={
                "number": "78404:409:0113",
                "geometry": parcel_geometry,
                "pindala_ha": 1,
            })),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertEqual(len(result["mets"]["eraldised"]), 1)
        self.assertNotIn("eraldised", result["map_layers"])
        self.assertIn(
            "metsaregister.eraldis_geomeetria",
            result["meta"]["unavailable_sources"],
        )
        self.assertTrue(result["meta"]["partial"])
        self.assertTrue(result["meta"]["ai_analysis_available"])

    async def test_search_stand_overlay_keeps_legacy_teal_below_half_cutting_age(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        stands = [{
            "id": 1,
            "eraldis_nr": 1,
            "geometry": geometry,
            "pindala_ha": 1,
            "puuliik_kood": "MA",
            "puuliik": "mänd",
            "vanus": 20,
            "vanus_raw": 20,
            "tagavara_y_ha": 10,
            "boniteedi_kood": 3,
        }]
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value={
                "number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1,
            })),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        properties = result["map_layers"]["eraldised"]["features"][0]["properties"]
        self.assertLess(properties["raie_ratio"], 0.5)
        self.assertEqual(properties["color"], "#17a2b8")
        self.assertEqual(properties["age_class_color"], "#7aa6c2")

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
            "sources_complete": True,
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

    def test_malformed_notice_fields_are_unknown_instead_of_zero_or_executable_text(self):
        normalized, complete = api._normalized_notice_properties({
            "teatise_nr": {"unexpected": True},
            "too_kood": ["LR"],
            "otsus": "JAH\x00INJECT",
            "pindala": "not-a-number",
            "raiutav_maht": -5,
            "eraldise_nr": "not-a-stand",
            "arhiiv": "false",
        })

        self.assertFalse(complete)
        self.assertEqual(normalized["teatise_nr"], "")
        self.assertEqual(normalized["too_kood"], "")
        self.assertEqual(normalized["otsus"], "JAH INJECT")
        self.assertIsNone(normalized["pindala"])
        self.assertIsNone(normalized["raiutav_maht"])
        self.assertIsNone(normalized["eraldise_nr"])
        self.assertFalse(normalized["arhiiv"])

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

    async def test_detail_failure_does_not_turn_missing_species_into_pine_composition(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        stands = [{
            "id": 1,
            "pindala_ha": 1,
            "puuliik_kood": "MA",
            "puuliik_kood_raw": None,
            "puuliik": "mänd",
            "vanus": 40,
            "vanus_raw": 40,
            "tagavara_y_ha": 100,
            "tagavara_provenance": "official",
            "boniteedi_kood": 3,
            "eraldis_nr": 1,
        }]
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value={
                "number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1,
            })),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(side_effect=RuntimeError("unavailable"))),
            patch("api.index.query_kahjustused", new=AsyncMock(side_effect=RuntimeError("unavailable"))),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        stand = result["mets"]["eraldised"][0]
        self.assertFalse(result["mets"]["liigiandmed_taielikud"])
        self.assertEqual(result["mets"]["liikide_koosseis"], [])
        self.assertFalse(stand["koosseisu_detail_kasutatud"])
        self.assertEqual(stand["hinna_allika_kvaliteet"], "fallback")

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
        kataster = {
            "number": "78404:409:0113",
            "geometry": geometry,
            "pindala_ha": 1,
            "maks_hind": 4_200,
        }
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
        recovered_notice = {"properties": {
            "teatise_nr": "C",
            "too_kood": "LR",
            "otsus": "JAH",
            "otsus_kinnitatud_kp": "2025-03-10T10:00:00Z",
            "raiutav_maht": 30,
            "eraldise_nr": 2026,
            "pindala": 1,
        }}
        unmatched_notice = {"properties": {
            "teatise_nr": "D",
            "too_kood": "LR",
            "otsus": "JAH",
            "otsus_kinnitatud_kp": "2025-04-10T10:00:00Z",
            "raiutav_maht": 40,
            "eraldise_nr": 2028,
            "pindala": 0.4,
        }}
        malformed_date_notice = {"properties": {
            "teatise_nr": "E",
            "too_kood": "LR",
            "otsus": "JAH",
            "otsus_kinnitatud_kp": "vigane-kuupäev",
            "raiutav_maht": 10,
            "eraldise_nr": 1,
            "pindala": 1,
        }}

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=eraldised)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({
                "lageraiealad": [clearcut],
                "yrask_eelis": [],
                "yrask_mke": [],
                "karuputk": [],
            }, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[notice, notice_second_row, notice_without_volume, recovered_notice, unmatched_notice, malformed_date_notice])),
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
        self.assertEqual(
            [passport["id"] for passport in result["vaartus"]["andmepassid"]],
            ["forest_volume", "timber_value", "land_reference", "property_estimate"],
        )
        volume_passport = result["vaartus"]["andmepassid"][0]
        self.assertEqual(volume_passport["value"], 200)
        self.assertEqual(volume_passport["source"]["name"], "Metsaregister")
        self.assertIn("m³/ha × pindala", volume_passport["derivation"])
        passports = {passport["id"]: passport for passport in result["vaartus"]["andmepassid"]}
        self.assertEqual(
            passports["timber_value"]["range"],
            {
                "low": result["vaartus"]["range_low_eur"],
                "base": result["vaartus"]["base_value_eur"],
                "high": result["vaartus"]["range_high_eur"],
            },
        )
        self.assertEqual(passports["land_reference"]["value"], 4_200)
        self.assertTrue(passports["land_reference"]["available"])
        self.assertEqual(passports["property_estimate"]["range"]["base"], result["vaartus"]["property_estimate"]["base_eur"])
        notices = {notice["number"]: notice for notice in result["teatised"]}
        self.assertTrue(notices["A"]["parast_inventuuri"])
        self.assertIsNone(notices["C"]["parast_inventuuri"])
        self.assertIsNone(notices["D"]["parast_inventuuri"])
        self.assertIsNone(notices["E"]["parast_inventuuri"])
        self.assertEqual(notices["E"]["inventuuri_seose_pohjus"], "otsuse_kuupaev_vigane")
        self.assertEqual(notices["A"]["eraldis_nr"], 1)
        self.assertEqual(notices["A"]["eraldis"], 1)
        self.assertEqual(notices["A"]["teatise_eraldis_nr"], 1)
        self.assertEqual(notices["C"]["eraldis_nr"], 1)
        self.assertEqual(notices["C"]["eraldis"], 1)
        self.assertEqual(notices["C"]["teatise_eraldis_nr"], 2026)
        self.assertIsNone(notices["D"]["eraldis_nr"])
        self.assertIsNone(notices["D"]["eraldis"])
        self.assertEqual(notices["D"]["teatise_eraldis_nr"], 2028)
        self.assertEqual(notices["B"]["otsuse_pohjendus"], "Arhiivi põhjendus")
        self.assertEqual(result["mets"]["inventuur"]["inventuurijargsed_teatised"], 2)
        self.assertEqual(result["mets"]["inventuur"]["inventuurijargsed_teatise_read"], 3)
        self.assertEqual(result["mets"]["inventuur"]["inventuurijargne_kavandatud_maht_m3"], 70)
        self.assertEqual(result["mets"]["inventuur"]["inventuurijargse_teatise_maht_puudub"], 1)
        self.assertEqual(result["mets"]["inventuur"]["inventuuri_seos_teadmata_teatised"], 3)
        self.assertEqual(result["teatised_meta"]["teatisi_kokku"], 5)
        self.assertEqual(result["teatised_meta"]["ridu_kokku"], 6)

    async def test_search_deduplicates_kpois_umbrella_records_already_in_specialized_sources(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        duplicate = {
            "type": "Feature",
            "id": "restriction.1",
            "geometry": geometry,
            "properties": {"id": 42, "kood": "VEE", "nimi": "Veekaitse"},
        }
        layers = {
            "veekaitse": [duplicate],
            "kma_kitsendused": [duplicate],
            "kaitsealad": [],
            "sood": [],
        }
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value={
                "number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1,
            })),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=(layers, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertEqual([item["tyyp"] for item in result["kitsendused"]], ["veekaitse"])

    async def test_beetle_observation_without_spruce_does_not_penalize_legacy_or_current_score(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        stands = [{
            "id": 1,
            "eraldis_nr": 1,
            "geometry": geometry,
            "pindala_ha": 1,
            "puuliik_kood": "MA",
            "puuliik_kood_raw": "MA",
            "puuliik": "mänd",
            "vanus": 60,
            "vanus_raw": 60,
            "tagavara_y_ha": 100,
            "tagavara_provenance": "official",
            "boniteedi_kood": 3,
            "invent_kp": "2026-01-01",
            "registreerimise_kp": "2026-01-01",
        }]
        observation = {"type": "Feature", "geometry": geometry, "properties": {}}
        layers = {
            "yrask_eelis": [observation],
            "yrask_mke": [],
            "karuputk": [],
            "kaitsealad": [],
            "sood": [],
        }
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value={
                "number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1,
            })),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=(layers, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertEqual(result["riskid"]["yrask"]["score"], 0)
        self.assertEqual(result["riskid"]["yrask_hinnang"]["score"], 0)
        self.assertEqual(result["riskid"]["terviseindeks"], 98)
        self.assertEqual(result["riskid"]["terviseskoor"], 100)

    async def test_beetle_assessment_marks_unavailable_layers_as_partial(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        stands = [{
            "id": 1,
            "eraldis_nr": 1,
            "geometry": geometry,
            "pindala_ha": 1,
            "puuliik_kood": "KU",
            "puuliik_kood_raw": "KU",
            "puuliik": "kuusk",
            "vanus": 60,
            "vanus_raw": 60,
            "tagavara_y_ha": 100,
            "tagavara_provenance": "official",
            "boniteedi_kood": 3,
            "invent_kp": "2026-01-01",
            "registreerimise_kp": "2026-01-01",
        }]
        layers = {
            "yrask_eelis": [], "yrask_mke": [], "karuputk": [],
            "kaitsealad": [], "sood": [],
        }
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value={
                "number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1,
            })),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=(
                layers, ["yrask_eelis"], []
            ))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        assessment = result["riskid"]["yrask_hinnang"]
        self.assertFalse(assessment["sources_complete"])
        self.assertFalse(assessment["layer_sources_complete"])
        self.assertIn("kihikontroll osaline", assessment["label"])

    async def test_unavailable_invasive_species_source_is_unknown_not_absent(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        layers = {"karuputk": [], "kaitsealad": [], "sood": []}
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value={
                "number": "78404:409:0113", "geometry": geometry, "pindala_ha": 1,
            })),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=(layers, ["karuputk"], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=[])),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        self.assertIsNone(result["riskid"]["karuputk"])
        self.assertEqual(result["riskid"]["karuputk_kontroll"], {
            "intersects": None,
            "sources_complete": False,
        })

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
        self.assertFalse(result["teatised_meta"]["sources_complete"])
        self.assertEqual(
            result["teatised_meta"]["unavailable_sources"],
            ["metsaregister.teatis_arhiiv"],
        )

    async def test_notice_event_status_and_location_scope_are_neutral_and_additive(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
        }
        kataster = {"number": "78404:409:0113", "geometry": geometry, "pindala_ha": 2}
        stands = [{
            "id": 1,
            "eraldis_nr": 7,
            "geometry": geometry,
            "pindala_ha": 2,
            "puuliik_kood": "MA",
            "puuliik": "Mänd",
            "vanus": 60,
            "tagavara_y_ha": 100,
            "boniteedi_kood": 3,
        }]

        def notice(number, decision, expiry=None, archived=False, stand=7, area=2, event_date="2026-01-02Z"):
            return {"properties": {
                "teatise_nr": number,
                "otsus": decision,
                "kehtiv_kuni": expiry,
                "arhiiv": archived,
                "eraldise_nr": stand,
                "pindala": area,
                "otsus_kinnitatud_kp": event_date,
            }}

        notices = [
            notice("CURRENT", "JAH", "2099-01-01Z"),
            notice("ARCHIVED", "JAH", "2099-01-01Z", archived=True),
            notice("DENIED", "EI", "2099-01-01Z"),
            notice("EXPIRED", "JAH", "2020-01-01Z"),
            notice("NO_EXPIRY", "JAH"),
            notice("UNKNOWN", "", "2099-01-01Z"),
            notice("MALFORMED", 7, "2099-01-01Z"),
            notice("REGISTERED", "REGISTREERITUD", "2099-01-01Z"),
            notice("AREA_INFERRED", "JAH", "2099-01-01Z", stand=2026),
            notice("UNMATCHED", "JAH", "2099-01-01Z", stand=2027, area=0.5),
        ]

        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=kataster)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_eraldis_element", new=AsyncMock(return_value=[])),
            patch("api.index.query_kahjustused", new=AsyncMock(return_value=[])),
            patch("api.index.query_all_layers", new=AsyncMock(return_value=({}, [], []))),
            patch("api.index.query_teatised", new=AsyncMock(return_value=notices)),
            patch("api.index.query_natura_2000", new=AsyncMock(return_value=[])),
        ):
            result = await api._search_core("78404:409:0113", api.time.time())

        by_number = {item["number"]: item for item in result["teatised"]}
        self.assertTrue(by_number["CURRENT"]["active"])
        self.assertEqual(by_number["CURRENT"]["event_status"], "permitted_current")
        self.assertEqual(by_number["CURRENT"]["event_status_label"], "Kehtiv lubatud töö")
        self.assertEqual(by_number["CURRENT"]["event_date"], "2026-01-02")
        self.assertEqual(by_number["CURRENT"]["location_scope"], "stand")

        self.assertFalse(by_number["ARCHIVED"]["active"])
        self.assertEqual(by_number["ARCHIVED"]["event_status"], "archived")
        self.assertFalse(by_number["DENIED"]["active"])
        self.assertEqual(by_number["DENIED"]["event_status"], "not_permitted")
        self.assertEqual(by_number["DENIED"]["event_status_label"], "Otsus ei luba tööd")
        self.assertFalse(by_number["EXPIRED"]["active"])
        self.assertEqual(by_number["EXPIRED"]["event_status"], "not_current")
        self.assertEqual(by_number["NO_EXPIRY"]["event_status"], "not_current")
        self.assertEqual(by_number["UNKNOWN"]["event_status"], "unknown")
        self.assertFalse(by_number["UNKNOWN"]["active"])
        self.assertFalse(by_number["MALFORMED"]["active"])
        self.assertEqual(by_number["MALFORMED"]["event_status"], "unknown")
        self.assertEqual(by_number["MALFORMED"]["event_status_label"], "Staatus määramata")
        self.assertEqual(by_number["REGISTERED"]["event_status"], "registered")
        self.assertFalse(by_number["REGISTERED"]["active"])
        self.assertNotEqual(by_number["REGISTERED"]["event_status"], "not_permitted")
        self.assertEqual(by_number["AREA_INFERRED"]["eraldise_seose_meetod"], "pindala")
        self.assertEqual(by_number["AREA_INFERRED"]["location_scope"], "parcel_unlocated")
        self.assertEqual(by_number["UNMATCHED"]["location_scope"], "parcel_unlocated")
        self.assertEqual(result["teatised"][0]["number"], "CURRENT")


if __name__ == "__main__":
    unittest.main()

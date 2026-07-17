import os
import unittest
from unittest.mock import AsyncMock, patch

import orjson
from fastapi.testclient import TestClient

from api import index as api


KATASTER_NR = "78404:409:0113"
PARCEL_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[[24.0, 59.0], [24.1, 59.0], [24.1, 59.1], [24.0, 59.0]]],
}
SQUARE_PARCEL_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
}
MATCHING_FEATURE = {
    "type": "Feature",
    "geometry": PARCEL_GEOMETRY,
    "properties": {"nimi": "Ametlik vaste"},
}


def parcel():
    return {
        "number": KATASTER_NR,
        "geometry": PARCEL_GEOMETRY,
        "pindala_ha": 1,
        "l_aadress": "Testi kinnistu",
    }


class MapContextCoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_queries_only_sources_required_by_requested_theme(self):
        selected_query = AsyncMock(return_value=({"natura_elupaik": []}, [], []))
        parcel_query = AsyncMock(return_value=parcel())
        with (
            patch("api.index.query_kataster", new=parcel_query),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_layers", new=selected_query),
        ):
            result = await api._map_context_core(KATASTER_NR, ["species_habitats"])

        selected_query.assert_awaited_once()
        parcel_query.assert_awaited_once_with(KATASTER_NR)
        self.assertEqual(selected_query.await_args.args[1], ["natura_elupaik"])
        self.assertEqual(result["requested_themes"], ["species_habitats"])
        self.assertEqual(set(result["themes"]), {"species_habitats"})
        self.assertEqual(result["themes"]["species_habitats"]["state"], "empty")

    async def test_heritage_matches_are_invariant_when_kpois_themes_are_requested(self):
        specialized = {
            "type": "Feature",
            "geometry": PARCEL_GEOMETRY,
            "properties": {"id": 42, "kood": "RANNA_PIIRANG"},
        }
        umbrella_duplicate = {
            "type": "Feature",
            "geometry": PARCEL_GEOMETRY,
            "properties": {"id": 42, "kma_kood": "ranna_piirang"},
        }
        heritage_match = {
            "type": "Feature",
            "geometry": PARCEL_GEOMETRY,
            "properties": {"id": 99, "kma_kood": "MUU_PIIRANG"},
        }

        async def layer_results(_bbox, source_keys, source_timeout):
            features = {source_key: [] for source_key in source_keys}
            if "ranna_piirang" in features:
                features["ranna_piirang"] = [specialized]
            features["kma_kitsendused"] = [umbrella_duplicate, heritage_match]
            return features, [], []

        selected_query = AsyncMock(side_effect=layer_results)
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_layers", new=selected_query),
        ):
            heritage_only = await api._map_context_core(KATASTER_NR, ["heritage_other"])
            with_restrictions = await api._map_context_core(
                KATASTER_NR,
                ["heritage_other", "water_restrictions", "flood_wetlands"],
            )

        heritage_only_result = heritage_only["themes"]["heritage_other"]
        combined_result = with_restrictions["themes"]["heritage_other"]
        self.assertEqual(heritage_only_result["match_count"], 1)
        self.assertEqual(combined_result["match_count"], 1)
        self.assertEqual(
            [feature["properties"]["id"] for feature in heritage_only_result["features"]],
            [99],
        )
        self.assertEqual(
            [feature["properties"]["id"] for feature in combined_result["features"]],
            [99],
        )
        self.assertEqual(set(heritage_only["themes"]), {"heritage_other"})
        self.assertTrue(
            set(("uleujutus", "veekaitse", "ranna_piirang", "vaetiste_keeld"))
            .issubset(selected_query.await_args_list[0].args[1])
        )

    async def test_truncated_single_source_keeps_matches_and_marks_theme_partial(self):
        selected_query = AsyncMock(return_value=({"lageraiealad": [MATCHING_FEATURE]}, [], ["lageraiealad"]))
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_layers", new=selected_query),
        ):
            result = await api._map_context_core(KATASTER_NR, ["archival_clearcuts"])

        theme = result["themes"]["archival_clearcuts"]
        self.assertEqual(theme["state"], "partial")
        self.assertEqual(theme["match_count"], 1)
        self.assertEqual(theme["sources"][0]["state"], "partial")
        self.assertIsNone(theme["sources"][0]["data_as_of"])
        self.assertIn("style", theme["sources"][0])

    async def test_all_theme_sources_failed_is_unavailable(self):
        selected_query = AsyncMock(return_value=({"yrask_eelis": [], "yrask_mke": []}, ["yrask_eelis", "yrask_mke"], []))
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_layers", new=selected_query),
        ):
            result = await api._map_context_core(KATASTER_NR, ["forest_health"])

        theme = result["themes"]["forest_health"]
        self.assertEqual(theme["state"], "unavailable")
        self.assertEqual(theme["match_count"], 0)
        self.assertEqual([source["state"] for source in theme["sources"]], ["unavailable", "unavailable"])
        for source in theme["sources"]:
            self.assertNotIn("checked_at", source)
            self.assertIn("attempted_at", source)
            self.assertNotIn("approximate_parcel_overlap_percent", source)
            self.assertNotIn("affected_stand_numbers", source)

    async def test_valid_match_survives_malformed_geometry_and_source_is_partial(self):
        malformed = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": "invalid"},
            "properties": {"nimi": "Vigane"},
        }
        selected_query = AsyncMock(return_value=({"natura_elupaik": [MATCHING_FEATURE, malformed]}, [], []))
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_layers", new=selected_query),
        ):
            result = await api._map_context_core(KATASTER_NR, ["species_habitats"])

        theme = result["themes"]["species_habitats"]
        self.assertEqual(theme["state"], "partial")
        self.assertEqual(theme["match_count"], 1)
        self.assertEqual(theme["features"][0]["properties"]["source_key"], "natura_elupaik")

    async def test_invalid_optional_geometries_are_dropped_and_mark_source_partial(self):
        invalid_geometries = [
            {"type": "Polygon", "coordinates": "invalid"},
            {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [float("nan"), 59.0], [24.0, 59.1], [24.0, 59.0]]],
            },
            {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.1], [24.1, 59.0], [24.0, 59.1], [24.0, 59.0]]],
            },
        ]
        malformed = [
            {"type": "Feature", "geometry": geometry, "properties": {"nimi": "Vigane"}}
            for geometry in invalid_geometries
        ]
        selected_query = AsyncMock(return_value=({"natura_elupaik": [MATCHING_FEATURE, *malformed]}, [], []))
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=[])),
            patch("api.index.query_layers", new=selected_query),
        ):
            result = await api._map_context_core(KATASTER_NR, ["species_habitats"])

        theme = result["themes"]["species_habitats"]
        self.assertEqual(theme["state"], "partial")
        self.assertEqual(theme["match_count"], 1)

    async def test_invalid_parcel_geometry_is_a_controlled_upstream_error(self):
        invalid_geometries = [
            {"type": "Polygon", "coordinates": "invalid"},
            {
                "type": "Polygon",
                "coordinates": [[[0, 0], [float("nan"), 0], [0, 1], [0, 0]]],
            },
            {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]],
            },
        ]
        for geometry in invalid_geometries:
            with self.subTest(geometry=geometry):
                invalid_parcel = {**parcel(), "geometry": geometry}
                with (
                    patch("api.index.query_kataster", new=AsyncMock(return_value=invalid_parcel)),
                    patch("api.index.query_eraldis", new=AsyncMock()) as stand_query,
                    patch("api.index.query_layers", new=AsyncMock()) as layer_query,
                ):
                    with self.assertRaises(api.HTTPException) as raised:
                        await api._map_context_core(KATASTER_NR, ["species_habitats"])

                self.assertEqual(raised.exception.status_code, 502)
                stand_query.assert_not_awaited()
                layer_query.assert_not_awaited()

    async def test_theme_and_source_include_approximate_overlap_and_affected_stands(self):
        parcel_data = {**parcel(), "geometry": SQUARE_PARCEL_GEOMETRY}
        overlap_feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.5, 0], [0.5, 1], [0, 1], [0, 0]]],
            },
            "properties": {"nimi": "Pool kinnistut"},
        }
        stands = [
            {
                "eraldis_nr": 4,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0.25, 0], [0.25, 1], [0, 1], [0, 0]]],
                },
                "puuliik_kood": "MA",
                "vanus": 40,
            },
            {
                "eraldis_nr": 7,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.75, 0], [1, 0], [1, 1], [0.75, 1], [0.75, 0]]],
                },
                "puuliik_kood": "KU",
                "vanus": 50,
            },
        ]
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel_data)),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch(
                "api.index.query_layers",
                new=AsyncMock(return_value=({"natura_elupaik": [overlap_feature]}, [], [])),
            ),
        ):
            result = await api._map_context_core(KATASTER_NR, ["species_habitats"])

        theme = result["themes"]["species_habitats"]
        source = theme["sources"][0]
        self.assertEqual(theme["match_count"], 1)
        self.assertEqual(theme["approximate_parcel_overlap_percent"], 50.0)
        self.assertEqual(theme["affected_stand_numbers"], [4])
        self.assertEqual(source["approximate_parcel_overlap_percent"], 50.0)
        self.assertEqual(source["affected_stand_numbers"], [4])

    async def test_stand_failure_does_not_block_parcel_or_theme_matches(self):
        selected_query = AsyncMock(return_value=({"natura_elupaik": [MATCHING_FEATURE]}, [], []))
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(side_effect=RuntimeError("stand source failed"))),
            patch("api.index.query_layers", new=selected_query),
        ):
            result = await api._map_context_core(KATASTER_NR, ["species_habitats"])

        self.assertEqual(result["persistent"]["parcel"]["state"], "matches")
        self.assertEqual(result["persistent"]["stands"]["state"], "unavailable")
        self.assertEqual(result["themes"]["species_habitats"]["state"], "matches")

    async def test_stands_use_neutral_age_class_colors_and_official_metadata(self):
        stands = [{
            "id": 999,
            "eraldis_nr": 4,
            "geometry": PARCEL_GEOMETRY,
            "puuliik_kood": "MA",
            "puuliik": "Mänd",
            "vanus": 100,
            "boniteedi_kood": 3,
            "pindala_ha": 1,
            "tagavara_y_ha": 210,
            "tagavara_provenance": "official",
            "korgus": 24,
            "invent_kp": "2024-01-01",
        }]
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_layers", new=AsyncMock(return_value=({"natura_elupaik": []}, [], []))),
        ):
            result = await api._map_context_core(KATASTER_NR, ["species_habitats"])

        stand_result = result["persistent"]["stands"]
        feature = stand_result["features"][0]
        self.assertEqual(stand_result["state"], "matches")
        self.assertEqual(stand_result["count"], 1)
        self.assertEqual(stand_result["source"]["provider"], "Keskkonnaagentuur")
        self.assertEqual(feature["properties"]["age_class"], "cutting_age_reached")
        self.assertEqual(feature["properties"]["color"], feature["properties"]["age_class_color"])
        self.assertEqual(feature["properties"]["age_class_provenance"], "Terrapointi tuletis")
        self.assertEqual(feature["properties"]["tagavara_y_ha"], 210)
        self.assertEqual(feature["properties"]["tagavara_provenance"], "official")
        self.assertEqual(feature["properties"]["korgus"], 24)
        self.assertNotIn("id", feature["properties"])

    async def test_stands_with_only_unusable_geometries_are_unavailable(self):
        stands = [{
            "eraldis_nr": 4,
            "geometry": {"type": "Polygon", "coordinates": "invalid"},
            "puuliik_kood": "MA",
            "vanus": 40,
        }]
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_layers", new=AsyncMock(return_value=({"natura_elupaik": []}, [], []))),
        ):
            result = await api._map_context_core(KATASTER_NR, ["species_habitats"])

        stand_result = result["persistent"]["stands"]
        self.assertEqual(stand_result["state"], "unavailable")
        self.assertFalse(stand_result["complete"])
        self.assertEqual(stand_result["count"], 0)

    async def test_valid_stand_survives_invalid_geometry_with_partial_signal(self):
        stands = [
            {
                "eraldis_nr": 4,
                "geometry": PARCEL_GEOMETRY,
                "puuliik_kood": "MA",
                "vanus": 40,
                "boniteedi_kood": 3,
            },
            {
                "eraldis_nr": 5,
                "geometry": None,
                "puuliik_kood": "KU",
                "vanus": 50,
            },
        ]
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_layers", new=AsyncMock(return_value=({"natura_elupaik": []}, [], []))),
        ):
            result = await api._map_context_core(KATASTER_NR, ["species_habitats"])

        stand_result = result["persistent"]["stands"]
        self.assertEqual(stand_result["state"], "matches")
        self.assertFalse(stand_result["complete"])
        self.assertEqual(stand_result["count"], 1)

    async def test_missing_source_age_and_species_are_classified_as_unknown(self):
        stands = [{
            "eraldis_nr": 4,
            "geometry": PARCEL_GEOMETRY,
            "puuliik": "mänd",
            "puuliik_kood": "MA",
            "puuliik_kood_raw": None,
            "vanus": 0,
            "vanus_raw": None,
            "boniteedi_kood": 3,
        }]
        with (
            patch("api.index.query_kataster", new=AsyncMock(return_value=parcel())),
            patch("api.index.query_eraldis", new=AsyncMock(return_value=stands)),
            patch("api.index.query_layers", new=AsyncMock(return_value=({"natura_elupaik": []}, [], []))),
        ):
            result = await api._map_context_core(KATASTER_NR, ["species_habitats"])

        properties = result["persistent"]["stands"]["features"][0]["properties"]
        self.assertEqual(properties["vanus"], 0)
        self.assertEqual(properties["puuliik_kood"], "MA")
        self.assertEqual(properties["age_class"], "unknown")
        self.assertEqual(properties["age_class_label"], "Määramata")
        self.assertFalse(properties["age_source_available"])
        self.assertFalse(properties["species_source_available"])


class MapContextEndpointTests(unittest.TestCase):
    def setUp(self):
        api._rate_limit_buckets.clear()
        self.client = TestClient(api.app)

    def test_unknown_theme_is_rejected_before_external_calls(self):
        with (
            patch("api.index.query_kataster", new=AsyncMock()) as parcel_query,
            patch("api.index.query_layers", new=AsyncMock()) as layer_query,
        ):
            response = self.client.get(f"/api/map-context/{KATASTER_NR}?themes=not_a_theme")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        parcel_query.assert_not_awaited()
        layer_query.assert_not_awaited()

    def test_omitted_themes_use_documented_defaults(self):
        expected = ["nature_protection", "species_habitats", "water_restrictions", "heritage_other"]
        core = AsyncMock(return_value={
            "parcel_id": KATASTER_NR,
            "requested_themes": expected,
            "checked_at": "2026-07-14T00:00:00Z",
            "persistent": {},
            "themes": {theme_id: {} for theme_id in expected},
        })
        with patch("api.index._map_context_core", new=core):
            response = self.client.get(f"/api/map-context/{KATASTER_NR}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requested_themes"], expected)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        core.assert_awaited_once_with(KATASTER_NR, expected)

    def test_repeated_theme_query_values_are_preserved_in_order(self):
        requested = ["forest_health", "flood_wetlands"]
        core = AsyncMock(return_value={
            "parcel_id": KATASTER_NR,
            "requested_themes": requested,
            "checked_at": "2026-07-14T00:00:00Z",
            "persistent": {},
            "themes": {theme_id: {} for theme_id in requested},
        })
        with patch("api.index._map_context_core", new=core):
            response = self.client.get(
                f"/api/map-context/{KATASTER_NR}",
                params=[("themes", "forest_health"), ("themes", "flood_wetlands")],
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requested_themes"], requested)
        core.assert_awaited_once_with(KATASTER_NR, requested)

    def test_invalid_cadastral_number_is_rejected(self):
        response = self.client.get("/api/map-context/not-a-cadastral-number")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["cache-control"], "private, no-store")

    def test_rate_limit_scope_is_normalized_by_parcel_and_themes(self):
        first = api._map_context_rate_scope(
            "78404:409:0113", ["forest_health", "flood_wetlands"]
        )
        reordered = api._map_context_rate_scope(
            "78404:409:0113", ["flood_wetlands", "forest_health"]
        )
        other_parcel = api._map_context_rate_scope(
            "17501:002:0490", ["forest_health", "flood_wetlands"]
        )

        self.assertEqual(first, reordered)
        self.assertNotEqual(first, other_parcel)

    def test_rotating_resources_collectively_hit_broad_client_quota(self):
        core = AsyncMock(return_value={
            "parcel_id": KATASTER_NR,
            "requested_themes": ["forest_health"],
            "checked_at": "2026-07-15T00:00:00Z",
            "persistent": {},
            "themes": {"forest_health": {}},
        })
        with (
            patch.dict(os.environ, {"VERCEL": ""}, clear=False),
            patch("api.index._map_context_core", new=core),
        ):
            for index in range(120):
                parcel_id = f"{10000 + index:05d}:001:0001"
                response = self.client.get(
                    f"/api/map-context/{parcel_id}?themes=forest_health"
                )
                self.assertEqual(response.status_code, 200, index)
            blocked = self.client.get(
                "/api/map-context/10120:001:0001?themes=invasive_species"
            )

        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked.headers)

    def test_one_resource_keeps_narrower_thirty_request_quota(self):
        core = AsyncMock(return_value={
            "parcel_id": KATASTER_NR,
            "requested_themes": ["forest_health"],
            "checked_at": "2026-07-15T00:00:00Z",
            "persistent": {},
            "themes": {"forest_health": {}},
        })
        with (
            patch.dict(os.environ, {"VERCEL": ""}, clear=False),
            patch("api.index._map_context_core", new=core),
        ):
            for index in range(30):
                response = self.client.get(
                    f"/api/map-context/{KATASTER_NR}?themes=forest_health"
                )
                self.assertEqual(response.status_code, 200, index)
            blocked = self.client.get(
                f"/api/map-context/{KATASTER_NR}?themes=forest_health"
            )

        self.assertEqual(blocked.status_code, 429)

    def test_vercel_proxy_preserves_repeated_theme_params(self):
        requested = ["forest_health", "flood_wetlands"]
        source = {
            "key": "official",
            "label": "Official source",
            "provider": "Official provider",
            "interpretation": "Official interpretation",
            "data_as_of": None,
            "checked_at": "2026-07-14T00:00:00Z",
        }
        upstream_payload = {
            "parcel_id": KATASTER_NR,
            "requested_themes": requested,
            "checked_at": "2026-07-14T00:00:00Z",
            "persistent": {
                "parcel": {"state": "matches", "feature": MATCHING_FEATURE, "source": source},
                "stands": {
                    "state": "empty", "complete": True, "count": 0,
                    "features": [], "source": source,
                },
            },
            "themes": {
                theme_id: {
                    "id": theme_id,
                    "label": theme_id,
                    "state": "empty",
                    "match_count": 0,
                    "features": [],
                    "sources": [],
                }
                for theme_id in requested
            },
        }
        captured = {}

        class UpstreamResponse:
            status_code = 200
            content = orjson.dumps(upstream_payload)
            headers = {}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, url, params=None):
                captured["url"] = url
                captured["params"] = params
                return UpstreamResponse()

        with (
            patch.dict(os.environ, {"VERCEL": "1"}, clear=False),
            patch("api.index.httpx.AsyncClient", FakeClient),
        ):
            response = self.client.get(
                f"/api/map-context/{KATASTER_NR}",
                params=[("themes", theme_id) for theme_id in requested],
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["params"], [("themes", theme_id) for theme_id in requested])
        self.assertTrue(captured["url"].endswith(f"/map-context/{KATASTER_NR}"))

    def test_vercel_proxy_rejects_schema_or_echo_mismatch(self):
        class UpstreamResponse:
            status_code = 200
            content = orjson.dumps({
                "parcel_id": KATASTER_NR,
                "requested_themes": ["nature_protection"],
                "persistent": {},
                "themes": {},
            })
            headers = {}

        response = api._map_context_proxy_response(
            UpstreamResponse(),
            KATASTER_NR,
            ["species_habitats"],
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(orjson.loads(response.body)["code"], "UPSTREAM_SCHEMA")
        self.assertEqual(response.headers["cache-control"], "private, no-store")

    def test_vercel_proxy_rejects_missing_map_context_contract_fields(self):
        class UpstreamResponse:
            status_code = 200
            content = orjson.dumps({
                "parcel_id": KATASTER_NR,
                "requested_themes": ["species_habitats"],
                "checked_at": "2026-07-14T00:00:00Z",
                "persistent": {"parcel": {}, "stands": {}},
                "themes": {"species_habitats": {}},
            })
            headers = {}

        response = api._map_context_proxy_response(
            UpstreamResponse(),
            KATASTER_NR,
            ["species_habitats"],
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(orjson.loads(response.body)["code"], "UPSTREAM_SCHEMA")

    def test_proxy_accepts_null_or_iso_source_date_and_stand_completeness(self):
        source = {
            "key": "official",
            "label": "Official source",
            "provider": "Official provider",
            "interpretation": "Official interpretation",
            "data_as_of": "2026-07-14",
            "checked_at": "2026-07-15T00:00:00Z",
        }
        payload = {
            "parcel_id": KATASTER_NR,
            "requested_themes": ["species_habitats"],
            "checked_at": "2026-07-15T00:00:00Z",
            "persistent": {
                "parcel": {"state": "matches", "feature": MATCHING_FEATURE, "source": source},
                "stands": {
                    "state": "matches",
                    "complete": False,
                    "count": 1,
                    "features": [MATCHING_FEATURE],
                    "source": {**source, "data_as_of": None},
                },
            },
            "themes": {
                "species_habitats": {
                    "id": "species_habitats",
                    "label": "Liigid ja elupaigad",
                    "state": "matches",
                    "match_count": 1,
                    "features": [MATCHING_FEATURE],
                    "sources": [{**source, "state": "matches", "match_count": 1}],
                },
            },
        }

        class UpstreamResponse:
            status_code = 200
            content = orjson.dumps(payload)
            headers = {}

        response = api._map_context_proxy_response(
            UpstreamResponse(), KATASTER_NR, ["species_habitats"]
        )

        self.assertEqual(response.status_code, 200)

    def test_proxy_rejects_invalid_source_dates(self):
        for invalid in ("", "14.07.2026", "2026-02-30", 20260714, True, []):
            with self.subTest(invalid=invalid):
                source = {
                    "key": "official",
                    "label": "Official source",
                    "provider": "Official provider",
                    "interpretation": "Official interpretation",
                    "data_as_of": invalid,
                    "checked_at": "2026-07-15T00:00:00Z",
                }
                payload = {
                    "parcel_id": KATASTER_NR,
                    "requested_themes": [],
                    "checked_at": "2026-07-15T00:00:00Z",
                    "persistent": {
                        "parcel": {"state": "matches", "feature": MATCHING_FEATURE, "source": source},
                        "stands": {
                            "state": "empty", "complete": True, "count": 0,
                            "features": [], "source": {**source, "data_as_of": None},
                        },
                    },
                    "themes": {},
                }

                class UpstreamResponse:
                    status_code = 200
                    content = orjson.dumps(payload)
                    headers = {}

                response = api._map_context_proxy_response(
                    UpstreamResponse(), KATASTER_NR, []
                )
                self.assertEqual(response.status_code, 502)

    def test_proxy_rejects_malformed_optional_feature_geometries(self):
        invalid_geometries = [
            {"type": "Polygon", "coordinates": "invalid"},
            {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [float("nan"), 59.0], [24.0, 59.1], [24.0, 59.0]]],
            },
            {
                "type": "Polygon",
                "coordinates": [[[24.0, 59.0], [24.1, 59.1], [24.1, 59.0], [24.0, 59.1], [24.0, 59.0]]],
            },
        ]
        source = {
            "key": "official",
            "label": "Official source",
            "provider": "Official provider",
            "interpretation": "Official interpretation",
            "data_as_of": None,
            "checked_at": "2026-07-15T00:00:00Z",
        }
        for geometry in invalid_geometries:
            with self.subTest(geometry=geometry):
                malformed_feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {},
                }
                payload = {
                    "parcel_id": KATASTER_NR,
                    "requested_themes": ["species_habitats"],
                    "checked_at": "2026-07-15T00:00:00Z",
                    "persistent": {
                        "parcel": {"state": "matches", "feature": MATCHING_FEATURE, "source": source},
                        "stands": {
                            "state": "empty",
                            "complete": True,
                            "count": 0,
                            "features": [],
                            "source": source,
                        },
                    },
                    "themes": {
                        "species_habitats": {
                            "id": "species_habitats",
                            "label": "Liigid ja elupaigad",
                            "state": "matches",
                            "match_count": 1,
                            "features": [malformed_feature],
                            "sources": [{**source, "state": "matches", "match_count": 1}],
                        },
                    },
                }

                class UpstreamResponse:
                    status_code = 200
                    content = orjson.dumps(payload)
                    headers = {}

                response = api._map_context_proxy_response(
                    UpstreamResponse(), KATASTER_NR, ["species_habitats"]
                )
                self.assertEqual(response.status_code, 502)
                self.assertEqual(orjson.loads(response.body)["code"], "UPSTREAM_SCHEMA")

    def test_proxy_validates_overlap_details_and_deterministic_stand_numbers(self):
        source = {
            "key": "official",
            "label": "Official source",
            "provider": "Official provider",
            "interpretation": "Official interpretation",
            "data_as_of": None,
            "checked_at": "2026-07-15T00:00:00Z",
        }
        payload = {
            "parcel_id": KATASTER_NR,
            "requested_themes": ["species_habitats"],
            "checked_at": "2026-07-15T00:00:00Z",
            "persistent": {
                "parcel": {"state": "matches", "feature": MATCHING_FEATURE, "source": source},
                "stands": {
                    "state": "empty",
                    "complete": True,
                    "count": 0,
                    "features": [],
                    "source": source,
                },
            },
            "themes": {
                "species_habitats": {
                    "id": "species_habitats",
                    "label": "Liigid ja elupaigad",
                    "state": "matches",
                    "match_count": 1,
                    "features": [MATCHING_FEATURE],
                    "approximate_parcel_overlap_percent": 50.0,
                    "affected_stand_numbers": [4, 7],
                    "sources": [{
                        **source,
                        "state": "matches",
                        "match_count": 1,
                        "approximate_parcel_overlap_percent": 50.0,
                        "affected_stand_numbers": [4, 7],
                    }],
                },
            },
        }

        class UpstreamResponse:
            status_code = 200
            content = orjson.dumps(payload)
            headers = {}

        accepted = api._map_context_proxy_response(
            UpstreamResponse(), KATASTER_NR, ["species_habitats"]
        )
        self.assertEqual(accepted.status_code, 200)

        invalid_payloads = []
        for invalid_overlap in (-0.1, 100.1, "50"):
            invalid_payloads.append({
                **payload,
                "themes": {
                    "species_habitats": {
                        **payload["themes"]["species_habitats"],
                        "approximate_parcel_overlap_percent": invalid_overlap,
                    },
                },
            })
        invalid_payloads.append({
            **payload,
            "themes": {
                "species_habitats": {
                    **payload["themes"]["species_habitats"],
                    "affected_stand_numbers": [7, 4, 4],
                },
            },
        })

        for invalid_payload in invalid_payloads:
            with self.subTest(theme=invalid_payload["themes"]["species_habitats"]):
                class InvalidUpstreamResponse:
                    status_code = 200
                    content = orjson.dumps(invalid_payload)
                    headers = {}

                rejected = api._map_context_proxy_response(
                    InvalidUpstreamResponse(), KATASTER_NR, ["species_habitats"]
                )
                self.assertEqual(rejected.status_code, 502)

    def test_proxy_requires_attempted_at_instead_of_checked_at_for_unavailable_source(self):
        checked_source = {
            "key": "official",
            "label": "Official source",
            "provider": "Official provider",
            "interpretation": "Official interpretation",
            "data_as_of": None,
            "checked_at": "2026-07-15T00:00:00Z",
        }
        unavailable_source = {
            "key": "natura_elupaik",
            "label": "Official source",
            "provider": "Official provider",
            "interpretation": "Official interpretation",
            "data_as_of": None,
            "state": "unavailable",
            "match_count": 0,
            "attempted_at": "2026-07-15T00:00:00Z",
        }
        payload = {
            "parcel_id": KATASTER_NR,
            "requested_themes": ["species_habitats"],
            "checked_at": "2026-07-15T00:00:00Z",
            "persistent": {
                "parcel": {"state": "matches", "feature": MATCHING_FEATURE, "source": checked_source},
                "stands": {
                    "state": "empty",
                    "complete": True,
                    "count": 0,
                    "features": [],
                    "source": checked_source,
                },
            },
            "themes": {
                "species_habitats": {
                    "id": "species_habitats",
                    "label": "Liigid ja elupaigad",
                    "state": "unavailable",
                    "match_count": 0,
                    "features": [],
                    "sources": [unavailable_source],
                },
            },
        }

        class UpstreamResponse:
            status_code = 200
            content = orjson.dumps(payload)
            headers = {}

        accepted = api._map_context_proxy_response(
            UpstreamResponse(), KATASTER_NR, ["species_habitats"]
        )
        self.assertEqual(accepted.status_code, 200)

        unavailable_source["approximate_parcel_overlap_percent"] = 0.0

        class FabricatedOverlapResponse:
            status_code = 200
            content = orjson.dumps(payload)
            headers = {}

        fabricated = api._map_context_proxy_response(
            FabricatedOverlapResponse(), KATASTER_NR, ["species_habitats"]
        )
        self.assertEqual(fabricated.status_code, 502)
        unavailable_source.pop("approximate_parcel_overlap_percent")

        unavailable_source["checked_at"] = unavailable_source.pop("attempted_at")

        class InvalidUpstreamResponse:
            status_code = 200
            content = orjson.dumps(payload)
            headers = {}

        rejected = api._map_context_proxy_response(
            InvalidUpstreamResponse(), KATASTER_NR, ["species_habitats"]
        )
        self.assertEqual(rejected.status_code, 502)


class SearchEndpointLayerOptionTests(unittest.TestCase):
    def setUp(self):
        api._rate_limit_buckets.clear()
        self.client = TestClient(api.app)

    def test_omitted_option_preserves_eager_layer_compatibility(self):
        search = AsyncMock(return_value=api.json_response({"ok": True}))
        with (
            patch.dict(os.environ, {"VERCEL": ""}, clear=False),
            patch("api.index._search", new=search),
        ):
            response = self.client.get(f"/api/search/{KATASTER_NR}")

        self.assertEqual(response.status_code, 200)
        search.assert_awaited_once_with(KATASTER_NR, include_map_layers=True)

    def test_false_option_skips_layers_in_direct_search(self):
        search = AsyncMock(return_value=api.json_response({"ok": True}))
        with (
            patch.dict(os.environ, {"VERCEL": ""}, clear=False),
            patch("api.index._search", new=search),
        ):
            response = self.client.get(
                f"/api/search/{KATASTER_NR}?include_map_layers=false"
            )

        self.assertEqual(response.status_code, 200)
        search.assert_awaited_once_with(KATASTER_NR, include_map_layers=False)

    def test_invalid_boolean_option_is_rejected(self):
        with patch("api.index._search", new=AsyncMock()) as search:
            response = self.client.get(
                f"/api/search/{KATASTER_NR}?include_map_layers=not-a-boolean"
            )

        self.assertEqual(response.status_code, 422)
        search.assert_not_awaited()

    def test_vercel_proxy_forwards_false_option(self):
        captured = {}

        class UpstreamResponse:
            status_code = 200
            content = b"{}"
            headers = {}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, url, params=None):
                captured["url"] = url
                captured["params"] = params
                return UpstreamResponse()

        with (
            patch.dict(os.environ, {"VERCEL": "1"}, clear=False),
            patch("api.index.httpx.AsyncClient", FakeClient),
            patch(
                "api.index._search_proxy_response",
                return_value=api.json_response({"ok": True}),
            ),
        ):
            response = self.client.get(
                f"/api/search/{KATASTER_NR}?include_map_layers=false"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["params"], {"include_map_layers": "false"})
        self.assertTrue(captured["url"].endswith(f"/search/{KATASTER_NR}"))


if __name__ == "__main__":
    unittest.main()

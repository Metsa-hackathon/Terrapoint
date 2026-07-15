import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from services.layers import (
    LAYER_CONFIGS,
    MAX_FEATURES_PER_LAYER,
    SOURCE_REGISTRY,
    THEME_REGISTRY,
    _fetch_layer,
    deduplicate_kpois_sources,
    deduplicate_source_records,
    query_all_layers,
    query_layers,
    reduce_theme,
)


class FakeResponse:
    def __init__(self, status_code=200, features=None):
        self.status_code = status_code
        self.features = features if features is not None else []

    def json(self):
        return {"features": self.features}


class FakeClient:
    def __init__(self, response):
        self.response = response

    async def get(self, url):
        return self.response


class LayerResultTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_layer_is_reported_as_unavailable(self):
        result = await _fetch_layer(FakeClient(FakeResponse(503)), "kaitsealad", "eelis", "eelis:kr_kaitseala", "24,59,25,60", attempts=1)

        self.assertEqual(result, ("kaitsealad", [], True, False))

    async def test_feature_limit_marks_layer_as_potentially_truncated(self):
        features = [{"type": "Feature"}] * MAX_FEATURES_PER_LAYER
        result = await _fetch_layer(FakeClient(FakeResponse(features=features)), "kaitsealad", "eelis", "eelis:kr_kaitseala", "24,59,25,60", attempts=1)

        self.assertEqual(result, ("kaitsealad", features, False, True))

    async def test_malformed_features_value_marks_layer_unavailable(self):
        result = await _fetch_layer(
            FakeClient(FakeResponse(features={"not": "a list"})),
            "kaitsealad",
            "eelis",
            "eelis:kr_kaitseala",
            "24,59,25,60",
            attempts=1,
        )

        self.assertEqual(result, ("kaitsealad", [], True, False))

    async def test_non_object_feature_marks_layer_unavailable(self):
        result = await _fetch_layer(
            FakeClient(FakeResponse(features=[None])),
            "kaitsealad",
            "eelis",
            "eelis:kr_kaitseala",
            "24,59,25,60",
            attempts=1,
        )

        self.assertEqual(result, ("kaitsealad", [], True, False))


class LayerRegistryTests(unittest.TestCase):
    def test_every_configured_layer_has_one_source_definition(self):
        configured_keys = [key for key, _workspace, _typename in LAYER_CONFIGS]

        self.assertEqual(list(SOURCE_REGISTRY), configured_keys)
        for source in SOURCE_REGISTRY.values():
            self.assertTrue(source.label)
            self.assertTrue(source.provider)
            self.assertTrue(source.source_label)
            self.assertTrue(source.interpretation)

    def test_sources_are_mapped_to_verified_user_themes(self):
        expected = {
            "nature_protection": ("kaitsealad", "piirang", "piirangukeelualad"),
            "species_habitats": ("natura_elupaik",),
            "water_restrictions": ("veekogud", "vooluveed", "veekaitse", "ranna_piirang", "vaetiste_keeld"),
            "heritage_other": ("malestised", "kaitsevoondid", "katsealad", "kma_kitsendused"),
            "flood_wetlands": ("sood", "uleujutus"),
            "forest_health": ("yrask_eelis", "yrask_mke"),
            "invasive_species": ("karuputk",),
            "archival_clearcuts": ("lageraiealad",),
        }

        self.assertEqual(
            {theme_id: theme.source_keys for theme_id, theme in THEME_REGISTRY.items()},
            expected,
        )
        self.assertIsNone(SOURCE_REGISTRY["kma_kitsendused"].theme_id)
        self.assertTrue(SOURCE_REGISTRY["kma_kitsendused"].technical_umbrella)

    def test_technical_umbrella_contributes_only_to_other_restrictions(self):
        self.assertIn("kma_kitsendused", THEME_REGISTRY["heritage_other"].source_keys)
        self.assertTrue(all(
            "kma_kitsendused" not in theme.source_keys
            for theme_id, theme in THEME_REGISTRY.items()
            if theme_id != "heritage_other"
        ))

    def test_adaptest_layer_is_not_presented_as_a_protected_area(self):
        source = SOURCE_REGISTRY["katsealad"]

        self.assertEqual(source.theme_id, "heritage_other")
        self.assertIn("AdaptEST", source.label)
        self.assertNotIn("Kaitseala", source.label)

    def test_registry_preserves_existing_map_style_metadata(self):
        style = SOURCE_REGISTRY["kaitsealad"].style

        self.assertEqual(style.label, "Kaitsealad")
        self.assertEqual(style.color, "#1b4332")
        self.assertIsNone(style.dash)
        self.assertEqual(style.weight, 4)
        self.assertEqual(style.fill_opacity, 0.35)
        self.assertIsNone(SOURCE_REGISTRY["vaetiste_keeld"].style)
        self.assertIsNone(SOURCE_REGISTRY["katsealad"].style)


class SelectedLayerQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_requested_layers_are_fetched_in_caller_order(self):
        requested = ["vooluveed", "kaitsealad", "sood"]

        async def fake_fetch(_client, key, _workspace, _typename, _bbox):
            if key == "kaitsealad":
                return key, [], True, False
            if key == "sood":
                return key, [{"id": "wetland"}], False, True
            return key, [{"id": "river"}], False, False

        with patch("services.layers._fetch_layer", new=AsyncMock(side_effect=fake_fetch)) as fetch:
            layers, unavailable, truncated = await query_layers("24,59,25,60", requested)

        self.assertEqual(list(layers), requested)
        self.assertEqual(layers["vooluveed"], [{"id": "river"}])
        self.assertEqual(layers["kaitsealad"], [])
        self.assertEqual(layers["sood"], [{"id": "wetland"}])
        self.assertEqual(unavailable, ["kaitsealad"])
        self.assertEqual(truncated, ["sood"])
        self.assertEqual([call.args[1] for call in fetch.await_args_list], requested)

    async def test_fetch_exception_is_reported_for_only_that_selected_layer(self):
        async def fake_fetch(_client, key, _workspace, _typename, _bbox):
            if key == "sood":
                raise RuntimeError("broken task")
            return key, [], False, False

        with patch("services.layers._fetch_layer", new=AsyncMock(side_effect=fake_fetch)):
            layers, unavailable, truncated = await query_layers(
                "24,59,25,60", ["sood", "karuputk"]
            )

        self.assertEqual(layers, {"sood": [], "karuputk": []})
        self.assertEqual(unavailable, ["sood"])
        self.assertEqual(truncated, [])

    async def test_per_source_timeout_preserves_completed_layer(self):
        completed = {"type": "Feature", "id": "fast"}

        async def fake_fetch(_client, key, _workspace, _typename, _bbox):
            if key == "sood":
                await asyncio.sleep(1)
            return key, [completed], False, False

        with patch("services.layers._fetch_layer", new=AsyncMock(side_effect=fake_fetch)):
            layers, unavailable, truncated = await query_layers(
                "24,59,25,60",
                ["kaitsealad", "sood"],
                source_timeout=0.01,
            )

        self.assertEqual(layers["kaitsealad"], [completed])
        self.assertEqual(layers["sood"], [])
        self.assertEqual(unavailable, ["sood"])
        self.assertEqual(truncated, [])

    async def test_unknown_layer_key_is_rejected_before_fetching(self):
        with patch("services.layers._fetch_layer", new=AsyncMock()) as fetch:
            with self.assertRaisesRegex(ValueError, "unknown_layer"):
                await query_layers("24,59,25,60", ["kaitsealad", "unknown_layer"])

        fetch.assert_not_awaited()

    async def test_query_all_layers_delegates_with_every_configured_key(self):
        expected = ({"sentinel": []}, ["failed"], ["truncated"])
        with patch("services.layers.query_layers", new=AsyncMock(return_value=expected)) as selected_query:
            result = await query_all_layers("24,59,25,60")

        self.assertEqual(result, expected)
        selected_query.assert_awaited_once_with(
            "24,59,25,60", [key for key, _workspace, _typename in LAYER_CONFIGS]
        )


class ThemeReducerTests(unittest.TestCase):
    def test_complete_sources_with_matches_preserve_features_in_source_order(self):
        lake = {"id": "lake"}
        river = {"id": "river"}

        result = reduce_theme(
            "water_restrictions",
            {"vooluveed": [river], "veekogud": [lake]},
            unavailable_keys=[],
            truncated_keys=[],
        )

        self.assertEqual(result.state, "matches")
        self.assertEqual(result.match_count, 2)
        self.assertEqual(result.features, (lake, river))
        self.assertEqual(
            [(source.key, source.state) for source in result.source_states],
            [
                ("veekogud", "matches"),
                ("vooluveed", "matches"),
                ("veekaitse", "empty"),
                ("ranna_piirang", "empty"),
                ("vaetiste_keeld", "empty"),
            ],
        )

    def test_complete_zero_result_is_empty(self):
        result = reduce_theme(
            "species_habitats",
            {"natura_elupaik": []},
            unavailable_keys=[],
            truncated_keys=[],
        )

        self.assertEqual(result.state, "empty")
        self.assertEqual(result.match_count, 0)
        self.assertEqual(result.features, ())

    def test_usable_zero_plus_failed_source_is_partial(self):
        result = reduce_theme(
            "forest_health",
            {"yrask_eelis": [], "yrask_mke": []},
            unavailable_keys=["yrask_mke"],
            truncated_keys=[],
        )

        self.assertEqual(result.state, "partial")
        self.assertEqual(result.match_count, 0)

    def test_all_required_sources_unusable_is_unavailable(self):
        result = reduce_theme(
            "forest_health",
            {},
            unavailable_keys=["yrask_eelis", "yrask_mke"],
            truncated_keys=[],
        )

        self.assertEqual(result.state, "unavailable")
        self.assertEqual(
            [source.state for source in result.source_states],
            ["unavailable", "unavailable"],
        )

    def test_single_truncated_source_with_matches_is_partial(self):
        feature = {"id": "archive-hit"}

        result = reduce_theme(
            "archival_clearcuts",
            {"lageraiealad": [feature]},
            unavailable_keys=[],
            truncated_keys=["lageraiealad"],
        )

        self.assertEqual(result.state, "partial")
        self.assertEqual(result.match_count, 1)
        self.assertEqual(result.features, (feature,))
        self.assertEqual(result.source_states[0].state, "partial")

    def test_matches_remain_visible_when_another_source_fails(self):
        feature = {"id": "official-hit"}

        result = reduce_theme(
            "forest_health",
            {"yrask_eelis": [feature]},
            unavailable_keys=["yrask_mke"],
            truncated_keys=[],
        )

        self.assertEqual(result.state, "partial")
        self.assertEqual(result.match_count, 1)
        self.assertEqual(result.features, (feature,))

    def test_unknown_theme_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown_theme"):
            reduce_theme("unknown_theme", {}, [], [])


class KpoisDeduplicationTests(unittest.TestCase):
    def test_exact_repeats_within_source_are_deduplicated_by_official_id(self):
        repeated = {
            "id": "kaitseala.42",
            "geometry": {"type": "Point", "coordinates": [24, 59]},
            "properties": {"id": 42, "nimi": "Sama kirje"},
        }
        same_id_different_meaning = {
            **repeated,
            "properties": {"id": 42, "nimi": "Teine õiguslik tähendus"},
        }
        no_official_id = {"properties": {"nimi": "ID-ta kirje"}}

        result = deduplicate_source_records({
            "kaitsealad": [
                repeated,
                dict(repeated),
                same_id_different_meaning,
                no_official_id,
                dict(no_official_id),
            ],
        })

        self.assertEqual(
            result["kaitsealad"],
            [repeated, same_id_different_meaning, no_official_id, no_official_id],
        )

    def test_umbrella_duplicate_requires_same_non_null_id_and_normalized_code(self):
        specialized = {"properties": {"id": 42, "kood": " RANNA_PIIRANG "}}
        duplicate = {"properties": {"id": 42, "kma_kood": "ranna_piirang"}}
        different_code = {"properties": {"id": 42, "kma_kood": "VEEKAITSE"}}
        missing_id = {"properties": {"id": None, "kma_kood": "RANNA_PIIRANG"}}

        result = deduplicate_kpois_sources(
            {
                "ranna_piirang": [specialized],
                "kma_kitsendused": [duplicate, different_code, missing_id],
            }
        )

        self.assertEqual(result["ranna_piirang"], [specialized])
        self.assertEqual(result["kma_kitsendused"], [different_code, missing_id])

    def test_shared_vid_does_not_merge_distinct_water_zones(self):
        water_protection = {"properties": {"id": 1, "kood": "VEEKAITSE", "vid": 900}}
        shore_restriction = {"properties": {"id": 2, "kood": "RANNA_PIIRANG", "vid": 900}}

        result = deduplicate_kpois_sources(
            {"veekaitse": [water_protection], "ranna_piirang": [shore_restriction]}
        )

        self.assertEqual(result["veekaitse"], [water_protection])
        self.assertEqual(result["ranna_piirang"], [shore_restriction])

    def test_protected_area_and_zone_records_are_never_cross_deduplicated(self):
        protected_area = {"properties": {"id": 7, "kood": "SAME"}}
        restriction_zone = {"properties": {"id": 7, "kood": "SAME"}}

        result = deduplicate_kpois_sources(
            {"kaitsealad": [protected_area], "piirang": [restriction_zone]}
        )

        self.assertEqual(result["kaitsealad"], [protected_area])
        self.assertEqual(result["piirang"], [restriction_zone])


if __name__ == "__main__":
    unittest.main()

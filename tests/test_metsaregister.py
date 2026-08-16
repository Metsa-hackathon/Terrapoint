import unittest
from unittest.mock import AsyncMock, patch

from services import metsaregister
from services.metsaregister import (
    MetsaregisterWFSError,
    query_eraldis,
    query_eraldis_element,
    query_kahjustused,
    query_teatised,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload if payload is not None else {"features": []}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("unexpected HTTP error")

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        return self.response


class MetsaregisterDataTests(unittest.IsolatedAsyncioTestCase):
    def test_species_names_match_the_official_metsaregister_classifier(self):
        self.assertEqual(metsaregister.SPECIES_NAMES, {
            "MA": "mänd", "KU": "kuusk", "NU": "nulg", "LH": "lehis",
            "SD": "seedermänd", "TS": "ebatsuuga", "TA": "tamm", "SA": "saar",
            "VA": "vaher", "JA": "jalakas", "KS": "kask", "HB": "haab",
            "LM": "sanglepp", "LV": "hall lepp", "PN": "pärn", "PP": "pappel",
            "RE": "remmelgas", "TM": "toomingas", "PI": "pihlakas", "KP": "künnapuu",
            "TO": "teised okaspuuliigid", "TL": "teised lehtpuuliigid",
            "SP": "sarapuu", "PK": "paakspuu", "TY": "türnpuu", "KL": "kuslapuu",
            "KD": "kadakas", "TP": "teised põõsaliigid", "PA": "paju", "JP": "jugapuu",
        })

    def test_stock_estimate_keeps_extreme_boniteet_codes_monotonic(self):
        estimates = {
            code: metsaregister.estimate_tagavara(code, 25, 60)
            for code in range(7)
        }

        self.assertEqual(estimates[0], estimates[1])
        self.assertEqual(estimates[6], estimates[5])
        self.assertEqual(
            list(estimates.values()),
            sorted(estimates.values(), reverse=True),
        )

    async def test_wfs_get_keeps_successful_empty_response_distinct_from_failure(self):
        with patch("services.metsaregister.httpx.AsyncClient", return_value=FakeAsyncClient(FakeResponse())):
            features = await metsaregister._wfs_get("https://example.test/wfs", retries=0)

        self.assertEqual(features, [])

    async def test_wfs_get_raises_after_retryable_http_failure(self):
        with patch("services.metsaregister.httpx.AsyncClient", return_value=FakeAsyncClient(FakeResponse(503))):
            with self.assertRaises(MetsaregisterWFSError):
                await metsaregister._wfs_get("https://example.test/wfs", retries=0)

    async def test_wfs_get_rejects_malformed_features_value(self):
        response = FakeResponse(payload={"features": None})

        with patch("services.metsaregister.httpx.AsyncClient", return_value=FakeAsyncClient(response)):
            with self.assertRaises(MetsaregisterWFSError):
                await metsaregister._wfs_get("https://example.test/wfs", retries=0)

    async def test_wfs_get_rejects_non_object_feature(self):
        response = FakeResponse(payload={"features": [None]})

        with patch("services.metsaregister.httpx.AsyncClient", return_value=FakeAsyncClient(response)):
            with self.assertRaises(MetsaregisterWFSError):
                await metsaregister._wfs_get("https://example.test/wfs", retries=0)

    async def test_explicit_zero_stock_is_not_replaced_with_an_estimate(self):
        features = [{
            "properties": {
                "id": 1,
                "peapuuliik_kood": "KU",
                "tagavara_1_ha": 0,
                "boniteedi_kood": 1,
                "korgus": 25,
                "keskm_vanus": 75,
                "pindala": 2,
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            eraldised = await query_eraldis("78404:409:0113")

        self.assertEqual(eraldised[0]["tagavara_y_ha"], 0)
        self.assertEqual(eraldised[0]["tagavara_provenance"], "official")

    async def test_stand_source_retry_policy_fits_api_deadline(self):
        with patch(
            "services.metsaregister._wfs_get",
            new=AsyncMock(return_value=[]),
        ) as wfs_get:
            self.assertEqual(await query_eraldis("78404:409:0113"), [])

        self.assertEqual(wfs_get.await_args.kwargs, {"timeout": 3.5, "retries": 1})

    async def test_missing_stock_is_marked_as_terrapoint_estimate(self):
        features = [{
            "properties": {
                "id": 1,
                "peapuuliik_kood": "KU",
                "boniteedi_kood": 1,
                "korgus": 25,
                "keskm_vanus": 75,
                "pindala": 2,
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            eraldised = await query_eraldis("78404:409:0113")

        self.assertGreater(eraldised[0]["tagavara_y_ha"], 0)
        self.assertEqual(eraldised[0]["tagavara_provenance"], "estimated")

    async def test_stock_without_registry_or_estimation_inputs_is_unavailable(self):
        features = [{"properties": {"id": 1, "peapuuliik_kood": "KU", "pindala": 2}}]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            eraldised = await query_eraldis("78404:409:0113")

        self.assertIsNone(eraldised[0]["tagavara_y_ha"])
        self.assertEqual(eraldised[0]["tagavara_provenance"], "unavailable")

    async def test_element_stock_preserves_official_and_estimated_provenance(self):
        features = [
            {"properties": {"puuliik_kood": "MA", "tagavara": 50, "vanus": 60}},
            {"properties": {"puuliik_kood": "LV", "vanus": 60}},
        ]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            elements = await query_eraldis_element(1)

        self.assertEqual(elements[0]["tagavara_provenance"], "official")
        self.assertEqual(elements[1]["tagavara_provenance"], "estimated")

    async def test_stand_keeps_internal_id_separate_from_official_compartment_number(self):
        features = [{
            "id": "eraldis.122861",
            "properties": {
                "sys_id": 20206585,
                "id": 11108251,
                "eraldise_nr": 16,
                "peapuuliik_kood": "MA",
                "tagavara_1_ha": 100,
                "boniteedi_kood": 2,
                "pindala": 1.5,
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            stands = await query_eraldis("78404:409:0113")

        self.assertEqual(stands[0]["id"], 11108251)
        self.assertEqual(stands[0]["eraldis_nr"], 16)
        self.assertNotEqual(stands[0]["id"], stands[0]["eraldis_nr"])

    async def test_live_stand_stock_sums_first_second_and_individual_tree_storeys(self):
        features = [{
            "properties": {
                "id": 12144170,
                "peapuuliik_kood": "KS",
                "tagavara_1_ha": 1,
                "tagavara_2_ha": 0,
                "tagavara_y_ha": 34,
                "tagavara_s_ha": 12,
                "tagavara_l_ha": 8,
                "boniteedi_kood": "3",
                "pindala": 2,
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            eraldised = await query_eraldis("78404:409:0113")

        self.assertEqual(eraldised[0]["tagavara_y_ha"], 35)
        self.assertEqual(eraldised[0]["elus_tagavara_ha"], 35)
        self.assertEqual(eraldised[0]["tagavara_rinded"], {"1": 1, "2": 0, "Y": 34})
        self.assertEqual(eraldised[0]["tagavara_provenance"], "official")

    async def test_stand_preserves_inventory_freshness_and_growth_fields(self):
        features = [{
            "properties": {
                "id": 1,
                "peapuuliik_kood": "LM",
                "tagavara_1_ha": 100,
                "boniteedi_kood": "2",
                "pindala": 1.5,
                "invent_kp": "2018-04-12Z",
                "registreerimise_kp": "2019-01-03T12:30:00Z",
                "juurdekasv": 4.2,
                "kasvukoht_kood": "MD",
                "keskm_raievanus": 67,
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            eraldised = await query_eraldis("78404:409:0113")

        self.assertEqual(eraldised[0]["invent_kp"], "2018-04-12")
        self.assertEqual(eraldised[0]["registreerimise_kp"], "2019-01-03")
        self.assertEqual(eraldised[0]["juurdekasv"], 4.2)
        self.assertEqual(eraldised[0]["kasvukoht_kood"], "MD")
        self.assertEqual(eraldised[0]["raievanus"], 67)

    async def test_missing_age_and_species_remain_available_to_classifiers_as_none(self):
        features = [{
            "properties": {
                "id": 1,
                "tagavara_1_ha": 0,
                "boniteedi_kood": 3,
                "pindala": 1,
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            stands = await query_eraldis("78404:409:0113")

        self.assertEqual(stands[0]["vanus"], 0)
        self.assertEqual(stands[0]["puuliik_kood"], "MA")
        self.assertIsNone(stands[0]["vanus_raw"])
        self.assertIsNone(stands[0]["puuliik_kood_raw"])

    async def test_invalid_boolean_and_date_stand_data_fails_closed(self):
        base = {
            "id": 1,
            "peapuuliik_kood": "MA",
            "tagavara_1_ha": 10,
            "boniteedi_kood": 2,
            "pindala": 1,
        }
        for extra in (
            {"kuivendatud": "false"},
            {"invent_kp": {"unexpected": True}},
            {"registreerimise_kp": "not-a-date"},
        ):
            with self.subTest(extra=extra):
                features = [{"properties": {**base, **extra}}]
                with patch(
                    "services.metsaregister._wfs_get",
                    new=AsyncMock(return_value=features),
                ):
                    with self.assertRaises(MetsaregisterWFSError):
                        await query_eraldis("78404:409:0113")

    async def test_invalid_numeric_stand_data_fails_closed(self):
        features = [{
            "properties": {
                "id": 1,
                "peapuuliik_kood": "MA",
                "tagavara_1_ha": -1,
                "boniteedi_kood": 2,
                "pindala": 1,
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            with self.assertRaises(MetsaregisterWFSError):
                await query_eraldis("78404:409:0113")

    async def test_missing_stand_area_fails_closed(self):
        features = [{"properties": {"id": 1, "peapuuliik_kood": "MA"}}]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            with self.assertRaises(MetsaregisterWFSError):
                await query_eraldis("78404:409:0113")

    async def test_zero_stand_area_fails_closed(self):
        features = [{"properties": {
            "id": 1,
            "peapuuliik_kood": "MA",
            "pindala": 0,
        }}]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            with self.assertRaises(MetsaregisterWFSError):
                await query_eraldis("78404:409:0113")

    async def test_notices_merge_current_and_archive_and_prefer_current_duplicate(self):
        current = [{"id": "teatis.1", "properties": {
            "teatise_nr": "A", "eraldise_nr": 1, "too_kood": "LR",
            "raiutav_maht": 100, "otsus": "JAH",
        }}]
        archive = [
            {"id": "teatis_arhiiv.1", "properties": {
                "teatise_nr": "A", "eraldise_nr": 1, "too_kood": "LR",
                "raiutav_maht": 100, "otsus": "VANA",
            }},
            {"id": "teatis_arhiiv.2", "properties": {
                "teatise_nr": "A", "eraldise_nr": 2, "too_kood": "LR",
                "raiutav_maht": 200, "otsus": "JAH",
            }},
            {"id": "teatis_arhiiv.3", "properties": {"teatise_nr": "B", "otsus": "JAH"}},
        ]

        async def fake_wfs(url, **_kwargs):
            return archive if "teatis_arhiiv" in url else current

        with patch("services.metsaregister._wfs_get", new=AsyncMock(side_effect=fake_wfs)) as fetch:
            notices, unavailable = await query_teatised("78404:409:0113")

        self.assertEqual(fetch.await_count, 2)
        self.assertEqual(unavailable, [])
        requested_urls = [call.args[0] for call in fetch.await_args_list]
        self.assertTrue(all("propertyName=" in url for url in requested_urls))
        self.assertTrue(all("shape" not in url for url in requested_urls))
        notice_a = [n["properties"] for n in notices if n["properties"]["teatise_nr"] == "A"]
        self.assertEqual(len(notice_a), 2)
        self.assertEqual({n.get("eraldise_nr") for n in notice_a}, {1, 2})
        current_a = next(n for n in notice_a if n.get("eraldise_nr") == 1)
        self.assertFalse(current_a["arhiiv"])
        self.assertEqual(current_a["otsus"], "JAH")

    async def test_notice_query_does_not_crash_on_unhashable_source_fields(self):
        current = [{
            "id": {"unexpected": True},
            "properties": {
                "teatise_nr": {"unexpected": True},
                "eraldise_nr": [1],
                "too_kood": ["LR"],
            },
        }]

        async def fake_wfs(url, **_kwargs):
            return [] if "teatis_arhiiv" in url else current

        with patch("services.metsaregister._wfs_get", new=AsyncMock(side_effect=fake_wfs)):
            notices, unavailable = await query_teatised("78404:409:0113")

        self.assertEqual(len(notices), 1)
        self.assertEqual(unavailable, [])

    async def test_notice_query_marks_malformed_properties_incomplete(self):
        current = [{"id": "teatis.1", "properties": None}]

        async def fake_wfs(url, **_kwargs):
            return [] if "teatis_arhiiv" in url else current

        with patch("services.metsaregister._wfs_get", new=AsyncMock(side_effect=fake_wfs)):
            notices, unavailable = await query_teatised("78404:409:0113")

        self.assertEqual(notices, [])
        self.assertEqual(unavailable, ["metsaregister.teatis"])

    async def test_notice_query_reports_single_layer_failure_with_surviving_rows(self):
        current = [{"id": "teatis.1", "properties": {"teatise_nr": "A"}}]

        async def fake_wfs(url, **_kwargs):
            if "teatis_arhiiv" in url:
                raise MetsaregisterWFSError("archive unavailable")
            return current

        with patch("services.metsaregister._wfs_get", new=AsyncMock(side_effect=fake_wfs)):
            notices, unavailable = await query_teatised("78404:409:0113")

        self.assertEqual(len(notices), 1)
        self.assertEqual(unavailable, ["metsaregister.teatis_arhiiv"])

    async def test_notice_query_raises_when_both_layers_fail(self):
        with patch(
            "services.metsaregister._wfs_get",
            new=AsyncMock(side_effect=MetsaregisterWFSError("unavailable")),
        ):
            with self.assertRaises(MetsaregisterWFSError):
                await query_teatised("78404:409:0113")

    async def test_stand_query_rejects_record_declared_for_another_parcel(self):
        features = [{
            "properties": {
                "id": 1,
                "katastri_nr": "78404:409:9999",
                "peapuuliik_kood": "MA",
                "tagavara_1_ha": 10,
                "pindala": 1,
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            with self.assertRaises(MetsaregisterWFSError):
                await query_eraldis("78404:409:0113")

    async def test_exact_duplicate_stands_do_not_double_area_or_stock(self):
        feature = {
            "id": "eraldis.1",
            "properties": {
                "id": 1,
                "katastri_nr": "78404:409:0113",
                "eraldise_nr": 1,
                "peapuuliik_kood": "MA",
                "tagavara_1_ha": 100,
                "boniteedi_kood": 2,
                "pindala": 1,
            },
        }

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=[feature, feature])):
            stands = await query_eraldis("78404:409:0113")

        self.assertEqual(len(stands), 1)

    async def test_damage_query_rejects_malformed_text_fields(self):
        features = [{
            "properties": {
                "eraldis_id": 1,
                "kahjustuse_tyyp": {"unexpected": True},
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            with self.assertRaises(MetsaregisterWFSError):
                await query_kahjustused(1)

    async def test_element_query_rejects_record_for_another_stand(self):
        features = [{
            "properties": {
                "eraldis_id": 2,
                "puuliik_kood": "MA",
                "tagavara": 50,
                "vanus": 60,
            },
        }]

        with patch("services.metsaregister._wfs_get", new=AsyncMock(return_value=features)):
            with self.assertRaises(MetsaregisterWFSError):
                await query_eraldis_element(1)


if __name__ == "__main__":
    unittest.main()

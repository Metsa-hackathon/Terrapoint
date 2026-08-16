import asyncio
import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from api import index as api
from services import kataster


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeInvalidJsonResponse(FakeResponse):
    def json(self):
        raise ValueError("invalid json")


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        return self.response


class SlowFakeAsyncClient(FakeAsyncClient):
    async def get(self, url):
        await kataster.asyncio.sleep(1)
        return self.response


class KatasterDataTests(unittest.IsolatedAsyncioTestCase):
    async def test_land_valuation_metadata_normalizes_official_latest_assessment(self):
        response = FakeResponse({
            "status": "OK",
            "message": {
                "assessment": {
                    "cadastreId": "10501:001:0001",
                    "totalValue": 7073,
                    "assessmentYear": 2022,
                    "assessmentTime": "2025-12-17T14:24:41.453627",
                    "validFrom": "2025-12-17",
                    "validUntil": None,
                    "basis": "Alusandmete uuendamine",
                }
            },
        })

        with patch("services.kataster.httpx.AsyncClient", return_value=FakeAsyncClient(response)):
            result = await kataster.query_land_valuation_metadata("10501:001:0001")

        self.assertEqual(result, {
            "state": "available",
            "total_value": 7073,
            "assessment_year": 2022,
            "assessment_time": "2025-12-17",
            "valid_from": "2025-12-17",
            "valid_until": None,
            "basis": "Alusandmete uuendamine",
        })

    async def test_land_valuation_metadata_rejects_non_object_payload(self):
        with patch(
            "services.kataster.httpx.AsyncClient",
            return_value=FakeAsyncClient(FakeResponse([])),
        ):
            result = await kataster.query_land_valuation_metadata("10501:001:0001")

        self.assertIsNone(result)

    async def test_land_valuation_metadata_enforces_total_deadline(self):
        with (
            patch(
                "services.kataster.httpx.AsyncClient",
                return_value=SlowFakeAsyncClient(FakeResponse({})),
            ),
            patch("services.kataster.LAND_VALUATION_TIMEOUT_SECONDS", 0.01),
        ):
            result = await kataster.query_land_valuation_metadata("10501:001:0001")

        self.assertIsNone(result)

    async def test_query_kataster_attaches_metadata_only_to_matching_value(self):
        feature = {
            "properties": {
                "tunnus": "10501:001:0001",
                "pindala": 47_489,
                "maks_hind": 7073,
            },
            "geometry": {"type": "Polygon", "coordinates": []},
        }
        matching = {
            "state": "available",
            "total_value": 7073,
            "assessment_year": 2022,
            "assessment_time": "2025-12-17",
            "valid_from": "2025-12-17",
            "valid_until": None,
            "basis": "Alusandmete uuendamine",
        }

        with (
            patch("services.kataster._wfs_get", new=AsyncMock(return_value=[feature])),
            patch(
                "services.kataster.query_land_valuation_metadata",
                new=AsyncMock(return_value=matching),
            ),
        ):
            result = await kataster.query_kataster(
                "10501:001:0001",
                include_valuation_metadata=True,
            )

        self.assertEqual(result["maks_hind_meta"]["assessment_year"], 2022)
        self.assertEqual(result["maks_hind_meta"]["valid_from"], "2025-12-17")

        mismatching = {**matching, "total_value": 8000}
        with (
            patch("services.kataster._wfs_get", new=AsyncMock(return_value=[feature])),
            patch(
                "services.kataster.query_land_valuation_metadata",
                new=AsyncMock(return_value=mismatching),
            ),
        ):
            result = await kataster.query_kataster(
                "10501:001:0001",
                include_valuation_metadata=True,
            )

        self.assertEqual(result["maks_hind"], 7073)
        self.assertEqual(result["maks_hind_meta"], {"state": "unavailable"})

    async def test_query_kataster_skips_valuation_metadata_by_default(self):
        feature = {
            "properties": {
                "tunnus": "10501:001:0001",
                "pindala": 47_489,
                "maks_hind": 7073,
            },
            "geometry": {"type": "Polygon", "coordinates": []},
        }

        with (
            patch("services.kataster._wfs_get", new=AsyncMock(return_value=[feature])),
            patch(
                "services.kataster.query_land_valuation_metadata",
                new=AsyncMock(),
            ) as valuation_query,
        ):
            result = await kataster.query_kataster("10501:001:0001")

        valuation_query.assert_not_awaited()
        self.assertEqual(result["maks_hind"], 7073)
        self.assertEqual(result["maks_hind_meta"], {"state": "unavailable"})

    async def test_query_kataster_retry_policy_fits_api_deadline(self):
        with patch(
            "services.kataster._wfs_get",
            new=AsyncMock(return_value=[]),
        ) as wfs_get:
            self.assertIsNone(await kataster.query_kataster("10501:001:0001"))

        self.assertEqual(
            wfs_get.await_args.kwargs,
            {
                "timeout": kataster.KATASTER_WFS_ATTEMPT_TIMEOUT_SECONDS,
                "retries": kataster.KATASTER_WFS_RETRIES,
            },
        )

    async def test_wfs_get_rejects_malformed_features_container(self):
        response = FakeResponse({"features": None})

        with patch("services.kataster.httpx.AsyncClient", return_value=FakeAsyncClient(response)):
            with self.assertRaises(kataster.KatasterWFSError):
                await kataster._wfs_get("https://example.test/wfs", retries=0)

    async def test_wfs_get_rejects_non_object_feature(self):
        response = FakeResponse({"features": [None]})

        with patch("services.kataster.httpx.AsyncClient", return_value=FakeAsyncClient(response)):
            with self.assertRaises(kataster.KatasterWFSError):
                await kataster._wfs_get("https://example.test/wfs", retries=0)

    async def test_wfs_get_normalizes_invalid_json(self):
        response = FakeInvalidJsonResponse(None)

        with patch("services.kataster.httpx.AsyncClient", return_value=FakeAsyncClient(response)):
            with self.assertRaises(kataster.KatasterWFSError):
                await kataster._wfs_get("https://example.test/wfs", retries=0)

    async def test_resolve_kataster_by_adob_id_retries_schema_without_tunnus(self):
        malformed = [{"properties": {"adob_id": 11006012, "l_aadress": "Taali metskond 19"}}]
        complete = [{"properties": {"adob_id": 11006012, "tunnus": "80802:001:0615"}}]

        with (
            patch(
                "services.kataster._wfs_get",
                new=AsyncMock(side_effect=[malformed, complete]),
            ) as wfs_get,
            patch("services.kataster.asyncio.sleep", new=AsyncMock()) as sleep,
        ):
            result = await kataster.resolve_kataster_by_adob_id(11006012)

        self.assertEqual(result, "80802:001:0615")
        self.assertEqual(wfs_get.await_count, 2)
        sleep.assert_awaited_once()
        query = parse_qs(urlparse(wfs_get.await_args_list[0].args[0]).query)
        self.assertEqual(query["CQL_FILTER"], ["adob_id=11006012"])
        self.assertEqual(query["propertyName"], ["adob_id,tunnus"])
        self.assertEqual(query["count"], ["1"])

    async def test_resolve_kataster_by_adob_id_retries_transient_wfs_failure(self):
        complete = [{"properties": {"adob_id": 11006012, "tunnus": "80802:001:0615"}}]

        with (
            patch(
                "services.kataster._wfs_get",
                new=AsyncMock(side_effect=[kataster.KatasterWFSError("transient"), complete]),
            ) as wfs_get,
            patch("services.kataster.asyncio.sleep", new=AsyncMock()) as sleep,
        ):
            result = await kataster.resolve_kataster_by_adob_id(11006012)

        self.assertEqual(result, "80802:001:0615")
        self.assertEqual(wfs_get.await_count, 2)
        sleep.assert_awaited_once()

    async def test_resolve_kataster_by_adob_id_exhausts_malformed_schema(self):
        malformed = [{"properties": {"adob_id": 11006012}}]

        with (
            patch("services.kataster._wfs_get", new=AsyncMock(return_value=malformed)) as wfs_get,
            patch("services.kataster.asyncio.sleep", new=AsyncMock()) as sleep,
        ):
            with self.assertRaises(kataster.KatasterWFSError):
                await kataster.resolve_kataster_by_adob_id(11006012, attempts=3)

        self.assertEqual(wfs_get.await_count, 3)
        self.assertEqual(sleep.await_count, 2)

    async def test_resolve_kataster_by_adob_id_enforces_total_deadline(self):
        async def slow_wfs(*args, **kwargs):
            await kataster.asyncio.sleep(1)
            return []

        with (
            patch("services.kataster._wfs_get", new=AsyncMock(side_effect=slow_wfs)),
            patch("services.kataster.ADOB_RESOLVE_DEADLINE_SECONDS", 0.01),
        ):
            with self.assertRaises(kataster.KatasterWFSError):
                await kataster.resolve_kataster_by_adob_id(11006012)


class KatasterApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def test_cadastral_object_returns_resolved_identifier(self):
        with patch(
            "api.index.resolve_kataster_by_adob_id",
            new=AsyncMock(return_value="80802:001:0615"),
        ):
            response = self.client.get("/api/cadastre/objects/11006012")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"katastri_nr": "80802:001:0615"})

    def test_cadastral_object_rejects_out_of_range_identifier(self):
        response = self.client.get("/api/cadastre/objects/-1")

        self.assertEqual(response.status_code, 400)

    def test_cadastral_object_rejects_non_numeric_identifier(self):
        response = self.client.get("/api/cadastre/objects/not-a-number")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Vigane katastriobjekti tunnus."})

    def test_cadastral_object_returns_not_found(self):
        with patch(
            "api.index.resolve_kataster_by_adob_id",
            new=AsyncMock(return_value=None),
        ):
            response = self.client.get("/api/cadastre/objects/11006012")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Katastriobjekti ei leitud."})

    def test_cadastral_object_maps_upstream_failure_to_502(self):
        with patch(
            "api.index.resolve_kataster_by_adob_id",
            new=AsyncMock(side_effect=kataster.KatasterWFSError("malformed")),
        ):
            response = self.client.get("/api/cadastre/objects/11006012")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"error": "Katastri andmeallikas ei vasta. Proovi uuesti."})

    def test_query_kataster_rejects_an_upstream_record_for_another_parcel(self):
        feature = {
            "properties": {
                "tunnus": "10501:001:9999",
                "pindala": 10_000,
            },
            "geometry": {"type": "Polygon", "coordinates": []},
        }

        with patch("services.kataster._wfs_get", new=AsyncMock(return_value=[feature])):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(kataster.query_kataster("10501:001:0001"))

        self.assertEqual(context.exception.status_code, 502)

    def test_query_kataster_rejects_conflicting_duplicate_records(self):
        feature = {
            "properties": {
                "tunnus": "10501:001:0001",
                "pindala": 10_000,
                "maks_hind": 1000,
            },
            "geometry": {"type": "Polygon", "coordinates": []},
        }
        conflict = {
            **feature,
            "properties": {**feature["properties"], "pindala": 20_000},
        }

        with patch(
            "services.kataster._wfs_get",
            new=AsyncMock(return_value=[feature, conflict]),
        ):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(kataster.query_kataster("10501:001:0001"))

        self.assertEqual(context.exception.status_code, 502)

    def test_query_kataster_accepts_an_exact_duplicate_only_once(self):
        feature = {
            "properties": {
                "tunnus": "10501:001:0001",
                "pindala": 10_000,
                "maks_hind": 1000,
            },
            "geometry": {"type": "Polygon", "coordinates": []},
        }

        with patch(
            "services.kataster._wfs_get",
            new=AsyncMock(return_value=[feature, feature]),
        ):
            result = asyncio.run(kataster.query_kataster("10501:001:0001"))

        self.assertEqual(result["pindala_ha"], 1)
        self.assertEqual(result["maks_hind"], 1000)

    def test_query_kataster_rejects_malformed_official_text(self):
        feature = {
            "properties": {
                "tunnus": "10501:001:0001",
                "pindala": 10_000,
                "l_aadress": {"unexpected": True},
            },
            "geometry": {"type": "Polygon", "coordinates": []},
        }

        with patch("services.kataster._wfs_get", new=AsyncMock(return_value=[feature])):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(kataster.query_kataster("10501:001:0001"))

        self.assertEqual(context.exception.status_code, 502)

    def test_query_kataster_rejects_invalid_official_taxable_value(self):
        for value in ("not-a-number", -1, float("nan"), True):
            with self.subTest(value=value):
                feature = {
                    "properties": {
                        "tunnus": "10501:001:0001",
                        "pindala": 10_000,
                        "maks_hind": value,
                    },
                    "geometry": {"type": "Polygon", "coordinates": []},
                }

                with patch("services.kataster._wfs_get", new=AsyncMock(return_value=[feature])):
                    with self.assertRaises(HTTPException) as context:
                        asyncio.run(kataster.query_kataster("10501:001:0001"))

                self.assertEqual(context.exception.status_code, 502)

    def test_query_kataster_preserves_missing_and_zero_taxable_values(self):
        for value in (None, 0):
            with self.subTest(value=value):
                feature = {
                    "properties": {
                        "tunnus": "10501:001:0001",
                        "pindala": 10_000,
                        "maks_hind": value,
                    },
                    "geometry": {"type": "Polygon", "coordinates": []},
                }

                with patch("services.kataster._wfs_get", new=AsyncMock(return_value=[feature])):
                    result = asyncio.run(kataster.query_kataster("10501:001:0001"))

                self.assertEqual(result["maks_hind"], value)

    def test_query_kataster_rejects_invalid_official_area(self):
        for area in ("not-a-number", -1, 0, float("nan"), True):
            with self.subTest(area=area):
                feature = {
                    "properties": {
                        "tunnus": "10501:001:0001",
                        "pindala": area,
                    },
                    "geometry": {"type": "Polygon", "coordinates": []},
                }

                with patch("services.kataster._wfs_get", new=AsyncMock(return_value=[feature])):
                    with self.assertRaises(HTTPException) as context:
                        asyncio.run(kataster.query_kataster("10501:001:0001"))

                self.assertEqual(context.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()

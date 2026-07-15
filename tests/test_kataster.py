import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock, patch

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


class KatasterDataTests(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()

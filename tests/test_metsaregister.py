import unittest
from unittest.mock import AsyncMock, patch

from services import metsaregister
from services.metsaregister import MetsaregisterWFSError, query_eraldis


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
    async def test_wfs_get_keeps_successful_empty_response_distinct_from_failure(self):
        with patch("services.metsaregister.httpx.AsyncClient", return_value=FakeAsyncClient(FakeResponse())):
            features = await metsaregister._wfs_get("https://example.test/wfs", retries=0)

        self.assertEqual(features, [])

    async def test_wfs_get_raises_after_retryable_http_failure(self):
        with patch("services.metsaregister.httpx.AsyncClient", return_value=FakeAsyncClient(FakeResponse(503))):
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


if __name__ == "__main__":
    unittest.main()

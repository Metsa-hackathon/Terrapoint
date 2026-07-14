import unittest
from unittest.mock import patch

from services import kataster


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

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


if __name__ == "__main__":
    unittest.main()

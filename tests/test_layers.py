import unittest

from services.layers import MAX_FEATURES_PER_LAYER, _fetch_layer


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


if __name__ == "__main__":
    unittest.main()

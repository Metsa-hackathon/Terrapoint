import unittest

from api.index import ChatRequest, _check_rate_limit, _rate_limit_buckets


class SecurityBoundaryTests(unittest.TestCase):
    def setUp(self):
        _rate_limit_buckets.clear()

    def test_rate_limit_blocks_after_window_quota(self):
        for i in range(8):
            allowed, retry_after = _check_rate_limit("198.51.100.10", "chat", 8, 60, now=float(i))
            self.assertTrue(allowed)
            self.assertEqual(retry_after, 0)

        allowed, retry_after = _check_rate_limit("198.51.100.10", "chat", 8, 60, now=8.0)

        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_chat_request_rejects_oversized_message(self):
        with self.assertRaises(Exception):
            ChatRequest.model_validate({
                "kataster_nr": "78404:409:0113",
                "message": "x" * 601,
                "data": {"kataster": {"number": "78404:409:0113"}},
            })

    def test_chat_request_rejects_oversized_history(self):
        with self.assertRaises(Exception):
            ChatRequest.model_validate({
                "kataster_nr": "78404:409:0113",
                "message": "Kas raiuda?",
                "history": [{"role": "user", "content": "x"}] * 11,
                "data": {"kataster": {"number": "78404:409:0113"}},
            })


if __name__ == "__main__":
    unittest.main()

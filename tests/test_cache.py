import unittest

from api.cache import TTLCache


class TTLCacheTests(unittest.TestCase):
    def test_updating_existing_key_does_not_evict_another_entry(self):
        cache = TTLCache(max_entries=2)
        cache.set("first", 1)
        cache.set("second", 2)

        cache.set("second", 3)

        self.assertEqual(cache.get("first"), 1)
        self.assertEqual(cache.get("second"), 3)
        self.assertEqual(cache.size, 2)

    def test_capacity_must_be_positive(self):
        with self.assertRaises(ValueError):
            TTLCache(max_entries=0)


if __name__ == "__main__":
    unittest.main()

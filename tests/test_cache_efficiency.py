"""
Unit tests for caching and efficiency: Microsecond LRU cache, 0ms repeat latency, and eviction.
"""

import time
import unittest
from sloth_box.security import MicrosecondCache, fnv1a32


class TestCacheEfficiency(unittest.TestCase):
    def test_lru_cache_retrieval_and_latency(self):
        cache = MicrosecondCache(capacity=10)
        key = fnv1a32("instagram recipe paneer")

        data = {"keywords": ["paneer", "recipe"], "results_count": 5}
        cache.set(key, data)

        # Retrieval latency test
        t0 = time.perf_counter()
        retrieved = cache.get(key)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000

        self.assertEqual(retrieved, data)
        # Verify sub-millisecond (microsecond) retrieval
        self.assertLess(elapsed_us, 1000)

    def test_lru_eviction(self):
        cache = MicrosecondCache(capacity=3)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")

        # Access k1 to make k2 the least recently used
        _ = cache.get("k1")

        # Add k4, causing k2 to be evicted
        cache.set("k4", "v4")

        self.assertIsNotNone(cache.get("k1"))
        self.assertIsNone(cache.get("k2"))
        self.assertIsNotNone(cache.get("k3"))
        self.assertIsNotNone(cache.get("k4"))


if __name__ == "__main__":
    unittest.main()

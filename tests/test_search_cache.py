import asyncio
import json
import unittest
from unittest.mock import AsyncMock

from search_cache import WebSearchCache, _cacheable


class WebSearchCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_reuses_search_result_within_ttl(self):
        cache = WebSearchCache(ttl_seconds=90)
        search = AsyncMock(return_value=json.dumps({"sources": [{"url": "https://example.com"}]}))

        first = await cache.get_or_search("  free python courses  ", search)
        second = await cache.get_or_search("FREE   PYTHON COURSES", search)

        self.assertEqual(first, second)
        search.assert_awaited_once()

    async def test_expired_result_is_refetched(self):
        now = [100.0]
        cache = WebSearchCache(ttl_seconds=5, clock=lambda: now[0])
        search = AsyncMock(side_effect=[
            json.dumps({"sources": [{"url": "https://example.com/1"}]}),
            json.dumps({"sources": [{"url": "https://example.com/2"}]}),
        ])

        await cache.get_or_search("python tutorial", search)
        now[0] += 6
        result = await cache.get_or_search("python tutorial", search)

        self.assertIn("/2", result)
        self.assertEqual(search.await_count, 2)

    async def test_freshness_sensitive_and_personal_queries_bypass_cache(self):
        self.assertFalse(_cacheable("latest AI news"))
        self.assertFalse(_cacheable("weather today"))
        self.assertFalse(_cacheable("my account details"))
        self.assertFalse(_cacheable("contact me at user@example.com"))

        cache = WebSearchCache()
        search = AsyncMock(return_value=json.dumps({"sources": [{"url": "https://example.com"}]}))
        await cache.get_or_search("latest AI news", search)
        await cache.get_or_search("latest AI news", search)
        self.assertEqual(search.await_count, 2)

    async def test_empty_or_invalid_results_are_not_cached(self):
        cache = WebSearchCache()
        search = AsyncMock(return_value=json.dumps({"sources": []}))
        await cache.get_or_search("python tutorials", search)
        await cache.get_or_search("python tutorials", search)
        self.assertEqual(search.await_count, 2)

    async def test_concurrent_identical_queries_are_coalesced(self):
        cache = WebSearchCache()
        count = [0]

        async def search(query):
            count[0] += 1
            await asyncio.sleep(0.01)
            return json.dumps({"sources": [{"url": "https://example.com"}]})

        results = await asyncio.gather(*[
            cache.get_or_search("public python tutorial", search)
            for _ in range(5)
        ])

        self.assertEqual(len(set(results)), 1)
        self.assertEqual(count[0], 1)


if __name__ == "__main__":
    unittest.main()

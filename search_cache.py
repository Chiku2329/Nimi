"""Short-lived cache for public web-search results only.

No conversation history or personal memory is stored here. Cache keys are hashed,
freshness-sensitive or personal-looking queries bypass caching, and entries expire
quickly in process memory.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections import OrderedDict
from typing import Awaitable, Callable

CACHE_TTL_SECONDS = 90.0
CACHE_MAX_ENTRIES = 128

_FRESHNESS_RE = re.compile(
    r"\\b(latest|today|now|currently|current|live|breaking|right now|"
    r"this morning|tonight|price|prices|stock|exchange rate|forecast)\\b",
    re.IGNORECASE,
)
_PERSONAL_RE = re.compile(
    r"\\b(my|mine|me|i|we|our|personal|private|account|address|"
    r"medical|health|bank|password|passport)\\b|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}|"
    r"(?<!\\d)(?:\\+?\\d[ .()-]?){8,}(?!\\d)",
    re.IGNORECASE,
)


def _normalized_query(query: str) -> str:
    return " ".join(query.casefold().split())


def _cacheable(query: str) -> bool:
    normalized = _normalized_query(query)
    return bool(normalized) and not _FRESHNESS_RE.search(normalized) and not _PERSONAL_RE.search(query)


def _key(query: str) -> str:
    normalized = _normalized_query(query)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class WebSearchCache:
    """Bounded TTL cache with per-query request coalescing."""

    def __init__(
        self,
        ttl_seconds: float = CACHE_TTL_SECONDS,
        max_entries: int = CACHE_MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.ttl_seconds = max(0.0, float(ttl_seconds))
        self.max_entries = max(1, int(max_entries))
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    def _read(self, key: str) -> str | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, result = entry
        if expires_at <= self._clock():
            self._entries.pop(key, None)
            return None
        self._entries.move_to_end(key)
        return result

    def _store(self, key: str, result: str) -> None:
        self._entries[key] = (self._clock() + self.ttl_seconds, result)
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    async def get_or_search(
        self,
        query: str,
        search: Callable[[str], Awaitable[str]],
    ) -> str:
        if not isinstance(query, str) or not _cacheable(query) or self.ttl_seconds <= 0:
            return await search(query)

        key = _key(query)
        async with self._guard:
            cached = self._read(key)
            if cached is not None:
                return cached
            lock = self._locks.setdefault(key, asyncio.Lock())

        async with lock:
            async with self._guard:
                cached = self._read(key)
                if cached is not None:
                    return cached

            result = await search(query)
            try:
                parsed = json.loads(result)
                has_sources = isinstance(parsed, dict) and bool(parsed.get("sources"))
            except (TypeError, ValueError):
                has_sources = False

            if has_sources:
                async with self._guard:
                    self._store(key, result)
            return result

        # The per-query lock is removed by the lock-owner cleanup below.

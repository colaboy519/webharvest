"""
Disk-based response cache — avoids re-fetching pages within the TTL window.

Uses diskcache (SQLite-backed). Zero infrastructure, works out of the box.
Cache key = normalized URL. Stores raw HTML + headers so content extraction
can be re-run with different settings without re-fetching.
"""

from __future__ import annotations

import hashlib
from typing import Any

import diskcache

from webharvest.config import settings


class ResponseCache:
    def __init__(
        self,
        directory: str | None = None,
        ttl: int | None = None,
    ):
        self._dir = directory or settings.cache_dir
        self._ttl = ttl or settings.cache_ttl
        self._cache = diskcache.Cache(self._dir)

    @staticmethod
    def _key(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def get(self, url: str) -> dict[str, Any] | None:
        return self._cache.get(self._key(url))

    def set(self, url: str, data: dict[str, Any]) -> None:
        self._cache.set(self._key(url), data, expire=self._ttl)

    def clear(self) -> None:
        self._cache.clear()

    def close(self) -> None:
        self._cache.close()

"""
FastAPI dependency injection — shared resources across routes.
"""

from __future__ import annotations

from functools import lru_cache

import httpx

from webharvest.cache.store import ResponseCache
from webharvest.config import Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


_cache: ResponseCache | None = None
_client: httpx.AsyncClient | None = None


async def get_cache() -> ResponseCache:
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(http2=True, follow_redirects=True, timeout=30)
    return _client


async def shutdown():
    global _cache, _client
    if _cache:
        _cache.close()
        _cache = None
    if _client:
        await _client.aclose()
        _client = None

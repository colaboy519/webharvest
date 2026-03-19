"""
Async HTTP fetcher — the primary way WebHarvest downloads pages.

Features:
  - Async via httpx with HTTP/2 support
  - Automatic retry on transient errors (see retry.py)
  - User-Agent rotation (see useragent.py)
  - Proxy rotation (see proxy.py)
  - Response caching (see cache/store.py)

Returns a FetchResult dataclass with status, headers, HTML, and timing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from webharvest.config import settings
from webharvest.fetch.retry import fetch_retry, RETRYABLE_STATUS
from webharvest.fetch.useragent import random_ua
from webharvest.fetch.proxy import next_proxy


@dataclass
class FetchResult:
    status_code: int
    headers: dict[str, str]
    html: str
    final_url: str
    elapsed_ms: int


@fetch_retry
async def fetch_url(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout_ms: int = 30_000,
    headers: dict[str, str] | None = None,
) -> FetchResult:
    """Fetch a URL and return its HTML content."""
    request_headers = {
        "User-Agent": random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        request_headers.update(headers)

    proxy = next_proxy()
    timeout = httpx.Timeout(timeout_ms / 1000)

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            http2=True,
            follow_redirects=True,
            timeout=timeout,
            proxy=proxy,
            verify=settings.verify_ssl,
        )

    try:
        start = time.perf_counter()
        response = await client.get(str(url), headers=request_headers)
        elapsed = int((time.perf_counter() - start) * 1000)

        if response.status_code in RETRYABLE_STATUS:
            response.raise_for_status()

        return FetchResult(
            status_code=response.status_code,
            headers=dict(response.headers),
            html=response.text,
            final_url=str(response.url),
            elapsed_ms=elapsed,
        )
    finally:
        if owns_client:
            await client.aclose()

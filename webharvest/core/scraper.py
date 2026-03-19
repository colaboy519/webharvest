"""
Single-page scraper — the main orchestrator.

Pipeline:  Fetch → Extract Content → Extract Metadata → Build Result

Fetch modes:
  - "httpx"   — standard HTTP client (default, fastest)
  - "browser" — Playwright for JS-rendered pages
  - "stealth" — curl_cffi TLS impersonation (anti-bot)
  - "smart"   — auto-escalation: httpx → stealth → stealth browser → CAPTCHA

This is the function everything else calls:
  - CLI `webharvest scrape <url>`
  - API `POST /v1/scrape`
  - Crawler (calls scrape per page)
  - Search (calls scrape per result)
"""

from __future__ import annotations

import logging

import httpx

from webharvest.fetch.http_client import fetch_url, FetchResult
from webharvest.fetch.browser import fetch_with_browser
from webharvest.cache.store import ResponseCache
from webharvest.core.content import extract_content, extract_metadata, extract_links
from webharvest.models.requests import ScrapeRequest
from webharvest.models.responses import ScrapeResult, PageMetadata

logger = logging.getLogger("webharvest.scraper")


async def scrape(
    request: ScrapeRequest,
    *,
    client: httpx.AsyncClient | None = None,
    cache: ResponseCache | None = None,
) -> ScrapeResult:
    """
    Scrape a single URL and return clean, agent-friendly content.

    Args:
        request: What to scrape and how.
        client:  Reusable httpx client (optional, for connection pooling).
        cache:   Response cache (optional).

    Returns:
        ScrapeResult with markdown, HTML, links, and metadata as requested.
    """
    url = str(request.url)

    # ── Check cache ──────────────────────────────────────────
    if cache:
        cached = cache.get(url)
        if cached:
            logger.info("Cache hit: %s", url)
            return _build_result(
                url=url,
                raw_html=cached["html"],
                final_url=cached["final_url"],
                status_code=cached["status_code"],
                formats=request.formats,
                only_main_content=request.only_main_content,
                include_tags=request.include_tags,
                exclude_tags=request.exclude_tags,
            )

    # ── Fetch (select mode) ──────────────────────────────────
    mode = request.fetch_mode
    if request.use_browser:
        mode = "browser"  # backward compat

    try:
        if mode == "smart":
            from webharvest.fetch.smart import smart_fetch
            result = await smart_fetch(
                url, timeout_ms=request.timeout_ms, headers=request.headers or None,
            )
        elif mode == "stealth":
            from webharvest.fetch.stealth import fetch_stealth
            result = await fetch_stealth(
                url, timeout_ms=request.timeout_ms, headers=request.headers or None,
            )
        elif mode == "browser":
            result = await fetch_with_browser(
                url, wait_for=request.wait_for, timeout_ms=request.timeout_ms,
            )
        else:
            result = await fetch_url(
                url, client=client, timeout_ms=request.timeout_ms,
                headers=request.headers or None,
            )
    except Exception as e:
        logger.error("Fetch failed for %s: %s", url, e)
        return ScrapeResult(success=False, url=url, error=str(e))

    # ── Cache response ───────────────────────────────────────
    if cache:
        cache.set(url, {
            "html": result.html,
            "final_url": result.final_url,
            "status_code": result.status_code,
        })

    return _build_result(
        url=url,
        raw_html=result.html,
        final_url=result.final_url,
        status_code=result.status_code,
        formats=request.formats,
        only_main_content=request.only_main_content,
        include_tags=request.include_tags,
        exclude_tags=request.exclude_tags,
    )


def _build_result(
    *,
    url: str,
    raw_html: str,
    final_url: str,
    status_code: int,
    formats: list[str],
    only_main_content: bool,
    include_tags: list[str],
    exclude_tags: list[str],
) -> ScrapeResult:
    """Build the response with only the requested formats."""

    clean_html, markdown = extract_content(
        raw_html,
        final_url,
        only_main_content=only_main_content,
        include_tags=include_tags or None,
        exclude_tags=exclude_tags or None,
    )

    metadata = extract_metadata(raw_html, final_url)
    metadata.status_code = status_code

    return ScrapeResult(
        success=True,
        url=final_url,
        markdown=markdown if "markdown" in formats else None,
        html=clean_html if "html" in formats else None,
        raw_html=raw_html if "raw_html" in formats else None,
        links=extract_links(raw_html, final_url) if "links" in formats else None,
        metadata=metadata if "metadata" in formats else metadata,
    )

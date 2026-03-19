"""
Search + Scrape — web search then scrape each result page.

Uses DuckDuckGo as the default search backend (no API key needed).
Install with: pip install webharvest[search]

Architecture: pluggable backends via the SearchBackend protocol.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

import httpx

from webharvest.core.scraper import scrape
from webharvest.models.requests import SearchRequest, ScrapeRequest
from webharvest.models.responses import SearchResult, SearchResultItem, ScrapeResult

logger = logging.getLogger("webharvest.searcher")


class SearchBackend(Protocol):
    """Interface for search providers."""

    def search(self, query: str, num_results: int) -> list[dict]:
        """Return list of {"title": str, "url": str, "snippet": str}."""
        ...


class DuckDuckGoBackend:
    """DuckDuckGo search — no API key required."""

    def search(self, query: str, num_results: int) -> list[dict]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            raise ImportError(
                "duckduckgo-search is not installed. Run: pip install webharvest[search]"
            )
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        return [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in results
        ]


async def search_and_scrape(
    request: SearchRequest,
    *,
    backend: SearchBackend | None = None,
) -> SearchResult:
    """Search the web, then scrape each result page."""
    backend = backend or DuckDuckGoBackend()

    try:
        raw_results = backend.search(request.query, request.num_results)
    except Exception as e:
        return SearchResult(success=False, query=request.query, error=str(e))

    # Scrape each result concurrently
    items: list[SearchResultItem] = []
    scrape_tasks = []

    async with httpx.AsyncClient(http2=True, follow_redirects=True, timeout=30) as client:
        for r in raw_results:
            if not r.get("url"):
                continue
            scrape_req = ScrapeRequest(url=r["url"], formats=["markdown", "metadata"])
            if request.scrape_options:
                scrape_req = request.scrape_options.model_copy(update={"url": r["url"]})
            scrape_tasks.append((r, scrape(scrape_req, client=client)))

        results = await asyncio.gather(
            *[task for _, task in scrape_tasks],
            return_exceptions=True,
        )

    for (r, _), scrape_result in zip(scrape_tasks, results):
        page = scrape_result if isinstance(scrape_result, ScrapeResult) else None
        items.append(SearchResultItem(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("snippet"),
            page=page,
        ))

    return SearchResult(success=True, query=request.query, results=items)

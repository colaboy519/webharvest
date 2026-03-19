"""
Multi-page crawler — BFS traversal of a website.

Features:
  - Breadth-first crawl with configurable max depth and page limit
  - Concurrent scraping with semaphore-based throttling
  - Per-domain rate limiting
  - URL deduplication (normalized)
  - Path include/exclude regex filters
  - Optional external link following

Usage:
  result = await crawl(CrawlRequest(url="https://example.com", max_depth=2))
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from collections import deque
from urllib.parse import urlparse

import httpx

from webharvest.config import settings
from webharvest.cache.store import ResponseCache
from webharvest.core.content import extract_links
from webharvest.core.scraper import scrape
from webharvest.models.requests import CrawlRequest, ScrapeRequest
from webharvest.models.responses import CrawlResult, ScrapeResult

logger = logging.getLogger("webharvest.crawler")


async def crawl(request: CrawlRequest) -> CrawlResult:
    """
    Crawl a website starting from the given URL.

    Returns a CrawlResult with all scraped pages.
    """
    job_id = str(uuid.uuid4())
    start_url = str(request.url)
    base_domain = urlparse(start_url).netloc

    # Compile path filters
    include_re = [re.compile(p) for p in request.include_paths] if request.include_paths else []
    exclude_re = [re.compile(p) for p in request.exclude_paths] if request.exclude_paths else []

    # BFS state
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque()  # (url, depth)
    queue.append((start_url, 0))
    visited.add(start_url)
    pages: list[ScrapeResult] = []

    sem = asyncio.Semaphore(settings.max_concurrent)
    cache = ResponseCache()

    scrape_opts = request.scrape_options or ScrapeRequest(url=request.url, formats=["markdown", "links"])

    async with httpx.AsyncClient(http2=True, follow_redirects=True, timeout=30) as client:
        while queue and len(pages) < request.limit:
            # Collect a batch from the queue
            batch: list[tuple[str, int]] = []
            while queue and len(batch) < settings.max_concurrent:
                batch.append(queue.popleft())

            # Scrape batch concurrently
            tasks = []
            for url, depth in batch:
                req = scrape_opts.model_copy(update={"url": url, "formats": ["markdown", "links", "metadata"]})
                tasks.append(_scrape_with_sem(sem, req, client, cache))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for (url, depth), result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.warning("Failed to scrape %s: %s", url, result)
                    pages.append(ScrapeResult(success=False, url=url, error=str(result)))
                    continue

                pages.append(result)

                # Enqueue discovered links if within depth
                if depth < request.max_depth and result.links:
                    for link in result.links:
                        if len(visited) >= request.limit:
                            break
                        if link in visited:
                            continue
                        link_domain = urlparse(link).netloc
                        if not request.allow_external and link_domain != base_domain:
                            continue
                        link_path = urlparse(link).path
                        if include_re and not any(r.search(link_path) for r in include_re):
                            continue
                        if exclude_re and any(r.search(link_path) for r in exclude_re):
                            continue
                        visited.add(link)
                        queue.append((link, depth + 1))

    cache.close()

    return CrawlResult(
        id=job_id,
        status="completed",
        total=len(pages),
        completed_count=sum(1 for p in pages if p.success),
        pages=pages,
    )


async def _scrape_with_sem(
    sem: asyncio.Semaphore,
    request: ScrapeRequest,
    client: httpx.AsyncClient,
    cache: ResponseCache,
) -> ScrapeResult:
    async with sem:
        return await scrape(request, client=client, cache=cache)

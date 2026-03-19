"""
Playwright-based fetcher — for JavaScript-rendered pages.

This is OPTIONAL. Install with: pip install webharvest[browser]
Then run: playwright install chromium

Use when:
  - The page loads content dynamically via JS (SPAs, React, etc.)
  - You need to wait for a specific element before capturing
  - You need to interact with the page (click, scroll, type)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from webharvest.fetch.http_client import FetchResult
from webharvest.fetch.useragent import random_ua


async def fetch_with_browser(
    url: str,
    *,
    headless: bool = True,
    wait_for: str | None = None,
    timeout_ms: int = 30_000,
) -> FetchResult:
    """Render a page with Playwright and return the fully-rendered HTML."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError(
            "Playwright is not installed. Run: pip install webharvest[browser] && playwright install chromium"
        )

    start = time.perf_counter()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=random_ua())
        page = await context.new_page()

        await page.goto(str(url), timeout=timeout_ms, wait_until="networkidle")

        if wait_for:
            if wait_for.isdigit():
                await page.wait_for_timeout(int(wait_for))
            else:
                await page.wait_for_selector(wait_for, timeout=timeout_ms)

        html = await page.content()
        final_url = page.url
        status = 200  # Playwright doesn't expose status easily

        await browser.close()

    elapsed = int((time.perf_counter() - start) * 1000)

    return FetchResult(
        status_code=status,
        headers={},
        html=html,
        final_url=final_url,
        elapsed_ms=elapsed,
    )

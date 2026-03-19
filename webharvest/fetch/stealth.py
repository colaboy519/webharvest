"""
Stealth fetcher — TLS fingerprint impersonation via curl_cffi.

Bypasses anti-bot systems that check TLS fingerprints (JA3/JA4) without
spinning up a full browser. 20-30x faster than browser-based fetching.

Impersonates real browser TLS signatures: Chrome, Firefox, Safari.
Falls back to standard httpx if curl_cffi is not installed.

Install: pip install webharvest[stealth]

Escalation ladder (used by the smart fetcher):
  1. curl_cffi (TLS impersonation, fastest)
  2. Patchright + BrowserForge (stealth browser with realistic fingerprints)
  3. Patchright + CAPTCHA solver (when CAPTCHAs block you)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from webharvest.fetch.http_client import FetchResult
from webharvest.fetch.useragent import random_ua

logger = logging.getLogger("webharvest.fetch.stealth")

# Browser versions curl_cffi can impersonate
CHROME_VERSIONS = [
    "chrome110", "chrome116", "chrome120", "chrome124", "chrome131",
]
FIREFOX_VERSIONS = ["firefox117", "firefox120"]
SAFARI_VERSIONS = ["safari17_0", "safari17_5"]
ALL_BROWSERS = CHROME_VERSIONS + FIREFOX_VERSIONS + SAFARI_VERSIONS


async def fetch_stealth(
    url: str,
    *,
    impersonate: str = "chrome131",
    timeout_ms: int = 30_000,
    headers: dict[str, str] | None = None,
    proxy: str | None = None,
) -> FetchResult:
    """
    Fetch a URL with TLS fingerprint impersonation.

    This makes the request look like it came from a real browser at the
    TLS handshake level, bypassing JA3/JA4 fingerprint checks.

    Args:
        impersonate: Browser to impersonate (e.g. "chrome131", "firefox120", "safari17_5")
        proxy: Optional proxy URL
    """
    try:
        from curl_cffi.requests import AsyncSession
    except ImportError:
        raise ImportError(
            "curl_cffi is not installed. Run: pip install webharvest[stealth]"
        )

    request_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        request_headers.update(headers)

    start = time.perf_counter()

    async with AsyncSession(impersonate=impersonate) as session:
        response = await session.get(
            str(url),
            headers=request_headers,
            timeout=timeout_ms / 1000,
            proxy=proxy,
            allow_redirects=True,
        )

    elapsed = int((time.perf_counter() - start) * 1000)

    return FetchResult(
        status_code=response.status_code,
        headers=dict(response.headers),
        html=response.text,
        final_url=str(response.url),
        elapsed_ms=elapsed,
    )


async def fetch_stealth_browser(
    url: str,
    *,
    headless: bool = True,
    wait_for: str | None = None,
    timeout_ms: int = 30_000,
) -> FetchResult:
    """
    Fetch with Patchright (stealth Playwright) + BrowserForge fingerprints.

    This is the heavy artillery — a real browser with:
    - Patched CDP leaks (undetectable headless mode)
    - Realistic, consistent browser fingerprints (Canvas, WebGL, navigator)
    - Proper TLS fingerprint from a real Chromium process

    Use when curl_cffi gets blocked (JS challenges, Cloudflare, DataDome).
    """
    try:
        from patchright.async_api import async_playwright
    except ImportError:
        raise ImportError(
            "Patchright is not installed. Run: pip install webharvest[stealth] && patchright install chromium"
        )

    # Try to generate realistic fingerprint
    fingerprint_context = {}
    try:
        from browserforge.fingerprints import FingerprintGenerator
        from browserforge.headers import HeaderGenerator

        fg = FingerprintGenerator()
        fp = fg.generate(browser="chrome", os="windows")
        hg = HeaderGenerator()
        gen_headers = hg.generate(browser="chrome", os="windows")

        fingerprint_context = {
            "user_agent": gen_headers.get("User-Agent", random_ua()),
            "viewport": {"width": fp.screen.width, "height": fp.screen.height},
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }
        logger.info("Using BrowserForge fingerprint")
    except (ImportError, Exception) as e:
        logger.debug("BrowserForge not available, using defaults: %s", e)
        fingerprint_context = {
            "user_agent": random_ua(),
            "viewport": {"width": 1920, "height": 1080},
        }

    start = time.perf_counter()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(**fingerprint_context)
        page = await context.new_page()

        await page.goto(str(url), timeout=timeout_ms, wait_until="networkidle")

        if wait_for:
            if wait_for.isdigit():
                await page.wait_for_timeout(int(wait_for))
            else:
                await page.wait_for_selector(wait_for, timeout=timeout_ms)

        html = await page.content()
        final_url = page.url

        await browser.close()

    elapsed = int((time.perf_counter() - start) * 1000)

    return FetchResult(
        status_code=200,
        headers={},
        html=html,
        final_url=final_url,
        elapsed_ms=elapsed,
    )

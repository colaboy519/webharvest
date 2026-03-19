"""
Structured data extractor — pull specific fields from pages using CSS selectors.

Given a URL and a schema (field name → CSS selector + type), extracts
structured JSON data. No LLM needed — pure selector-based extraction.

Example schema:
    {
        "title":  {"selector": "h1.product-title", "type": "string"},
        "price":  {"selector": ".price", "type": "number"},
        "in_stock": {"selector": ".stock-status", "type": "boolean"}
    }

Usage:
    result = await extract(ExtractRequest(url="...", schema={...}))
"""

from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from webharvest.fetch.http_client import fetch_url
from webharvest.fetch.browser import fetch_with_browser
from webharvest.models.requests import ExtractRequest, SelectorField
from webharvest.models.responses import ExtractResult

logger = logging.getLogger("webharvest.extractor")


async def extract(
    request: ExtractRequest,
    *,
    client: httpx.AsyncClient | None = None,
) -> ExtractResult:
    """Extract structured data from a page using CSS selectors."""
    url = str(request.url)

    try:
        if request.use_browser:
            result = await fetch_with_browser(url, timeout_ms=request.timeout_ms)
        else:
            result = await fetch_url(url, client=client, timeout_ms=request.timeout_ms)
    except Exception as e:
        return ExtractResult(success=False, url=url, error=str(e))

    soup = BeautifulSoup(result.html, "lxml")
    data: dict = {}

    for field_name, field_spec in request.schema_.items():
        data[field_name] = _extract_field(soup, field_spec)

    return ExtractResult(success=True, url=url, data=data)


def _extract_field(soup: BeautifulSoup, spec: SelectorField):
    """Extract and cast a single field from the parsed HTML."""
    elements = soup.select(spec.selector)
    if not elements:
        return None

    if spec.type == "list":
        return [_get_value(el, spec.attribute) for el in elements]

    el = elements[0]
    raw = _get_value(el, spec.attribute)
    return _cast(raw, spec.type)


def _get_value(el, attribute: str | None) -> str | None:
    if attribute:
        return el.get(attribute)
    return el.get_text(strip=True)


def _cast(value: str | None, type_name: str):
    if value is None:
        return None
    try:
        if type_name == "number":
            # Strip currency symbols, commas
            cleaned = "".join(c for c in value if c.isdigit() or c in ".,-")
            return float(cleaned.replace(",", ""))
        elif type_name == "integer":
            cleaned = "".join(c for c in value if c.isdigit() or c == "-")
            return int(cleaned)
        elif type_name == "boolean":
            return value.lower() in ("true", "yes", "1", "in stock", "available")
        else:
            return value
    except (ValueError, TypeError):
        return value

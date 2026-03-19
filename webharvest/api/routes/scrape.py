"""
POST /v1/scrape — Scrape a single URL and return agent-friendly content.

Request body: ScrapeRequest (url, formats, only_main_content, use_browser, ...)
Response:     ScrapeResult  (markdown, html, links, metadata)
"""

from fastapi import APIRouter, Depends

from webharvest.core.scraper import scrape
from webharvest.models.requests import ScrapeRequest
from webharvest.models.responses import ScrapeResult
from webharvest.api.deps import get_client, get_cache

router = APIRouter()


@router.post("/v1/scrape", response_model=ScrapeResult)
async def scrape_url(request: ScrapeRequest):
    client = await get_client()
    cache = await get_cache()
    return await scrape(request, client=client, cache=cache)

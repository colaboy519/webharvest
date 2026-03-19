"""
POST /v1/search — Web search + scrape each result page.

Request body: SearchRequest (query, num_results)
Response:     SearchResult  (list of pages with markdown + metadata)
"""

from fastapi import APIRouter

from webharvest.core.searcher import search_and_scrape
from webharvest.models.requests import SearchRequest
from webharvest.models.responses import SearchResult

router = APIRouter()


@router.post("/v1/search", response_model=SearchResult)
async def search(request: SearchRequest):
    return await search_and_scrape(request)

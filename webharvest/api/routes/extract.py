"""
POST /v1/extract — Extract structured JSON data from a page using CSS selectors.

Request body: ExtractRequest (url, schema with CSS selectors)
Response:     ExtractResult  (data dict matching the schema)
"""

from fastapi import APIRouter

from webharvest.core.extractor import extract
from webharvest.models.requests import ExtractRequest
from webharvest.models.responses import ExtractResult

router = APIRouter()


@router.post("/v1/extract", response_model=ExtractResult)
async def extract_data(request: ExtractRequest):
    return await extract(request)

"""
POST /v1/crawl       — Start a crawl job (returns job ID)
GET  /v1/crawl/{id}  — Poll crawl job status

Crawl jobs run in the background. The POST returns immediately with an ID.
Poll the GET endpoint to check progress and retrieve results.
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from webharvest.core.crawler import crawl
from webharvest.models.requests import CrawlRequest
from webharvest.models.responses import CrawlResult

router = APIRouter()

# In-memory job store (fine for self-hosted single-process)
_jobs: dict[str, CrawlResult] = {}


@router.post("/v1/crawl")
async def start_crawl(request: CrawlRequest):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = CrawlResult(id=job_id, status="in_progress")

    async def _run():
        try:
            result = await crawl(request)
            result.id = job_id
            _jobs[job_id] = result
        except Exception as e:
            _jobs[job_id] = CrawlResult(id=job_id, status="failed", error=str(e))

    asyncio.create_task(_run())
    return {"id": job_id, "status": "in_progress"}


@router.get("/v1/crawl/{job_id}", response_model=CrawlResult)
async def get_crawl_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]

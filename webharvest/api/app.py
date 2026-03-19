"""
FastAPI application — REST API server for WebHarvest.

Endpoints:
  POST /v1/scrape          Scrape a single URL → markdown / HTML / JSON
  POST /v1/crawl           Start a crawl job (async)
  GET  /v1/crawl/{id}      Poll crawl job status
  POST /v1/extract         Extract structured data via CSS selectors
  POST /v1/search          Web search + scrape results
  POST /v1/agent           Run autonomous browser agent (LLM-driven)
  POST /v1/agent/extract   LLM-powered extraction (natural language)

Start with:  webharvest serve
  or:        uvicorn webharvest.api.app:create_app --factory --port 8787
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from webharvest.api.deps import shutdown
from webharvest.api.routes import scrape, crawl, extract, search, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="WebHarvest",
        description="Self-hosted web scraper — convert any URL to agent-friendly markdown, HTML, or structured JSON. Includes anti-bot bypass and autonomous browser agents.",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(scrape.router, tags=["Scrape"])
    app.include_router(crawl.router, tags=["Crawl"])
    app.include_router(extract.router, tags=["Extract"])
    app.include_router(search.router, tags=["Search"])
    app.include_router(agent.router, tags=["Agent"])

    return app

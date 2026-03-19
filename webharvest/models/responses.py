"""
Response models — define what each endpoint / function returns.

All responses follow a consistent envelope:
  { "success": bool, "data": ..., "error": str | None }
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  METADATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class PageMetadata(BaseModel):
    title: str | None = None
    description: str | None = None
    language: str | None = None
    og_image: str | None = None
    og_type: str | None = None
    og_site_name: str | None = None
    canonical_url: str | None = None
    status_code: int = 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCRAPE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ScrapeResult(BaseModel):
    success: bool = True
    url: str
    markdown: str | None = None
    html: str | None = None
    raw_html: str | None = None
    links: list[str] | None = None
    metadata: PageMetadata = Field(default_factory=PageMetadata)
    error: str | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CRAWL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class CrawlResult(BaseModel):
    id: str
    status: str = "in_progress"  # in_progress | completed | failed
    total: int = 0
    completed_count: int = 0
    pages: list[ScrapeResult] = []
    error: str | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXTRACT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ExtractResult(BaseModel):
    success: bool = True
    url: str
    data: dict = {}
    error: str | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SEARCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str | None = None
    page: ScrapeResult | None = None


class SearchResult(BaseModel):
    success: bool = True
    query: str
    results: list[SearchResultItem] = []
    error: str | None = None

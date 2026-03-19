"""
WebHarvest - Self-hosted web scraper for agent-friendly content.

FEATURES:
  - Scrape:   Convert any URL to clean markdown / HTML / JSON
  - Crawl:    Follow links across an entire site (BFS, depth-limited)
  - Extract:  Pull structured data using CSS/XPath selectors
  - Search:   Web search + scrape results in one call
  - Serve:    REST API server (FastAPI) for programmatic access

QUICK START:
  CLI:   webharvest scrape https://example.com
  API:   webharvest serve  →  POST http://localhost:8787/v1/scrape
  Code:  from webharvest.core.scraper import scrape
"""

__version__ = "0.1.0"

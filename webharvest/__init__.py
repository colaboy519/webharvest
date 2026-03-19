"""
WebHarvest — web scraper plugin that runs 100% locally.

pip install webharvest → runs on YOUR machine, no server, no cloud.

FEATURES:
  - Scrape:         Convert any URL to clean markdown / HTML / JSON
  - Crawl:          Follow links across an entire site (BFS, depth-limited)
  - Extract:        Pull structured data using CSS selectors
  - Search:         Web search + scrape results in one call
  - Agent:          LLM-driven autonomous browser (navigates, clicks, extracts)
  - Agent Extract:  Natural language data extraction (no selectors needed)
  - Anti-Bot:       TLS impersonation, stealth browser, CAPTCHA solving

QUICK START:
  CLI:   webharvest scrape https://example.com
  Code:  from webharvest.core.scraper import scrape
"""

__version__ = "0.3.0"

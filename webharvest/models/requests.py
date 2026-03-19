"""
Request models — define what callers send to each endpoint / function.

These Pydantic models are shared across the CLI, REST API, and Python API
so the contract is consistent everywhere.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCRAPE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ScrapeRequest(BaseModel):
    """Scrape a single URL and return clean content."""

    url: HttpUrl
    formats: list[str] = Field(
        default=["markdown"],
        description="Output formats: markdown, html, raw_html, links, metadata",
    )
    only_main_content: bool = Field(
        default=True,
        description="Use readability to extract main article content only",
    )
    include_tags: list[str] = Field(default=[], description="HTML tags to keep")
    exclude_tags: list[str] = Field(default=[], description="HTML tags to remove")
    use_browser: bool = Field(
        default=False, description="Render JavaScript via Playwright"
    )
    fetch_mode: str = Field(
        default="httpx",
        description=(
            "How to fetch the page:\n"
            "  httpx    — standard HTTP client (default, fastest)\n"
            "  browser  — Playwright for JS-rendered pages\n"
            "  stealth  — curl_cffi TLS impersonation (anti-bot)\n"
            "  smart    — auto-escalate: httpx → stealth → stealth browser"
        ),
    )
    wait_for: str | None = Field(
        default=None, description="CSS selector or ms to wait before capture (browser mode)"
    )
    timeout_ms: int = Field(default=30_000, description="Request timeout in milliseconds")
    headers: dict[str, str] = Field(default={}, description="Extra HTTP headers")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CRAWL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class CrawlRequest(BaseModel):
    """Crawl a website following links up to a given depth."""

    url: HttpUrl
    max_depth: int = Field(default=2, ge=0, le=10, description="Max link-follow depth")
    limit: int = Field(default=100, ge=1, le=10_000, description="Max pages to scrape")
    include_paths: list[str] = Field(
        default=[], description="Regex patterns — only crawl matching paths"
    )
    exclude_paths: list[str] = Field(
        default=[], description="Regex patterns — skip matching paths"
    )
    allow_external: bool = Field(default=False, description="Follow links to other domains")
    scrape_options: ScrapeRequest | None = Field(
        default=None, description="Override scrape settings for each page"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXTRACT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class SelectorField(BaseModel):
    """One field to extract from a page."""

    selector: str = Field(description="CSS selector to locate the element")
    attribute: str | None = Field(default=None, description="HTML attribute to read (default: text content)")
    type: str = Field(default="string", description="Cast to: string, number, integer, boolean, list")


class ExtractRequest(BaseModel):
    """Extract structured JSON from a page using CSS selectors."""

    url: HttpUrl
    schema_: dict[str, SelectorField] = Field(
        alias="schema",
        description="Map of field names → CSS selectors + types",
    )
    use_browser: bool = False
    timeout_ms: int = 30_000


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SEARCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class SearchRequest(BaseModel):
    """Search the web and scrape each result page."""

    query: str
    num_results: int = Field(default=5, ge=1, le=20)
    scrape_options: ScrapeRequest | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class AgentRequest(BaseModel):
    """Run an autonomous browser agent to complete a web task."""

    task: str = Field(description="Natural language task for the agent")
    llm_provider: str = Field(
        default="openai",
        description="LLM provider: openai, anthropic, google",
    )
    llm_model: str | None = Field(
        default=None, description="Model name (auto-selects if not set)"
    )
    headless: bool = Field(default=True, description="Run browser in headless mode")
    max_steps: int = Field(default=50, ge=1, le=200, description="Max agent steps")


class AgentExtractRequest(BaseModel):
    """LLM-powered extraction — describe what you want in plain English."""

    url: HttpUrl
    prompt: str = Field(
        description="What to extract, in natural language (e.g., 'product name, price, and rating')"
    )
    llm_provider: str = "openai"
    llm_model: str | None = None

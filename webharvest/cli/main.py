"""
CLI interface — human-friendly commands for all WebHarvest features.

Commands:
  webharvest scrape <url>           Scrape a single page → markdown
  webharvest crawl <url>            Crawl a website (BFS, depth-limited)
  webharvest extract <url>          Extract structured data with a JSON schema
  webharvest search <query>         Web search + scrape each result
  webharvest agent <task>           Run autonomous browser agent (LLM-driven)
  webharvest agent-extract <url>    LLM-powered extraction (natural language)
  webharvest serve                  Start the REST API server

Examples:
  webharvest scrape https://example.com
  webharvest scrape https://example.com --format json --mode stealth
  webharvest scrape https://protected-site.com --mode smart
  webharvest crawl https://docs.python.org --depth 2 --limit 50
  webharvest extract https://shop.com/product --schema schema.json
  webharvest search "python web scraping" --num 5
  webharvest agent "Go to HN and get the top 5 stories"
  webharvest agent-extract https://example.com/product --prompt "name, price, rating"
  webharvest serve --port 8787
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="webharvest",
    help="Self-hosted web scraper — convert any URL to agent-friendly content.\n\nIncludes anti-bot bypass and autonomous browser agents.",
    no_args_is_help=True,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCRAPE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command()
def scrape(
    url: str = typer.Argument(help="URL to scrape"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output: markdown, html, json, raw_html"),
    mode: str = typer.Option(
        "httpx", "--mode", "-m",
        help="Fetch mode: httpx (default), browser (JS), stealth (anti-bot), smart (auto-escalate)",
    ),
    browser: bool = typer.Option(False, "--browser", "-b", help="Shortcut for --mode browser"),
    no_main: bool = typer.Option(False, "--no-main", help="Don't extract main content (keep full page)"),
    output: str | None = typer.Option(None, "--output", "-o", help="Write output to file"),
):
    """Scrape a single URL and output clean content."""
    from webharvest.core.scraper import scrape as do_scrape
    from webharvest.models.requests import ScrapeRequest

    formats = ["markdown", "metadata"]
    if format == "json":
        formats = ["markdown", "metadata", "links"]
    elif format in ("html", "raw_html"):
        formats = [format, "metadata"]

    fetch_mode = mode
    if browser:
        fetch_mode = "browser"

    req = ScrapeRequest(
        url=url,
        formats=formats,
        only_main_content=not no_main,
        fetch_mode=fetch_mode,
        use_browser=browser,
    )

    result = asyncio.run(do_scrape(req))

    if not result.success:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)

    if format == "json":
        out = result.model_dump_json(indent=2, exclude_none=True)
    elif format == "html":
        out = result.html or ""
    elif format == "raw_html":
        out = result.raw_html or ""
    else:
        out = result.markdown or ""

    if output:
        Path(output).write_text(out, encoding="utf-8")
        typer.echo(f"Written to {output}")
    else:
        typer.echo(out)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CRAWL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command()
def crawl(
    url: str = typer.Argument(help="Starting URL"),
    depth: int = typer.Option(2, "--depth", "-d", help="Max crawl depth"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max pages to scrape"),
    output_dir: str = typer.Option(".", "--output-dir", "-o", help="Directory for output files"),
):
    """Crawl a website and save each page as markdown."""
    from webharvest.core.crawler import crawl as do_crawl
    from webharvest.models.requests import CrawlRequest

    req = CrawlRequest(url=url, max_depth=depth, limit=limit)
    result = asyncio.run(do_crawl(req))

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for i, page in enumerate(result.pages):
        if page.success and page.markdown:
            filename = f"{i:04d}_{_slugify(page.url)}.md"
            (out_path / filename).write_text(page.markdown, encoding="utf-8")

    typer.echo(f"Crawled {result.completed_count}/{result.total} pages → {out_path}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXTRACT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command()
def extract(
    url: str = typer.Argument(help="URL to extract from"),
    schema: str = typer.Option(..., "--schema", "-s", help="Path to JSON schema file"),
    output: str | None = typer.Option(None, "--output", "-o", help="Write output to file"),
):
    """Extract structured JSON data from a page using CSS selectors."""
    from webharvest.core.extractor import extract as do_extract
    from webharvest.models.requests import ExtractRequest

    schema_data = json.loads(Path(schema).read_text(encoding="utf-8"))
    req = ExtractRequest(url=url, schema=schema_data)
    result = asyncio.run(do_extract(req))

    out = result.model_dump_json(indent=2)
    if output:
        Path(output).write_text(out, encoding="utf-8")
        typer.echo(f"Written to {output}")
    else:
        typer.echo(out)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SEARCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command()
def search(
    query: str = typer.Argument(help="Search query"),
    num: int = typer.Option(5, "--num", "-n", help="Number of results"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output: markdown, json"),
):
    """Search the web and scrape each result page."""
    from webharvest.core.searcher import search_and_scrape
    from webharvest.models.requests import SearchRequest

    req = SearchRequest(query=query, num_results=num)
    result = asyncio.run(search_and_scrape(req))

    if format == "json":
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
    else:
        for item in result.results:
            typer.echo(f"\n## {item.title}")
            typer.echo(f"URL: {item.url}")
            if item.page and item.page.markdown:
                typer.echo(item.page.markdown[:500])
            typer.echo("---")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT — autonomous browser agent
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command()
def agent(
    task: str = typer.Argument(help="Natural language task for the agent"),
    provider: str = typer.Option("openai", "--provider", "-p", help="LLM: openai, anthropic, google"),
    model: str | None = typer.Option(None, "--model", help="LLM model name"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Run browser headless"),
    max_steps: int = typer.Option(50, "--max-steps", help="Max agent steps"),
):
    """Run an autonomous browser agent (LLM-driven).

    The agent navigates websites, clicks buttons, fills forms, and extracts
    data — all driven by an LLM that understands your natural language task.

    Requires: pip install webharvest[agent]
    Plus an LLM API key in env vars (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)

    Examples:
      webharvest agent "Go to HN and get the top 5 stories with title and URL"
      webharvest agent "Search Google for 'AI startups 2026' and list the first 10 results"
      webharvest agent "Go to github.com/trending and extract repo names and stars" --provider anthropic
    """
    from webharvest.core.agent import run_agent, AgentConfig

    config = AgentConfig(
        llm_provider=provider,
        llm_model=model,
        headless=headless,
        max_steps=max_steps,
    )
    result = asyncio.run(run_agent(task=task, config=config))

    if not result.success:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)

    if isinstance(result.extracted_data, (dict, list)):
        typer.echo(json.dumps(result.extracted_data, indent=2, ensure_ascii=False))
    else:
        typer.echo(result.extracted_data or result.markdown or "No data extracted")

    typer.echo(f"\nPages visited: {len(result.pages_visited)} | Steps: {result.steps_taken}", err=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT-EXTRACT — LLM-powered extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command("agent-extract")
def agent_extract(
    url: str = typer.Argument(help="URL to extract from"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="What to extract (natural language)"),
    provider: str = typer.Option("openai", "--provider", help="LLM: openai, anthropic, google"),
    model: str | None = typer.Option(None, "--model", help="LLM model name"),
):
    """Extract structured data using natural language (no CSS selectors needed).

    Unlike 'extract' which needs CSS selectors, this uses an LLM to understand
    the page and pull out exactly what you describe.

    Examples:
      webharvest agent-extract https://example.com/product --prompt "product name, price, and rating"
      webharvest agent-extract https://news.ycombinator.com --prompt "top 10 story titles with URLs and points"
    """
    from webharvest.core.agent import run_agent_extract, AgentConfig

    config = AgentConfig(llm_provider=provider, llm_model=model)
    result = asyncio.run(run_agent_extract(url=url, prompt=prompt, config=config))

    if not result.success:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(1)

    if isinstance(result.extracted_data, (dict, list)):
        typer.echo(json.dumps(result.extracted_data, indent=2, ensure_ascii=False))
    else:
        typer.echo(result.extracted_data or "No data extracted")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SERVE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind address"),
    port: int = typer.Option(8787, "--port", "-p", help="Port"),
):
    """Start the WebHarvest REST API server."""
    import uvicorn

    typer.echo(f"Starting WebHarvest API on http://{host}:{port}")
    typer.echo(f"Docs: http://localhost:{port}/docs")
    uvicorn.run("webharvest.api.app:create_app", factory=True, host=host, port=port)


def _slugify(url: str) -> str:
    """Turn a URL into a safe filename slug."""
    import re
    from urllib.parse import urlparse

    parsed = urlparse(url)
    slug = f"{parsed.netloc}{parsed.path}".replace("/", "_").replace(".", "_")
    slug = re.sub(r"[^a-zA-Z0-9_-]", "", slug)
    return slug[:80]


if __name__ == "__main__":
    app()

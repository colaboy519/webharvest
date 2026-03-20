"""
WebHarvest MCP Server — exposes scrape/crawl/extract/search as native Claude Code tools.

This lets any Claude Code session use WebHarvest directly as:
  mcp__webharvest__scrape
  mcp__webharvest__crawl
  mcp__webharvest__extract
  mcp__webharvest__search

Run standalone:  python -m webharvest.mcp_server
Configured in:   ~/.claude/settings.json under mcpServers
"""

from __future__ import annotations

import asyncio
import json
import sys

# MCP protocol via stdio - simple JSON-RPC implementation
# Compatible with Claude Code's MCP client

import logging

logger = logging.getLogger("webharvest.mcp")


def _run_async(coro):
    """Run an async function synchronously."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


TOOLS = [
    {
        "name": "scrape",
        "description": (
            "Scrape a single URL and return clean, agent-friendly content. "
            "Converts any webpage to markdown with metadata. "
            "Supports fetch_mode: httpx (default), browser (JS pages), stealth (anti-bot), smart (auto-escalate)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape"},
                "formats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["markdown", "metadata", "links"],
                    "description": "Output formats: markdown, html, raw_html, links, metadata",
                },
                "fetch_mode": {
                    "type": "string",
                    "enum": ["httpx", "browser", "stealth", "smart"],
                    "default": "httpx",
                    "description": "httpx=standard, browser=JS rendering, stealth=anti-bot TLS, smart=auto-escalate",
                },
                "only_main_content": {
                    "type": "boolean",
                    "default": True,
                    "description": "Extract main article content only (strip nav/footer/ads)",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "crawl",
        "description": (
            "Crawl a website following links up to a given depth. "
            "Returns markdown content for each page discovered via BFS traversal."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Starting URL"},
                "max_depth": {"type": "integer", "default": 2, "description": "Max link-follow depth (0-10)"},
                "limit": {"type": "integer", "default": 50, "description": "Max pages to scrape (1-10000)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "extract",
        "description": (
            "Extract structured JSON data from a page using CSS selectors. "
            "Provide a schema mapping field names to CSS selectors."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to extract from"},
                "schema": {
                    "type": "object",
                    "description": "Map of field names to {selector, type, attribute}. type: string|number|integer|boolean|list",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string"},
                            "type": {"type": "string", "default": "string"},
                            "attribute": {"type": "string"},
                        },
                        "required": ["selector"],
                    },
                },
            },
            "required": ["url", "schema"],
        },
    },
    {
        "name": "search",
        "description": (
            "Search the web using DuckDuckGo and scrape each result page. "
            "Returns markdown content for each search result. Requires: pip install webharvest[search]"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "default": 5, "description": "Number of results (1-20)"},
            },
            "required": ["query"],
        },
    },
]


def handle_initialize(params):
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "webharvest", "version": "0.3.0"},
    }


def handle_tools_list(params):
    return {"tools": TOOLS}


def handle_tools_call(params):
    name = params.get("name")
    args = params.get("arguments", {})

    try:
        if name == "scrape":
            return _do_scrape(args)
        elif name == "crawl":
            return _do_crawl(args)
        elif name == "extract":
            return _do_extract(args)
        elif name == "search":
            return _do_search(args)
        else:
            return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}


def _do_scrape(args):
    from webharvest.core.scraper import scrape
    from webharvest.models.requests import ScrapeRequest

    req = ScrapeRequest(
        url=args["url"],
        formats=args.get("formats", ["markdown", "metadata", "links"]),
        fetch_mode=args.get("fetch_mode", "httpx"),
        only_main_content=args.get("only_main_content", True),
    )
    result = _run_async(scrape(req))

    if not result.success:
        return {"content": [{"type": "text", "text": f"Scrape failed: {result.error}"}], "isError": True}

    output = result.model_dump_json(indent=2, exclude_none=True)
    return {"content": [{"type": "text", "text": output}]}


def _do_crawl(args):
    from webharvest.core.crawler import crawl
    from webharvest.models.requests import CrawlRequest

    req = CrawlRequest(
        url=args["url"],
        max_depth=args.get("max_depth", 2),
        limit=args.get("limit", 50),
    )
    result = _run_async(crawl(req))

    # Return a summary + first few pages (full crawl can be huge)
    summary = f"Crawled {result.completed_count}/{result.total} pages\n\n"
    pages_output = []
    for page in result.pages:
        if page.success and page.markdown:
            pages_output.append(f"## {page.metadata.title or page.url}\nURL: {page.url}\n\n{page.markdown}\n\n---\n")

    output = summary + "\n".join(pages_output)
    return {"content": [{"type": "text", "text": output}]}


def _do_extract(args):
    from webharvest.core.extractor import extract
    from webharvest.models.requests import ExtractRequest

    req = ExtractRequest(url=args["url"], schema=args["schema"])
    result = _run_async(extract(req))

    output = result.model_dump_json(indent=2)
    return {"content": [{"type": "text", "text": output}]}


def _do_search(args):
    from webharvest.core.searcher import search_and_scrape
    from webharvest.models.requests import SearchRequest

    req = SearchRequest(
        query=args["query"],
        num_results=args.get("num_results", 5),
    )
    result = _run_async(search_and_scrape(req))

    output = result.model_dump_json(indent=2, exclude_none=True)
    return {"content": [{"type": "text", "text": output}]}


def main():
    """Run the MCP server over stdio (JSON-RPC)."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        params = msg.get("params", {})
        msg_id = msg.get("id")

        result = None
        if method == "initialize":
            result = handle_initialize(params)
        elif method == "notifications/initialized":
            continue  # notification, no response needed
        elif method == "tools/list":
            result = handle_tools_list(params)
        elif method == "tools/call":
            result = handle_tools_call(params)
        else:
            # Unknown method
            if msg_id is not None:
                response = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            continue

        if msg_id is not None and result is not None:
            response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

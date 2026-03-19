# WebHarvest

Web scraper plugin that converts any webpage into agent-friendly markdown, HTML, or structured JSON. **Runs 100% locally** on whoever installs it — no server, no cloud, no data leaves your machine.

Free, open-source alternative to Firecrawl.

## Install

```bash
pip install webharvest
```

That's it. Everything runs on your machine.

### Optional extras

```bash
pip install webharvest[stealth]   # Anti-bot: curl_cffi + Patchright + BrowserForge
pip install webharvest[agent]     # Autonomous agent: browser-use + Patchright
pip install webharvest[browser]   # JS rendering: Playwright
pip install webharvest[search]    # Web search: DuckDuckGo
pip install webharvest[captcha]   # CAPTCHA solving: 2Captcha
pip install webharvest[all]       # Everything
```

## Features

| Feature | Command | Description |
|---------|---------|-------------|
| **Scrape** | `webharvest scrape <url>` | Any URL → clean markdown, HTML, JSON with metadata |
| **Crawl** | `webharvest crawl <url>` | BFS website crawl, depth-limited, concurrent |
| **Extract** | `webharvest extract <url>` | CSS selectors → structured JSON |
| **Search** | `webharvest search "query"` | DuckDuckGo search + scrape each result |
| **Agent** | `webharvest agent "task"` | LLM-driven autonomous browsing |
| **Agent Extract** | `webharvest agent-extract <url>` | Natural language extraction (no selectors needed) |

### Anti-Bot Bypass (auto-escalation)

```bash
webharvest scrape https://protected-site.com --mode smart
```

Automatically escalates through increasingly aggressive bypass strategies:

| Level | Method | Speed | What it beats |
|-------|--------|-------|---------------|
| 0 | Standard httpx | ~200ms | Unprotected sites |
| 1 | curl_cffi TLS impersonation | ~200ms | JA3/JA4 fingerprint checks |
| 2 | Patchright + BrowserForge | ~3-5s | JS challenges, headless detection |
| 3 | Stealth browser + CAPTCHA solver | ~20-60s | reCAPTCHA, Turnstile, hCaptcha |

```bash
webharvest scrape https://example.com                          # Level 0 (default)
webharvest scrape https://protected-site.com --mode stealth    # Level 1
webharvest scrape https://cf-protected.com --mode smart        # Auto-escalate
```

### Autonomous Browser Agent

Give the agent a task in plain English — it navigates, clicks, scrolls, and extracts:

```bash
webharvest agent "Go to Hacker News and get the top 5 stories with title, URL, and points"
webharvest agent-extract https://example.com/product --prompt "product name, price, and rating"
```

Powered by [browser-use](https://github.com/browser-use/browser-use). Supports OpenAI, Anthropic, and Google as LLM backends.

## Usage

### CLI

```bash
# Scrape a page to markdown
webharvest scrape https://example.com

# Get JSON with metadata and links
webharvest scrape https://example.com --format json

# Scrape a JS-heavy SPA
webharvest scrape https://spa-site.com --mode browser

# Scrape a bot-protected page (auto-escalate)
webharvest scrape https://protected-site.com --mode smart

# Crawl an entire site
webharvest crawl https://docs.python.org --depth 2 --limit 50

# Extract structured data with CSS selectors
webharvest extract https://shop.com/product --schema schema.json

# LLM-powered extraction (no selectors needed)
webharvest agent-extract https://example.com/product --prompt "name, price, reviews"

# Autonomous agent
webharvest agent "Search Google Scholar for 'transformer architecture' and get the top 10 paper titles"
```

### Python library

```python
import asyncio
from webharvest.core.scraper import scrape
from webharvest.models.requests import ScrapeRequest

async def main():
    result = await scrape(ScrapeRequest(
        url="https://example.com",
        formats=["markdown", "metadata", "links"],
        fetch_mode="smart",  # auto-escalate anti-bot bypass
    ))
    print(result.markdown)
    print(result.metadata.title)

asyncio.run(main())
```

## Configuration

All settings via environment variables (prefix `WEBHARVEST_`) or `.env` file:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHARVEST_VERIFY_SSL` | `true` | Set `false` if you have cert issues |
| `WEBHARVEST_MAX_CONCURRENT` | `5` | Max parallel requests |
| `WEBHARVEST_CACHE_TTL` | `3600` | Response cache TTL (seconds) |
| `WEBHARVEST_PROXY_URLS` | `[]` | JSON array of proxy URLs |

For the agent, set your LLM API key:

```bash
export OPENAI_API_KEY=sk-...       # or
export ANTHROPIC_API_KEY=sk-ant-...  # or
export GOOGLE_API_KEY=...
```

## Architecture

```
webharvest/
├── core/                    ★ Features
│   ├── scraper.py           Single URL → clean content
│   ├── crawler.py           BFS website traversal
│   ├── extractor.py         CSS selectors → JSON
│   ├── searcher.py          Search + scrape
│   ├── agent.py             LLM autonomous browser
│   └── content.py           HTML → markdown pipeline
├── fetch/                   ★ HTTP layer
│   ├── http_client.py       Standard httpx (Level 0)
│   ├── stealth.py           curl_cffi + Patchright (Level 1-2)
│   ├── smart.py             Auto-escalation engine
│   ├── captcha.py           CAPTCHA solver (Level 3)
│   ├── browser.py           Playwright JS rendering
│   ├── proxy.py             Proxy rotation
│   ├── useragent.py         UA rotation
│   └── retry.py             Exponential backoff
├── cli/                     Typer CLI
├── models/                  Pydantic schemas
└── cache/                   SQLite disk cache
```

## How it compares to Firecrawl

| | WebHarvest | Firecrawl |
|---|---|---|
| **Price** | Free | $16+/mo |
| **Runs on** | Your machine | Their cloud |
| **Data leaves your machine** | Never | Yes (their servers process it) |
| **Anti-bot** | curl_cffi + Patchright + BrowserForge | Managed proxy fleet |
| **LLM extraction** | BYO API key (OpenAI/Anthropic/Google) | Built-in |
| **CAPTCHA solving** | 2Captcha integration (BYO key) | Built-in |
| **Scale** | Single machine | Distributed infrastructure |

## License

MIT

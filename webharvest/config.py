"""
Configuration — loaded from environment variables or .env file.

All settings have sensible defaults. Override via env vars prefixed WEBHARVEST_
or by placing a .env file in the project root.

Example .env:
    WEBHARVEST_USE_BROWSER=true
    WEBHARVEST_PROXY_URLS=["http://proxy1:8080","http://proxy2:8080"]
    WEBHARVEST_RATE_LIMIT_RPM=30
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "WEBHARVEST_", "env_file": ".env"}

    # ── Fetch ────────────────────────────────────────────────
    default_timeout_ms: int = 30_000
    max_concurrent: int = 5
    rate_limit_rpm: int = 60  # per domain
    verify_ssl: bool = True  # set to false if you have SSL cert issues

    # ── Proxy ────────────────────────────────────────────────
    proxy_urls: list[str] = []

    # ── User-Agent rotation ──────────────────────────────────
    user_agents: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    ]

    # ── Cache ────────────────────────────────────────────────
    cache_dir: str = ".webharvest_cache"
    cache_ttl: int = 3600  # seconds

    # ── Browser (Playwright) ─────────────────────────────────
    use_browser: bool = False
    browser_headless: bool = True



settings = Settings()

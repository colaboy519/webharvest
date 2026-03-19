"""
Proxy rotation — round-robin through configured proxy URLs.

If no proxies are configured, returns None (direct connection).
"""

from __future__ import annotations

import itertools

from webharvest.config import settings

_cycle = itertools.cycle(settings.proxy_urls) if settings.proxy_urls else None


def next_proxy() -> str | None:
    if _cycle is None:
        return None
    return next(_cycle)

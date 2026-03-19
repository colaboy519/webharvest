"""
CAPTCHA solver integration — pluggable solvers for reCAPTCHA, hCaptcha, Turnstile.

Supports multiple backends:
  - 2Captcha (human-powered, most reliable, ~$2.99/1000 solves)
  - CapSolver (AI-powered, fastest, ~$0.80/1000 solves)

You bring your own API key via environment variable.

Install: pip install webharvest[captcha]

Usage:
    solver = get_captcha_solver()
    token = await solver.solve_recaptcha(sitekey="...", url="...")
"""

from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger("webharvest.fetch.captcha")


class CaptchaSolver(ABC):
    """Interface for CAPTCHA solving backends."""

    @abstractmethod
    async def solve_recaptcha_v2(self, sitekey: str, url: str) -> str:
        """Solve reCAPTCHA v2 and return the response token."""
        ...

    @abstractmethod
    async def solve_turnstile(self, sitekey: str, url: str) -> str:
        """Solve Cloudflare Turnstile and return the response token."""
        ...

    @abstractmethod
    async def solve_hcaptcha(self, sitekey: str, url: str) -> str:
        """Solve hCaptcha and return the response token."""
        ...


class TwoCaptchaSolver(CaptchaSolver):
    """2Captcha backend — human-powered, most reliable."""

    def __init__(self, api_key: str | None = None):
        try:
            from twocaptcha import TwoCaptcha
        except ImportError:
            raise ImportError("Run: pip install webharvest[captcha]")
        self._key = api_key or os.environ.get("TWOCAPTCHA_API_KEY", "")
        if not self._key:
            raise ValueError("Set TWOCAPTCHA_API_KEY environment variable")
        self._solver = TwoCaptcha(self._key)

    async def solve_recaptcha_v2(self, sitekey: str, url: str) -> str:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self._solver.recaptcha(sitekey=sitekey, url=url)
        )
        logger.info("reCAPTCHA v2 solved (2captcha)")
        return result["code"]

    async def solve_turnstile(self, sitekey: str, url: str) -> str:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self._solver.turnstile(sitekey=sitekey, url=url)
        )
        logger.info("Turnstile solved (2captcha)")
        return result["code"]

    async def solve_hcaptcha(self, sitekey: str, url: str) -> str:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self._solver.hcaptcha(sitekey=sitekey, url=url)
        )
        logger.info("hCaptcha solved (2captcha)")
        return result["code"]


def get_captcha_solver(backend: str = "2captcha", api_key: str | None = None) -> CaptchaSolver:
    """
    Factory to get the configured CAPTCHA solver.

    Args:
        backend: "2captcha" or "capsolver"
        api_key: API key (or set via env var)
    """
    if backend == "2captcha":
        return TwoCaptchaSolver(api_key)
    else:
        raise ValueError(f"Unknown CAPTCHA backend: {backend}")

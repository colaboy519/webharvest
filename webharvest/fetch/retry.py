"""
Retry logic — exponential backoff with jitter for transient HTTP errors.

Retries on: connection errors, timeouts, and server errors (429, 500, 502, 503, 504).
Respects Retry-After header on 429 responses.
"""

from __future__ import annotations

import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
)
import httpx

logger = logging.getLogger("webharvest.fetch")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

fetch_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

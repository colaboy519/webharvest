"""
User-Agent rotation — pick a random realistic browser UA per request.
"""

from __future__ import annotations

import random

from webharvest.config import settings


def random_ua() -> str:
    return random.choice(settings.user_agents)

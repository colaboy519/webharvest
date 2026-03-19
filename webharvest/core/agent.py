"""
Autonomous browser agent — LLM-driven web navigation and data extraction.

Uses browser-use to let an LLM autonomously browse websites:
  - Navigate multi-page flows (pagination, search results, drill-downs)
  - Fill forms and interact with UI elements
  - Extract data from complex, dynamic pages
  - Handle login/auth flows
  - Understand page layout and content without CSS selectors

The agent observes the page DOM, decides what to do, executes actions,
and repeats until the task is complete.

Install: pip install webharvest[agent]

Requires an LLM API key (OpenAI, Anthropic, or any LangChain-compatible provider).

Usage:
    # Simple data extraction
    result = await run_agent(
        task="Go to https://news.ycombinator.com and extract the top 5 stories with title, URL, and points",
        llm_provider="anthropic",
        llm_api_key="sk-...",
    )

    # Multi-step navigation
    result = await run_agent(
        task="Search for 'python web scraping' on Google Scholar, then extract the titles and citation counts of the first 10 results",
        llm_provider="openai",
        llm_api_key="sk-...",
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from webharvest.models.responses import PageMetadata

logger = logging.getLogger("webharvest.agent")


@dataclass
class AgentResult:
    """Result from an autonomous agent run."""

    success: bool
    task: str
    extracted_data: dict | list | str | None = None
    pages_visited: list[str] = field(default_factory=list)
    steps_taken: int = 0
    final_url: str | None = None
    markdown: str | None = None
    error: str | None = None


@dataclass
class AgentConfig:
    """Configuration for the autonomous agent."""

    # LLM settings
    llm_provider: str = "openai"  # openai, anthropic, google
    llm_model: str | None = None  # auto-selects based on provider
    llm_api_key: str | None = None

    # Browser settings
    headless: bool = True
    timeout_ms: int = 60_000
    max_steps: int = 50

    # Session persistence
    save_session: bool = False
    session_file: str | None = None  # path to Playwright storageState JSON

    # Output
    return_markdown: bool = True
    return_screenshots: bool = False


async def run_agent(
    task: str,
    *,
    config: AgentConfig | None = None,
) -> AgentResult:
    """
    Run an autonomous browser agent to complete a web task.

    The agent will:
    1. Parse your natural-language task
    2. Open a browser and navigate to the relevant page(s)
    3. Interact with the page (click, type, scroll) as needed
    4. Extract the requested data
    5. Return structured results

    Args:
        task: Natural language description of what to do.
              Examples:
              - "Extract all product prices from https://example.com/shop"
              - "Log into https://app.example.com with user@test.com / password123, then download the report"
              - "Search for 'AI startups' on Crunchbase and get the top 20 company names and funding amounts"
        config: Agent configuration (LLM provider, browser settings, etc.)
    """
    try:
        from browser_use import Agent
        from langchain_core.language_models.chat_models import BaseChatModel
    except ImportError:
        raise ImportError(
            "browser-use is not installed. Run: pip install webharvest[agent]\n"
            "You also need an LLM provider: pip install langchain-openai or langchain-anthropic"
        )

    config = config or AgentConfig()

    # ── Set up LLM ───────────────────────────────────────────
    llm = _create_llm(config)

    # ── Set up browser context ───────────────────────────────
    browser_kwargs = {}

    # Use Patchright if available (stealth mode)
    try:
        import patchright  # noqa: F401
        logger.info("Using Patchright (stealth) browser")
    except ImportError:
        logger.info("Using standard Playwright browser")

    # ── Run the agent ────────────────────────────────────────
    try:
        agent = Agent(
            task=task,
            llm=llm,
            max_steps=config.max_steps,
        )

        result = await agent.run()

        # Extract results
        extracted = None
        if result.final_result():
            raw = result.final_result()
            # Try to parse as JSON
            try:
                extracted = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                extracted = raw

        pages = []
        for step in result.history():
            if hasattr(step, "state") and hasattr(step.state, "url"):
                if step.state.url not in pages:
                    pages.append(step.state.url)

        return AgentResult(
            success=True,
            task=task,
            extracted_data=extracted,
            pages_visited=pages,
            steps_taken=len(result.history()),
            final_url=pages[-1] if pages else None,
            markdown=str(extracted) if config.return_markdown else None,
        )

    except Exception as e:
        logger.error("Agent failed: %s", e)
        return AgentResult(success=False, task=task, error=str(e))


def _create_llm(config: AgentConfig) -> "BaseChatModel":
    """Create an LLM instance based on the provider configuration."""
    import os

    provider = config.llm_provider.lower()

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Run: pip install langchain-openai")

        api_key = config.llm_api_key or os.environ.get("OPENAI_API_KEY")
        return ChatOpenAI(
            model=config.llm_model or "gpt-4o",
            api_key=api_key,
        )

    elif provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("Run: pip install langchain-anthropic")

        api_key = config.llm_api_key or os.environ.get("ANTHROPIC_API_KEY")
        return ChatAnthropic(
            model=config.llm_model or "claude-sonnet-4-20250514",
            api_key=api_key,
        )

    elif provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("Run: pip install langchain-google-genai")

        api_key = config.llm_api_key or os.environ.get("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(
            model=config.llm_model or "gemini-2.0-flash",
            google_api_key=api_key,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use: openai, anthropic, google")


async def run_agent_extract(
    url: str,
    prompt: str,
    *,
    config: AgentConfig | None = None,
) -> AgentResult:
    """
    LLM-powered extraction — like Firecrawl's /extract but with natural language.

    Instead of CSS selectors, describe what you want in plain English:
      "Get the product name, price, rating, and number of reviews"

    The agent navigates to the page and extracts the data.

    Args:
        url: Page to extract from
        prompt: Natural language description of what to extract
        config: Agent configuration
    """
    task = f"Go to {url} and extract the following data: {prompt}. Return the result as JSON."
    return await run_agent(task=task, config=config)


async def run_agent_crawl(
    url: str,
    task: str,
    *,
    max_pages: int = 10,
    config: AgentConfig | None = None,
) -> AgentResult:
    """
    LLM-powered crawl — autonomously navigate and collect data across pages.

    The agent will handle pagination, drill-downs, and multi-page flows.

    Args:
        url: Starting URL
        task: What to collect across pages (e.g., "all blog post titles and dates")
        max_pages: Limit on pages to visit
        config: Agent configuration
    """
    full_task = (
        f"Starting from {url}, {task}. "
        f"Navigate through pages (pagination, links) to collect data from up to {max_pages} pages. "
        f"Return all collected data as a JSON array."
    )
    return await run_agent(task=full_task, config=config)

"""
POST /v1/agent          — Run an autonomous browser agent
POST /v1/agent/extract  — LLM-powered data extraction (natural language)

These endpoints use an LLM to autonomously browse and extract data.
Requires: pip install webharvest[agent] + LLM API key
"""

from fastapi import APIRouter

from webharvest.models.requests import AgentRequest, AgentExtractRequest

router = APIRouter()


@router.post("/v1/agent")
async def run_agent_endpoint(request: AgentRequest):
    from webharvest.core.agent import run_agent, AgentConfig

    config = AgentConfig(
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        headless=request.headless,
        max_steps=request.max_steps,
    )
    result = await run_agent(task=request.task, config=config)
    return result


@router.post("/v1/agent/extract")
async def agent_extract_endpoint(request: AgentExtractRequest):
    from webharvest.core.agent import run_agent_extract, AgentConfig

    config = AgentConfig(
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
    )
    result = await run_agent_extract(
        url=str(request.url), prompt=request.prompt, config=config,
    )
    return result

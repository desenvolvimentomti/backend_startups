"""
FastAPI router for Agno agent endpoints.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import get_current_user
from .. import schemas as user_schemas
from ..agent.agent_service import StartupSearchAgent
from ..agent.schemas import (
    AgentSearchRequest,
    AgentSearchResponse,
    AgentHealthResponse
)
from ..agent.config import get_agent_settings

router = APIRouter(
    prefix="/agent",
    tags=["AI Agent Search"]
)


@router.post(
    "/search",
    response_model=AgentSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search startups using AI agent",
    description="""
    Search for startups using natural language queries.
    The AI agent interprets your query and uses appropriate search strategies.

    **Query Types Supported:**
    - Multi-filter: "fintechs em SP com investimento"
    - Comparative: "startups similares a X mas em fase inicial"
    - Exploratory: "healthtechs inovadoras com patentes"
    """
)
def agent_search(
    request: AgentSearchRequest,
    db: Session = Depends(get_db),
    current_user: user_schemas.User = Depends(get_current_user)
):
    """Process natural language search query using AI agent."""
    agent = StartupSearchAgent(db)
    result = agent.search(request.query)

    return AgentSearchResponse(
        success=result.get("success", False),
        query=request.query,
        response=result.get("response", ""),
        results=result.get("results"),
        fallback=result.get("fallback", False),
        error=result.get("error")
    )


@router.get(
    "/health",
    response_model=AgentHealthResponse,
    summary="Check agent health status"
)
def agent_health():
    """Check if the AI agent is properly configured and ready."""
    try:
        settings = get_agent_settings()
        return AgentHealthResponse(
            status="healthy",
            agent_ready=bool(settings.openai_api_key),
            model=settings.agent_model,
            tools_count=5
        )
    except Exception:
        return AgentHealthResponse(
            status="unhealthy",
            agent_ready=False,
            model="unknown",
            tools_count=0
        )

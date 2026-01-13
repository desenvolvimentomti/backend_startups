"""
Pydantic schemas for agent endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class AgentSearchRequest(BaseModel):
    """Request schema for agent search endpoint."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language search query",
        examples=[
            "fintechs em SP com funding e mais de 10 funcionarios",
            "startups similares a Nubank mas em estagio inicial",
            "healthtechs inovadoras com patentes"
        ]
    )


class StartupResult(BaseModel):
    """Schema for a startup in search results."""
    id: int
    nome: str
    setor_principal: Optional[str] = None
    setor_secundario: Optional[str] = None
    fase: Optional[str] = None
    colaboradores: Optional[str] = None
    endereco: Optional[str] = None
    recebeu_investimento: Optional[str] = None
    patente: Optional[str] = None
    solucao: Optional[str] = None


class AgentSearchResponse(BaseModel):
    """Response schema for agent search endpoint."""
    success: bool
    query: str
    response: str = Field(description="Agent's natural language response")
    results: Optional[List[StartupResult]] = Field(
        default=None,
        description="Structured results if available"
    )
    fallback: bool = Field(
        default=False,
        description="True if fallback search was used"
    )
    error: Optional[str] = None


class AgentHealthResponse(BaseModel):
    """Health check response for agent service."""
    status: str
    agent_ready: bool
    model: str
    tools_count: int

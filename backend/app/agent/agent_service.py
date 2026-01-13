"""
Agno Agent service for natural language startup search.
"""
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from .config import get_agent_settings
from .tools import (
    search_startups_structured,
    search_startups_semantic,
    get_startup_details,
    find_similar_startups,
    get_filter_options
)


class StartupSearchAgent:
    """
    Agno-based agent for intelligent startup search.
    Combines structured filtering with semantic search.
    """

    SYSTEM_INSTRUCTIONS = """
    Voce e um assistente especializado em busca de startups brasileiras.
    Voce ajuda usuarios a encontrar startups com base em varios criterios.

    DIRETRIZES IMPORTANTES:
    1. Sempre use a ferramenta apropriada para o tipo de consulta:
       - Para criterios especificos (setor, fase, investimento): use structured_search
       - Para consultas conceituais/inovacao: use semantic_search
       - Para consultas "similar a X": primeiro obtenha a startup de referencia, depois use find_similar

    2. Entendimento de Consultas:
       - "fintechs" -> setor contem "fintech" ou "financeiro"
       - "em SP" ou "de Sao Paulo" -> estado = "SP"
       - "com funding" ou "investimento" -> recebeu_investimento = "Sim"
       - "10+ funcionarios" -> interprete o campo colaboradores
       - "early stage" -> fase como "Ideacao" ou "MVP"
       - "scale-up" ou "em tracao" -> fase como "Tracao" ou "Scale-up"

    3. Para consultas comparativas ("similar a X mas..."):
       - Primeiro identifique a empresa de referencia
       - Depois encontre similares com as diferencas especificadas

    4. Formato de Resposta:
       - Sempre forneca um breve resumo do que voce buscou
       - Liste os resultados em formato claro e estruturado
       - Inclua detalhes relevantes: nome, setor, fase, localizacao
       - Se nenhum resultado for encontrado, sugira estrategias alternativas

    5. Idioma: Responda em Portugues (Brasil).
    """

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_agent_settings()
        self._agent = None

    def _create_tools(self):
        """Create tool functions bound to the current db session."""

        def structured_search(
            setor: Optional[str] = None,
            fase: Optional[str] = None,
            estado: Optional[str] = None,
            min_colaboradores: Optional[int] = None,
            recebeu_investimento: Optional[str] = None,
            tem_patente: Optional[str] = None,
            modelo_negocio: Optional[str] = None,
            limit: int = 10
        ) -> str:
            """
            Busca startups usando filtros estruturados como setor, fase, localizacao, status de investimento.
            Use para consultas com criterios especificos.

            Args:
                setor: Setor principal (ex: "fintech", "healthtech", "agritech")
                fase: Fase da startup (ex: "Ideacao", "MVP", "Tracao", "Scale-up")
                estado: Estado do endereco (ex: "SP", "RJ", "MG")
                min_colaboradores: Numero minimo de funcionarios
                recebeu_investimento: "Sim" ou "Nao"
                tem_patente: "Sim" ou "Nao"
                modelo_negocio: Modelo de negocio (ex: "B2B", "B2C", "SaaS")
                limit: Maximo de resultados
            """
            return search_startups_structured(
                self.db, setor, fase, estado, min_colaboradores,
                recebeu_investimento, tem_patente, modelo_negocio, limit
            )

        def semantic_search(query_text: str, fase: Optional[str] = None, limit: int = 10) -> str:
            """
            Busca startups usando similaridade semantica/conceitual.
            Use para consultas exploratorias sobre inovacao, solucoes ou conceitos.

            Args:
                query_text: Descricao em linguagem natural do que buscar
                fase: Filtro opcional de fase
                limit: Maximo de resultados
            """
            return search_startups_semantic(self.db, query_text, fase, limit)

        def get_details(empresa_id: Optional[int] = None, nome: Optional[str] = None) -> str:
            """
            Obtem informacoes detalhadas sobre uma startup especifica por ID ou nome.

            Args:
                empresa_id: ID da startup no banco
                nome: Nome da startup (busca parcial)
            """
            return get_startup_details(self.db, empresa_id, nome)

        def find_similar(
            reference_id: int,
            exclude_same_fase: bool = False,
            target_fase: Optional[str] = None,
            limit: int = 5
        ) -> str:
            """
            Encontra startups similares a uma empresa de referencia.
            Use para consultas comparativas como 'similar a X mas em fase inicial'.

            Args:
                reference_id: ID da startup de referencia
                exclude_same_fase: Se True, exclui startups na mesma fase
                target_fase: Se fornecido, filtra para esta fase especifica
                limit: Maximo de resultados
            """
            return find_similar_startups(
                self.db, reference_id, exclude_same_fase, target_fase, limit
            )

        def get_options() -> str:
            """
            Obtem valores disponiveis para filtros (setores, fases, etc).
            Use para entender quais valores de filtro sao validos.
            """
            return get_filter_options(self.db)

        return [structured_search, semantic_search, get_details, find_similar, get_options]

    def _get_agent(self) -> Agent:
        """Lazily initialize the Agno agent."""
        if self._agent is None:
            self._agent = Agent(
                model=OpenAIChat(
                    id=self.settings.agent_model,
                    api_key=self.settings.openai_api_key,
                    temperature=self.settings.agent_temperature,
                    max_tokens=self.settings.agent_max_tokens
                ),
                description="Assistente especializado em busca de startups brasileiras",
                instructions=self.SYSTEM_INSTRUCTIONS.split("\n"),
                tools=self._create_tools(),
                show_tool_calls=False,
                markdown=True
            )
        return self._agent

    def search(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language search query.

        Args:
            query: User's natural language query

        Returns:
            Dict with 'response' (text) and 'results' (parsed data if available)
        """
        try:
            agent = self._get_agent()
            response = agent.run(query)

            # Extract the response content
            response_text = response.content if hasattr(response, 'content') else str(response)

            return {
                "success": True,
                "response": response_text,
                "query": query
            }

        except Exception as e:
            # Fallback to existing vector search
            return self._fallback_search(query, str(e))

    def _fallback_search(self, query: str, error: str) -> Dict[str, Any]:
        """Fallback to vector search if agent fails."""
        try:
            results_json = search_startups_semantic(self.db, query, limit=10)
            results = json.loads(results_json)

            return {
                "success": True,
                "response": f"Busca realizada usando metodo alternativo. Encontradas {len(results)} startups.",
                "results": results,
                "fallback": True,
                "original_error": error
            }
        except Exception as fallback_error:
            return {
                "success": False,
                "error": f"Agent error: {error}. Fallback error: {str(fallback_error)}",
                "query": query
            }

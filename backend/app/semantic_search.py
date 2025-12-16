"""
Semantic Search Engine using OpenAI Embeddings + pgvector + LangChain

This module provides semantic search capabilities for startup matching using:
- OpenAI text-embedding-3-small (1536 dimensions)
- PostgreSQL pgvector extension for vector similarity search
- LangChain for RAG orchestration
"""

import os
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, select
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector as PGVectorStore

from . import models
from .database import engine

# Lazy initialization of OpenAI client (only when needed)
_client = None
_embeddings_model = None


def _get_openai_client() -> OpenAI:
    """Get or create OpenAI client (lazy initialization)."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not set in environment variables. "
                "Add it to your .env file to use semantic search."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def _get_embeddings_model() -> OpenAIEmbeddings:
    """Get or create embeddings model (lazy initialization)."""
    global _embeddings_model
    if _embeddings_model is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not set in environment variables. "
                "Add it to your .env file to use semantic search."
            )
        _embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=api_key
        )
    return _embeddings_model


def create_empresa_text(empresa: models.Empresa) -> str:
    """
    Create a rich text representation of an empresa for embedding.
    Combines all relevant fields to maximize semantic searchability.

    IMPORTANT: Includes problem-solving keywords to match user needs.
    """
    text_parts = [
        f"Empresa: {empresa.nome_da_empresa}",
        f"Solução: {empresa.solucao}",
        f"Setor Principal: {empresa.setor_principal}",
        f"Setor Secundário: {empresa.setor_secundario}",
        f"Fase: {empresa.fase_da_startup}",
        f"Modelo de Negócio: {empresa.modelo_de_negocio}",
        f"Público Alvo: {empresa.publico_alvo}",
        f"Colaboradores: {empresa.colaboradores}",
        f"Faturamento: {empresa.faturamento}",
    ]

    # Add tags if available (tags often contain problem-solving keywords)
    if empresa.tag:
        text_parts.append(f"Tags: {empresa.tag}")

    # Extract problem-solving keywords from solution
    # This helps match user needs to startup solutions
    problem_keywords = extract_problem_keywords(empresa.solucao, empresa.setor_principal)
    if problem_keywords:
        text_parts.append(f"Resolve problemas de: {problem_keywords}")

    return " | ".join(text_parts)


def extract_problem_keywords(solucao: str, setor: str) -> str:
    """
    Extract problem-solving keywords from solution text.
    Maps solutions to user problems they solve.
    """
    keywords = []

    solucao_lower = solucao.lower()

    # Financial/Credit keywords
    if any(word in solucao_lower for word in ['crédito', 'financiamento', 'empréstimo', 'capital', 'investimento', 'dinheiro']):
        keywords.extend(['precisa de dinheiro', 'precisa de crédito', 'precisa de capital', 'precisa de financiamento'])

    # Agriculture keywords
    if 'agro' in setor.lower() or 'agríc' in solucao_lower or 'fazend' in solucao_lower or 'produt' in solucao_lower:
        keywords.extend(['fazendeiro', 'agricultor', 'produtor rural', 'fazenda'])

    # Logistics/Transport keywords
    if any(word in solucao_lower for word in ['logística', 'transporte', 'entrega', 'frete', 'rastreamento']):
        keywords.extend(['precisa transportar', 'precisa de logística', 'precisa rastrear'])

    # Technology/Software keywords
    if any(word in solucao_lower for word in ['software', 'sistema', 'plataforma', 'app', 'aplicativo']):
        keywords.extend(['precisa de sistema', 'precisa de software', 'precisa automatizar'])

    # Management keywords
    if any(word in solucao_lower for word in ['gestão', 'gerenciamento', 'controle', 'administração']):
        keywords.extend(['precisa gerenciar', 'precisa organizar', 'precisa controlar'])

    # Data/Analytics keywords
    if any(word in solucao_lower for word in ['dados', 'análise', 'inteligência', 'insights', 'métricas']):
        keywords.extend(['precisa de dados', 'precisa de análise', 'precisa de insights'])

    return ', '.join(keywords)


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for given text using OpenAI API.
    Uses text-embedding-3-small model (1536 dimensions, ~$0.02 per 1M tokens)
    """
    client = _get_openai_client()
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def generate_empresa_embedding(empresa: models.Empresa) -> List[float]:
    """Generate embedding for an empresa based on its text representation."""
    text = create_empresa_text(empresa)
    return generate_embedding(text)


def embed_all_empresas(db: Session, batch_size: int = 50) -> int:
    """
    Generate embeddings for all empresas that don't have one yet.
    Processes in batches to avoid rate limits and memory issues.

    Returns: Number of empresas embedded
    """
    # Get all empresas without embeddings
    empresas = db.query(models.Empresa).filter(
        models.Empresa.embedding == None
    ).all()

    if not empresas:
        print("All empresas already have embeddings!")
        return 0

    print(f"Generating embeddings for {len(empresas)} empresas...")

    embedded_count = 0
    for i in range(0, len(empresas), batch_size):
        batch = empresas[i:i + batch_size]

        for empresa in batch:
            try:
                embedding = generate_empresa_embedding(empresa)
                empresa.embedding = embedding
                embedded_count += 1

                if embedded_count % 10 == 0:
                    print(f"  Processed {embedded_count}/{len(empresas)}...")

            except Exception as e:
                print(f"  Error embedding empresa {empresa.id}: {e}")
                continue

        # Commit batch
        db.commit()
        print(f"  Committed batch {i//batch_size + 1}")

    print(f"✓ Successfully embedded {embedded_count} empresas")
    return embedded_count


def expand_query_with_llm(query: str) -> str:
    """
    Expand user query into better search terms using LLM.
    Transforms natural language needs into technical startup terminology.

    Example:
        "sou fazendeiro e preciso de dinheiro"
        -> "crédito rural financiamento agrícola agfintech empréstimo para produtores"
    """
    client = _get_openai_client()

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cheap model for query expansion
            messages=[
                {
                    "role": "system",
                    "content": """Você é um especialista em startups brasileiras. Sua tarefa é expandir consultas de usuários em termos de busca otimizados.

Regras:
1. Transforme necessidades do usuário em soluções que startups oferecem
2. Use termos técnicos e palavras-chave do mercado
3. Mantenha o foco no problema que o usuário quer resolver
4. Adicione sinônimos e termos relacionados
5. Responda APENAS com os termos de busca, sem explicações

Exemplos:
- "preciso de dinheiro para minha fazenda" -> "crédito rural financiamento agrícola agfintech empréstimo produtor capital"
- "quero rastrear minha frota" -> "rastreamento veicular gestão frota GPS telemetria monitoramento"
- "preciso vender produtos online" -> "e-commerce marketplace plataforma vendas loja virtual"
"""
                },
                {
                    "role": "user",
                    "content": f"Expanda esta consulta: {query}"
                }
            ],
            temperature=0.3,
            max_tokens=100
        )

        expanded = response.choices[0].message.content.strip()
        print(f"[Query Expansion] Original: '{query}' -> Expanded: '{expanded}'")
        return expanded

    except Exception as e:
        print(f"[Query Expansion] Error: {e}, using original query")
        return query


def semantic_search(
    query: str,
    db: Session,
    top_k: int = 10,
    similarity_threshold: float = 0.5,
    use_query_expansion: bool = True
) -> List[models.Empresa]:
    """
    Perform semantic search using vector similarity.

    Args:
        query: Natural language query from user
        db: Database session
        top_k: Number of results to return
        similarity_threshold: Minimum cosine similarity (0-1)
        use_query_expansion: Use LLM to expand query (default: True)

    Returns:
        List of most relevant Empresa objects
    """
    # Expand query using LLM for better matching
    if use_query_expansion:
        expanded_query = expand_query_with_llm(query)
    else:
        expanded_query = query

    # Generate embedding for the expanded query
    query_embedding = generate_embedding(expanded_query)

    # Perform vector similarity search using pgvector
    # Using cosine distance (<=> operator in pgvector)
    sql = text("""
        SELECT
            id,
            nome_da_empresa,
            1 - (embedding <=> :query_embedding) AS similarity
        FROM startups
        WHERE embedding IS NOT NULL
            AND (1 - (embedding <=> :query_embedding)) >= :threshold
        ORDER BY embedding <=> :query_embedding
        LIMIT :top_k
    """)

    # Execute search
    result = db.execute(
        sql,
        {
            "query_embedding": str(query_embedding),
            "threshold": similarity_threshold,
            "top_k": top_k
        }
    )

    # Get matching IDs
    matches = result.fetchall()

    if not matches:
        return []

    # Fetch full Empresa objects
    empresa_ids = [match[0] for match in matches]
    empresas = db.query(models.Empresa).filter(
        models.Empresa.id.in_(empresa_ids)
    ).all()

    # Sort by original order (most similar first)
    empresas_dict = {e.id: e for e in empresas}
    sorted_empresas = [empresas_dict[id] for id in empresa_ids if id in empresas_dict]

    return sorted_empresas


def refresh_empresa_embedding(empresa: models.Empresa, db: Session):
    """Regenerate embedding for a single empresa (useful after updates)."""
    empresa.embedding = generate_empresa_embedding(empresa)
    db.commit()

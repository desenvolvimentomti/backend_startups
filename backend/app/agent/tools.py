"""
Custom tools for the Agno startup search agent.
Each tool is a Python function that the agent can call.
"""
import json
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from unidecode import unidecode

from ..models import Empresa
from .. import embedding_service


def search_startups_structured(
    db: Session,
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
    Search startups using structured filters.

    Args:
        setor: Primary sector (e.g., "fintech", "healthtech", "agritech")
        fase: Startup phase (e.g., "Ideacao", "MVP", "Tracao", "Scale-up")
        estado: State from address (e.g., "SP", "RJ", "MG")
        min_colaboradores: Minimum number of employees
        recebeu_investimento: "Sim" or "Nao"
        tem_patente: "Sim" or "Nao"
        modelo_negocio: Business model (e.g., "B2B", "B2C", "SaaS")
        limit: Maximum results to return

    Returns:
        JSON string with matching startups or empty list
    """
    query = db.query(Empresa)
    filters = []

    if setor:
        setor_norm = unidecode(setor).lower()
        filters.append(
            or_(
                Empresa.setor_principal.ilike(f"%{setor_norm}%"),
                Empresa.setor_secundario.ilike(f"%{setor_norm}%")
            )
        )

    if fase:
        filters.append(Empresa.fase_da_startup.ilike(f"%{fase}%"))

    if estado:
        filters.append(Empresa.endereco.ilike(f"%{estado}%"))

    if recebeu_investimento:
        filters.append(Empresa.recebeu_investimento.ilike(f"%{recebeu_investimento}%"))

    if tem_patente:
        filters.append(Empresa.patente.ilike(f"%{tem_patente}%"))

    if modelo_negocio:
        filters.append(Empresa.modelo_de_negocio.ilike(f"%{modelo_negocio}%"))

    if filters:
        query = query.filter(and_(*filters))

    results = query.limit(limit).all()

    return _format_empresa_list(results)


def search_startups_semantic(
    db: Session,
    query_text: str,
    fase: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Search startups using semantic similarity (vector search).
    Best for exploratory queries, innovation-related searches,
    or when looking for conceptually similar companies.

    Args:
        query_text: Natural language description of what to find
        fase: Optional phase filter
        limit: Maximum results

    Returns:
        JSON string with matching startups
    """
    query_vector = embedding_service.generate_query_embedding(query_text)

    candidate_query = db.query(Empresa)
    if fase:
        candidate_query = candidate_query.filter(
            Empresa.fase_da_startup.ilike(f"%{fase}%")
        )

    # Filter only empresas with embeddings
    candidate_query = candidate_query.filter(Empresa.embedding_vector.isnot(None))

    results = candidate_query.order_by(
        Empresa.embedding_vector.cosine_distance(query_vector)
    ).limit(limit).all()

    return _format_empresa_list(results)


def get_startup_details(
    db: Session,
    empresa_id: Optional[int] = None,
    nome: Optional[str] = None
) -> str:
    """
    Get detailed information about a specific startup.

    Args:
        empresa_id: The startup's database ID
        nome: The startup's name (partial match)

    Returns:
        JSON string with startup details or error message
    """
    if empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    elif nome:
        nome_norm = unidecode(nome).lower()
        empresa = db.query(Empresa).filter(
            Empresa.nome_da_empresa.ilike(f"%{nome_norm}%")
        ).first()
    else:
        return '{"error": "Provide either empresa_id or nome"}'

    if not empresa:
        return '{"error": "Startup not found"}'

    return _format_empresa_detail(empresa)


def find_similar_startups(
    db: Session,
    reference_id: int,
    exclude_same_fase: bool = False,
    target_fase: Optional[str] = None,
    limit: int = 5
) -> str:
    """
    Find startups similar to a reference company.
    Useful for comparative queries like "startups similar to X but earlier stage".

    Args:
        reference_id: ID of the reference startup
        exclude_same_fase: If True, exclude startups in the same phase
        target_fase: If provided, filter to this specific phase
        limit: Maximum results

    Returns:
        JSON string with similar startups
    """
    reference = db.query(Empresa).filter(Empresa.id == reference_id).first()
    if not reference or not reference.embedding_vector:
        return '{"error": "Reference startup not found or has no embedding"}'

    query = db.query(Empresa).filter(Empresa.id != reference_id)
    query = query.filter(Empresa.embedding_vector.isnot(None))

    if exclude_same_fase:
        query = query.filter(Empresa.fase_da_startup != reference.fase_da_startup)

    if target_fase:
        query = query.filter(Empresa.fase_da_startup.ilike(f"%{target_fase}%"))

    results = query.order_by(
        Empresa.embedding_vector.cosine_distance(reference.embedding_vector)
    ).limit(limit).all()

    return _format_empresa_list(results)


def get_filter_options(db: Session) -> str:
    """
    Get the available values for filters (sectors, phases, etc).
    Use this to understand what filter values are valid.

    Returns:
        JSON with available filter options
    """
    setores = db.query(Empresa.setor_principal).distinct().all()
    fases = db.query(Empresa.fase_da_startup).distinct().all()
    modelos = db.query(Empresa.modelo_de_negocio).distinct().all()

    return json.dumps({
        "setores_principais": [s[0] for s in setores if s[0]],
        "fases": [f[0] for f in fases if f[0]],
        "modelos_negocio": [m[0] for m in modelos if m[0]],
        "investimento_opcoes": ["Sim", "Nao"],
        "patente_opcoes": ["Sim", "Nao"]
    }, ensure_ascii=False)


def _format_empresa_list(empresas: List[Empresa]) -> str:
    """Format list of empresas for agent response."""
    results = []
    for e in empresas:
        solucao = e.solucao or ""
        results.append({
            "id": e.id,
            "nome": e.nome_da_empresa,
            "setor_principal": e.setor_principal,
            "setor_secundario": e.setor_secundario,
            "fase": e.fase_da_startup,
            "colaboradores": e.colaboradores,
            "endereco": e.endereco,
            "recebeu_investimento": e.recebeu_investimento,
            "patente": e.patente,
            "solucao": solucao[:200] + "..." if len(solucao) > 200 else solucao
        })
    return json.dumps(results, ensure_ascii=False)


def _format_empresa_detail(empresa: Empresa) -> str:
    """Format single empresa with full details."""
    return json.dumps({
        "id": empresa.id,
        "nome": empresa.nome_da_empresa,
        "cnpj": empresa.cnpj,
        "endereco": empresa.endereco,
        "ano_fundacao": empresa.ano_de_fundacao,
        "setor_principal": empresa.setor_principal,
        "setor_secundario": empresa.setor_secundario,
        "fase": empresa.fase_da_startup,
        "colaboradores": empresa.colaboradores,
        "publico_alvo": empresa.publico_alvo,
        "modelo_negocio": empresa.modelo_de_negocio,
        "recebeu_investimento": empresa.recebeu_investimento,
        "faturamento": empresa.faturamento,
        "patente": empresa.patente,
        "negocios_exterior": empresa.negocios_no_exterior,
        "solucao": empresa.solucao,
        "site": empresa.site,
        "email": empresa.email,
        "telefone": empresa.telefone_contato
    }, ensure_ascii=False)

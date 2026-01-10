import nltk
from unidecode import unidecode
from nltk.corpus import stopwords
from nltk.tokenize import wordpunct_tokenize
from nltk.stem import SnowballStemmer
from typing import List, Optional
from fuzzywuzzy import fuzz
from sqlalchemy.orm import Session
from sqlalchemy import func

# Importações internas
from . import embedding_service
from .models import Empresa

# --- Variável Global Singleton ---
# Mantem a estrutura para não quebrar as importações no main.py,

search_engine_vector_instance = None

try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except Exception:
    pass


class SearchEngineVector:
    """
    Motor de Busca Otimizado.
    Agora utiliza pgvector no PostgreSQL para busca semântica em tempo real,
    eliminando o cache de memória.
    """
    
    def optimized_search_vector(self, db: Session, query: str, fase: Optional[str] = None, limit: int = 5):
        """
        Realiza a busca combinando Similaridade de Cosseno (via SQL) e Fuzzy Match (via Python).
        """
        # 1. Gerar o vetor da query usando a sua lógica de tokens (via embedding_service)
        query_vector = embedding_service.generate_query_embedding(query)

        # 2. Busca inicial no banco via pgvector (Distância de Cosseno)
        # Busca um número maior de candidatos para o refinamento fuzzy
        candidate_query = db.query(Empresa)
        
        if fase:
            candidate_query = candidate_query.filter(Empresa.fase_da_startup == fase)

        # O operador <=> representa a distância de cosseno no pgvector.
        # Quanto menor a distância, mais parecido é o conteúdo.
        candidates = candidate_query.order_by(
            Empresa.embedding_vector.cosine_distance(query_vector)
        ).limit(limit * 3).all()

        if not candidates:
            return []

        # 3. Refinamento e Re-rank com Fuzzy Matching (lógica original)
        scored_companies = []
        normalized_query = unidecode(query).lower()

        for company in candidates:
            # Nome da empresa (Peso alto no fuzzy)
            nome_da_empresa_norm = unidecode(company.nome_da_empresa).lower()
            name_fuzzy_score = fuzz.token_set_ratio(nome_da_empresa_norm, normalized_query)

            # Contexto (Solução + Setores)
            contexto_raw = f"{company.solucao} {company.setor_principal} {company.setor_secundario}{company.tag}"
            contexto_norm = unidecode(contexto_raw).lower()
            context_fuzzy_score = fuzz.token_set_ratio(contexto_norm, normalized_query)

            # Cálculo de Score Final
            # Como o filtro vetorial do banco já trouxe os mais parecidos, aqui aplicamos o ajuste fino.
            final_score = (name_fuzzy_score * 1.5) + (context_fuzzy_score * 0.5)
            
            # Limiar de corte para evitar resultados irrelevantes
            if final_score > 70.0: 
                scored_companies.append({'company': company, 'score': final_score})
        
        # Ordenar pelos melhores resultados após o re-rank
        scored_companies.sort(key=lambda x: x['score'], reverse=True)
        return [item['company'] for item in scored_companies[:limit]]
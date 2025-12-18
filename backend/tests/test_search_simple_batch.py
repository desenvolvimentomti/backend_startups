import pytest
from typing import Set, Dict, Any, List
from unidecode import unidecode
from http import HTTPStatus

# Importar o SearchEngine real
from ..app.search_engine import SearchEngine

# --- MOCK CLASS ---
# Usamos isto em vez de models.Empresa para evitar erros de banco de dados (init=False no id)
class MockEmpresa:
    def __init__(self, id, nome_da_empresa, solucao, setor_principal, setor_secundario, fase_da_startup="Operação", cnpj=None, endereco=None,tag="Placeholder", **kwargs):
        self.id = id
        self.nome_da_empresa = nome_da_empresa
        self.solucao = solucao
        self.setor_principal = setor_principal
        self.setor_secundario = setor_secundario
        self.fase_da_startup = fase_da_startup
        self.cnpj = cnpj
        self.endereco = endereco
        self.tag = tag

# --- DADOS DE MOCK ---
MOCK_COMPANIES_DATA = [
    {
        "id": 1, 
        "nome_da_empresa": "AgroSense BR", 
        "solucao": "Plataforma de IA para otimização de logística agrícola", 
        "setor_principal": "Agrotech", 
        "setor_secundario": "Inteligência Artificial", 
        "fase_da_startup": "Scale-up"
    },
    {
        "id": 2, 
        "nome_da_empresa": "CyberGuard Pro", 
        "solucao": "Software de segurança proativa que utiliza machine learning", 
        "setor_principal": "Segurança da Informação", 
        "setor_secundario": "SaaS",
        "fase_da_startup": "Seed"
    },
    {
        "id": 3, 
        "nome_da_empresa": "ProtoMesh 3D", 
        "solucao": "Serviço de impressão 3D industrial e prototipagem rápida", 
        "setor_principal": "Manufatura Aditiva", 
        "setor_secundario": "Engenharia",
        "fase_da_startup": "Growth"
    },
]

# Criar objetos Mock em vez de modelos SQLAlchemy
MOCK_COMPANIES = [MockEmpresa(**data) for data in MOCK_COMPANIES_DATA]

# Inicializar SearchEngine
TEST_ENGINE = SearchEngine(MOCK_COMPANIES)

SEARCH_TEST_CASES = [
    {
        "query": "Plataforma de IA para fazendas",
        "description": "Teste 1: Busca AGROTECH (Deve achar #1)",
        "expected_ids": {1}
    },
    {
        "query": "Segurança de dados e Machine Learning",
        "description": "Teste 2: Busca TECH (Deve achar #2)",
        "expected_ids": {2}
    },
    {
        "query": "Impressão industrial com 3D",
        "description": "Teste 3: Busca 3D/Manufatura (Deve achar #3)",
        "expected_ids": {3}
    },
    {
        "query": "Software Machine Learning",
        "description": "Teste 4: Busca por Software com Filtro de Fase Seed (Deve achar #2)",
        "fase_filter": "Seed",
        "expected_ids": {2}
    },
]

def calculate_metrics(retrieved_ids: list, expected_ids: Set[int]):
    retrieved_set = set(retrieved_ids)
    expected_set = set(expected_ids)
    
    true_positives = retrieved_set.intersection(expected_set)
    tp_count = len(true_positives)
    
    precision = tp_count / len(retrieved_set) if retrieved_set else 0.0
    recall = tp_count / len(expected_set) if expected_set else 0.0
    
    return precision, recall

@pytest.mark.parametrize("case", SEARCH_TEST_CASES, ids=[c["description"] for c in SEARCH_TEST_CASES])
def test_optimized_search_logic_metrics(case: Dict[str, Any]):
    
    expected_ids = case["expected_ids"]
    
    # Executar a busca
    retrieved_companies = TEST_ENGINE.optimized_search(
        query=case['query'], 
        fase=case.get('fase_filter')
    )
    
    retrieved_ids = [company.id for company in retrieved_companies]
    
    precision, recall = calculate_metrics(retrieved_ids, expected_ids)

    print(f"\n--- Teste Lógico: {case['description']} ---")
    print(f"Query: {case['query']}")
    print(f"IDs Esperados: {expected_ids}")
    print(f"IDs Retornados: {retrieved_ids}")
    
    # Validar com HTTPStatus (simbolicamente, sucesso na busca)
    status_busca = HTTPStatus.OK if retrieved_ids else HTTPStatus.NOT_FOUND
    
    # Se esperávamos encontrar algo, o status deve ser OK
    if expected_ids:
        assert status_busca == HTTPStatus.OK, "Deveria ter encontrado resultados (HTTP 200)"
        assert recall >= 1.0, f"Falha: Não encontrou a empresa esperada. Retornou: {retrieved_ids}"
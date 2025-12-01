import pytest
from http import HTTPStatus # Importar HTTPStatus
from ..app.search_engine import SearchEngine
#from ..app import models as models_app 


# --- MOCK CLASS ---
# Definida localmente para não depender do models.py e evitar erro de 'id'
class MockEmpresa:
    def __init__(self, id, nome_da_empresa, solucao, setor_principal, setor_secundario, fase_da_startup="Operação", **kwargs):
        self.id = id
        self.nome_da_empresa = nome_da_empresa
        self.solucao = solucao
        self.setor_principal = setor_principal
        self.setor_secundario = setor_secundario
        self.fase_da_startup = fase_da_startup


# Dados de Mock Específicos para Teste de Plurais
MOCK_PLURAL_DATA = [
    {
        "id": 1, "nome_da_empresa": "HealthCorp", 
        # A palavra chave aqui é "nutricionistas" (PLURAL)
        "solucao": "Plataforma para conectar nutricionistas aos pacientes.", 
        "setor_principal": "Saúde", "setor_secundario": "Bem-estar",
        "fase_da_startup": "Operação", "cnpj": "11.111.111/0001-11", "endereco": "A", "ano_de_fundacao": 2024, "site": "a", "rede_social": "a", "cadastrado_por": "a", "cargo": "a", "email": "a", "colaboradores": "a", "publico_alvo": "a", "modelo_de_negocio": "a", "recebeu_investimento": "a", "negocios_no_exterior": "a", "faturamento": "a", "patente": "a", "ja_pivotou": "a", "comunidades": "a", 
        "link_apresentacao": None, "link_video": None, "telefone_contato": None
    },
    {
        "id": 2, "nome_da_empresa": "TechDev", 
        "solucao": "Desenvolvimento de software.", 
        "setor_principal": "TI", "setor_secundario": "Dev",
        "fase_da_startup": "Operação", "cnpj": "22.222.222/0001-22", "endereco": "A", "ano_de_fundacao": 2024, "site": "a", "rede_social": "a", "cadastrado_por": "a", "cargo": "a", "email": "a", "colaboradores": "a", "publico_alvo": "a", "modelo_de_negocio": "a", "recebeu_investimento": "a", "negocios_no_exterior": "a", "faturamento": "a", "patente": "a", "ja_pivotou": "a", "comunidades": "a", 
        "link_apresentacao": None, "link_video": None, "telefone_contato": None
    },
    {
        "id": 3, "nome_da_empresa": "NutriOne", 
        # A palavra chave aqui é "nutricionista" (SINGULAR)
        "solucao": "Sou um nutricionista focado em desporto.", 
        "setor_principal": "Saúde", "setor_secundario": "Sport",
        "fase_da_startup": "Operação", "cnpj": "33.333.333/0001-33", "endereco": "A", "ano_de_fundacao": 2024, "site": "a", "rede_social": "a", "cadastrado_por": "a", "cargo": "a", "email": "a", "colaboradores": "a", "publico_alvo": "a", "modelo_de_negocio": "a", "recebeu_investimento": "a", "negocios_no_exterior": "a", "faturamento": "a", "patente": "a", "ja_pivotou": "a", "comunidades": "a", 
        "link_apresentacao": None, "link_video": None, "telefone_contato": None
    }
]

MOCK_COMPANIES = [MockEmpresa(**data) for data in MOCK_PLURAL_DATA]

def test_search_singular_finds_plural():
    """
    pesquisar (singular) encontra empresa
    que tem (plural) na descrição.
    """
    # 1. Inicializar Engine
    engine = SearchEngine(MOCK_COMPANIES)

    # 2. Pesquisar SINGULAR

    resultados = engine.optimized_search("nutricionista")

    # 3. Validar com HTTPStatus
    # não  vazia, (200 OK)
   
    status_obtido = HTTPStatus.OK if resultados else HTTPStatus.NOT_FOUND
    
    assert status_obtido == HTTPStatus.OK, "(HTTP 200)"
    
    ids_encontrados = [c.id for c in resultados]
    assert 1 in ids_encontrados#, f"Deveria ter encontrado a HealthCorp (ID 1). Encontrou: {ids_encontrados}"
    
    # A empresa #3 (NutriOne) tem "nutricionista" (singular), também deve ser encontrada
    assert 3 in ids_encontrados

def test_search_plural_finds_singular():
    """
    Teste inverso: (plural) encontra (singular).
    """
    engine = SearchEngine(MOCK_COMPANIES)
    
    # Pesquisar  PLURAL
    resultados = engine.optimized_search("nutricionistas")
    
    # Validar com HTTPStatus
    status_obtido = HTTPStatus.OK if resultados else HTTPStatus.NOT_FOUND
    
    assert status_obtido == HTTPStatus.OK#, "(HTTP 200)"
    
    ids_encontrados = [c.id for c in resultados]
    
    # A empresa #3 tem "nutricionista" (singular) na solução.
    assert 3 in ids_encontrados#, f"Deveria ter encontrado a NutriOne (ID 3). Encontrou: {ids_encontrados}"
    assert 1 in ids_encontrados
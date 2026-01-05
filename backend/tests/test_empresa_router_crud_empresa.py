import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from http import HTTPStatus

# Importar a aplicação e os componentes necessários
from ..app.main import app
from ..app.database import get_db, table_registry
from ..app import models
from ..app.security import get_current_user

# --- Configuração do Banco de Dados de Teste (SQLite em memória) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Cria um banco de dados limpo e popula com um usuário e uma empresa de teste.
    Respeita a ordem dos campos obrigatórios definida no models.py.
    """
    connection = engine.connect()
    trans = connection.begin()
    table_registry.metadata.create_all(bind=connection)
    db = TestingSessionLocal(bind=connection)

    try:
        # 1. Criar usuário para o Mock de Autenticação
        test_user = models.Usuario(
            email="pytest@mti.com", 
            senha_hash="hash_ficticio"
        )
        db.add(test_user)
        
        # 2. Criar empresa base seguindo a ordem do models.py
        # Campos obrigatórios primeiro, opcionais depois
        test_empresa = models.Empresa(
            nome_da_empresa="Empresa de Teste Original",
            endereco="Rua dos Testes, 100",
            cnpj="00.000.000/0001-00",
            ano_de_fundacao=2024,
            email="contato@original.com", # Obrigatório
            setor_principal="Tecnologia",
            setor_secundario="Software",
            fase_da_startup="Operação",
            colaboradores="11-50",
            publico_alvo="B2B",
            modelo_de_negocio="SaaS",
            recebeu_investimento="Não",
            negocios_no_exterior="Não",
            faturamento="R$ 100k - 500k",
            patente="Não",
            ja_pivotou="Não",
            comunidades="MTI",
            solucao="Solução inicial de teste.",
            # Opcionais (default=None)
            site="https://original.com",
            tag="teste_unitario"
        )
        db.add(test_empresa)
        db.commit()
        db.refresh(test_empresa) 
        db.refresh(test_user)
        
        yield db, test_empresa, test_user
        
    finally:
        db.close()
        trans.rollback()
        table_registry.metadata.drop_all(bind=connection)
        connection.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """
    Cria um cliente de teste com overrides para o banco e para o usuário logado.
    """
    db, _, test_user = db_session

    def override_get_db():
        yield db

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as c:
        yield c
        
    app.dependency_overrides.clear()


# --- TESTES CRUD ---

def test_create_empresa_success(client: TestClient):
    """Testa a criação de uma empresa via POST /empresa/"""
    payload = {
        "nome_da_empresa": "Nova Startup Criada",
        "endereco": "Av. Inovação, 999",
        "cnpj": "11.111.111/0001-11",
        "ano_de_fundacao": 2025,
        "email": "contato@nova.com", # Obrigatório no Create
        "setor_principal": "Fintech",
        "setor_secundario": "Banking",
        "fase_da_startup": "Seed",
        "colaboradores": "1-10",
        "publico_alvo": "B2C",
        "modelo_de_negocio": "Transacional",
        "recebeu_investimento": "Sim",
        "negocios_no_exterior": "Não",
        "faturamento": "R$ 0",
        "patente": "Não",
        "ja_pivotou": "Não",
        "comunidades": "Nenhuma",
        "solucao": "Solução de pagamentos rápidos."
    }
    
    response = client.post("/empresa/", json=payload)
    
    assert response.status_code == HTTPStatus.CREATED, response.text
    data = response.json()
    assert data["nome_da_empresa"] == "Nova Startup Criada"
    assert "id" in data

def test_read_all_empresas(client: TestClient, db_session):
    """Testa a listagem de empresas GET /empresa/"""
    response = client.get("/empresa/")
    
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["nome_da_empresa"] == "Empresa de Teste Original" 

def test_read_single_empresa(client: TestClient, db_session):
    """Testa a busca de uma empresa específica GET /empresa/{id}"""
    _, test_empresa, _ = db_session
    
    response = client.get(f"/empresa/{test_empresa.id}")
    
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["id"] == test_empresa.id
    assert data["nome_da_empresa"] == test_empresa.nome_da_empresa

def test_update_empresa_success(client: TestClient, db_session):
    """Testa a atualização parcial via PUT /empresa/{id}"""
    db, test_empresa, _ = db_session
    
    update_payload = {
        "nome_da_empresa": "Nome Atualizado via API",
        "fase_da_startup": "Scale-up",
        "telefone_contato": "(11) 99999-9999" # Validador deve passar
    }
    
    response = client.put(f"/empresa/{test_empresa.id}", json=update_payload)
    
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["nome_da_empresa"] == "Nome Atualizado via API"
    assert data["fase_da_startup"] == "Scale-up"
    assert data["telefone_contato"] == "(11) 99999-9999"

def test_delete_empresa_success(client: TestClient, db_session):
    """Testa a exclusão de uma empresa DELETE /empresa/{id}"""
    _, test_empresa, _ = db_session
    empresa_id = test_empresa.id
    
    # Deletar
    response = client.delete(f"/empresa/{empresa_id}")
    assert response.status_code in [HTTPStatus.OK, HTTPStatus.NO_CONTENT]
    
    # Verificar se sumiu
    response_check = client.get(f"/empresa/{empresa_id}")
    assert response_check.status_code == HTTPStatus.NOT_FOUND

def test_create_empresa_invalid_cnpj(client: TestClient):
    """Exemplo de teste de erro: Criar com dados faltando (ano_de_fundacao)"""
    payload = {
        "nome_da_empresa": "Erro de Validação",
        "cnpj": "99.999.999/0001-99"
        # Faltam campos obrigatórios do EmpresaCreate
    }
    
    response = client.post("/empresa/", json=payload)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY # 422,
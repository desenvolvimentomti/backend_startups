import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Importar a app principal e as dependências
from ..app.main import app
from ..app.database import get_db, table_registry
from ..app import models

# --- Configuração do Banco de Dados de Teste (SQLite em memória) ---
# (Exatamente o mesmo setup do test_upload_endpoint.py)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Fixture reutilizada do test_upload_endpoint.py.
    Cria um banco de dados limpo e uma Empresa de teste para cada teste.
    """
    
    connection = engine.connect()
    trans = connection.begin()
    table_registry.metadata.create_all(bind=connection)
    db = TestingSessionLocal(bind=connection)

    try:
        test_empresa = models.Empresa(
            nome_da_empresa="Empresa de Teste (Midia)",
            endereco="Rua do Teste, 123",
            cnpj="00.000.000/0001-11",
            ano_de_fundacao=2024,
            site="https://teste-midia.com",
            rede_social="https://linkedin.com/teste-midia",
            cadastrado_por="pytest",
            cargo="Tester",
            email="teste@empresa-midia.com",
            setor_principal="Tecnologia",
            setor_secundario="SaaS",
            fase_da_startup="Operação",
            colaboradores="1-10",
            publico_alvo="B2B",
            modelo_de_negocio="Assinatura",
            recebeu_investimento="Não",
            negocios_no_exterior="Não",
            faturamento="R$ 100.000+",
            patente="Não",
            ja_pivotou="Não",
            comunidades="Nenhuma",
            solucao="Solução de teste.",
            link_apresentacao = None,
            link_video= None,
            telefone_contato= None,
            tag= None    
        
        )
        db.add(test_empresa)
        db.commit()
        db.refresh(test_empresa) 
        
        yield db, test_empresa 
        
    finally:
        db.close()
        trans.rollback()
        table_registry.metadata.drop_all(bind=connection)
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Fixture reutilizada. Cria um TestClient que usa o banco de dados de teste.
    """
    
    def override_get_db():
        db, _ = db_session
        try:
            yield db
        finally:
            pass # A fixture 'db_session' trata de fechar

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()


# --- Testes para o empresa_router ---

def test_get_empresa_midia_success(client: TestClient, db_session: Session):
    """
    Testa o GET /empresa/{id}/midia (Caminho Feliz)
    """
    db, test_empresa = db_session
    
    response = client.get(f"/empresa/{test_empresa.id}/midia")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verifica se o schema EmpresaMidiaResponse foi aplicado
    assert "link_apresentacao" in data
    assert "link_video" in data
    assert "telefone_contato" in data
    assert "nome_da_empresa" not in data # Garante que só os campos de midia vieram
    
    # Verifica se os valores iniciais (nulos) estão corretos
    assert data["link_apresentacao"] is None
    assert data["telefone_contato"] is None

def test_get_empresa_midia_not_found(client: TestClient, db_session: Session):
    """
    Testa o GET /empresa/{id}/midia para um ID que não existe
    """
    response = client.get("/empresa/99999/midia")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Empresa não encontrada"

def test_update_empresa_midia_success(client: TestClient, db_session: Session):

    """
    Testa as rotas PATCH específicas: /video e /telefone.
    Adaptado para chamar endpoints separados, já que o router não tem update unificado.
    """
    db, test_empresa = db_session
    
    # 1. Atualizar Vídeo
    video_payload = {"link_video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    resp_video = client.patch(
        f"/empresa/{test_empresa.id}/video",
        json=video_payload
    )
    assert resp_video.status_code == 200
    assert resp_video.json()["link_video"] == video_payload["link_video"]

    # 2. Atualizar Telefone
    phone_payload = {"telefone_contato": "(11) 98765-4321"}
    resp_phone = client.patch(
        f"/empresa/{test_empresa.id}/telefone",
        json=phone_payload
    )
    assert resp_phone.status_code == 200
    assert resp_phone.json()["telefone_contato"] == phone_payload["telefone_contato"]
    
    # 3. Verificar persistência no banco
    db.refresh(test_empresa)
    assert test_empresa.link_video == video_payload["link_video"]
    assert test_empresa.telefone_contato == phone_payload["telefone_contato"]
    assert test_empresa.link_apresentacao is None # Não mexemos neste

def test_update_empresa_midia_validation_error(client: TestClient, db_session: Session):
    """
    Testa se o POST /empresa/{id}/midia usa os validadores do schemas.py
    """
    db, test_empresa = db_session
    
    # Enviar um telefone com formato inválido
    invalid_data = {
        "telefone_contato": "123456789"
    }
    
    response = client.patch(
        f"/empresa/{test_empresa.id}/telefone",
        json=invalid_data
    )
    
    # 422 é o código do FastAPI para Erro de Validação Pydantic
    assert response.status_code == 422 
    assert "O telefone deve estar no formato (99) 99999-9999" in response.text

def test_update_empresa_midia_not_found(client: TestClient, db_session: Session):
    """
    Testa o POST /empresa/{id}/midia para um ID que não existe
    """
    data_to_update = {
        "link_video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
    
    response = client.patch(
        "/empresa/99999/video",
        json=data_to_update
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Empresa não encontrada"

    # Teste  DELETE 
def test_delete_empresa_video(client: TestClient, db_session: Session):
    db, test_empresa = db_session
    
    # Primeiro define um valor
    test_empresa.link_video = "https://youtube.com/test"
    db.commit()
    
    response = client.delete(f"/empresa/{test_empresa.id}/video")
    
    assert response.status_code == 204
    
    db.refresh(test_empresa)
    assert test_empresa.link_video is None
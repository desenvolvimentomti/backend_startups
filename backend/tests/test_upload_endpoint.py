import pytest
import os
import io
import shutil
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session  # Importar Session
from typing import Generator

# Importar a app principal e as dependências
from ..app.main import app
from ..app.database import get_db, table_registry
from ..app import models

# --- Configuração do Banco de Dados de Teste (SQLite em memória) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} # Necessário para SQLite
)

# Criamos a Sessionmaker, mas NÃO a ligamos (bind) ao engine ainda
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)

# --- Diretório de Uploads para Teste ---
TEST_UPLOADS_DIR = "static/uploads"
os.makedirs(TEST_UPLOADS_DIR, exist_ok=True)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Cria um banco de dados limpo em memória para cada função de teste.
    Garante que as tabelas e a sessão usem a MESMA conexão.
    """
    
    # 1. Criar uma CONEXÃO
    connection = engine.connect()
    
    # 2. Iniciar uma transação
    trans = connection.begin()
    
    # 3. Criar as tabelas NESSA conexão
    table_registry.metadata.create_all(bind=connection)

    # 4. Criar a sessão LIGADA (bind) a essa conexão específica
    db = TestingSessionLocal(bind=connection)

    try:
        # Criamos uma empresa de teste VÁLIDA
        test_empresa = models.Empresa(
            nome_da_empresa="Empresa de Teste para Upload",
            endereco="Rua do Teste, 123",
            cnpj="00.000.000/0001-99",
            ano_de_fundacao=2024,
            site="https://teste.com",
            rede_social="https://linkedin.com/teste",
            cadastrado_por="pytest",
            cargo="Tester",
            email="teste@empresa.com",
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
            solucao="Solução de teste."
        )
        db.add(test_empresa)
        db.commit()
        db.refresh(test_empresa) 
        
        # 5. Entregar a sessão e a empresa (agora na mesma conexão)
        yield db, test_empresa 
        
    finally:
        # 6. Limpeza
        db.close()
        # Reverter a transação e apagar tabelas
        trans.rollback()
        table_registry.metadata.drop_all(bind=connection)
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Cria um TestClient que usa o banco de dados de teste (na conexão correta).
    """
    
    def override_get_db():
        """Função interna para sobrescrever a dependência get_db."""
        db, _ = db_session # Pega o 'db' da fixture
        try:
            yield db
        finally:
            # Não fechamos o 'db' aqui; a fixture 'db_session' trata disso.
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()


# --- Testes (NÃO PRECISAM DE MUDANÇA) ---

def test_upload_presentation_local_success(client: TestClient, db_session: Session):
    """
    Testa o upload bem-sucedido de um arquivo .pdf.
    """
    db, test_empresa = db_session # Pega a empresa criada na fixture (com id=1)
    
    # Criar um arquivo .pdf falso em memória
    fake_pdf_content = b"%PDF-1.0..." # Conteúdo binário simples
    fake_file = io.BytesIO(fake_pdf_content)
    
    caminho_arquivo_salvo = None
    
    try:
        # Simular o POST do form-data
        response = client.post(
            f"/upload/apresentacao/{test_empresa.id}", # Usa o ID dinâmico
            files={"file": ("teste.pdf", fake_file, "application/pdf")}
        )
        
        # 1. Verificar a Resposta da API
        assert response.status_code == 200, response.text
        data = response.json()
        assert "link_apresentacao" in data
        
        file_url = data["link_apresentacao"]
        assert file_url is not None
        assert file_url.startswith("http://testserver/static/uploads/")
        assert file_url.endswith(".pdf")
        
        file_name = file_url.split("/")[-1]
        caminho_arquivo_salvo = os.path.join(TEST_UPLOADS_DIR, file_name)

        # 2. Verificar se Salvo Fisicamente
        assert os.path.exists(caminho_arquivo_salvo)
        
        # 3. Verificar  BD se esta Atualizado
        db.refresh(test_empresa) # Recarregar dados do BD
        assert test_empresa.link_apresentacao == file_url

    finally:
        # 4. Limpeza: 
        if caminho_arquivo_salvo and os.path.exists(caminho_arquivo_salvo):
            os.remove(caminho_arquivo_salvo)

def test_upload_file_invalid_mime_type(client: TestClient, db_session: Session):
    """
    Testa a falha ao tentar dar upload de um tipo de arquivo não permitido (ex: .txt).
    """
    db, test_empresa = db_session
    
    fake_txt_content = b"isso e um teste"
    fake_file = io.BytesIO(fake_txt_content)
    
    response = client.post(
        f"/upload/apresentacao/{test_empresa.id}",
        files={"file": ("teste.txt", fake_file, "text/plain")}
    )
    
    assert response.status_code == 400
    assert "Tipo de arquivo não permitido" in response.json()["detail"]

def test_upload_to_non_existent_empresa(client: TestClient, db_session: Session):
    """
    Testa a falha ao tentar dar upload para uma empresa que não existe.
    """
    fake_pdf_content = b"%PDF-1.0..."
    fake_file = io.BytesIO(fake_pdf_content)
    
    response = client.post(
        "/upload/apresentacao/99999", # ID que não existe
        files={"file": ("teste.pdf", fake_file, "application/pdf")}
    )
    
    assert response.status_code == 404
    assert "Empresa não encontrada" in response.json()["detail"]
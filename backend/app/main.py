import uvicorn
import nltk
import warnings

warnings.filterwarnings(
    "ignore", 
    message="The parameter 'token_pattern' will not be used since 'tokenizer' is not None", 
    category=UserWarning
)
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from contextlib import asynccontextmanager

# --- para StaticFiles ---
import os
from fastapi.staticfiles import StaticFiles
# -----
# Importar text para comandos SQL puros
from sqlalchemy import text 
# -----

from .search_engine import SearchEngine
from .database import engine,  get_db, table_registry # Base,
from . import models, security, schemas, crud
from .routers import upload_router, empresa_router
from .schemas import UserLogin


# --- ADICIONADO: Configuração do Diretório Estático ---
# Deve corresponder ao STATIC_DIR no upload_router.py
STATIC_DIR = "static"
# Garante que o diretório base exista
os.makedirs(STATIC_DIR, exist_ok=True)
# ------

search_engine_instance: Optional[SearchEngine] = None

def sync_database_sequences():
    """
    Sincroniza automaticamente o contador de IDs (Sequence) com o valor máximo da tabela.
    Funciona para SQLite e PostgreSQL.
    """
    db_type = engine.name # 'postgresql' ou 'sqlite'
    
    with engine.connect() as connection:
        try:
            if db_type == "postgresql":
                print("Sincronizando sequências no PostgreSQL (Render)...")
                # alinhar a sequência do Postgres com o MAX(id)
                query = text("""
                    SELECT setval(
                        pg_get_serial_sequence('startups', 'id'), 
                        COALESCE((SELECT MAX(id) FROM startups), 1), 
                        (SELECT MAX(id) FROM startups) IS NOT NULL
                    )
                """)
                connection.execute(query)
                connection.commit()
                
            elif db_type == "sqlite":
                print("Sincronizando sequências no SQLite (Local)...")
                # No SQLite, atualizamos a tabela interna sqlite_sequence
                query = text("""
                    UPDATE sqlite_sequence 
                    SET seq = (SELECT MAX(id) FROM startups) 
                    WHERE name = 'startups'
                """)
                connection.execute(query)
                connection.commit()
            
            print("Sincronização concluída com sucesso!")
        except Exception as e:
            # Se a tabela ainda não existir (primeiro boot), o erro é ignorado silenciosamente
            print(f"Nota: Sincronização de sequência ignorada ou falhou: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global search_engine_instance
    
    # --- CORREÇÃO: INVERSÃO DE LÓGICA ---
    # Bloco 1: CRIAR as tabelas primeiro.
    # ligar ao DB 
    print("Iniciando a criação das tabelas do banco de dados...")
    try:
        table_registry.metadata.create_all(bind=engine)
        print("Banco de dados e tabelas criadas com sucesso!")
    except Exception as e:
        print(f"Erro na criação das tabelas do BD: {e}")
        # Se isto falhar (ex: má conexão), a app não deve arrancar.
        raise RuntimeError(f"Falha na criação das tabelas: {e}")
    
    # AUTO-SINCRONIZAÇÃO DE IDS 
    # Executamos logo após garantir que as tabelas existem
    sync_database_sequences()
    # ------
    # Bloco 2: LER as tabelas (agora que existem) para o NLTK.
    print("Verificando e baixando recursos do NLTK...")
    try:
        nltk.download('punkt', quiet=True) 
        nltk.download('stopwords', quiet=True)
        nltk.download('rslp', quiet=True) 
        print("Recursos do NLTK prontos com sucesso!")
        
        db = next(get_db())

        # USANDO CRUD
        all_companies_list = crud.get_all_empresas(db)
        
        # (Agora 'all_companies_list' será uma lista vazia [] caso não exista antes, 
        # o que está correto)
        
        if all_companies_list:
            search_engine_instance = SearchEngine(all_companies_list)
            print("Índice TF-IDF criado com sucesso!")
        else:
            print("Banco de dados vazio, SearchEngine iniciado sem dados.")
        
    except Exception as e:
        print(f"Erro na inicialização do NLTK/TF-IDF: {e}")
        raise RuntimeError(f"Falha na inicialização: {e}")
    # --- FIM DA CORREÇÃO ---
        
    yield
    print("Aplicação encerrada.")


app = FastAPI(title="API de Pesquisa de Startups", lifespan=lifespan)

# --- Montar Roteadores ---
app.include_router(upload_router.router, tags=["Uploads"])
app.include_router(empresa_router.router)


@app.post("/register", response_model=schemas.Token)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Lógica de banco de dados movida para crud.py
    db_user = crud.get_user_by_email(db, email=user_data.email)
    #db_user = db.query(models.Usuario).filter(models.Usuario.email == user_data.email).first()

    if db_user:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")
    # Lógica de banco de dados movida para crud.py
    new_user = crud.create_user(db=db, user=user_data)

    #hashed_password = security.hash_password(user_data.password)
    #new_user = models.Usuario(email=user_data.email, senha_hash=hashed_password)
    #db.add(new_user)
    #db.commit()
    #db.refresh(new_user)
    
    access_token = security.create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/token/json", response_model=schemas.Token)
def login_with_json(user_data: UserLogin, db: Session = Depends(get_db)):

    # Lógica de banco de dados movida para crud.py
    user = crud.get_user_by_email(db, email=user_data.email)
    #user = db.query(models.Usuario).filter(models.Usuario.email == user_data.email).first()

    if not user or not security.verify_password(user_data.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/token", response_model=schemas.Token)
def login_with_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

    # Lógica de banco de dados movida para crud.py
    user = crud.get_user_by_email(db, email=form_data.username)
    #user = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()

    if not user or not security.verify_password(form_data.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/companies", response_model=List[schemas.Empresa], status_code=status.HTTP_200_OK)
def list_all_companies(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_user)
):
    # Lógica de banco de dados movida para crud.py
    results = crud.get_all_empresas(db)
    #results = db.query(models.Empresa).all()
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma empresa encontrada no sistema.")
    return results


@app.get("/optimized_search", response_model=List[schemas.Empresa], status_code=status.HTTP_200_OK)
def optimized_search_companies(
    query: str,
    fase: Optional[str] = None,
    current_user: schemas.User = Depends(security.get_current_user)
):
    global search_engine_instance
    
    if search_engine_instance is None:
        raise HTTPException(
             status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
             detail="O serviço de busca ainda não foi inicializado ou falhou ao carregar o índice."
        )

    results = search_engine_instance.optimized_search(query=query, fase=fase)

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma startup encontrada com a sua pesquisa."
        )
    
    return results


# --- ADICIONADO: Montar o diretório estático ---

app.mount(f"/{STATIC_DIR}", StaticFiles(directory=STATIC_DIR), name="static")

## http://127.0.0.1:8000/docs
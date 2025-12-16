import uvicorn
import nltk
import warnings

from .routers import empresa_router, upload_router 
warnings.filterwarnings(
    "ignore", 
    message="The parameter 'token_pattern' will not be used since 'tokenizer' is not None", 
    category=UserWarning
)
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from contextlib import asynccontextmanager

# --- para StaticFiles ---
import os
from fastapi.staticfiles import StaticFiles

# -----

from .search_engine import SearchEngine
from .database import engine,  get_db, table_registry # Base,
from . import models, security, schemas, crud, semantic_search
from .routers import upload_router, empresa_router
from .schemas import UserLogin






# --- ADICIONADO: Configuração do Diretório Estático ---
# Deve corresponder ao STATIC_DIR no upload_router.py
STATIC_DIR = "static"
# Garante que o diretório base exista
os.makedirs(STATIC_DIR, exist_ok=True)
# --- FIM ADICIONADO ---


search_engine_instance: Optional[SearchEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global search_engine_instance
    
    # --- CORREÇÃO: INVERSÃO DE LÓGICA ---
    # Bloco 1: CRIAR as tabelas primeiro.
    # ligar ao DB
    print("Iniciando a criação das tabelas do banco de dados...")
    try:
        # NOTE: create_all() only creates tables that don't exist, it doesn't modify existing ones.
        # If you need to modify the schema, use migrations (e.g., Alembic)
        table_registry.metadata.create_all(bind=engine)
        print("Banco de dados e tabelas criadas com sucesso!")
    except Exception as e:
        print(f"Erro na criação das tabelas do BD: {e}")
        # Se isto falhar (ex: má conexão), a app não deve arrancar.
        raise RuntimeError(f"Falha na criação das tabelas: {e}")
        
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

        # Filtrar valores None que podem aparecer na lista
        all_companies_list = [c for c in all_companies_list if c is not None]

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


@app.get("/companies", response_model=Union[List[schemas.Empresa], List[schemas.EmpresaPublic]], status_code=status.HTTP_200_OK)
def list_all_companies(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_user)
):
    """
    Lista todas as empresas do sistema.
    RBAC: Todos os roles autenticados (ADMIN, MAINTAINER, USER).
    Field-level access: USER role recebe apenas campos públicos (sem dados sensíveis).
    """
    # Lógica de banco de dados movida para crud.py
    results = crud.get_all_empresas(db)
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma empresa encontrada no sistema.")

    # Field-level authorization: USER role gets filtered data
    if security.can_view_sensitive_fields(current_user):
        # ADMIN and MAINTAINER see all fields
        return [schemas.Empresa.model_validate(empresa) for empresa in results]
    else:
        # USER role sees only public fields
        return [schemas.EmpresaPublic.model_validate(empresa) for empresa in results]


@app.get("/optimized_search", response_model=Union[List[schemas.Empresa], List[schemas.EmpresaPublic]], status_code=status.HTTP_200_OK)
def optimized_search_companies(
    query: str,
    fase: Optional[str] = None,
    current_user: schemas.User = Depends(security.get_current_user)
):
    """
    Busca otimizada de empresas usando TF-IDF.
    RBAC: Todos os roles autenticados (ADMIN, MAINTAINER, USER).
    Field-level access: USER role recebe apenas campos públicos (sem dados sensíveis).
    """
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

    # Field-level authorization: USER role gets filtered data
    if security.can_view_sensitive_fields(current_user):
        # ADMIN and MAINTAINER see all fields
        return [schemas.Empresa.model_validate(empresa) for empresa in results]
    else:
        # USER role sees only public fields
        return [schemas.EmpresaPublic.model_validate(empresa) for empresa in results]


@app.get("/semantic-search", response_model=Union[List[schemas.Empresa], List[schemas.EmpresaPublic]], status_code=status.HTTP_200_OK)
def semantic_search_companies(
    query: str,
    top_k: int = 10,
    similarity_threshold: float = 0.5,
    use_query_expansion: bool = True,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_user)
):
    """
    Semantic search usando embeddings OpenAI + pgvector + LLM query expansion.
    Busca empresas por significado semântico, não apenas palavras-chave.

    RBAC: Todos os roles autenticados (ADMIN, MAINTAINER, USER).
    Field-level access: USER role recebe apenas campos públicos (sem dados sensíveis).

    Args:
        query: Natural language query (e.g., "sou fazendeiro e preciso de dinheiro")
        top_k: Number of results to return (default: 10, max: 50)
        similarity_threshold: Minimum similarity score 0-1 (default: 0.5)
        use_query_expansion: Use LLM to expand query for better results (default: True)
    """
    # Validate parameters
    if top_k > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k cannot exceed 50"
        )

    if similarity_threshold < 0 or similarity_threshold > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="similarity_threshold must be between 0 and 1"
        )

    # Check if OpenAI API key is configured
    import os
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search not configured. OpenAI API key missing."
        )

    # Perform semantic search
    try:
        results = semantic_search.semantic_search(
            query=query,
            db=db,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            use_query_expansion=use_query_expansion
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma startup encontrada com a sua pesquisa semântica."
        )

    # Field-level authorization: USER role gets filtered data
    if security.can_view_sensitive_fields(current_user):
        # ADMIN and MAINTAINER see all fields
        return [schemas.Empresa.model_validate(empresa) for empresa in results]
    else:
        # USER role sees only public fields
        return [schemas.EmpresaPublic.model_validate(empresa) for empresa in results]


# --- RBAC: User Role Management (Admin Only) ---

@app.patch("/users/{user_id}/role", response_model=schemas.User)
def update_user_role(
    user_id: int,
    role_update: schemas.UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin)
):
    """
    Atualiza a role de um usuário.
    RBAC: Apenas ADMIN pode executar esta operação.
    """
    # Get the target user
    target_user = crud.get_user_by_id(db, user_id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    # Update the role
    target_user.role = role_update.role
    db.commit()
    db.refresh(target_user)

    return target_user


@app.get("/users/me", response_model=schemas.User)
def get_current_user_info(
    current_user: schemas.User = Depends(security.get_current_user)
):
    """
    Retorna informações do usuário autenticado, incluindo sua role.
    """
    return current_user


# --- ADICIONADO: Montar o diretório estático ---

app.mount(f"/{STATIC_DIR}", StaticFiles(directory=STATIC_DIR), name="static")

## http://127.0.0.1:8000/docs
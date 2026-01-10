from sqlalchemy.orm import Session
from typing import Optional
from . import models, schemas, security, embedding_service # Importamos security para o hashing

# --- Funções CRUD para Empresa ---


# --- (CREATE) ---

def create_empresa(db: Session, empresa: schemas.EmpresaCreate):
    """
    Cria uma nova empresa no banco de dados.
    Usado pelo 'empresa_router'.
    """
    # Converte o schema Pydantic para um dict
    empresa_data = empresa.model_dump()
    # Cria a instância do modelo SQLAlchemy
    db_empresa = models.Empresa(**empresa_data)

    # GERAÇÃO DO VETOR: Transforma os textos em tokens e salva na nova coluna
    db_empresa.embedding_vector = embedding_service.generate_embedding(db_empresa)

    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)

    return db_empresa


# --- ( READ ) ---

def get_empresa(db: Session, empresa_id: int):
    """
    Busca uma empresa pelo seu ID.

    """
    return db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()

def get_all_empresas(db: Session,  skip: int = 0, limit: Optional[int] = None):
    """
    Busca todas as empresas

    """
    #return db.query(models.Empresa).offset(skip).limit(limit).all()
    query = db.query(models.Empresa).offset(skip)
    if limit:
        query = query.limit(limit)
    return query.all()

# --- (UPDATE) ---

def update_empresa(db: Session, db_empresa: models.Empresa, empresa_data: schemas.EmpresaUpdate):
    """
    Atualiza uma empresa (atualização parcial).
    Usado pelo 'empresa_router'.
    """

    # Converte o Pydantic model para um dict, ignorando campos não enviados (ex: None)
    update_data = empresa_data.model_dump(exclude_unset=True)

    """Atualiza a empresa e regenera o vetor se campos de texto mudarem."""
    # Lista de campos que afetam a busca
    campos_busca = ['nome_da_empresa', 'solucao', 'setor_principal', 'setor_secundario', 'tag']
    mudou_texto = any(campo in update_data for campo in campos_busca)

    for key, value in update_data.items():
        setattr(db_empresa, key, value)

        # Se algum campo de texto mudou, precisamos atualizar a matriz de tokens
    if mudou_texto:
        db_empresa.embedding_vector = embedding_service.generate_embedding(db_empresa)
    
    db.commit()
    db.refresh(db_empresa)

    return db_empresa

# --- campos MIDIA (UPDATE) ---

def update_empresa_link(db: Session, empresa_id: int, link: str):
    """
    Atualiza o campo link_apresentacao de uma empresa específica.
    Usado pelo 'empresa_router'.

    """
    db_empresa = get_empresa(db, empresa_id=empresa_id)
    if db_empresa:
        db_empresa.link_apresentacao = link
        db.commit()
        db.refresh(db_empresa)
    return db_empresa

def update_empresa_link_apresentacao(db: Session, db_empresa: models.Empresa, link: Optional[str]):
    """
    Atualiza o link_apresentacao de uma empresa.
    Usado pelo 'empresa_router'.
    """

    db_empresa.link_apresentacao = link
    db.commit()
    db.refresh(db_empresa)

    return db_empresa

def update_empresa_link_video(db: Session, db_empresa: models.Empresa, link: Optional[str]):
    """
    Atualiza o link_video de uma empresa.
    Usado pelo 'empresa_router'.
    """

    db_empresa.link_video = link
    db.commit()
    db.refresh(db_empresa)

    return db_empresa

def update_empresa_telefone_contato(db: Session, db_empresa: models.Empresa, telefone: Optional[str]):
    """
    Atualiza o telefone_contato de uma empresa.
    Usado pelo 'empresa_router'.
    """

    db_empresa.telefone_contato = telefone
    db.commit()
    db.refresh(db_empresa)

    return db_empresa

# --- (DELETE) ---
def delete_empresa(db: Session, db_empresa: models.Empresa):
    """
    Deleta uma empresa INTEIRA  .
    Usado pelo 'empresa_router'.
    """

    db.delete(db_empresa)
    db.commit()
    #db.refresh(db_empresa)

    try:
        db.refresh(db_empresa)
    except Exception:
        # Silencia caso o objeto já não exista, não quebra a API
        pass

    return db_empresa

# --- Funções CRUD para Usuário ---

def get_user_by_email(db: Session, email: str):
    """
    Busca um usuário pelo seu e-mail.
    (Refatoração do seu endpoint /register e /token)
    """
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    """
    Cria um novo usuário no banco de dados com senha hasheada.
    (Refatoração do seu endpoint /register)
    """
    hashed_password = security.hash_password(user.password)
    db_user = models.Usuario(email=user.email, senha_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
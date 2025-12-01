from sqlalchemy.orm import Session
from typing import Optional
from . import models, schemas, security # Importamos security para o hashing

# --- Funções CRUD para Empresa ---

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

def update_empresa_link(db: Session, empresa_id: int, link: str):
    """
    Atualiza o campo link_apresentacao de uma empresa específica.

    """
    db_empresa = get_empresa(db, empresa_id=empresa_id)
    if db_empresa:
        db_empresa.link_apresentacao = link
        db.commit()
        db.refresh(db_empresa)
    return db_empresa

def update_empresa_link_apresentacao(db: Session, db_empresa: models.Empresa, link: Optional[str]):
    """Atualiza o link_apresentacao de uma empresa."""
    db_empresa.link_apresentacao = link
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

def update_empresa_link_video(db: Session, db_empresa: models.Empresa, link: Optional[str]):
    """Atualiza o link_video de uma empresa."""
    db_empresa.link_video = link
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

def update_empresa_telefone_contato(db: Session, db_empresa: models.Empresa, telefone: Optional[str]):
    """Atualiza o telefone_contato de uma empresa."""
    db_empresa.telefone_contato = telefone
    db.commit()
    db.refresh(db_empresa)
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
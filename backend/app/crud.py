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

def create_empresa(db: Session, empresa: schemas.EmpresaCreate):
    """
    Cria uma nova empresa no banco de dados.
    """
    db_empresa = models.Empresa(
        nome_da_empresa=empresa.nome_da_empresa,
        endereco=empresa.endereco,
        cnpj=empresa.cnpj,
        ano_de_fundacao=empresa.ano_de_fundacao,
        site=empresa.site or "",
        rede_social=empresa.rede_social or "",
        cadastrado_por=empresa.cadastrado_por or "",
        cargo=empresa.cargo or "",
        email=empresa.email or "",
        setor_principal=empresa.setor_principal,
        setor_secundario=empresa.setor_secundario,
        fase_da_startup=empresa.fase_da_startup,
        colaboradores=empresa.colaboradores,
        publico_alvo=empresa.publico_alvo,
        modelo_de_negocio=empresa.modelo_de_negocio,
        recebeu_investimento=empresa.recebeu_investimento,
        negocios_no_exterior=empresa.negocios_no_exterior,
        faturamento=empresa.faturamento,
        patente=empresa.patente,
        ja_pivotou=empresa.ja_pivotou,
        comunidades=empresa.comunidades,
        solucao=empresa.solucao,
        link_apresentacao=empresa.link_apresentacao,
        link_video=empresa.link_video,
        telefone_contato=empresa.telefone_contato,
        tag=empresa.tag
    )
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

def update_empresa(db: Session, empresa_id: int, empresa_update: schemas.EmpresaUpdate):
    """
    Atualiza todos os campos de uma empresa existente.
    Apenas os campos fornecidos (não None) serão atualizados.
    """
    db_empresa = get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        return None

    # Atualiza apenas os campos que foram fornecidos
    update_data = empresa_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_empresa, field, value)

    db.commit()
    db.refresh(db_empresa)
    return db_empresa

def delete_empresa(db: Session, empresa_id: int):
    """
    Deleta uma empresa do banco de dados.
    Retorna True se deletado com sucesso, False se não encontrado.
    """
    db_empresa = get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        return False

    db.delete(db_empresa)
    db.commit()
    return True




# --- Funções CRUD para Usuário ---

def get_user_by_email(db: Session, email: str):
    """
    Busca um usuário pelo seu e-mail.
    (Refatoração do seu endpoint /register e /token)
    """
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    """
    Busca um usuário pelo seu ID.
    (Usado para RBAC - atualização de roles)
    """
    return db.query(models.Usuario).filter(models.Usuario.id == user_id).first()


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
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Union


from .. import crud, schemas, security
from ..database import get_db

router = APIRouter(
    prefix="/empresa",  # Adiciona /empresa a todas as rotas
    tags=["Empresas"]    # Agrupa no Swagger UI
)

# --- CRUD Completo de Empresas ---

@router.post("", response_model=schemas.Empresa, status_code=status.HTTP_201_CREATED)
def create_empresa(
    empresa: schemas.EmpresaCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin_or_maintainer)
):
    """
    Cria uma nova startup no sistema.
    RBAC: Requer role ADMIN ou MAINTAINER.
    """
    # Verifica se CNPJ já existe
    existing_empresa = db.query(crud.models.Empresa).filter(
        crud.models.Empresa.cnpj == empresa.cnpj
    ).first()

    if existing_empresa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma empresa com este CNPJ já está cadastrada"
        )

    return crud.create_empresa(db=db, empresa=empresa)


@router.get("/{empresa_id}", response_model=Union[schemas.Empresa, schemas.EmpresaPublic])
def get_empresa_by_id(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_user)
):
    """
    Retorna os detalhes de uma startup pelo ID.
    RBAC: Todos os roles autenticados (ADMIN, MAINTAINER, USER).
    Field-level access: USER role recebe apenas campos públicos (sem dados sensíveis).
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )

    # Field-level authorization: USER role gets filtered data
    if security.can_view_sensitive_fields(current_user):
        # ADMIN and MAINTAINER see all fields
        return schemas.Empresa.model_validate(db_empresa)
    else:
        # USER role sees only public fields
        return schemas.EmpresaPublic.model_validate(db_empresa)


@router.put("/{empresa_id}", response_model=schemas.Empresa)
def update_empresa(
    empresa_id: int,
    empresa_update: schemas.EmpresaUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin_or_maintainer)
):
    """
    Atualiza os dados de uma startup existente.
    Apenas os campos fornecidos serão atualizados.
    RBAC: Requer role ADMIN ou MAINTAINER.
    """
    # Verifica se o CNPJ já está sendo usado por outra empresa
    if empresa_update.cnpj:
        existing_empresa = db.query(crud.models.Empresa).filter(
            crud.models.Empresa.cnpj == empresa_update.cnpj,
            crud.models.Empresa.id != empresa_id
        ).first()

        if existing_empresa:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este CNPJ já está sendo usado por outra empresa"
            )

    updated_empresa = crud.update_empresa(db, empresa_id=empresa_id, empresa_update=empresa_update)
    if not updated_empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    return updated_empresa


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin_or_maintainer)
):
    """
    Deleta uma startup do sistema permanentemente.
    RBAC: Requer role ADMIN ou MAINTAINER.
    """
    success = crud.delete_empresa(db, empresa_id=empresa_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Endpoints de Mídia (Parciais) ---

@router.get("/{empresa_id}/midia", response_model=schemas.EmpresaMidiaResponse)
def get_empresa_midia_links(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.get_current_user)
):
    """
    Retorna apenas os links de mídia e o telefone de uma empresa específica.
    RBAC: Todos os roles autenticados (ADMIN, MAINTAINER, USER).
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    # O schemas.EmpresaMidiaResponse 
    # irá filtra os campos que foram alterados.
    return db_empresa


@router.patch("/{empresa_id}/apresentacao", response_model=schemas.EmpresaMidiaResponse)
def update_empresa_apresentacao(
    empresa_id: int,
    data: schemas.SchemaLinkApresentacaoUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin_or_maintainer)
):
    """
    Atualiza APENAS o link de apresentação de uma empresa.
    O link é validado pelo schema.
    RBAC: Requer role ADMIN ou MAINTAINER.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    updated_empresa = crud.update_empresa_link_apresentacao(db, db_empresa=db_empresa, link=data.link_apresentacao)
    return updated_empresa

@router.patch("/{empresa_id}/video", response_model=schemas.EmpresaMidiaResponse)
def update_empresa_video(
    empresa_id: int,
    data: schemas.SchemaLinkVideoUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin_or_maintainer)
):
    """
    Atualiza APENAS o link de vídeo de uma empresa.
    O link é validado pelo schema.
    RBAC: Requer role ADMIN ou MAINTAINER.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    updated_empresa = crud.update_empresa_link_video(db, db_empresa=db_empresa, link=data.link_video)
    return updated_empresa

@router.patch("/{empresa_id}/telefone", response_model=schemas.EmpresaMidiaResponse)
def update_empresa_telefone(
    empresa_id: int,
    data: schemas.SchemaTelefoneUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin_or_maintainer)
):
    """
    Atualiza APENAS o telefone de contato de uma empresa.
    O telefone é validado pelo schema.
    RBAC: Requer role ADMIN ou MAINTAINER.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    updated_empresa = crud.update_empresa_telefone_contato(db, db_empresa=db_empresa, telefone=data.telefone_contato)
    return updated_empresa


@router.delete("/{empresa_id}/apresentacao", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa_apresentacao(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin_or_maintainer)
):
    """
    Remove (define como nulo) o link de apresentação de uma empresa.
    RBAC: Requer role ADMIN ou MAINTAINER.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    # Você usa a MESMA função de update, mas força o link como None
    # (Ou pode criar uma função crud.remove_link_apresentacao)
    crud.update_empresa_link_apresentacao(db, db_empresa=db_empresa, link=None)
    
    # Retorna 204 - No Content, que é o padrão para DELETE bem-sucedido
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete("/{empresa_id}/telefone", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa_telefone(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin_or_maintainer)
):
    """
    Remove (define como nulo) o link de apresentação de uma empresa.
    RBAC: Requer role ADMIN ou MAINTAINER.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    # Você usa a MESMA função de update, mas força o link como None
    # (Ou pode criar uma função crud.remove_link_apresentacao)
    crud.update_empresa_telefone_contato(db, db_empresa=db_empresa, telefone=None)
    
    # Retorna 204 - No Content, que é o padrão para DELETE bem-sucedido
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete("/{empresa_id}/video", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa_video(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(security.require_admin_or_maintainer)
):
    """
    Remove (define como nulo) o link de vídeo de uma empresa.
    RBAC: Requer role ADMIN ou MAINTAINER.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    # Você usa a MESMA função de update, mas força o link como None
    # (Ou pode criar uma função crud.remove_link_apresentacao)
    crud.update_empresa_link_video(db, db_empresa=db_empresa, link=None)
    
    # Retorna 204 - No Content, que é o padrão para DELETE bem-sucedido
    return Response(status_code=status.HTTP_204_NO_CONTENT)
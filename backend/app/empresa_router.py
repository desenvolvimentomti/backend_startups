from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from . import crud, schemas
from .database import get_db

# from .security import get_current_user

router = APIRouter(
    prefix="/empresa",  # Adiciona /empresa a todas as rotas
    tags=["Empresas"]    # Agrupa no Swagger UI
)

@router.get("/{empresa_id}/midia", response_model=schemas.EmpresaMidiaResponse)
def get_empresa_midia_links(
    empresa_id: int, 
    db: Session = Depends(get_db)
    
    # current_user: schemas.User = Depends(get_current_user) 
):
    """
    Retorna apenas os links de mídia e o telefone de uma empresa específica.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    # O schemas.EmpresaMidiaResponse 
    # irá filtra os campos que foram alterados.
    return db_empresa


@router.post("/{empresa_id}/midia", response_model=schemas.EmpresaMidiaResponse)
def update_empresa_midia_links(
    empresa_id: int,
    midia_data: schemas.EmpresaMidiaUpdate, # <-- Usa o novo schema de validação
    db: Session = Depends(get_db)
    
    # current_user: schemas.User = Depends(get_current_user)
):
    """
    Atualiza os links de mídia e/ou telefone de uma empresa.
    são validados no schemas.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    # A função crud fará a atualização parcial
    updated_empresa = crud.update_empresa_midia(db, db_empresa=db_empresa, midia_data=midia_data)
    
    return updated_empresa
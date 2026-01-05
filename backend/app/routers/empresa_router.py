from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List


from .. import crud, schemas, models
from ..database import get_db
from ..security import get_current_user

router = APIRouter(
    prefix="/empresa",  # Adiciona /empresa a todas as rotas
    tags=["Empresas"]    # Agrupa no Swagger UI
    
)

# --- ADICIONADO: Endpoint de CRUD para empresas   ---


# (Create)

@router.post("/", response_model=schemas.Empresa, status_code=status.HTTP_201_CREATED)
def create_new_empresa(
    empresa: schemas.EmpresaCreate, 
    db: Session = Depends(get_db),
    #current_user: schemas.User = Depends(get_current_user)  # adição para segurança 
):
    """
    Cria uma nova empresa no banco de dados.
    """
    # (Opcional: Verificar se o CNPJ já existe)
    # db_empresa = db.query(models.Empresa).filter(models.Empresa.cnpj == empresa.cnpj).first()
    # if db_empresa:
    #     raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
        
    return crud.create_empresa(db=db, empresa=empresa)

#(Read)

# --- (Read All) ---
@router.get("/", response_model=List[schemas.Empresa], status_code=status.HTTP_200_OK)
def list_all_companies(
    db: Session = Depends(get_db),
    #current_user: schemas.User = Depends(get_current_user)
):
    """
    Lista todas as empresas cadastradas no sistema.
    """
    return crud.get_all_empresas(db)

# --- (Read One) ---
@router.get("/{empresa_id}", response_model=schemas.Empresa)
def get_single_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    #current_user: schemas.User = Depends(get_current_user)
):
    """
    Retorna os dados completos de uma empresa específica pelo ID.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    return db_empresa



# --- Endpoints de Mídia (Já existentes) ---
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


#(Update)

@router.put("/{empresa_id}", response_model=schemas.Empresa)
def update_single_empresa(
    empresa_id: int,
    empresa_data: schemas.EmpresaUpdate,
    db: Session = Depends(get_db),
    #current_user: schemas.User = Depends(get_current_user)
):
    """
    Atualiza os campos de uma empresa. Envie apenas os campos que deseja alterar.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    # Este endpoint chama crud.update_empresa
    return crud.update_empresa(db=db, db_empresa=db_empresa, empresa_data=empresa_data)


# --- Endpoints de Mídia (Já existentes) ---

@router.patch("/{empresa_id}/apresentacao", response_model=schemas.EmpresaMidiaResponse)
def update_empresa_apresentacao(
    empresa_id: int,
    data: schemas.SchemaLinkApresentacaoUpdate,
    db: Session = Depends(get_db)
    # current_user: schemas.User = Depends(get_current_user)
):
    """
    Atualiza APENAS o link de apresentação de uma empresa.
    O link é validado pelo schema.
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
    db: Session = Depends(get_db)
    # current_user: schemas.User = Depends(get_current_user)
):
    """
    Atualiza APENAS o link de vídeo de uma empresa.
    O link é validado pelo schema.
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
    db: Session = Depends(get_db)
    # current_user: schemas.User = Depends(get_current_user)
):
    """
    Atualiza APENAS o telefone de contato de uma empresa.
    O telefone é validado pelo schema.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    updated_empresa = crud.update_empresa_telefone_contato(db, db_empresa=db_empresa, telefone=data.telefone_contato)
    return updated_empresa



#(Delete)


# --- ADICIONADO: Endpoint de Deleção (Delete) ---
@router.delete("/{empresa_id}", response_model=schemas.Empresa)
def delete_single_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    #current_user: schemas.User = Depends(get_current_user)
):
    """
    Deleta uma empresa do banco de dados pelo ID.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    # Este endpoint chama crud.delete_empresa
    crud.delete_empresa(db=db, db_empresa=db_empresa)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
    #return db_empresa # Retorna os dados da empresa que foi deletada



# --- Endpoints de Mídia (Já existentes) ---

@router.delete("/{empresa_id}/apresentacao", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa_apresentacao(
    empresa_id: int,
    db: Session = Depends(get_db)
    # current_user: schemas.User = Depends(get_current_user)
):
    """
    Remove (define como nulo) o link de apresentação de uma empresa.
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
    db: Session = Depends(get_db)
    # current_user: schemas.User = Depends(get_current_user)
):
    """
    Remove (define como nulo) o link de apresentação de uma empresa.
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
def delete_empresa_apresentacao(
    empresa_id: int,
    db: Session = Depends(get_db)
    # current_user: schemas.User = Depends(get_current_user)
):
    """
    Remove (define como nulo) o link de apresentação de uma empresa.
    """
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    
    # Você usa a MESMA função de update, mas força o link como None
    
    crud.update_empresa_link_video(db, db_empresa=db_empresa, link=None)
    
    # Retorna 204 - No Content, padrão para DELETE bem-sucedido
    return Response(status_code=status.HTTP_204_NO_CONTENT)
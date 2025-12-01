import uuid
import os
import shutil
from fastapi import (
    APIRouter, 
    Depends, 
    File, 
    UploadFile, 
    HTTPException, 
    status,
    Request
)
from sqlalchemy.orm import Session

# Importe os seus módulos de banco de dados e schemas
from .. import crud, schemas  # <--- crud.py é importado aqui
from ..database import get_db

# --- Configuração do Armazenamento Local ---
STATIC_DIR = "static"
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

router = APIRouter()

# --- Tipos de Conteúdo Permitidos ---
ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
]

@router.patch("/upload/apresentacao/{empresa_id}", response_model=schemas.Empresa)
def upload_presentation_local(
    empresa_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    
    # 1. Validar o tipo de arquivo
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não permitido. Use .pdf, .ppt ou .pptx."
        )

    # 2. Verificar se a empresa existe (USANDO CRUD)
    db_empresa = crud.get_empresa(db, empresa_id=empresa_id) # <--- USO DO CRUD
    if not db_empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")

    # 3. Criar nome de arquivo único e caminho
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOADS_DIR, file_name)

    # 4. Salvar o arquivo no disco
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao salvar o arquivo localmente: {e}"
        )
    finally:
        file.file.close()

    # 5. Construir a URL pública
    base_url = str(request.base_url)
    relative_path = f"{STATIC_DIR}/uploads/{file_name}".replace("\\", "/")
    file_url = f"{base_url}{relative_path}"

    # 6. Atualizar o link no banco de dados (USANDO CRUD)
    updated_empresa = crud.update_empresa_link(db, empresa_id=empresa_id, link=file_url) # <--- USO DO CRUD
    if not updated_empresa:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao salvar a URL no banco de dados")

    return updated_empresa
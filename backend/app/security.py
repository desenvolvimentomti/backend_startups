import os
# --- CORREÇÃO DE IMPORTAÇÃO ---
# Precisamos da classe 'datetime', da classe 'timedelta', e do objeto 'timezone'
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

from .database import get_db
from sqlalchemy.orm import Session
from . import models
from .models import UserRole
from typing import Union


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
# (Vou usar 1800 segundos (30 min) como o seu código, 
# mas manter esta variável é uma boa prática)
ACCESS_TOKEN_EXPIRE_MINUTES = 30

if not SECRET_KEY:
    raise ValueError("A variável de ambiente SECRET_KEY não está configurada.")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    
    # --- CORREÇÃO DA LÓGICA DE TEMPO ---
    
    if expires_delta:
        # 1. Usar datetime.now(timezone.utc) para obter a hora atual em UTC
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # 2. Usar timedelta(seconds=...) para somar corretamente
        expire = datetime.now(timezone.utc) + timedelta(seconds=1800) # 1800 segundos = 30 minutos
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Extract and validate user from JWT token.
    Returns the full Usuario model instance.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if user is None:
        raise credentials_exception
    return user


# --- RBAC: Authorization Dependencies ---

def require_role(*allowed_roles: UserRole):
    """
    Factory function that creates a dependency requiring specific roles.
    Usage: Depends(require_role(UserRole.ADMIN, UserRole.MAINTAINER))
    """
    def role_checker(current_user: models.Usuario = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Roles permitidas: {', '.join(r.value for r in allowed_roles)}"
            )
        return current_user
    return role_checker


# Convenience dependencies for common role combinations

def require_admin(current_user: models.Usuario = Depends(get_current_user)):
    """
    Require ADMIN role.
    Used for: changing user roles, sensitive operations
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem executar esta ação."
        )
    return current_user


def require_admin_or_maintainer(current_user: models.Usuario = Depends(get_current_user)):
    """
    Require ADMIN or MAINTAINER role.
    Used for: create, update, delete empresa endpoints
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MAINTAINER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Requer permissões de administrador ou mantenedor."
        )
    return current_user


# --- RBAC: Field-Level Access Control ---

def can_view_sensitive_fields(user: models.Usuario) -> bool:
    """
    Check if user has permission to view sensitive empresa fields.
    Only ADMIN and MAINTAINER can view: email, telefone_contato, cnpj, cadastrado_por, cargo
    """
    return user.role in [UserRole.ADMIN, UserRole.MAINTAINER]
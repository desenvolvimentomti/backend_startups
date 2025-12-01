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
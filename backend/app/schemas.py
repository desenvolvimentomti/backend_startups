from pydantic import BaseModel, Field, EmailStr, field_validator, HttpUrl, constr,  AnyHttpUrl,ConfigDict
import re
from typing import Optional
from .models import UserRole

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str = Field(min_length=4)

    @field_validator('email')
    def validate_email_domain(cls, v):
        if not v.endswith('@mti.com'):
            raise ValueError('O e-mail deve terminar com @mti.com')
        return v

    @field_validator('password')
    def validate_password_complexity(cls, v):
        if not re.search(r'\d', v):
            raise ValueError('A senha deve conter pelo menos um número')
        return v
    
class UserLogin(BaseModel):
    email: str
    password: str
    
class Token(BaseModel):
    access_token: str
    token_type: str

class User(UserBase):
    id: int
    role: UserRole  # RBAC: Include user role
    is_active: Optional[bool] = True

    model_config = ConfigDict(from_attributes=True)

# RBAC: Schema for updating user role (admin only)
class UserRoleUpdate(BaseModel):
    role: UserRole


class EmpresaBase(BaseModel):
    """Schema base com campos comuns para criar/atualizar empresa"""
    nome_da_empresa: str
    endereco: str
    cnpj: str
    ano_de_fundacao: int
    site: Optional[str] = None
    rede_social: Optional[str] = None
    cadastrado_por: Optional[str] = None
    cargo: Optional[str] = None
    email: Optional[str] = None
    setor_principal: str
    setor_secundario: str
    fase_da_startup: str
    colaboradores: str
    publico_alvo: str
    modelo_de_negocio: str
    recebeu_investimento: str
    negocios_no_exterior: str
    faturamento: str
    patente: str
    ja_pivotou: str
    comunidades: str
    solucao: str
    link_apresentacao: Optional[str] = None
    link_video: Optional[str] = None
    telefone_contato: Optional[str] = None
    tag: Optional[str] = None

    @field_validator('telefone_contato')
    def validate_telefone(cls, v):
        """Valida o formato do telefone (99) 99999-9999."""
        if v is None:
            return v
        regex_telefone = r'^\(\d{2}\)\s\d{5}-\d{4}$'
        if not re.match(regex_telefone, v):
            raise ValueError('O telefone deve estar no formato (99) 99999-9999')
        return v

    @field_validator('link_video')
    def validate_video_url(cls, v):
        if v is None:
            return v
        try:
            url = AnyHttpUrl(v)
        except Exception:
            raise ValueError(f'"{v}" não é uma URL válida.')
        host = url.host or ""
        allowed_hosts = [
            'youtube.com',
            'www.youtube.com',
            'youtu.be',
            'vimeo.com',
            'www.vimeo.com',
            'loom.com',
            'www.loom.com'
        ]
        if not any(host.endswith(allowed) for allowed in allowed_hosts):
             raise ValueError('A URL do vídeo deve ser do YouTube, Vimeo ou Loom')
        return v

    @field_validator('link_apresentacao')
    def validate_presentation_link(cls, v):
        """Valida apresentação (.pdf, .ppt, .pptx, GDrive, OneDrive)."""
        if v is None:
            return v
        v_lower = v.lower()
        allowed_extensions = ['.pdf', '.ppt', '.pptx']
        if any(v_lower.endswith(ext) for ext in allowed_extensions):
            try:
                AnyHttpUrl(v)
                return v
            except Exception:
                 raise ValueError('O link da apresentação deve ser uma URL válida')
        try:
            url = AnyHttpUrl(v)
            host = url.host or ""
            allowed_domains = ['drive.google.com', 'onedrive.live.com']
            if any(domain in host for domain in allowed_domains):
                return v
        except Exception:
            pass
        raise ValueError('O link da apresentação deve ser um .pdf, .ppt, .pptx, Google Drive ou OneDrive')


class EmpresaCreate(EmpresaBase):
    """Schema para criar uma nova empresa (sem ID)"""
    pass


class EmpresaUpdate(EmpresaBase):
    """Schema para atualizar uma empresa existente (todos os campos opcionais)"""
    nome_da_empresa: Optional[str] = None
    endereco: Optional[str] = None
    cnpj: Optional[str] = None
    ano_de_fundacao: Optional[int] = None
    setor_principal: Optional[str] = None
    setor_secundario: Optional[str] = None
    fase_da_startup: Optional[str] = None
    colaboradores: Optional[str] = None
    publico_alvo: Optional[str] = None
    modelo_de_negocio: Optional[str] = None
    recebeu_investimento: Optional[str] = None
    negocios_no_exterior: Optional[str] = None
    faturamento: Optional[str] = None
    patente: Optional[str] = None
    ja_pivotou: Optional[str] = None
    comunidades: Optional[str] = None
    solucao: Optional[str] = None


class Empresa(EmpresaBase):
    """Schema de resposta com ID incluído"""
    id: int

    model_config = ConfigDict(from_attributes=True)


# RBAC: Public schema for USER role (excludes sensitive fields)
class EmpresaPublic(BaseModel):
    """
    Schema público de empresa para usuários com role USER.
    Exclui campos sensíveis: email, telefone_contato, cnpj, cadastrado_por, cargo
    """
    id: int
    nome_da_empresa: str
    endereco: str
    # cnpj: HIDDEN for USER role
    ano_de_fundacao: int
    site: Optional[str] = None
    rede_social: Optional[str] = None
    # cadastrado_por: HIDDEN for USER role
    # cargo: HIDDEN for USER role
    # email: HIDDEN for USER role
    setor_principal: str
    setor_secundario: str
    fase_da_startup: str
    colaboradores: str
    publico_alvo: str
    modelo_de_negocio: str
    recebeu_investimento: str
    negocios_no_exterior: str
    faturamento: str
    patente: str
    ja_pivotou: str
    comunidades: str
    solucao: str
    link_apresentacao: Optional[str] = None
    link_video: Optional[str] = None
    # telefone_contato: HIDDEN for USER role
    tag: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)




# ---para os novos endpoints de editar os dados de links pelo id ---

class EmpresaMidiaResponse(BaseModel):
    """Schema para GET /empresa/{id}/midia (retorna apenas estes campos)"""
    link_apresentacao: Optional[str] = None
    link_video: Optional[str] = None
    telefone_contato: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


    
class SchemaLinkApresentacaoUpdate(BaseModel):
    """Schema para POST /empresa/{id}/apresentacao"""
    link_apresentacao: Optional[str] = None
    
    @field_validator('link_apresentacao')
    def validate_presentation_link(cls, v):
        # Reutiliza o validador principal
        return Empresa.validate_presentation_link(v)

class SchemaLinkVideoUpdate(BaseModel):
    """Schema para POST /empresa/{id}/video"""
    link_video: Optional[str] = None

    @field_validator('link_video')
    def validate_video_url(cls, v):
        # Reutiliza o validador principal
        return Empresa.validate_video_url(v)

class SchemaTelefoneUpdate(BaseModel):
    """Schema para POST /empresa/{id}/telefone"""
    telefone_contato: Optional[str] = None
    
    @field_validator('telefone_contato')
    def validate_telefone(cls, v):
        # Reutiliza o validador principal
        return Empresa.validate_telefone(v)
    
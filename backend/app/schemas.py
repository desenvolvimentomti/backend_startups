from pydantic import BaseModel, Field, EmailStr, field_validator, HttpUrl, constr,  AnyHttpUrl,ConfigDict
import re
from typing import Optional

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
    is_active: Optional[bool] = True

    model_config = ConfigDict(from_attributes=True)


class Empresa(BaseModel):
    id: int
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
    # --- NOVOS CAMPOS ADICIONADOS ---
    link_apresentacao: Optional[str] = None
    link_video: Optional[str] = None
    telefone_contato: Optional[str] = None   

    @field_validator('telefone_contato')
    def validate_telefone(cls, v):
        """Valida o formato do telefone (99) 99999-9999."""
        if v is None:
            return v  # Permite valores nulos
        
        # Regex para (99) 99999-9999
        regex_telefone = r'^\(\d{2}\)\s\d{5}-\d{4}$'
        
        if not re.match(regex_telefone, v):
            raise ValueError('O telefone deve estar no formato (99) 99999-9999')
        return v
    

    @field_validator('link_video')
    def validate_video_url(cls, v):
        if v is None:
            return v  # Permite valores nulos

        try:
            # validar se é uma URL HTTP/HTTPS válida
            url = AnyHttpUrl(v)
        except Exception:
            raise ValueError(f'"{v}" não é uma URL válida.')

        # Pega o host (ex: 'www.youtube.com', 'youtu.be')
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
        
        # Verifica se o host termina com um dos domínios permitidos
        if not any(host.endswith(allowed) for allowed in allowed_hosts):
             raise ValueError('A URL do vídeo deve ser do YouTube, Vimeo ou Loom')
        
        return v  # Retorna a string original
    

    @field_validator('link_apresentacao')
    def validate_presentation_link(cls, v):
        """Valida apresentação (.pdf, .ppt, .pptx, GDrive, OneDrive)."""

        if v is None:
            return v

        v_lower = v.lower()
        # 1. Checar extensões de arquivo permitidas
        allowed_extensions = ['.pdf', '.ppt', '.pptx']

        if any(v_lower.endswith(ext) for ext in allowed_extensions):

            try:
                AnyHttpUrl(v)
                return v
            except Exception:

                 raise ValueError('O link da apresentação deve ser uma URL válida')

        # 2. Se não for extensão, checar se é uma URL de nuvem válida

        try:
            url = AnyHttpUrl(v)

            host = url.host or ""
            allowed_domains = ['drive.google.com', 'onedrive.live.com']
            
            if any(domain in host for domain in allowed_domains):

                return v
        except Exception:
            # Se falhar a validação da URL, cai no raise abaixo

            pass 
        
        # 3. Se não passou em nenhum, falha
        raise ValueError('O link da apresentação deve ser um .pdf, .ppt, .pptx, Google Drive ou OneDrive')




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
    
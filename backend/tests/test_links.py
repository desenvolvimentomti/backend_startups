import pytest
from pydantic import ValidationError
from ..app.schemas import Empresa  # Importa a classe Empresa do seu arquivo schemas.py
#backend.app.
# --- Dados Base ---

EMPRESA_BASE_VALIDA = {
    "id": 1,
    "nome_da_empresa": "Startup Teste",
    "endereco": "Rua Fictícia, 123",
    "cnpj": "00.000.000/0001-00",
    "ano_de_fundacao": 2023,
    "setor_principal": "Tecnologia",
    "setor_secundario": "SaaS",
    "fase_da_startup": "Operação",
    "colaboradores": "1-10",
    "publico_alvo": "B2B",
    "modelo_de_negocio": "Assinatura",
    "recebeu_investimento": "Não",
    "negocios_no_exterior": "Não",
    "faturamento": "R$ 0 - R$ 50.000",
    "patente": "Não",
    "ja_pivotou": "Não",
    "comunidades": "Nenhuma",
    "solucao": "Uma solução inovadora."
    # Os campos opcionais (site, email, etc.) serão None por padrão
}

# --- Testes para telefone_contato ---

def test_telefone_valido():
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['telefone_contato'] = '(11) 98765-4321'
    empresa = Empresa(**dados)
    assert empresa.telefone_contato == '(11) 98765-4321'

def test_telefone_nulo_valido():
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['telefone_contato'] = None
    empresa = Empresa(**dados)
    assert empresa.telefone_contato is None

def test_telefone_invalido_formato():
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['telefone_contato'] = '11987654321'  # Sem formatação
    with pytest.raises(ValidationError, match='O telefone deve estar no formato'):
        Empresa(**dados)

def test_telefone_invalido_texto():
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['telefone_contato'] = 'nao-e-um-telefone'
    with pytest.raises(ValidationError, match='O telefone deve estar no formato'):
        Empresa(**dados)

# --- Testes para link_video ---

@pytest.mark.parametrize("url_valida", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://vimeo.com/123456789",
    "https://www.loom.com/share/123456789"
])
def test_link_video_valido(url_valida):
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['link_video'] = url_valida
    empresa = Empresa(**dados)
    assert empresa.link_video == url_valida

def test_link_video_nulo_valido():
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['link_video'] = None
    empresa = Empresa(**dados)
    assert empresa.link_video is None

@pytest.mark.parametrize("url_invalida", [
    "https://www.google.com",  # Domínio não permitido
    "https://www.dropbox.com/meu-video.mp4", # Domínio não permitido
    "nao_e_uma_url" # Formato inválido
])
def test_link_video_invalido(url_invalida):
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['link_video'] = url_invalida
    
    # A mensagem de erro pode ser por "não é uma URL válida" ou "deve ser do YouTube..."
    with pytest.raises(ValidationError, match='(não é uma URL válida|deve ser do YouTube, Vimeo ou Loom)'):
        Empresa(**dados)


# --- Testes para link_apresentacao ---
#  pode ser um link, se for tem q ser google ou onedrive. 
# pode ser arquivo,mas tem que mostrar um link com BUCKET ?

@pytest.mark.parametrize("link_valido", [
    "https://drive.google.com/file/d/123xyz/view",
    "https://onedrive.live.com/redir?resid=123XYZ",
    "https://exemplo.com/minha_apresentacao.pdf",
    "http://outro.site/docs/arquivo.ppt",
    "https://site.seguro/apresentacao.pptx"
])
def test_link_apresentacao_valido(link_valido):
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['link_apresentacao'] = link_valido
    empresa = Empresa(**dados)
    assert empresa.link_apresentacao == link_valido

def test_link_apresentacao_nulo_valido():
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['link_apresentacao'] = None
    empresa = Empresa(**dados)
    assert empresa.link_apresentacao is None

@pytest.mark.parametrize("link_invalido", [
    #"https://www.dropbox.com/s/123/arquivo.pdf", # Domínio não permitido
    "https://site.com/documento.docx", # Extensão não permitida
    #"apenas_um_texto.pdf", # Não é uma URL (e a validação espera uma URL ou link)
    "nao_e_link"
])
def test_link_apresentacao_invalido(link_invalido):
    dados = EMPRESA_BASE_VALIDA.copy()
    dados['link_apresentacao'] = link_invalido
    with pytest.raises(ValidationError, match='O link da apresentação deve ser um .pdf, .ppt, .pptx, Google Drive ou OneDrive'):
        Empresa(**dados)
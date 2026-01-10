import nltk
from unidecode import unidecode
from nltk.corpus import stopwords
from nltk.tokenize import wordpunct_tokenize
from nltk.stem import SnowballStemmer
from sklearn.feature_extraction.text import HashingVectorizer
import numpy as np

# --- CONFIGURAÇÃO DE RECURSOS NLP ---
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except Exception:
    pass

# Inicialização de componentes globais
stemmer = SnowballStemmer("portuguese")
stop_words_pt = set(stopwords.words('portuguese'))
CORP_AND_COMMON_STOP_WORDS = {
    'ltda', 's.a', 'eireli', 'companhia', 'group', 'grupo',
    'foco', 'quer', 'busco', 'ramo', 'eu', 'tu', 'ele', 'ela', 
    'documento', 'fazer', 'quero', 'peca', 'faz',
    'de', 'a', 'o', 'e', 'do', 'da', 'dos', 'as', 'os', 
    'um', 'uma', 'uns', 'umas', 'para', 'na', 'no', 'em', 'por', 'com', 'que',
    'empresa', 'ltda', 's.a', 'eireli', 'companhia', 'solucoes', 'inovacao', 'tecnologia', 
    'group', 'grupo', 'de', 'a', 'o', 'e', 'do', 'da', 'dos', 'as', 'os', 
    'um', 'uma', 'uns', 'umas', 'para', 'na', 'no', 'em', 'por', 'foco', ',','quer',
    'busco', 'ramo', 'com', 'eu', 'tu', 'ele', 'ela', 'documento', 'fazer', 'quero', 
    'um', 'peca', 'faz', 'que'
}
stop_words_pt.update(CORP_AND_COMMON_STOP_WORDS)

def custom_tokenizer(text):
    """
    Sua lógica original de tokenização: unidecode, lowercase, removal of stopwords e stemming.
    """
    # 1. Normalização
    text = unidecode(text).lower()
    # 2. Tokenização
    tokens = wordpunct_tokenize(text)
    final_tokens = []
    # 3. Filtragem e Stemming
    for t in tokens:
        # 3.1. Remover Stop Words e Palavras monossilábicas
        if t in stop_words_pt or len(t) <= 1:
            continue
        # 3.2. Stemming (Redução à Raiz)
        if t.isalpha():
            final_tokens.append(stemmer.stem(t))
        # 3.3. Números e Códigos
        #alfanumérico (ex: "3d", "xpto1"), mantemos como está.
        elif t.isalnum(): 
            final_tokens.append(t)
    # 4. Retorno limpo e "stemizado"
    return final_tokens

# --- CONFIGURAÇÃO DO VETORIZADOR ---
# Usamos HashingVectorizer com 1024 dimensões. 
# Hashing não precisa de "fit" global, 
# então permite processar cada empresa isoladamente e salvar no banco.
vectorizer = HashingVectorizer(
    n_features=1024, 
    tokenizer=custom_tokenizer, 
    alternate_sign=False,
    token_pattern=None
)

def clean_text(text: str) -> str:
    if not text:
        return ""
    return unidecode(text).lower()

def generate_embedding(empresa_obj) -> list[float]:
    """
    Cria o texto combinado baseado na sua lógica de busca e gera o vetor para o banco de dados.
    """
    texto_combinado = f"{empresa_obj.nome_da_empresa} {empresa_obj.solucao} {empresa_obj.setor_principal} {empresa_obj.setor_secundario} {empresa_obj.tag or ''}"
    
    # Gera a matriz esparsa e converte para uma lista densa de floats
    vector_sparse = vectorizer.transform([texto_combinado])
    vector_dense = vector_sparse.toarray().flatten().tolist()
    
    return vector_dense

def generate_query_embedding(query: str) -> list[float]:
    """Gera o vetor para a frase de busca do usuário"""
    vector_sparse = vectorizer.transform([query])
    vector_dense = vector_sparse.toarray().flatten().tolist()
    return vector_dense
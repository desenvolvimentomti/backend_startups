import nltk
from unidecode import unidecode
from nltk.corpus import stopwords
from nltk.tokenize import wordpunct_tokenize
#from nltk.stem import RSLPStemmer 
from nltk.stem import SnowballStemmer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Any
from fuzzywuzzy import fuzz
import inspect

try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
#    nltk.download('rslp', quiet=True)
except Exception:
    pass

def initialize_nlp_resources():
    global stemmer, stop_words_pt
    try:
        stemmer = SnowballStemmer("portuguese")
        #stemmer = RSLPStemmer()
        stop_words_pt = set(stopwords.words('portuguese'))
    except LookupError:
        #nltk.download('rslp', quiet=True)
        stemmer = SnowballStemmer("portuguese")
        #stemmer = RSLPStemmer()
        stop_words_pt = set(stopwords.words('portuguese'))
    
    # STOP WORDS:
    CORP_AND_COMMON_STOP_WORDS = {'empresa', 'ltda', 's.a', 'eireli', 'companhia', 'solucoes', 'inovacao', 'tecnologia', 'group', 'grupo', 'de', 'a', 'o', 'e', 'do', 'da', 'dos', 'as', 'os', 
        'um', 'uma', 'uns', 'umas', 'para', 'na', 'no', 'em', 'por', 'foco', ',','quer', 'busco', 'ramo', 'com', 'eu', 'tu', 'ele', 'ela', 'documento', 'fazer', 'quero', 'um', 'peca', 'faz', 'que'}
    stop_words_pt.update(CORP_AND_COMMON_STOP_WORDS)
    
initialize_nlp_resources()

def custom_tokenizer(text):
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


class SearchEngine:
    
    def __init__(self, all_companies_list: List[Any]):
        self.all_companies_list = all_companies_list
        self.tfidf_vectorizer = None
        self.company_vectors = None
        
        if self.all_companies_list:
            # --- 1. INDEXAÇÃO ---
            company_texts = [
                unidecode(f"{c.nome_da_empresa} {c.solucao} {c.setor_principal} {c.setor_secundario}{c.tag}").lower()
                for c in self.all_companies_list
            ]
            
            self.tfidf_vectorizer = TfidfVectorizer(tokenizer=custom_tokenizer, ngram_range=(1, 2),token_pattern=None)
            self.company_vectors = self.tfidf_vectorizer.fit_transform(company_texts)
        else:
             print("Aviso: SearchEngine inicializado sem dados.")

    def optimized_search(self, query: str, fase: str = None, limit: int = 5):
        if self.tfidf_vectorizer is None or self.company_vectors is None:
            return []

        normalized_query = unidecode(query).lower()
        # --- 2. BUSCA TF-IDF ( em todas as informações da empressa)
        query_vector = self.tfidf_vectorizer.transform([normalized_query])
        cosine_scores = cosine_similarity(query_vector, self.company_vectors).flatten()
        
        scored_companies = []
        RELEVANCE_THRESHOLD = 0.015

        for i, score in enumerate(cosine_scores):
            company = self.all_companies_list[i]
            
            if score < RELEVANCE_THRESHOLD: 
                continue
                
            if fase and company.fase_da_startup != fase:
                continue

            # --- 3. REFINAMENTO (Fuzzy Matching)

            # A. Score de NOME
            nome_da_empresa_norm = unidecode(company.nome_da_empresa).lower()
            name_fuzzy_score = fuzz.token_set_ratio(nome_da_empresa_norm, normalized_query)

            # B. Score de CONTEXTO (Solução + Setores)
            contexto_raw = f"{company.solucao} {company.setor_principal} {company.setor_secundario}{company.tag}"
            context_fuzzy_score = fuzz.token_set_ratio(unidecode(contexto_raw).lower(), normalized_query)

            # --- 4. CÁLCULO FINAL (Ponderação) ---
            # Score Final =
            #   (TF-IDF * 200)       -> Relevância estatística (Olha todos os campos, resolve plurais )
            # + (Fuzzy Nome * 1.5)   -> Bónus se acertar no nome
            # + (Fuzzy Contexto * 0.5) -> Bónus se acertar na descrição
            
            final_score = (score * 200) + (name_fuzzy_score * 1.5) + (context_fuzzy_score * 0.5)

            # metodo anterior 
            #tf_idf_weighted = score * 400
            #fuzzy_bonus = context_fuzzy_score * 0.50 
            #final_score = tf_idf_weighted + fuzzy_bonus
            
            if final_score > 70.0: 
                scored_companies.append({'company': company, 'score': final_score})
        
        scored_companies.sort(key=lambda x: x['score'], reverse=True)
        
        return [item['company'] for item in scored_companies[:limit]]
    
    
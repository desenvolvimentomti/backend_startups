"""
Embedding service using OpenAI's text-embedding-3-small model.
"""
import os
from openai import OpenAI
from unidecode import unidecode
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Model configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def clean_text(text: str) -> str:
    """Normalize text for embedding."""
    if not text:
        return ""
    return unidecode(text).lower().strip()


def generate_embedding(empresa_obj) -> list[float]:
    """
    Generate embedding for a startup using OpenAI's text-embedding-3-small.
    Combines relevant fields into a single text for embedding.
    """
    # Combine relevant fields
    parts = [
        empresa_obj.nome_da_empresa or "",
        empresa_obj.solucao or "",
        empresa_obj.setor_principal or "",
        empresa_obj.setor_secundario or "",
        empresa_obj.tag or "",
        empresa_obj.publico_alvo or "",
        empresa_obj.modelo_de_negocio or ""
    ]

    texto_combinado = " ".join(filter(None, parts))
    texto_combinado = clean_text(texto_combinado)

    if not texto_combinado:
        return [0.0] * EMBEDDING_DIMENSIONS

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texto_combinado,
        dimensions=EMBEDDING_DIMENSIONS
    )

    return response.data[0].embedding


def generate_query_embedding(query: str) -> list[float]:
    """Generate embedding for a search query."""
    query = clean_text(query)

    if not query:
        return [0.0] * EMBEDDING_DIMENSIONS

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
        dimensions=EMBEDDING_DIMENSIONS
    )

    return response.data[0].embedding

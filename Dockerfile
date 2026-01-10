FROM python:3.11-slim

ENV NLTK_DATA=/app/nltk_data

# Evita que o Python gere arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NLTK_DATA=/usr/share/nltk_data

WORKDIR /app


#  Instalar dependências do sistema 
# gcc, g++ e python3-dev são necessários para compilar scikit-learn, Levenshtein e Numpy
# libpq-dev é necessário para o driver do PostgreSQL (psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Atualizar o pip e ferramentas de metadados para as versões mais recentes
# Isso resolve o erro "metadata-generation-failed" para pacotes modernos
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p ${NLTK_DATA} \
    && python -c "import nltk; \
                  nltk.download('punkt', download_dir='${NLTK_DATA}', quiet=True); \
                  nltk.download('stopwords', download_dir='${NLTK_DATA}', quiet=True); \
                  nltk.download('rslp', download_dir='${NLTK_DATA}', quiet=True)"

COPY . .


CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

#CMD ["/bin/sh", "-c", "echo cheguei aqui"]
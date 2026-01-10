import pandas as pd
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Adiciona o diretório raiz ao path para permitir importações dos módulos locais
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.database import SessionLocal
from backend.app.models import Empresa
from backend.app import embedding_service

def setup_and_import(csv_file_path, dbname, user, password, host, port, table_name):
    """
    Script completo: Prepara o banco, limpa dados antigos, importa CSV e gera vetores.
    """
    db_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    engine = create_engine(db_string)

    try:
        # 1. Preparação do Banco de Dados
        with engine.connect() as conn:
            print("--- Passo 1: Preparando extensões e estrutura ---")
            # Ativa pgvector
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # Verifica se a coluna de vetor existe
            check_col = conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='{table_name}' AND column_name='embedding_vector';
            """)).fetchone()
            
            if not check_col:
                print("Criando coluna 'embedding_vector' (1024 dimensões)...")
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN embedding_vector vector(1024);"))
            
            # --- LIMPEZA PARA EVITAR UNIQUE VIOLATION ---
            print(f"Limpando dados antigos da tabela '{table_name}' para evitar conflitos de ID...")
            conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"))
            
            conn.commit()
            print("Estrutura preparada e tabela limpa.")

        # 2. Leitura e Limpeza do CSV
        print("\n--- Passo 2: Carregando CSV ---")
        df = pd.read_csv(csv_file_path, sep=',', quotechar='"')
        
        # Ajusta nomes de colunas
        df.columns = df.columns.str.replace(' ', '_').str.replace('(', '').str.replace(')', '').str.lower()
        
        # Garante que campos nulos sejam tratados como None (NULL no SQL)
        df = df.where(pd.notnull(df), None)

        print(f"Inserindo {len(df)} registros na tabela '{table_name}'...")
        # Inserimos os dados. Como usamos TRUNCATE acima, os IDs do CSV não colidirão com nada.
        df.to_sql(table_name, engine, if_exists='append', index=False)
        print("Dados importados com sucesso.")

        # 3. Geração de Vetores
        print("\n--- Passo 3: Gerando vetores de busca (Embedding) ---")
        db = SessionLocal()
        try:
            empresas_pendentes = db.query(Empresa).filter(Empresa.embedding_vector == None).all()
            total = len(empresas_pendentes)
            
            if total > 0:
                print(f"Processando NLP (Hashing 1024) para {total} empresas...")
                for i, empresa in enumerate(empresas_pendentes, 1):
                    # Gera o vetor usando sua lógica original de tokens
                    vetor = embedding_service.generate_embedding(empresa)
                    empresa.embedding_vector = vetor
                    
                    if i % 50 == 0:
                        db.commit()
                        print(f"Progresso: {i}/{total}...", end="\r")
                
                db.commit()
                print(f"\nTodos os {total} vetores foram gerados.")
        finally:
            db.close()

        # 4. Sincronizar Sequência de IDs
        print("\n--- Passo 4: Sincronizando contador de IDs ---")
        with engine.connect() as conn:
            conn.execute(text(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table_name}', 'id'), 
                    COALESCE((SELECT MAX(id) FROM {table_name}), 1), 
                    (SELECT MAX(id) FROM {table_name}) IS NOT NULL
                );
            """))
            conn.commit()
            print("Contador de IDs sincronizado.")

        print("\nSUCESSO: O banco está populado, vetorizado e pronto para a API!")

    except Exception as e:
        print(f"\nErro crítico: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    DB_NAME = "startups_db"
    DB_USER = "startups"
    DB_PASSWORD = "keystartups"
    DB_HOST = "localhost"
    DB_PORT = "5432"

    CSV_FILE = "startups_data.csv"
    TABLE_NAME = "startups"

    #import_csv_to_postgres(CSV_FILE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, TABLE_NAME)
    setup_and_import(CSV_FILE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, TABLE_NAME)
    #"""
''''
if __name__ == "__main__":
    # Exemplo de uso (Ajuste os valores conforme seu ambiente)
    # setup_and_import('caminho/para/seu.csv', 'startups_db', 'startups', 'senha', 'localhost', '5432', 'startups')
    pass
'''''
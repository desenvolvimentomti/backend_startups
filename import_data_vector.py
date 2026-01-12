import pandas as pd
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session # Importamos a classe Session explicitamente

# Adiciona o diretório raiz ao path para permitir importações dos módulos locais
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.models import Empresa
from backend.app import embedding_service

def setup_and_import(csv_file_path, dbname, user, password, host, port, table_name):
    """
    Script de provisionamento com logs detalhados para depuração.
    """
    db_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    engine = create_engine(db_string)
    
    # Criamos a factory de sessão vinculada a este engine específico
    # Renomeamos para SessionFactory para evitar NameError com a classe Session
    SessionFactory = sessionmaker(bind=engine)

    try:
        # 1. Preparação do Banco de Dados
        with engine.connect() as conn:
            print("--- Passo 1: Preparando extensões e estrutura ---")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # Garante que a coluna existe
            check_col = conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='{table_name}' AND column_name='embedding_vector';
            """)).fetchone()
            
            if not check_col:
                print(f"Criando coluna 'embedding_vector' na tabela '{table_name}'...")
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN embedding_vector vector(1024);"))
            
            print(f"Limpando dados antigos da tabela '{table_name}'...")
            conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"))
            conn.commit()
            print("Estrutura preparada e tabela limpa.")

        # 2. Leitura e Importação do CSV via Pandas
        print("\n--- Passo 2: Carregando CSV ---")
        df = pd.read_csv(csv_file_path, sep=',', quotechar='"')
        
        # Normalização das colunas (mesmo padrão do models.py)
        df.columns = df.columns.str.replace(' ', '_').str.replace('(', '').str.replace(')', '').str.lower()
        df = df.where(pd.notnull(df), None)

        print(f"Inserindo {len(df)} registros via Pandas...")
        # Usamos o engine diretamente. O Pandas faz o commit ao final.
        df.to_sql(table_name, engine, if_exists='append', index=False)
        print("Dados importados para o banco com sucesso.")

        # 3. Geração de Vetores via SQLAlchemy
        print("\n--- Passo 3: Gerando vetores de busca (Embedding) ---")
        # Usamos a SessionFactory criada no início da função
        db = SessionFactory()
        try:
            # DEBUG: Vamos ver se o SQLAlchemy encontra as empresas
            total_empresas = db.query(Empresa).count()
            print(f"O SQLAlchemy detectou {total_empresas} empresas na tabela '{table_name}'.")

            if total_empresas == 0:
                print("ERRO: O SQLAlchemy não encontrou as empresas inseridas pelo Pandas.")
                print("Verifique se o nome da tabela no models.py é exatamente igual a 'table_name'.")
                return

            # Filtramos as que precisam de vetor (que acabamos de inserir)
            empresas_pendentes = db.query(Empresa).filter(Empresa.embedding_vector == None).all()
            total_pendentes = len(empresas_pendentes)
            
            if total_pendentes > 0:
                print(f"Processando tokens para {total_pendentes} empresas...")
                for i, empresa in enumerate(empresas_pendentes, 1):
                    # Gera a matriz de 1024 posições
                    vetor = embedding_service.generate_embedding(empresa)
                    empresa.embedding_vector = vetor
                    
                    if i % 25 == 0:
                        db.commit()
                        print(f"Progresso: {i}/{total_pendentes}...", end="\r")
                
                db.commit()
                print(f"\nSucesso: {total_pendentes} vetores gerados e salvos.")
            else:
                print("Aviso: Nenhuma empresa pendente de vetorização encontrada.")
                
        except Exception as e:
            print(f"Erro no processamento de vetores: {e}")
            db.rollback()
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

        print("\nCONCLUÍDO: O sistema está pronto para buscas vetoriais!")

    except Exception as e:
        print(f"\nErro crítico no processo: {e}")
    finally:
        engine.dispose()
# atualizar db online dp Render 


if __name__ == "__main__":
    DB_NAME = "startups_db_4x73"
    DB_USER = "startups_db_4x73_user"
    DB_PASSWORD = "BSNOSW6a7yceaLlepdiWibIGrTc6zrRF"
    DB_HOST = "dpg-d4cgsjfdiees7393sdc0-a.oregon-postgres.render.com"
    DB_PORT = "5432"

    CSV_FILE = "startups_data.csv"
    TABLE_NAME = "startups"

    setup_and_import(CSV_FILE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, TABLE_NAME)

    

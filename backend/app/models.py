from sqlalchemy import Column, Integer, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, registry
from sqlalchemy.types import Integer 
#from .database import Base
from .database import table_registry

# --- CORREÇÃO DE COMPATIBILIDADE (SQLite/PostgreSQL) ---

PG_BIGINT = BigInteger().with_variant(Integer, "sqlite")

#table_registry = registry()

@table_registry.mapped_as_dataclass
class Empresa:
    __tablename__ = "startups"
    #__table_args__ = {'schema': 'public'}

    id: Mapped[int] = mapped_column(PG_BIGINT, primary_key=True, index=True, init=False)
    nome_da_empresa: Mapped[str] = mapped_column(String(255), index=True)
    endereco: Mapped[str] = mapped_column("endereço")
    cnpj: Mapped[str] = mapped_column(String(18), unique=True, index=True)
    ano_de_fundacao: Mapped[int] = mapped_column("ano_de_fundação", BigInteger)
    site: Mapped[str]
    rede_social: Mapped[str]
    cadastrado_por: Mapped[str]
    cargo: Mapped[str]
    email: Mapped[str] = mapped_column("e-mail")
    setor_principal: Mapped[str] = mapped_column(index=True)
    setor_secundario: Mapped[str]
    fase_da_startup: Mapped[str]
    colaboradores: Mapped[str]
    publico_alvo: Mapped[str]
    modelo_de_negocio: Mapped[str]
    recebeu_investimento: Mapped[str]
    negocios_no_exterior: Mapped[str] = mapped_column("negócios_no_exterior")
    faturamento: Mapped[str]
    patente: Mapped[str]
    ja_pivotou: Mapped[str] = mapped_column("já_pivotou?")
    comunidades: Mapped[str]
    solucao: Mapped[str] = mapped_column("solução", Text)
    
    # --- NOVOS CAMPOS (Nuláveis) ---

    link_apresentacao: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    link_video: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    telefone_contato: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    tag: Mapped[str | None] = mapped_column(String, nullable=True, default=None)



    #def __repr__(self):
    #    return f"<Empresa(nome='{self.nome_da_empresa}', setor='{self.setor_principal}')>"

@table_registry.mapped_as_dataclass
class Usuario:
    __tablename__ = "usuarios"
    #__table_args__ = {'schema': 'public'}

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))

    
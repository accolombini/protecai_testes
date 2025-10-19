"""
Configuração do banco de dados PostgreSQL
=========================================

Setup SQLAlchemy para integração com PostgreSQL.
"""

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import logging

from api.core.config import settings

logger = logging.getLogger(__name__)

# Configurar engine do SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "options": "-c search_path=relay_configs,public"
    },
    echo=True if settings.LOG_LEVEL == "DEBUG" else False
)

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Metadata para schema relay_configs
metadata = MetaData(schema="relay_configs")

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def test_connection():
    """Testa conexão com o banco"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info(f"✅ PostgreSQL conectado: {version}")
            return True
    except Exception as e:
        logger.error(f"❌ Erro na conexão PostgreSQL: {e}")
        return False

def check_schema():
    """Verifica se o schema relay_configs existe"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'relay_configs'
            """))
            schema_exists = result.fetchone() is not None
            
            if schema_exists:
                logger.info("✅ Schema relay_configs encontrado")
                return True
            else:
                logger.warning("⚠️ Schema relay_configs não encontrado")
                return False
    except Exception as e:
        logger.error(f"❌ Erro ao verificar schema: {e}")
        return False
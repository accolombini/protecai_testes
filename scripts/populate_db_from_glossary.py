#!/usr/bin/env python3
"""
================================================================================
POPULADOR DE BANCO DE DADOS A PARTIR DO GLOSSÁRIO
================================================================================
Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 1.0.0

Description:
    Executa a população das tabelas protec_ai.protection_functions e 
    protec_ai.relay_settings usando os arquivos SQL/CSV gerados pelo
    extrator de glossário.
    
    Este script:
    1. Conecta ao banco PostgreSQL
    2. Executa SQL de população de protection_functions
    3. Executa SQL de população de relay_settings (template)
    4. Gera relatório de auditoria

Usage:
    python scripts/populate_db_from_glossary.py

Prerequisites:
    - PostgreSQL rodando
    - Database protecai_db criado
    - Schema protec_ai existente
    - Tabelas protection_functions e relay_settings criadas
================================================================================
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# ================================================================================
# CONFIGURAÇÃO
# ================================================================================

BASE_DIR = Path(__file__).parent.parent

# Configuração do banco (ajuste conforme seu ambiente)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

# Arquivos SQL gerados
SQL_FUNCTIONS = BASE_DIR / "outputs/sql/populate_protection_functions.sql"
SQL_SETTINGS = BASE_DIR / "outputs/sql/populate_relay_settings.sql"
AUDIT_LOG = BASE_DIR / "outputs/logs/populate_db_audit.log"

# Criar diretório de logs
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(AUDIT_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ================================================================================
# FUNÇÕES AUXILIARES
# ================================================================================

def conectar_db() -> Optional[psycopg2.extensions.connection]:
    """
    Conecta ao banco PostgreSQL.
    
    Returns:
        Connection object ou None se falhar
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False  # Usar transações
        logger.info("✅ Conexão estabelecida com PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}")
        return None


def verificar_tabelas(conn: psycopg2.extensions.connection) -> bool:
    """
    Verifica se as tabelas necessárias existem.
    
    Args:
        conn: Conexão PostgreSQL
    
    Returns:
        True se todas as tabelas existem, False caso contrário
    """
    try:
        cursor = conn.cursor()
        
        # Verificar protection_functions
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'protec_ai' 
                AND table_name = 'protection_functions'
            );
        """)
        if not cursor.fetchone()[0]:
            logger.error("❌ Tabela protec_ai.protection_functions não existe")
            return False
        
        # Verificar relay_settings
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'protec_ai' 
                AND table_name = 'relay_settings'
            );
        """)
        if not cursor.fetchone()[0]:
            logger.error("❌ Tabela protec_ai.relay_settings não existe")
            return False
        
        logger.info("✅ Tabelas necessárias existem")
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tabelas: {e}")
        return False


def obter_estatisticas_antes(conn: psycopg2.extensions.connection) -> Dict[str, int]:
    """
    Obtém estatísticas antes da importação.
    
    Args:
        conn: Conexão PostgreSQL
    
    Returns:
        Dicionário com contagens
    """
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM protec_ai.protection_functions;")
        func_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM protec_ai.relay_settings;")
        settings_count = cursor.fetchone()[0]
        
        cursor.close()
        
        return {
            'protection_functions': func_count,
            'relay_settings': settings_count
        }
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas: {e}")
        return {'protection_functions': 0, 'relay_settings': 0}


def executar_sql_file(conn: psycopg2.extensions.connection, sql_file: Path) -> bool:
    """
    Executa um arquivo SQL.
    
    Args:
        conn: Conexão PostgreSQL
        sql_file: Caminho do arquivo SQL
    
    Returns:
        True se sucesso, False caso contrário
    """
    try:
        logger.info(f"[INFO] Executando SQL: {sql_file.name}")
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Remover comentários e linhas vazias
        sql_lines = [
            line for line in sql_content.split('\n')
            if line.strip() and not line.strip().startswith('--')
        ]
        sql_clean = '\n'.join(sql_lines)
        
        cursor = conn.cursor()
        cursor.execute(sql_clean)
        conn.commit()
        
        logger.info(f"✅ SQL executado com sucesso: {sql_file.name}")
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar {sql_file.name}: {e}")
        conn.rollback()
        return False


def popular_protection_functions(conn: psycopg2.extensions.connection) -> bool:
    """
    Popula tabela protection_functions.
    
    Args:
        conn: Conexão PostgreSQL
    
    Returns:
        True se sucesso, False caso contrário
    """
    logger.info("\n" + "="*80)
    logger.info("POPULANDO PROTECTION_FUNCTIONS")
    logger.info("="*80)
    
    if not SQL_FUNCTIONS.exists():
        logger.error(f"❌ Arquivo não encontrado: {SQL_FUNCTIONS}")
        return False
    
    return executar_sql_file(conn, SQL_FUNCTIONS)


def popular_relay_settings_template(conn: psycopg2.extensions.connection) -> bool:
    """
    Popula tabela relay_settings (template - sem equipment_id).
    
    NOTA: Este script insere parâmetros como template.
    Os campos equipment_id e function_id devem ser atualizados posteriormente
    quando os equipamentos forem cadastrados.
    
    Args:
        conn: Conexão PostgreSQL
    
    Returns:
        True se sucesso, False caso contrário
    """
    logger.info("\n" + "="*80)
    logger.info("POPULANDO RELAY_SETTINGS (TEMPLATE)")
    logger.info("="*80)
    logger.info("⚠️  NOTA: equipment_id e function_id serão NULL (template)")
    logger.info("⚠️  Vincule a equipamentos reais posteriormente")
    
    if not SQL_SETTINGS.exists():
        logger.error(f"❌ Arquivo não encontrado: {SQL_SETTINGS}")
        return False
    
    return executar_sql_file(conn, SQL_SETTINGS)


def gerar_relatorio_final(
    conn: psycopg2.extensions.connection,
    stats_antes: Dict[str, int],
    stats_depois: Dict[str, int]
) -> None:
    """
    Gera relatório final da importação.
    
    Args:
        conn: Conexão PostgreSQL
        stats_antes: Estatísticas antes
        stats_depois: Estatísticas depois
    """
    logger.info("\n" + "="*80)
    logger.info("RELATÓRIO FINAL DE IMPORTAÇÃO")
    logger.info("="*80)
    
    func_inseridos = stats_depois['protection_functions'] - stats_antes['protection_functions']
    settings_inseridos = stats_depois['relay_settings'] - stats_antes['relay_settings']
    
    logger.info(f"Protection Functions:")
    logger.info(f"  Antes:     {stats_antes['protection_functions']:>6}")
    logger.info(f"  Depois:    {stats_depois['protection_functions']:>6}")
    logger.info(f"  Inseridos: {func_inseridos:>6}")
    
    logger.info(f"\nRelay Settings:")
    logger.info(f"  Antes:     {stats_antes['relay_settings']:>6}")
    logger.info(f"  Depois:    {stats_depois['relay_settings']:>6}")
    logger.info(f"  Inseridos: {settings_inseridos:>6}")
    
    # Mostrar amostra de funções inseridas
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT function_code, function_name, is_primary 
            FROM protec_ai.protection_functions 
            ORDER BY id 
            LIMIT 10;
        """)
        functions = cursor.fetchall()
        
        if functions:
            logger.info("\n📋 Amostra de funções inseridas (10 primeiras):")
            for func in functions:
                primary_mark = "⭐" if func['is_primary'] else "  "
                logger.info(f"  {primary_mark} {func['function_code']:>6} - {func['function_name']}")
        
        cursor.close()
    except Exception as e:
        logger.warning(f"⚠️  Não foi possível gerar amostra: {e}")
    
    logger.info("="*80)
    logger.info(f"✅ Importação concluída em: {datetime.now().isoformat()}")
    logger.info(f"📄 Log completo salvo em: {AUDIT_LOG}")
    logger.info("="*80)


# ================================================================================
# MAIN
# ================================================================================

def main():
    """Função principal."""
    logger.info("="*80)
    logger.info("POPULADOR DE BANCO DE DADOS - GLOSSÁRIO DE RELÉS")
    logger.info("="*80)
    logger.info(f"Data/Hora: {datetime.now().isoformat()}")
    logger.info(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    
    # 1. Conectar
    conn = conectar_db()
    if not conn:
        logger.error("❌ Falha na conexão. Abortando.")
        sys.exit(1)
    
    try:
        # 2. Verificar tabelas
        if not verificar_tabelas(conn):
            logger.error("❌ Tabelas necessárias não existem. Abortando.")
            conn.close()
            sys.exit(1)
        
        # 3. Estatísticas antes
        stats_antes = obter_estatisticas_antes(conn)
        logger.info(f"\n📊 Estatísticas ANTES:")
        logger.info(f"  Protection Functions: {stats_antes['protection_functions']}")
        logger.info(f"  Relay Settings:       {stats_antes['relay_settings']}")
        
        # 4. Popular protection_functions
        if not popular_protection_functions(conn):
            logger.error("❌ Falha ao popular protection_functions")
            conn.close()
            sys.exit(1)
        
        # 5. Popular relay_settings (opcional - comentar se não quiser)
        # NOTA: Insere template sem equipment_id
        logger.info("\n⚠️  Pulando population de relay_settings (template sem equipment_id)")
        logger.info("   Para popular, descomente a linha no código ou execute SQL manualmente")
        # if not popular_relay_settings_template(conn):
        #     logger.warning("⚠️  Falha ao popular relay_settings (não crítico)")
        
        # 6. Estatísticas depois
        stats_depois = obter_estatisticas_antes(conn)
        
        # 7. Relatório final
        gerar_relatorio_final(conn, stats_antes, stats_depois)
        
    except Exception as e:
        logger.error(f"❌ Erro durante execução: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()
        logger.info("🔌 Conexão fechada")


if __name__ == '__main__':
    main()

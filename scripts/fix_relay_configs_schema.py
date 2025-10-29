#!/usr/bin/env python3
"""
🔧 CORREÇÃO ESPECÍFICA: Schema relay_configs
Resolve problemas de foreign keys e tipos de dados
"""

import psycopg2
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def conectar_postgresql():
    """Conecta ao PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="protecai_db", 
            user="protecai",
            password="protecai",
            port="5432"
        )
        conn.autocommit = True
        logger.info("✅ Conectado ao PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"❌ Erro conectando PostgreSQL: {e}")
        return None

def corrigir_relay_configs_schema(conn):
    """Corrige problemas específicos do schema relay_configs"""
    cursor = conn.cursor()
    
    try:
        logger.info("🔧 Iniciando correção do schema relay_configs")
        
        # 1. Dropar tabelas problemáticas para recriá-las
        logger.info("🗑️ Removendo tabelas problemáticas")
        cursor.execute("""
            DROP TABLE IF EXISTS relay_configs.relay_equipment CASCADE;
            DROP TABLE IF EXISTS relay_configs.relay_models CASCADE;
            DROP TABLE IF EXISTS relay_configs.protection_functions CASCADE;
        """)
        
        # 2. Recriar relay_models com estrutura correta
        logger.info("📱 Recriando relay_models")
        cursor.execute("""
            CREATE TABLE relay_configs.relay_models (
                id SERIAL PRIMARY KEY,
                manufacturer_id INTEGER REFERENCES relay_configs.fabricantes(id),
                model_name VARCHAR(100) NOT NULL,
                series VARCHAR(50),
                protection_functions TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 3. Recriar protection_functions com estrutura correta
        logger.info("🛡️ Recriando protection_functions")
        cursor.execute("""
            CREATE TABLE relay_configs.protection_functions (
                id SERIAL PRIMARY KEY,
                function_code VARCHAR(10) NOT NULL UNIQUE,
                function_name VARCHAR(200) NOT NULL,
                description TEXT,
                category VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 4. Recriar relay_equipment com estrutura correta
        logger.info("📋 Recriando relay_equipment")
        cursor.execute("""
            CREATE TABLE relay_configs.relay_equipment (
                id SERIAL PRIMARY KEY,
                tag VARCHAR(100) NOT NULL UNIQUE,
                relay_model_id INTEGER REFERENCES relay_configs.relay_models(id),
                installation_date DATE,
                location VARCHAR(200),
                status VARCHAR(20) DEFAULT 'active',
                csv_file_path VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 5. Copiar dados com conversão de tipos
        logger.info("📊 Copiando dados com conversão de tipos")
        
        # Copiar relay_models
        cursor.execute("""
            INSERT INTO relay_configs.relay_models (manufacturer_id, model_name, series, protection_functions, created_at)
            SELECT 
                CAST(manufacturer_id AS INTEGER),
                model_name,
                series,
                protection_functions,
                created_at
            FROM protec_ai.relay_models;
        """)
        
        # Copiar protection_functions
        cursor.execute("""
            INSERT INTO relay_configs.protection_functions (function_code, function_name, description, category, created_at)
            SELECT 
                function_code,
                function_name,
                description,
                category,
                created_at
            FROM protec_ai.protection_functions;
        """)
        
        # Copiar relay_equipment
        cursor.execute("""
            INSERT INTO relay_configs.relay_equipment (tag, relay_model_id, installation_date, location, status, csv_file_path, created_at)
            SELECT 
                tag,
                CAST(relay_model_id AS INTEGER),
                installation_date,
                location,
                status,
                csv_file_path,
                created_at
            FROM protec_ai.relay_equipment;
        """)
        
        # Copiar equipment_protection_functions
        cursor.execute("""
            INSERT INTO relay_configs.equipment_protection_functions (equipment_id, function_id, parameter_code, parameter_value, is_enabled, created_at)
            SELECT 
                CAST(equipment_id AS INTEGER),
                CAST(function_id AS INTEGER),
                parameter_code,
                parameter_value,
                is_enabled,
                created_at
            FROM protec_ai.equipment_protection_functions;
        """)
        
        # Copiar relay_settings  
        cursor.execute("""
            INSERT INTO relay_configs.relay_settings (equipment_id, parameter_name, parameter_value, parameter_unit, is_enabled, created_at)
            SELECT 
                CAST(equipment_id AS INTEGER),
                parameter_name,
                parameter_value,
                parameter_unit,
                is_enabled,
                created_at
            FROM protec_ai.relay_settings;
        """)
        
        logger.info("✅ Schema relay_configs corrigido com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro corrigindo schema: {e}")
        raise

def verificar_dados_finais(conn):
    """Verifica os dados finais em todos os schemas"""
    cursor = conn.cursor()
    
    schemas = ['protec_ai', 'relay_configs', 'ml_gateway']
    tabelas = ['relay_equipment', 'equipment_protection_functions', 'relay_settings', 
              'fabricantes', 'relay_models', 'protection_functions']
    
    logger.info("📊 VERIFICAÇÃO FINAL DOS DADOS:")
    logger.info("=" * 50)
    
    for schema in schemas:
        logger.info(f"\n🏗️ SCHEMA: {schema}")
        for tabela in tabelas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {schema}.{tabela}")
                count = cursor.fetchone()[0]
                
                if tabela == 'relay_equipment':
                    emoji = "📋"
                elif tabela == 'equipment_protection_functions':
                    emoji = "🔧"
                elif tabela == 'relay_settings':
                    emoji = "⚙️"
                elif tabela == 'fabricantes':
                    emoji = "🏭"
                elif tabela == 'relay_models':
                    emoji = "📱"
                elif tabela == 'protection_functions':
                    emoji = "🛡️"
                else:
                    emoji = "📄"
                    
                logger.info(f"   {emoji} {tabela}: {count}")
            except Exception as e:
                logger.info(f"   ❌ {tabela}: ERRO - {e}")

def main():
    """Função principal"""
    logger.info("🎯 INICIANDO CORREÇÃO ESPECÍFICA - SCHEMA relay_configs")
    logger.info("=" * 60)
    
    # Conectar ao PostgreSQL
    conn = conectar_postgresql()
    if not conn:
        logger.error("❌ ERRO: Falha na conexão!")
        return
    
    try:
        # Corrigir schema relay_configs
        corrigir_relay_configs_schema(conn)
        
        # Verificar dados finais
        verificar_dados_finais(conn)
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 CORREÇÃO CONCLUÍDA - SCHEMA relay_configs FUNCIONAL!")
        
    except Exception as e:
        logger.error(f"❌ ERRO: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
🧹 LIMPEZA CORRETA: Schemas Teams ETAP e ML
Mantém estruturas preparadas mas SEM DADOS (como deve ser)
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

def limpar_dados_teams(conn):
    """Limpa dados dos schemas das teams, mantendo apenas estruturas"""
    cursor = conn.cursor()
    
    try:
        logger.info("🧹 INICIANDO LIMPEZA DOS SCHEMAS DAS TEAMS")
        logger.info("=" * 50)
        
        # Schemas das teams que devem ficar VAZIOS
        team_schemas = ['relay_configs', 'ml_gateway']
        
        # Tabelas a serem limpas (em ordem para respeitar foreign keys)
        tabelas_ordem = [
            'relay_settings',
            'equipment_protection_functions', 
            'relay_equipment',
            'protection_functions',
            'relay_models',
            'fabricantes'
        ]
        
        for schema in team_schemas:
            logger.info(f"\n🏗️ LIMPANDO SCHEMA: {schema}")
            logger.info("-" * 30)
            
            for tabela in tabelas_ordem:
                try:
                    # Verificar se tabela existe
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = '{schema}' AND table_name = '{tabela}'
                    """)
                    
                    if cursor.fetchone()[0] > 0:
                        # Contar registros antes
                        cursor.execute(f"SELECT COUNT(*) FROM {schema}.{tabela}")
                        count_antes = cursor.fetchone()[0]
                        
                        if count_antes > 0:
                            # Limpar dados
                            cursor.execute(f"DELETE FROM {schema}.{tabela}")
                            logger.info(f"   🗑️ {tabela}: {count_antes} registros removidos")
                        else:
                            logger.info(f"   ✅ {tabela}: já vazia")
                    else:
                        logger.info(f"   ⚠️ {tabela}: não existe")
                        
                except Exception as e:
                    logger.error(f"   ❌ {tabela}: ERRO - {e}")
        
        logger.info("\n✅ LIMPEZA CONCLUÍDA")
        
    except Exception as e:
        logger.error(f"❌ Erro na limpeza: {e}")
        raise

def verificar_status_final(conn):
    """Verifica o status final dos três schemas"""
    cursor = conn.cursor()
    
    logger.info("\n📊 VERIFICAÇÃO FINAL - STATUS DOS SCHEMAS")
    logger.info("=" * 55)
    
    schemas = ['protec_ai', 'relay_configs', 'ml_gateway']
    tabelas = ['relay_equipment', 'equipment_protection_functions', 'relay_settings', 
              'fabricantes', 'relay_models', 'protection_functions']
    
    for schema in schemas:
        logger.info(f"\n🏗️ SCHEMA: {schema}")
        
        total_registros = 0
        for tabela in tabelas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {schema}.{tabela}")
                count = cursor.fetchone()[0]
                total_registros += count
                
                # Emojis por tipo de tabela
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
        
        # Status do schema
        if schema == 'protec_ai':
            if total_registros > 0:
                status_emoji = "✅ DADOS REAIS"
            else:
                status_emoji = "⚠️ VAZIO (PROBLEMA)"
        else:  # relay_configs ou ml_gateway
            if total_registros == 0:
                status_emoji = "✅ VAZIO (CORRETO)"
            else:
                status_emoji = "⚠️ COM DADOS (PROBLEMA)"
        
        logger.info(f"   📊 STATUS: {status_emoji}")

def main():
    """Função principal"""
    logger.info("🎯 LIMPEZA SCHEMAS TEAMS - MANTER APENAS ESTRUTURAS")
    logger.info("=" * 60)
    logger.info("📝 OBJETIVO:")
    logger.info("   • protec_ai: MANTER dados reais")
    logger.info("   • relay_configs (ETAP): ESTRUTURA vazia")
    logger.info("   • ml_gateway (ML): ESTRUTURA vazia")
    logger.info("=" * 60)
    
    # Conectar ao PostgreSQL
    conn = conectar_postgresql()
    if not conn:
        logger.error("❌ ERRO: Falha na conexão!")
        return
    
    try:
        # Limpar dados das teams
        limpar_dados_teams(conn)
        
        # Verificar status final
        verificar_status_final(conn)
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 SCHEMAS TEAMS LIMPOS - ESTRUTURAS PREPARADAS!")
        logger.info("✅ relay_configs (ETAP): Pronto para receber dados")
        logger.info("✅ ml_gateway (ML): Pronto para receber dados")
        logger.info("✅ protec_ai: Dados reais preservados")
        
    except Exception as e:
        logger.error(f"❌ ERRO: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
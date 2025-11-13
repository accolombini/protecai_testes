#!/usr/bin/env python3
"""
Script de validação de integridade do banco de dados
Compara registros do PostgreSQL com CSVs normalizados
"""

import pandas as pd
import psycopg2
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração do banco
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

NORMALIZED_CSV_DIR = Path("outputs/norm_csv")

def connect_db():
    """Conectar ao PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)

def count_csv_records():
    """Contar registros em todos os CSVs normalizados"""
    csv_files = sorted(NORMALIZED_CSV_DIR.glob("*_normalized.csv"))
    
    total_rows = 0
    file_counts = {}
    
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        rows = len(df)
        total_rows += rows
        file_counts[csv_file.name] = rows
    
    return total_rows, file_counts, len(csv_files)

def count_db_records(conn):
    """Contar registros no banco de dados"""
    cursor = conn.cursor()
    
    # Contar equipamentos
    cursor.execute("SELECT COUNT(*) FROM protec_ai.relay_equipment;")
    equipments_count = cursor.fetchone()[0]
    
    # Contar settings
    cursor.execute("SELECT COUNT(*) FROM protec_ai.relay_settings;")
    settings_count = cursor.fetchone()[0]
    
    # Contar grupos multipart
    cursor.execute("SELECT COUNT(*) FROM protec_ai.multipart_groups;")
    multipart_count = cursor.fetchone()[0]
    
    # Contar unidades
    cursor.execute("SELECT COUNT(*) FROM protec_ai.units;")
    units_count = cursor.fetchone()[0]
    
    # Contar settings por equipamento
    cursor.execute("""
        SELECT e.equipment_tag, COUNT(s.id) as settings_count
        FROM protec_ai.relay_equipment e
        LEFT JOIN protec_ai.relay_settings s ON e.id = s.equipment_id
        GROUP BY e.equipment_tag
        ORDER BY e.equipment_tag;
    """)
    equipment_details = cursor.fetchall()
    
    cursor.close()
    
    return {
        'equipments': equipments_count,
        'settings': settings_count,
        'multipart_groups': multipart_count,
        'units': units_count,
        'equipment_details': equipment_details
    }

def validate_integrity():
    """Validar integridade comparando CSV vs DB"""
    logger.info("="*80)
    logger.info("🔍 VALIDAÇÃO DE INTEGRIDADE DO BANCO DE DADOS")
    logger.info("="*80)
    
    # Contar registros nos CSVs
    logger.info("\n📁 Contando registros nos CSVs normalizados...")
    csv_total, csv_file_counts, csv_files_count = count_csv_records()
    logger.info(f"   ✓ Total de arquivos CSV: {csv_files_count}")
    logger.info(f"   ✓ Total de linhas nos CSVs: {csv_total}")
    
    # Contar registros no banco
    logger.info("\n🗄️  Contando registros no PostgreSQL...")
    conn = connect_db()
    db_counts = count_db_records(conn)
    conn.close()
    
    logger.info(f"   ✓ Equipamentos: {db_counts['equipments']}")
    logger.info(f"   ✓ Settings: {db_counts['settings']}")
    logger.info(f"   ✓ Grupos multipart: {db_counts['multipart_groups']}")
    logger.info(f"   ✓ Unidades: {db_counts['units']}")
    
    # Comparação
    logger.info("\n" + "="*80)
    logger.info("📊 COMPARAÇÃO CSV vs BANCO DE DADOS")
    logger.info("="*80)
    
    # Validar número de arquivos vs equipamentos
    if csv_files_count == db_counts['equipments']:
        logger.info(f"✅ Arquivos CSV: {csv_files_count} = Equipamentos DB: {db_counts['equipments']}")
    else:
        logger.error(f"❌ DIVERGÊNCIA! CSV: {csv_files_count} ≠ DB: {db_counts['equipments']}")
    
    # Validar número total de linhas vs settings
    if csv_total == db_counts['settings']:
        logger.info(f"✅ Linhas CSV: {csv_total} = Settings DB: {db_counts['settings']}")
    else:
        logger.error(f"❌ DIVERGÊNCIA! CSV: {csv_total} ≠ DB: {db_counts['settings']}")
    
    # Validação detalhada por equipamento
    logger.info("\n" + "="*80)
    logger.info("📋 VALIDAÇÃO DETALHADA POR EQUIPAMENTO")
    logger.info("="*80)
    
    divergences = []
    
    for equipment_tag, db_count in db_counts['equipment_details']:
        # Encontrar arquivo CSV correspondente
        csv_filename = f"{equipment_tag}_normalized.csv"
        
        if csv_filename in csv_file_counts:
            csv_count = csv_file_counts[csv_filename]
            
            if csv_count == db_count:
                logger.info(f"✅ {equipment_tag}: CSV={csv_count}, DB={db_count}")
            else:
                logger.error(f"❌ {equipment_tag}: CSV={csv_count}, DB={db_count} (DIVERGÊNCIA: {csv_count - db_count})")
                divergences.append({
                    'equipment': equipment_tag,
                    'csv': csv_count,
                    'db': db_count,
                    'diff': csv_count - db_count
                })
        else:
            logger.warning(f"⚠️  {equipment_tag}: Arquivo CSV não encontrado!")
    
    # Relatório final
    logger.info("\n" + "="*80)
    logger.info("📊 RELATÓRIO FINAL")
    logger.info("="*80)
    
    if len(divergences) == 0 and csv_total == db_counts['settings'] and csv_files_count == db_counts['equipments']:
        logger.info("✅ INTEGRIDADE 100% VALIDADA!")
        logger.info("   • Todos os arquivos CSV foram importados corretamente")
        logger.info("   • Todos os registros estão no banco de dados")
        logger.info("   • Nenhuma divergência encontrada")
    else:
        logger.warning("⚠️  DIVERGÊNCIAS ENCONTRADAS:")
        logger.warning(f"   • Total de divergências: {len(divergences)}")
        
        if len(divergences) > 0:
            logger.warning("\n   Detalhes:")
            for div in divergences:
                logger.warning(f"      • {div['equipment']}: CSV tem {div['diff']} registros a mais que DB")
    
    logger.info("\n" + "="*80)

if __name__ == "__main__":
    validate_integrity()

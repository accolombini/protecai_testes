#!/usr/bin/env python3
"""
Importa funções ativas detectadas para o banco de dados PostgreSQL.
Lê o relatório consolidado e popula a tabela active_protection_functions.
"""

import sys
import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/logs/import_functions_db.log'),
        logging.StreamHandler()
    ]
)

# Configuração do banco
DB_CONFIG = {
    'dbname': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai',
    'host': 'localhost',
    'port': '5432'  # Porta correta do container
}

def create_active_functions_table(conn):
    """
    Cria tabela active_protection_functions se não existir.
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS active_protection_functions (
        id SERIAL PRIMARY KEY,
        relay_file VARCHAR(255) NOT NULL,
        relay_model VARCHAR(100),
        function_code VARCHAR(50) NOT NULL,
        function_description VARCHAR(255),
        detection_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        detection_method VARCHAR(50),
        source_file VARCHAR(255),
        UNIQUE(relay_file, function_code)
    );
    
    CREATE INDEX IF NOT EXISTS idx_active_functions_relay 
        ON active_protection_functions(relay_file);
    CREATE INDEX IF NOT EXISTS idx_active_functions_code 
        ON active_protection_functions(function_code);
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
            conn.commit()
            logging.info("✅ Tabela active_protection_functions criada/verificada")
            return True
    except Exception as e:
        logging.error(f"❌ Erro ao criar tabela: {e}")
        conn.rollback()
        return False


def load_relay_models_config():
    """
    Carrega configuração de modelos para mapear função → descrição.
    """
    import json
    config_path = Path('inputs/glossario/relay_models_config.json')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Cria dicionário função → descrição por modelo
    function_descriptions = {}
    for model_name, model_config in config['models'].items():
        for func_code, func_data in model_config['functions'].items():
            if func_code not in function_descriptions:
                function_descriptions[func_code] = func_data['description']
    
    return config['models'], function_descriptions


def identify_relay_model(filename: str, models_config: dict) -> str:
    """
    Identifica modelo do relé baseado no nome do arquivo.
    """
    filename_upper = filename.upper()
    
    # Padrões de identificação (ordem importa!)
    patterns = [
        ('P122_52', 'MICON_P122_52'),
        ('P122_204', 'MICON_P122_204'),
        ('P122_205', 'MICON_P122_205'),
        ('P122', 'MICON_P122_52'),  # Genérico
        ('P143', 'MICON_P143'),
        ('P220', 'MICON_P220'),
        ('P241', 'MICON_P241'),
        ('P922S', 'MICON_P922'),
        ('P922', 'MICON_P922'),
        ('.S40', 'SEPAM_S40')
    ]
    
    for pattern, model in patterns:
        if pattern in filename_upper:
            return model
    
    return 'UNKNOWN'


def import_active_functions(conn, csv_path: Path):
    """
    Importa funções ativas do CSV para o banco de dados.
    """
    # Carrega configuração de modelos
    models_config, function_descriptions = load_relay_models_config()
    
    # Lê CSV consolidado
    df = pd.read_csv(csv_path)
    
    logging.info(f"\n📊 INICIANDO IMPORTAÇÃO")
    logging.info(f"Total de registros no CSV: {len(df)}")
    
    inserted = 0
    updated = 0
    errors = 0
    
    with conn.cursor() as cur:
        for idx, row in df.iterrows():
            relay_file = row['relay_file']
            active_functions = row['active_functions']
            
            # Pula se não há funções ativas (NaN ou vazio)
            if pd.isna(active_functions) or not str(active_functions).strip():
                continue
            
            # Identifica modelo
            relay_model = identify_relay_model(relay_file, models_config)
            
            # Determina método de detecção
            if relay_model in models_config:
                detection_method = models_config[relay_model]['detection_method']
            else:
                detection_method = 'unknown'
            
            # Parse funções ativas (string separada por vírgula)
            functions = [f.strip() for f in str(active_functions).split(',') if f.strip()]
            
            # Insere cada função
            for func_code in functions:
                func_description = function_descriptions.get(func_code, 'Descrição não disponível')
                
                try:
                    # Tenta inserir (com UPSERT usando ON CONFLICT)
                    insert_sql = """
                    INSERT INTO active_protection_functions 
                        (relay_file, relay_model, function_code, function_description, 
                         detection_method, source_file, detection_timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (relay_file, function_code) 
                    DO UPDATE SET
                        relay_model = EXCLUDED.relay_model,
                        function_description = EXCLUDED.function_description,
                        detection_method = EXCLUDED.detection_method,
                        detection_timestamp = EXCLUDED.detection_timestamp
                    """
                    
                    cur.execute(insert_sql, (
                        relay_file,
                        relay_model,
                        func_code,
                        func_description,
                        detection_method,
                        str(csv_path),
                        datetime.now()
                    ))
                    
                    if cur.rowcount > 0:
                        inserted += 1
                    else:
                        updated += 1
                        
                except Exception as e:
                    logging.error(f"❌ Erro ao inserir {relay_file} - {func_code}: {e}")
                    errors += 1
                    conn.rollback()
                    continue
        
        # Commit final
        conn.commit()
    
    logging.info(f"\n✅ IMPORTAÇÃO CONCLUÍDA")
    logging.info(f"  Inseridos: {inserted}")
    logging.info(f"  Atualizados: {updated}")
    logging.info(f"  Erros: {errors}")
    
    return inserted, updated, errors


def generate_validation_report(conn):
    """
    Gera relatório de validação comparando banco com CSV.
    """
    logging.info(f"\n📈 GERANDO RELATÓRIO DE VALIDAÇÃO")
    
    with conn.cursor() as cur:
        # Total de funções no banco
        cur.execute("SELECT COUNT(*) FROM active_protection_functions")
        total_db = cur.fetchone()[0]
        
        # Funções por código ANSI
        cur.execute("""
            SELECT function_code, COUNT(*) as count
            FROM active_protection_functions
            GROUP BY function_code
            ORDER BY count DESC
        """)
        functions_by_code = cur.fetchall()
        
        # Funções por modelo
        cur.execute("""
            SELECT relay_model, COUNT(*) as count
            FROM active_protection_functions
            GROUP BY relay_model
            ORDER BY count DESC
        """)
        functions_by_model = cur.fetchall()
        
        # Relés únicos
        cur.execute("SELECT COUNT(DISTINCT relay_file) FROM active_protection_functions")
        unique_relays = cur.fetchone()[0]
    
    # Imprime relatório
    logging.info(f"\n{'='*80}")
    logging.info(f"RELATÓRIO DE VALIDAÇÃO - BANCO DE DADOS")
    logging.info(f"{'='*80}")
    logging.info(f"Total de funções ativas no banco: {total_db}")
    logging.info(f"Relés únicos com funções: {unique_relays}")
    
    logging.info(f"\nFunções por código ANSI:")
    for func_code, count in functions_by_code:
        logging.info(f"  {func_code}: {count} relés")
    
    logging.info(f"\nFunções por modelo:")
    for model, count in functions_by_model:
        logging.info(f"  {model}: {count} funções")
    
    logging.info(f"{'='*80}\n")
    
    return total_db, unique_relays


def main():
    """
    Executa importação completa.
    """
    logging.info("="*80)
    logging.info("🚀 INICIANDO IMPORTAÇÃO DE FUNÇÕES ATIVAS PARA BANCO DE DADOS")
    logging.info("="*80)
    
    # Paths
    csv_path = Path('outputs/reports/funcoes_ativas_consolidado.csv')
    
    if not csv_path.exists():
        logging.error(f"❌ Arquivo não encontrado: {csv_path}")
        logging.error("Execute primeiro: python scripts/reprocess_pipeline_complete.py")
        sys.exit(1)
    
    # Conecta ao banco
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logging.info(f"✅ Conectado ao banco: {DB_CONFIG['dbname']}")
    except Exception as e:
        logging.error(f"❌ Erro ao conectar ao banco: {e}")
        sys.exit(1)
    
    try:
        # Cria tabela
        if not create_active_functions_table(conn):
            sys.exit(1)
        
        # Importa funções
        inserted, updated, errors = import_active_functions(conn, csv_path)
        
        # Gera relatório de validação
        total_db, unique_relays = generate_validation_report(conn)
        
        # Valida consistência
        df = pd.read_csv(csv_path)
        total_csv_functions = sum(
            len([f.strip() for f in str(row['active_functions']).split(',') if f.strip()]) 
            for _, row in df.iterrows() 
            if pd.notna(row['active_functions']) and str(row['active_functions']).strip()
        )
        
        if total_db == total_csv_functions:
            logging.info("✅ VALIDAÇÃO: Banco e CSV consistentes!")
        else:
            logging.warning(f"⚠️  VALIDAÇÃO: Divergência detectada (CSV: {total_csv_functions}, DB: {total_db})")
        
    finally:
        conn.close()
        logging.info("Conexão com banco encerrada")
    
    logging.info("\n" + "="*80)
    logging.info("✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    logging.info("="*80)


if __name__ == '__main__':
    main()

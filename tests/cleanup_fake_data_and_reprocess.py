#!/usr/bin/env python3
"""
SCRIPT ROBUSTA PARA LIMPEZA E REPROCESSAMENTO
Trata a CAUSA RAIZ: Remove dados FAKE e processa apenas 50 relés REAIS
Data: 28/10/2025
Autor: ProtecAI Team
"""

import os
import sys
import logging
import glob
import psycopg2
from datetime import datetime

# Adicionar path do projeto
sys.path.append('/Users/accol/Library/Mobile Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes')

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'outputs/logs/cleanup_fake_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

# Configuração do banco de dados
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

# Padrões de arquivos FAKE que devem ser removidos
FAKE_PATTERNS = [
    'reprocess_*',
    'tela1*',
    'tela3*'
]

# Diretórios para limpeza
CLEANUP_DIRS = [
    'outputs/csv',
    'outputs/norm_csv',
    'outputs/excel',
    'outputs/norm_excel'
]

def conectar_banco():
    """Conecta ao banco PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        logging.info("✅ Conectado ao PostgreSQL")
        return conn
    except Exception as e:
        logging.error(f"❌ Erro ao conectar PostgreSQL: {e}")
        return None

def limpar_arquivos_fake():
    """Remove todos os arquivos FAKE dos diretórios de output"""
    total_removidos = 0
    
    for dir_path in CLEANUP_DIRS:
        if not os.path.exists(dir_path):
            continue
            
        logging.info(f"🧹 Limpando diretório: {dir_path}")
        
        for pattern in FAKE_PATTERNS:
            files = glob.glob(os.path.join(dir_path, f"{pattern}*"))
            for file_path in files:
                try:
                    os.remove(file_path)
                    logging.info(f"🗑️ Removido: {os.path.basename(file_path)}")
                    total_removidos += 1
                except Exception as e:
                    logging.error(f"❌ Erro ao remover {file_path}: {e}")
    
    logging.info(f"🧹 Total de arquivos FAKE removidos: {total_removidos}")
    return total_removidos

def limpar_banco_dados():
    """Limpa completamente as tabelas de equipamentos"""
    conn = conectar_banco()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Limpar dados de equipamentos (preservar estrutura)
        cleanup_queries = [
            "DELETE FROM protec_ai.relay_settings;",
            "DELETE FROM protec_ai.relay_equipment;", 
            "DELETE FROM protec_ai.relay_models WHERE model_code NOT IN ('P122', 'P143', 'P220', 'P241', 'P922', 'SEPAM_S40');",
            "DELETE FROM protec_ai.protection_functions WHERE id > 10;",  # Manter apenas funções básicas
        ]
        
        for query in cleanup_queries:
            cursor.execute(query)
            logging.info(f"✅ Executado: {query}")
        
        # Verificar limpeza
        cursor.execute("SELECT COUNT(*) FROM protec_ai.relay_equipment;")
        count = cursor.fetchone()[0]
        logging.info(f"🗄️ Equipamentos restantes no banco: {count}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao limpar banco: {e}")
        return False

def contar_arquivos_reais():
    """Conta apenas os arquivos REAIS de relés"""
    real_files = []
    
    # Verificar PDFs originais
    pdf_dir = 'inputs/pdf'
    if os.path.exists(pdf_dir):
        pdfs = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        real_files.extend(pdfs)
    
    # Verificar arquivos S40
    txt_dir = 'inputs/txt'
    if os.path.exists(txt_dir):
        s40_files = [f for f in os.listdir(txt_dir) if f.endswith('.S40')]
        real_files.extend(s40_files)
    
    # Filtrar apenas arquivos reais (sem reprocess, tela1, tela3)
    real_files = [f for f in real_files if not any(fake in f for fake in ['reprocess', 'tela1', 'tela3'])]
    
    logging.info(f"📁 Arquivos REAIS encontrados: {len(real_files)}")
    for f in sorted(real_files):
        logging.info(f"   📄 {f}")
    
    return real_files

def executar_processamento_universal():
    """Executa o processamento universal apenas com dados REAIS"""
    try:
        # Verificar se existe o script universal
        script_path = '/Users/accol/Library/Mobile Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes/scripts/universal_robust_relay_processor.py'
        
        if os.path.exists(script_path):
            logging.info("🚀 Executando processador universal via comando...")
            
            import subprocess
            result = subprocess.run([
                'python3', script_path
            ], capture_output=True, text=True, cwd='/Users/accol/Library/Mobile Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes')
            
            if result.returncode == 0:
                logging.info("✅ Processamento UNIVERSAL concluído com sucesso")
                logging.info(f"📊 Output: {result.stdout}")
                return True
            else:
                logging.error(f"❌ Erro no processamento: {result.stderr}")
                return False
        else:
            logging.error(f"❌ Script não encontrado: {script_path}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Erro ao executar processamento: {e}")
        return False

def main():
    """Função principal de limpeza e reprocessamento"""
    logging.info("🎯 INICIANDO LIMPEZA DE DADOS FAKE E REPROCESSAMENTO")
    logging.info("="*60)
    
    # 1. Contar arquivos reais antes da limpeza
    arquivos_reais = contar_arquivos_reais()
    
    # 2. Limpar arquivos FAKE dos outputs
    arquivos_removidos = limpar_arquivos_fake()
    
    # 3. Limpar banco de dados
    if limpar_banco_dados():
        logging.info("✅ Banco de dados limpo")
    else:
        logging.error("❌ Erro na limpeza do banco")
        return False
    
    # 4. Reprocessar apenas dados REAIS
    if executar_processamento_universal():
        logging.info("✅ Reprocessamento concluído")
    else:
        logging.error("❌ Erro no reprocessamento")
        return False
    
    # 5. Relatório final
    logging.info("="*60)
    logging.info("📊 RELATÓRIO FINAL:")
    logging.info(f"   📁 Arquivos REAIS identificados: {len(arquivos_reais)}")
    logging.info(f"   🗑️ Arquivos FAKE removidos: {arquivos_removidos}")
    logging.info("   🎯 CAUSA RAIZ TRATADA: Apenas dados REAIS processados")
    logging.info("🎉 LIMPEZA E REPROCESSAMENTO CONCLUÍDOS!")
    
    return True

if __name__ == "__main__":
    main()
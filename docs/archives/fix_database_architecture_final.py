#!/usr/bin/env python3
"""
CORREÇÃO ARQUITETURA DATABASE - CAUSA RAIZ - VERSÃO FINAL
Trata o problema fundamental: mapeamento exato 1:1 entre equipamentos e CSVs
Data: 28/10/2025
Autor: ProtecAI Team - ROBUSTA e FLEXÍVEL
"""

import os
import sys
import logging
import psycopg2
import csv
import re
from datetime import datetime
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'outputs/logs/fix_architecture_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
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

def criar_mapeamento_exato():
    """Cria mapeamento EXATO 1:1 entre equipment_tag e arquivo CSV"""
    
    # Dicionário de mapeamento EXATO baseado nos dados reais
    mapeamento = {
        # SEPAM S40 Files
        'REL-SEPAMS40-00-MF-122016-0': '00-MF-12_2016-03-31_params.csv',
        'REL-SEPAMS40-00-MF-142016-0': '00-MF-14_2016-03-31_params.csv', 
        'REL-SEPAMS40-00-MF-242024-0': '00-MF-24_2024-09-10_params.csv',
        
        # P122 Files
        'REL-P122-P12252-MF-02A': 'P122 52-MF-02A_2021-03-08_params.csv',
        'REL-P122-P12252-MF-03A1': 'P122 52-MF-03A1_2021-03-11_params.csv',
        'REL-P122-P122204-MF-2B1': 'P122_204-MF-2B1_2014-07-28_params.csv',
        'REL-P122-P122204-PN-04': 'P122_204-PN-04_2014-08-02_params.csv',
        'REL-P122-P122204-PN-05': 'P122_204-PN-05_2014-08-09_params.csv',
        'REL-P122-P122204-PN-06': 'P122_204-PN-06_LADO_A_2014-08-01_params.csv',
        'REL-P122-P122204-PN-06-f291841f': 'P122_204-PN-06_LADO_B_2014-08-09_params.csv',
        'REL-P122-P122205-TF-3A': 'P122_205-TF-3A_2021-03-08_params.csv',
        'REL-P122-P122205-TF-3B': 'P122_205-TF-3B_2018-06-13_params.csv',
        'REL-P122-P12252-MP-202': 'P122_52-MP-20_2018-08-20_params.csv',
        'REL-P122-P12252-Z-08L': 'P122_52-Z-08_L_PATIO_2014-08-06_params.csv',
        'REL-P122-P12252-Z-08L-8cdd528c': 'P122_52-Z-08_L_REATOR_2014-08-07_params.csv',
        'REL-P122-P12252-MF-03B': 'P_122 52-MF-03B1_2021-03-17_params.csv',
        
        # P143 Files
        'REL-P143-P14352-MF-03A': 'P143 52-MF-03A_params.csv',
        'REL-P143-P143204-MF-03B': 'P143_204-MF-03B_2014-08-14_params.csv',
        'REL-P143-P143204-MF-2A': 'P143_204-MF-2A_2018-06-13_params.csv',
        'REL-P143-P143204-MF-2B': 'P143_204-MF-2B_2018-06-13_params.csv',
        'REL-P143-P143204-MF-2C': 'P143_204-MF-2C_2018-06-13_params.csv',
        'REL-P143-P143204-MF-3C': 'P143_204-MF-3C_2014-08-09_params.csv',
        
        # P220 Files - MAPEAMENTO CORRETO!
        'REL-P122-P220223-MP-01A': 'P220 223-MP-01A_params.csv',
        'REL-P122-P220223-MP-01B': 'P220 223-MP-01B_params.csv',
        'REL-P122-P22052-MP-01A': 'P220 52-MP-01A_params.csv',
        'REL-P122-P22052-MP-04A': 'P220 52-MP-04A_params.csv',
        'REL-P122-P22052-MP-04B': 'P220 52-MP-04B_params.csv',
        'REL-P122-P22052-MP-06A': 'P220 52-MP-06A_params.csv',
        'REL-P122-P22052-MP-06B': 'P220 52-MP-06B_params.csv',
        'REL-P122-P22052-MP-08A': 'P220 52-MP-08A_params.csv',
        'REL-P122-P22052-MP-21A': 'P220 52-MP-21A_params.csv',
        'REL-P122-P22052-MP-21B': 'P220 52-MP-21B_params.csv',
        'REL-P122-P22052-MP-29B': 'P220 52-MP-29B_params.csv',
        'REL-P122-P22052-MP-30': 'P220 52-MP-30_params.csv',
        'REL-P122-P22053-MP-01A': 'P220 53-MP-01A_params.csv',
        'REL-P122-P22053-MP-01B': 'P220 53-MP-01B_params.csv',
        'REL-P122-P22053-MP-08A': 'P220 53-MP-08A_params.csv',
        'REL-P122-P22053-MP-08B': 'P220 53-MP-08B_params.csv',
        'REL-P122-P220-52-MP-08B': 'P220-52-MP-08B_2016-03-11_params.csv',
        'REL-P122-P22052-MK-02A': 'P220_52-MK-02A_2020-07-08_params.csv',
        'REL-P122-P22052-MK-02B': 'P220_52-MK-02B_2017-11-07_params.csv',
        'REL-P122-P22054-MP-1A2': 'P220_54-MP-1A_2018-11-13_params.csv',
        
        # P241 Files
        'REL-P241-P24152-MP-202': 'P241_52-MP-20_2019-08-15_params.csv',
        'REL-P241-P24153-MK-012': 'P241_53-MK-01_2019-08-15_params.csv',
        
        # P922 Files
        'REL-P122-P92252-MF-01BC': 'P922 52-MF-01BC_params.csv',
        'REL-P122-P92252-MF-02AC': 'P922 52-MF-02AC_params.csv',
        'REL-P122-P92252-MF-03AC': 'P922 52-MF-03AC_params.csv',
        'REL-P122-P92252-MF-03BC': 'P922 52-MF-03BC_params.csv',
        'REL-P122-P92252-MF-2BC': 'P922 52-MF-2BC_2021-03-06_params.csv',
        'REL-P122-P922S204-MF-1A': 'P922S_204-MF-1AC_2014-07-28_params.csv'
    }
    
    return mapeamento

def mapear_funcoes_protection():
    """Mapeia códigos de função para IDs das protection_functions"""
    conn = conectar_banco()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, function_code FROM protec_ai.protection_functions;")
        
        mapping = {}
        for row in cursor.fetchall():
            function_id, function_code = row
            # Mapear códigos conhecidos
            if '50' in function_code or 'I>' in function_code:
                mapping['0200'] = function_id  # I>
                mapping['0210'] = function_id  # I>>
                mapping['0220'] = function_id  # I>>>
            elif '51' in function_code or 'Ie>' in function_code:
                mapping['0230'] = function_id  # Ie>
                mapping['0240'] = function_id  # Ie>>
                mapping['0250'] = function_id  # Ie>>>
            elif '46' in function_code or 'I2>' in function_code:
                mapping['025C'] = function_id  # I2>
                mapping['0266'] = function_id  # I2>>
            elif '49' in function_code or 'Therm' in function_code:
                mapping['0253'] = function_id  # Thermal
        
        cursor.close()
        conn.close()
        return mapping
        
    except Exception as e:
        logging.error(f"❌ Erro ao mapear funções: {e}")
        return {}

def processar_arquivo_csv(csv_path, equipment_id, function_mapping):
    """Processa um arquivo CSV e extrai configurações REAIS"""
    
    configurations = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                code = row.get('Code', '').strip()
                description = row.get('Description', '').strip()
                value = row.get('Value', '').strip()
                
                # Identificar funções de proteção
                if code in ['0200', '0210', '0220', '0230', '0240', '0250', '025C', '0266', '0253']:
                    # Determinar se está habilitada
                    is_enabled = False
                    if 'Function' in description:
                        is_enabled = (value.lower() == 'yes')
                    
                    function_id = function_mapping.get(code)
                    if function_id:
                        configurations.append({
                            'type': 'function',
                            'equipment_id': equipment_id,
                            'function_id': function_id,
                            'parameter_code': code,
                            'is_enabled': is_enabled,
                            'description': description
                        })
                
                # Identificar configurações de valores
                elif code in ['0201', '0202', '0204', '0231', '0234', '0241', '0242']:
                    # Valores de configuração das funções
                    set_value = None
                    unit = ''
                    
                    # Extrair valor numérico e unidade
                    if value:
                        # Exemplos: "0.63In", "0.500", "0.10s"
                        match = re.match(r'([0-9.]+)([A-Za-z]*)', value)
                        if match:
                            set_value = float(match.group(1))
                            unit = match.group(2)
                    
                    configurations.append({
                        'type': 'setting',
                        'equipment_id': equipment_id,
                        'parameter_code': code,
                        'parameter_name': description,
                        'set_value': set_value,
                        'unit_of_measure': unit,
                        'is_enabled': True  # Settings são sempre enabled quando existem
                    })
        
        return configurations
        
    except Exception as e:
        logging.error(f"❌ Erro ao processar {csv_path}: {e}")
        return []

def main():
    """Função principal"""
    logging.info("🎯 INICIANDO CORREÇÃO FINAL DA ARQUITETURA - MAPEAMENTO EXATO")
    logging.info("============================================================")
    
    # 1. Limpar dados existentes
    conn = conectar_banco()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM protec_ai.relay_settings;")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'protec_ai' 
                AND table_name = 'equipment_protection_functions'
            );
        """)
        if cursor.fetchone()[0]:
            cursor.execute("DELETE FROM protec_ai.equipment_protection_functions;")
        cursor.close()
        conn.close()
        logging.info("🧹 Dados limpos")
    
    # 2. Obter mapeamentos
    mapeamento_exato = criar_mapeamento_exato()
    function_mapping = mapear_funcoes_protection()
    
    if not function_mapping:
        logging.error("❌ Falha no mapeamento de funções")
        return False
    
    # 3. Processar com mapeamento EXATO
    conn = conectar_banco()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Obter todos os equipamentos
        cursor.execute("SELECT id, equipment_tag FROM protec_ai.relay_equipment ORDER BY id;")
        equipments = cursor.fetchall()
        
        csv_dir = Path('outputs/csv')
        total_functions = 0
        total_settings = 0
        arquivos_processados = 0
        arquivos_nao_encontrados = []
        
        for equipment_id, equipment_tag in equipments:
            # Usar mapeamento EXATO
            csv_filename = mapeamento_exato.get(equipment_tag)
            
            if csv_filename:
                csv_path = csv_dir / csv_filename
                
                if csv_path.exists():
                    logging.info(f"📄 EXATO: {equipment_tag} -> {csv_filename}")
                    
                    configurations = processar_arquivo_csv(csv_path, equipment_id, function_mapping)
                    
                    for config in configurations:
                        if config['type'] == 'function':
                            # Inserir em equipment_protection_functions
                            cursor.execute("""
                                INSERT INTO protec_ai.equipment_protection_functions 
                                (equipment_id, function_id, is_enabled, parameter_code, created_at)
                                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                                ON CONFLICT (equipment_id, function_id, parameter_code) DO UPDATE SET
                                is_enabled = EXCLUDED.is_enabled;
                            """, (
                                config['equipment_id'],
                                config['function_id'],
                                config['is_enabled'],
                                config['parameter_code']
                            ))
                            total_functions += 1
                            
                        elif config['type'] == 'setting':
                            # Inserir em relay_settings
                            cursor.execute("""
                                INSERT INTO protec_ai.relay_settings 
                                (equipment_id, parameter_code, parameter_name, set_value, unit_of_measure, is_enabled, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
                            """, (
                                config['equipment_id'],
                                config['parameter_code'],
                                config['parameter_name'],
                                config['set_value'],
                                config['unit_of_measure'],
                                config['is_enabled']
                            ))
                            total_settings += 1
                    
                    arquivos_processados += 1
                    
                else:
                    logging.error(f"❌ CSV não existe: {csv_filename}")
                    arquivos_nao_encontrados.append(equipment_tag)
            else:
                logging.error(f"❌ Sem mapeamento para: {equipment_tag}")
                arquivos_nao_encontrados.append(equipment_tag)
        
        # 4. Validar resultado
        cursor.execute("SELECT COUNT(*) FROM protec_ai.equipment_protection_functions;")
        total_func_db = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM protec_ai.equipment_protection_functions WHERE is_enabled = TRUE;")
        func_enabled = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM protec_ai.relay_settings;")
        total_settings_db = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        # 5. Relatório final
        logging.info("============================================================")
        logging.info("📊 RESULTADO FINAL - MAPEAMENTO EXATO:")
        logging.info(f"   📁 Arquivos processados: {arquivos_processados}/50")
        logging.info(f"   🔧 Funções no banco: {total_func_db}")
        logging.info(f"   ✅ Funções ativas: {func_enabled}")
        logging.info(f"   ❌ Funções inativas: {total_func_db - func_enabled}")
        logging.info(f"   ⚙️ Settings no banco: {total_settings_db}")
        
        if arquivos_nao_encontrados:
            logging.warning(f"⚠️ Não processados: {len(arquivos_nao_encontrados)}")
            for tag in arquivos_nao_encontrados:
                logging.warning(f"   - {tag}")
        
        logging.info("============================================================")
        logging.info("🎉 MAPEAMENTO EXATO 1:1 CONCLUÍDO!")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro no processamento: {e}")
        return False

if __name__ == "__main__":
    main()
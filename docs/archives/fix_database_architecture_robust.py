#!/usr/bin/env python3
"""
CORREÇÃO ARQUITETURA DATABASE - CAUSA RAIZ
Trata o problema fundamental: falta de status ENABLED/DISABLED nas funções e configurações
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
        logging.FileHandler(f'outputs/logs/fix_architecture_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
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

def criar_nova_estrutura():
    """Cria a nova estrutura de tabelas ROBUSTA"""
    conn = conectar_banco()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 1. Criar tabela equipment_protection_functions
        logging.info("🔧 Criando tabela equipment_protection_functions...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS protec_ai.equipment_protection_functions (
                id SERIAL PRIMARY KEY,
                equipment_id INTEGER NOT NULL REFERENCES protec_ai.relay_equipment(id),
                function_id INTEGER NOT NULL REFERENCES protec_ai.protection_functions(id),
                is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                configuration_group VARCHAR(20) DEFAULT 'GROUP_1',
                parameter_code VARCHAR(10),
                set_value NUMERIC(15,6),
                unit_of_measure VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(equipment_id, function_id, parameter_code)
            );
        """)
        
        # 2. Adicionar índices para performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_equipment_protection_equipment 
            ON protec_ai.equipment_protection_functions(equipment_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_equipment_protection_function 
            ON protec_ai.equipment_protection_functions(function_id);
        """)
        
        # 3. Adicionar coluna is_enabled à relay_settings se não existir
        logging.info("🔧 Verificando coluna is_enabled em relay_settings...")
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'protec_ai' 
            AND table_name = 'relay_settings' 
            AND column_name = 'is_enabled';
        """)
        
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE protec_ai.relay_settings 
                ADD COLUMN is_enabled BOOLEAN DEFAULT TRUE;
            """)
            logging.info("✅ Coluna is_enabled adicionada à relay_settings")
        
        cursor.close()
        conn.close()
        logging.info("✅ Nova estrutura criada com sucesso")
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao criar estrutura: {e}")
        return False

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

def criar_mapeamento_exato():
    """Cria mapeamento EXATO 1:1 entre equipment_tag e arquivo CSV"""
    
    # Mapeamento EXATO baseado nos nomes reais dos arquivos
    mapeamento_exato = {
        # Arquivos S40
        'REL-SEPAMS40-00-MF-122016-0': '00-MF-12_2016-03-31_params.csv',
        'REL-SEPAMS40-00-MF-142016-0': '00-MF-14_2016-03-31_params.csv', 
        'REL-SEPAMS40-00-MF-242024-0': '00-MF-24_2024-09-10_params.csv',
        
        # P122 
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
        
        # P143
        'REL-P143-P14352-MF-03A': 'P143 52-MF-03A_params.csv',
        'REL-P143-P143204-MF-03B': 'P143_204-MF-03B_2014-08-14_params.csv',
        'REL-P143-P143204-MF-2A': 'P143_204-MF-2A_2018-06-13_params.csv',
        'REL-P143-P143204-MF-2B': 'P143_204-MF-2B_2018-06-13_params.csv',
        'REL-P143-P143204-MF-2C': 'P143_204-MF-2C_2018-06-13_params.csv',
        'REL-P143-P143204-MF-3C': 'P143_204-MF-3C_2014-08-09_params.csv',
        
        # P220 (estavam sendo mapeados incorretamente!)
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
        
        # P241
        'REL-P241-P24152-MP-202': 'P241_52-MP-20_2019-08-15_params.csv',
        'REL-P241-P24153-MK-012': 'P241_53-MK-01_2019-08-15_params.csv',
        
        # P922
        'REL-P122-P92252-MF-01BC': 'P922 52-MF-01BC_params.csv',
        'REL-P122-P92252-MF-02AC': 'P922 52-MF-02AC_params.csv',
        'REL-P122-P92252-MF-03AC': 'P922 52-MF-03AC_params.csv',
        'REL-P122-P92252-MF-03BC': 'P922 52-MF-03BC_params.csv',
        'REL-P122-P92252-MF-2BC': 'P922 52-MF-2BC_2021-03-06_params.csv',
        'REL-P122-P922S204-MF-1A': 'P922S_204-MF-1AC_2014-07-28_params.csv'
    }
    
    return mapeamento_exato
    
    conn = conectar_banco()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Obter mapeamento de funções
        function_mapping = mapear_funcoes_protection()
        if not function_mapping:
            logging.error("❌ Não foi possível mapear funções")
            return False
        
        # Obter todos os equipamentos
        cursor.execute("SELECT id, equipment_tag FROM protec_ai.relay_equipment ORDER BY id;")
        equipments = cursor.fetchall()
        
        csv_dir = Path('outputs/csv')
        total_functions = 0
        total_settings = 0
        
        for equipment_id, equipment_tag in equipments:
            # Encontrar arquivo CSV correspondente - ALGORITMO ROBUSTO
            csv_files = []
            
            # 1. Busca exata por tag (removendo prefixo REL-)
            clean_tag = equipment_tag.replace('REL-', '').replace('-', '_')
            csv_files = list(csv_dir.glob(f"*{clean_tag}*_params.csv"))
            
            # 2. Se não encontrou, busca por partes da tag
            if not csv_files:
                tag_parts = equipment_tag.split('-')
                if len(tag_parts) >= 3:
                    # Exemplo: REL-P122-P12252-MF-02A -> buscar P122*MF*02A
                    model = tag_parts[1]  # P122
                    device = tag_parts[-1]  # 02A
                    csv_files = list(csv_dir.glob(f"{model}*{device}*_params.csv"))
            
            # 3. Se ainda não encontrou, busca flexível
            if not csv_files:
                # Buscar apenas pelo modelo e parte final
                if 'SEPAMS40' in equipment_tag:
                    csv_files = list(csv_dir.glob("00-MF-*_params.csv"))
                elif 'P122' in equipment_tag:
                    csv_files = list(csv_dir.glob("P*122*_params.csv"))
                elif 'P143' in equipment_tag:
                    csv_files = list(csv_dir.glob("P143*_params.csv"))
                elif 'P220' in equipment_tag:
                    csv_files = list(csv_dir.glob("P220*_params.csv"))
                elif 'P241' in equipment_tag:
                    csv_files = list(csv_dir.glob("P241*_params.csv"))
                elif 'P922' in equipment_tag:
                    csv_files = list(csv_dir.glob("P922*_params.csv"))
            
            if csv_files:
                csv_path = csv_files[0]
                logging.info(f"📄 Processando: {equipment_tag} -> {csv_path.name}")
                
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
            
            else:
                logging.warning(f"⚠️ Arquivo CSV não encontrado para: {equipment_tag}")
        
        cursor.close()
        conn.close()
        
        logging.info(f"✅ Processamento concluído:")
        logging.info(f"   🔧 Funções de proteção processadas: {total_functions}")
        logging.info(f"   ⚙️ Configurações processadas: {total_settings}")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao processar arquivos: {e}")
        return False
def processar_todos_arquivos():
    """Processa todos os 50 arquivos CSV e extrai configurações REAIS"""
    
    conn = conectar_banco()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Obter mapeamento EXATO
        mapeamento_exato = criar_mapeamento_exato()
        
        # Obter mapeamento de funções
        function_mapping = mapear_funcoes_protection()
        if not function_mapping:
            logging.error("❌ Não foi possível mapear funções")
            return False
        
        # Obter todos os equipamentos
        cursor.execute("SELECT id, equipment_tag FROM protec_ai.relay_equipment ORDER BY id;")
        equipments = cursor.fetchall()
        
        csv_dir = Path('outputs/csv')
        total_functions = 0
        total_settings = 0
        arquivos_processados = 0
        arquivos_nao_encontrados = 0
        
        for equipment_id, equipment_tag in equipments:
            # Usar mapeamento EXATO
            csv_filename = mapeamento_exato.get(equipment_tag)
            
            if csv_filename:
                csv_path = csv_dir / csv_filename
                
                if csv_path.exists():
                    logging.info(f"📄 Processando: {equipment_tag} -> {csv_filename}")
                    
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
                    logging.error(f"❌ Arquivo CSV não existe: {csv_filename}")
                    arquivos_nao_encontrados += 1
            else:
                logging.error(f"❌ Mapeamento não encontrado para: {equipment_tag}")
                arquivos_nao_encontrados += 1
        
        cursor.close()
        conn.close()
        
        logging.info(f"✅ Processamento concluído:")
        logging.info(f"   📁 Arquivos processados: {arquivos_processados}/50")
        logging.info(f"   ❌ Arquivos não encontrados: {arquivos_nao_encontrados}")
        logging.info(f"   🔧 Funções de proteção processadas: {total_functions}")
        logging.info(f"   ⚙️ Configurações processadas: {total_settings}")
        
        if arquivos_processados == 50:
            logging.info("🎉 TODOS OS 50 ARQUIVOS PROCESSADOS COM SUCESSO!")
        else:
            logging.warning(f"⚠️ Apenas {arquivos_processados}/50 arquivos processados")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao processar arquivos: {e}")
        return False                    elif config['type'] == 'setting':
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
            
            else:
                logging.warning(f"⚠️ Arquivo CSV não encontrado para: {equipment_tag}")
        
        cursor.close()
        conn.close()
        
        logging.info(f"✅ Processamento concluído:")
        logging.info(f"   🔧 Funções de proteção processadas: {total_functions}")
        logging.info(f"   ⚙️ Configurações processadas: {total_settings}")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao processar arquivos: {e}")
        return False

def validar_resultado():
    """Valida o resultado final"""
    conn = conectar_banco()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Contar registros
        queries = [
            ("EQUIPMENT_PROTECTION_FUNCTIONS", "SELECT COUNT(*) FROM protec_ai.equipment_protection_functions;"),
            ("FUNCTIONS_ENABLED", "SELECT COUNT(*) FROM protec_ai.equipment_protection_functions WHERE is_enabled = TRUE;"),
            ("FUNCTIONS_DISABLED", "SELECT COUNT(*) FROM protec_ai.equipment_protection_functions WHERE is_enabled = FALSE;"),
            ("RELAY_SETTINGS", "SELECT COUNT(*) FROM protec_ai.relay_settings;"),
            ("SETTINGS_ENABLED", "SELECT COUNT(*) FROM protec_ai.relay_settings WHERE is_enabled = TRUE;")
        ]
        
        logging.info("============================================================")
        logging.info("📊 VALIDAÇÃO RESULTADO FINAL:")
        
        for name, query in queries:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            logging.info(f"   {name}: {count}")
        
        cursor.close()
        conn.close()
        
        logging.info("============================================================")
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro na validação: {e}")
        return False

def main():
    """Função principal"""
    logging.info("🎯 INICIANDO CORREÇÃO DA ARQUITETURA DATABASE")
    logging.info("============================================================")
    
    # 1. Limpar dados existentes problemáticos
    conn = conectar_banco()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM protec_ai.relay_settings;")
        # Verificar se tabela equipment_protection_functions existe antes de deletar
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
        logging.info("🧹 Dados problemáticos removidos")
    
    # 2. Criar nova estrutura
    if not criar_nova_estrutura():
        logging.error("❌ Falha na criação da estrutura")
        return False
    
    # 3. Processar todos os arquivos
    if not processar_todos_arquivos():
        logging.error("❌ Falha no processamento dos arquivos")
        return False
    
    # 4. Validar resultado
    if not validar_resultado():
        logging.error("❌ Falha na validação")
        return False
    
    logging.info("🎉 CORREÇÃO DA ARQUITETURA CONCLUÍDA COM SUCESSO!")
    logging.info("✅ CAUSA RAIZ TRATADA: Status ENABLED/DISABLED implementado")
    
    return True

if __name__ == "__main__":
    main()
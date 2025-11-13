#!/usr/bin/env python3
"""
================================================================================
GERADOR DE POPULAÇÃO DE BANCO DE DADOS A PARTIR DO GLOSSÁRIO
================================================================================
Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 1.0.0

Description:
    Gera scripts SQL e arquivos CSV para popular as tabelas:
    - protec_ai.protection_functions
    - protec_ai.relay_settings
    
    A partir do glossário extraído (glossary_mapping.json/csv).

Usage:
    python scripts/generate_db_population_from_glossary.py

Output:
    - outputs/sql/populate_protection_functions.sql
    - outputs/sql/populate_relay_settings.sql
    - outputs/csv/protection_functions.csv
    - outputs/csv/relay_settings.csv
================================================================================
"""

import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime

# ================================================================================
# CONFIGURAÇÃO
# ================================================================================

BASE_DIR = Path(__file__).parent.parent
GLOSSARY_JSON = BASE_DIR / "inputs/glossario/glossary_mapping.json"
GLOSSARY_CSV = BASE_DIR / "inputs/glossario/glossary_mapping.csv"

OUTPUT_SQL_DIR = BASE_DIR / "outputs/sql"
OUTPUT_CSV_DIR = BASE_DIR / "outputs/csv"

# Criar diretórios de saída
OUTPUT_SQL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV_DIR.mkdir(parents=True, exist_ok=True)

# ================================================================================
# MAPEAMENTO DE FUNÇÕES ANSI/IEEE
# ================================================================================

ANSI_FUNCTION_MAP = {
    # Sobrecorrente
    'I>': ('50', 'Instantaneous Overcurrent'),
    'I>>': ('50', 'Instantaneous Overcurrent - Stage 2'),
    'I>>>': ('50', 'Instantaneous Overcurrent - Stage 3'),
    'I<': ('37', 'Undercurrent'),
    
    # Terra
    'Ie>': ('50N', 'Instantaneous Ground Overcurrent'),
    'Ie>>': ('50N', 'Instantaneous Ground Overcurrent - Stage 2'),
    'Ie>>>': ('50N', 'Instantaneous Ground Overcurrent - Stage 3'),
    'I0>': ('50N', 'Zero Sequence Overcurrent'),
    
    # Sequência negativa
    'I2>': ('46', 'Negative Sequence Overcurrent'),
    'I2>>': ('46', 'Negative Sequence Overcurrent - Stage 2'),
    
    # Direcionais
    'DIR': ('67', 'Directional Overcurrent'),
    'DIR-N': ('67N', 'Directional Ground Overcurrent'),
    
    # Diferencial
    'DIFF': ('87', 'Differential Protection'),
    
    # Distância
    'Z1': ('21', 'Distance Protection - Zone 1'),
    'Z2': ('21', 'Distance Protection - Zone 2'),
    'Z3': ('21', 'Distance Protection - Zone 3'),
    
    # Frequência
    'f>': ('81O', 'Over Frequency'),
    'f<': ('81U', 'Under Frequency'),
    
    # Tensão
    'V>': ('59', 'Overvoltage'),
    'V<': ('27', 'Undervoltage'),
    'V2>': ('47', 'Negative Sequence Voltage'),
    'V0>': ('59N', 'Neutral Overvoltage'),
    
    # Térmicas
    'THM': ('49', 'Thermal Overload'),
    
    # Religamento
    'AUTO': ('79', 'Auto Reclosing'),
    
    # Sincronismo
    'SYNC': ('25', 'Synchronism Check'),
}

# ================================================================================
# FUNÇÕES AUXILIARES
# ================================================================================

def extract_function_from_name(name: str) -> Tuple[str, str, str]:
    """
    Extrai código ANSI e função a partir do nome do parâmetro.
    
    Args:
        name: Nome do parâmetro (ex: "Function I>", "I>>", "Ie>")
    
    Returns:
        Tuple (ansi_code, function_name, clean_name)
    
    Examples:
        >>> extract_function_from_name("Function I>")
        ('50', 'Instantaneous Overcurrent', 'I>')
        >>> extract_function_from_name("I2>>")
        ('46', 'Negative Sequence Overcurrent - Stage 2', 'I2>>')
    """
    # Remove "Function" prefix
    clean = name.replace('Function ', '').strip()
    
    # Busca padrões conhecidos
    for pattern, (ansi_code, func_name) in ANSI_FUNCTION_MAP.items():
        if pattern in clean or clean.startswith(pattern):
            return ansi_code, func_name, clean
    
    # Fallback: tenta detectar por padrões
    if re.match(r'I\d*>{1,3}', clean):
        return '50', 'Overcurrent Protection', clean
    elif re.match(r'Ie\d*>{1,3}', clean):
        return '50N', 'Ground Overcurrent Protection', clean
    elif re.match(r'V\d*[><]', clean):
        return '59/27', 'Voltage Protection', clean
    elif re.match(r'f[><]', clean):
        return '81', 'Frequency Protection', clean
    
    return 'PARAM', 'Parameter Setting', clean


def categorize_parameter(code: str, name: str) -> str:
    """
    Categoriza o parâmetro em grupo funcional.
    
    Args:
        code: Código do parâmetro (ex: "0200", "010A")
        name: Nome do parâmetro
    
    Returns:
        Categoria do parâmetro
    """
    name_lower = name.lower()
    
    if 'function' in name_lower:
        return 'PROTECTION_FUNCTION'
    elif any(x in name_lower for x in ['delay', 'time', 'tms', 'reset']):
        return 'TIMING'
    elif any(x in name_lower for x in ['ct', 'vt', 'primary', 'secondary', 'ratio']):
        return 'INSTRUMENTATION'
    elif any(x in name_lower for x in ['frequency', 'voltage', 'phase']):
        return 'ELECTRICAL_CONFIG'
    elif any(x in name_lower for x in ['idmt', 'curve', 'characteristic']):
        return 'CURVE_SETTING'
    elif 'description' in name_lower or 'reference' in name_lower or 'text' in name_lower:
        return 'IDENTIFICATION'
    elif re.match(r'I[e0-9]*>{1,3}', name):
        return 'OVERCURRENT_SETTING'
    elif 'sample' in name_lower:
        return 'SAMPLING'
    else:
        return 'GENERAL_PARAMETER'


def parse_value_and_unit(value_example: str) -> Tuple[str, str, str]:
    """
    Extrai valor numérico, texto e unidade do exemplo.
    
    Args:
        value_example: Exemplo de valor (ex: "0.63In", "YES / NO", "0.10s")
    
    Returns:
        Tuple (numeric_value, text_value, unit)
    
    Examples:
        >>> parse_value_and_unit("0.63In")
        ('0.63', '0.63In', 'In')
        >>> parse_value_and_unit("YES / NO")
        ('', 'YES / NO', '')
        >>> parse_value_and_unit("0.10s")
        ('0.10', '0.10s', 's')
    """
    if not value_example or str(value_example).strip() == '':
        return '', '', ''
    
    value_str = str(value_example).strip()
    
    # Tenta extrair número
    numeric_match = re.search(r'[\d.]+', value_str)
    numeric_value = numeric_match.group(0) if numeric_match else ''
    
    # Tenta extrair unidade
    unit_match = re.search(r'(In|Ien|Hz|s|A|V|Ω|%|°)$', value_str)
    unit = unit_match.group(1) if unit_match else ''
    
    return numeric_value, value_str, unit


# ================================================================================
# GERAÇÃO DE DADOS
# ================================================================================

def load_glossary() -> List[Dict]:
    """Carrega o glossário do arquivo JSON."""
    print(f"[INFO] Carregando glossário de: {GLOSSARY_JSON}")
    with open(GLOSSARY_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # O JSON está estruturado como {modelo: [registros]}
    # Precisamos achatar para lista única
    all_records = []
    if isinstance(data, dict):
        for model, records in data.items():
            if isinstance(records, list):
                all_records.extend(records)
    elif isinstance(data, list):
        all_records = data
    
    print(f"[OK] Carregados {len(all_records)} registros")
    return all_records


def generate_protection_functions(glossary: List[Dict]) -> Tuple[List[Dict], Set[str]]:
    """
    Gera lista de funções de proteção únicas.
    
    Returns:
        Tuple (functions_list, processed_codes)
    """
    functions = {}
    processed = set()
    
    for record in glossary:
        name = record['name']
        code = record['code']
        
        # Ignora parâmetros que não são funções
        if not name.startswith('Function ') and 'Function' not in name:
            continue
        
        ansi_code, func_name, clean_name = extract_function_from_name(name)
        
        # Cria chave única
        key = f"{ansi_code}_{clean_name}"
        
        if key not in functions:
            functions[key] = {
                'function_code': ansi_code,
                'function_name': func_name,
                'function_description': f'Protection function {clean_name}',
                'ansi_ieee_standard': f'ANSI {ansi_code}',
                'typical_application': 'Relay protection',
                'is_primary': ansi_code in ['50', '51', '87', '21'],
                'is_backup': False
            }
            processed.add(code)
    
    print(f"[INFO] Identificadas {len(functions)} funções de proteção únicas")
    return list(functions.values()), processed


def generate_relay_settings(glossary: List[Dict], function_codes: Set[str]) -> List[Dict]:
    """
    Gera lista de configurações/parâmetros dos relés.
    
    Args:
        glossary: Lista do glossário
        function_codes: Códigos já processados como funções
    
    Returns:
        Lista de settings
    """
    settings = []
    
    for record in glossary:
        code = record['code']
        name = record['name']
        value_example = record.get('value_example', '')
        unit = record.get('unit', '')
        model = record['model']
        
        # Pula funções já processadas
        if code in function_codes:
            continue
        
        # Extrai valores
        numeric_val, text_val, extracted_unit = parse_value_and_unit(value_example)
        final_unit = unit if unit else extracted_unit
        
        # Categoriza
        category = categorize_parameter(code, name)
        
        # Determina function_id (NULL por enquanto, será resolvido via JOIN no SQL)
        ansi_code, func_name, _ = extract_function_from_name(name)
        
        setting = {
            'parameter_name': name,
            'parameter_code': code,
            'set_value': numeric_val if numeric_val else None,
            'set_value_text': text_val if text_val else None,
            'unit_of_measure': final_unit if final_unit else None,
            'category': category,
            'model_reference': model,
            'ansi_reference': ansi_code if ansi_code != 'PARAM' else None,
            'is_enabled': True,
            'setting_group': 'GROUP_1'
        }
        
        settings.append(setting)
    
    print(f"[INFO] Geradas {len(settings)} configurações de parâmetros")
    return settings


# ================================================================================
# EXPORTAÇÃO SQL
# ================================================================================

def generate_sql_protection_functions(functions: List[Dict]) -> str:
    """Gera script SQL para popular protection_functions."""
    sql_lines = [
        "-- ================================================================================",
        "-- POPULAÇÃO DE FUNÇÕES DE PROTEÇÃO (protec_ai.protection_functions)",
        "-- ================================================================================",
        f"-- Gerado automaticamente em: {datetime.now().isoformat()}",
        f"-- Total de funções: {len(functions)}",
        "-- ================================================================================\n",
        "-- Limpar dados existentes (CUIDADO: use apenas em ambiente de desenvolvimento)",
        "-- DELETE FROM protec_ai.protection_functions;\n",
        "-- Inserir funções de proteção",
        "INSERT INTO protec_ai.protection_functions (",
        "    function_code, function_name, function_description,",
        "    ansi_ieee_standard, typical_application, is_primary, is_backup",
        ") VALUES"
    ]
    
    for i, func in enumerate(functions):
        comma = ',' if i < len(functions) - 1 else ';'
        sql_lines.append(
            f"    ('{func['function_code']}', '{func['function_name']}', "
            f"'{func['function_description']}', '{func['ansi_ieee_standard']}', "
            f"'{func['typical_application']}', {func['is_primary']}, {func['is_backup']}){comma}"
        )
    
    sql_lines.append("\n-- ================================================================================")
    sql_lines.append("-- FIM DO SCRIPT")
    sql_lines.append("-- ================================================================================")
    
    return '\n'.join(sql_lines)


def generate_sql_relay_settings(settings: List[Dict]) -> str:
    """Gera script SQL para popular relay_settings."""
    sql_lines = [
        "-- ================================================================================",
        "-- POPULAÇÃO DE CONFIGURAÇÕES DE RELÉS (protec_ai.relay_settings)",
        "-- ================================================================================",
        f"-- Gerado automaticamente em: {datetime.now().isoformat()}",
        f"-- Total de parâmetros: {len(settings)}",
        "-- ================================================================================\n",
        "-- NOTA: Este script insere parâmetros SEM vincular a equipamentos específicos.",
        "-- Os campos equipment_id e function_id devem ser atualizados posteriormente.",
        "-- Use este script como template ou adapte para seu cenário.\n",
        "-- Inserir configurações (template - ajustar equipment_id conforme necessário)",
        "INSERT INTO protec_ai.relay_settings (",
        "    equipment_id, function_id, parameter_name, parameter_code,",
        "    set_value, set_value_text, unit_of_measure, setting_group, is_enabled",
        ") VALUES"
    ]
    
    for i, setting in enumerate(settings):
        comma = ',' if i < len(settings) - 1 else ';'
        
        # NULL para equipment_id e function_id (devem ser preenchidos depois)
        set_value = setting['set_value'] if setting['set_value'] else 'NULL'
        set_value_text = f"'{setting['set_value_text']}'" if setting['set_value_text'] else 'NULL'
        unit = f"'{setting['unit_of_measure']}'" if setting['unit_of_measure'] else 'NULL'
        
        sql_lines.append(
            f"    (NULL, NULL, '{setting['parameter_name']}', '{setting['parameter_code']}', "
            f"{set_value}, {set_value_text}, {unit}, '{setting['setting_group']}', "
            f"{setting['is_enabled']}){comma}"
        )
    
    sql_lines.append("\n-- ================================================================================")
    sql_lines.append("-- OBSERVAÇÕES:")
    sql_lines.append("-- 1. Os campos equipment_id e function_id estão como NULL")
    sql_lines.append("-- 2. Atualize-os com base nos equipamentos reais do seu sistema")
    sql_lines.append("-- 3. Use JOINs para vincular parâmetros a funções pelo ansi_reference")
    sql_lines.append("-- ================================================================================")
    
    return '\n'.join(sql_lines)


# ================================================================================
# EXPORTAÇÃO CSV
# ================================================================================

def export_csv_protection_functions(functions: List[Dict], filepath: Path):
    """Exporta funções para CSV."""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        if not functions:
            return
        
        fieldnames = list(functions[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(functions)
    
    print(f"[OK] CSV de funções salvo: {filepath}")


def export_csv_relay_settings(settings: List[Dict], filepath: Path):
    """Exporta settings para CSV."""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        if not settings:
            return
        
        fieldnames = list(settings[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(settings)
    
    print(f"[OK] CSV de settings salvo: {filepath}")


# ================================================================================
# MAIN
# ================================================================================

def main():
    """Função principal."""
    print("=" * 80)
    print("GERADOR DE POPULAÇÃO DE BANCO DE DADOS")
    print("=" * 80)
    
    # 1. Carregar glossário
    glossary = load_glossary()
    
    # 2. Gerar funções de proteção
    functions, function_codes = generate_protection_functions(glossary)
    
    # 3. Gerar settings
    settings = generate_relay_settings(glossary, function_codes)
    
    # 4. Gerar SQL
    print("\n[INFO] Gerando scripts SQL...")
    sql_functions = generate_sql_protection_functions(functions)
    sql_settings = generate_sql_relay_settings(settings)
    
    # 5. Salvar SQL
    sql_func_file = OUTPUT_SQL_DIR / "populate_protection_functions.sql"
    sql_settings_file = OUTPUT_SQL_DIR / "populate_relay_settings.sql"
    
    with open(sql_func_file, 'w', encoding='utf-8') as f:
        f.write(sql_functions)
    print(f"[OK] SQL funções salvo: {sql_func_file}")
    
    with open(sql_settings_file, 'w', encoding='utf-8') as f:
        f.write(sql_settings)
    print(f"[OK] SQL settings salvo: {sql_settings_file}")
    
    # 6. Exportar CSV
    print("\n[INFO] Exportando CSVs...")
    csv_func_file = OUTPUT_CSV_DIR / "protection_functions.csv"
    csv_settings_file = OUTPUT_CSV_DIR / "relay_settings.csv"
    
    export_csv_protection_functions(functions, csv_func_file)
    export_csv_relay_settings(settings, csv_settings_file)
    
    # 7. Resumo
    print("\n" + "=" * 80)
    print("[SUCESSO] Geração concluída!")
    print("=" * 80)
    print(f"Funções de proteção: {len(functions)}")
    print(f"Parâmetros/settings: {len(settings)}")
    print(f"\nArquivos gerados:")
    print(f"  SQL Funções:  {sql_func_file}")
    print(f"  SQL Settings: {sql_settings_file}")
    print(f"  CSV Funções:  {csv_func_file}")
    print(f"  CSV Settings: {csv_settings_file}")
    print("=" * 80)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Script para detectar funções de proteção com nomenclatura IEC em relés P122, P241 e P922
Lê os CSVs já extraídos com is_active e mapeia códigos IEC → ANSI
Adiciona as funções detectadas à tabela active_protection_functions
"""

import sys
import re
import psycopg2
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple

# Mapeamento IEC → ANSI
IEC_TO_ANSI = {
    # Sobrecorrente de fase
    'I>': ('50/51', 'Sobrecorrente de Fase'),
    'I>>': ('50', 'Sobrecorrente de Fase Instantânea'),
    'I>>>': ('50', 'Sobrecorrente de Fase Alta'),
    'tI>': ('51', 'Sobrecorrente de Fase Temporizada'),
    
    # Sobrecorrente de terra
    'Ie>': ('50N/51N', 'Sobrecorrente de Terra'),
    'Ie>>': ('50N', 'Sobrecorrente de Terra Instantânea'),
    'Ie>>>': ('50N', 'Sobrecorrente de Terra Alta'),
    'ISEF>': ('50N/51N', 'Sobrecorrente de Terra Sensível'),
    'ISEF>>': ('50N', 'Sobrecorrente de Terra Sensível Instantânea'),
    
    # Sequência negativa
    'I2>': ('46', 'Corrente de Sequência Negativa'),
    'I2>>': ('46', 'Corrente de Sequência Negativa Instantânea'),
    
    # Subtensão
    'U<': ('27', 'Subtensão'),
    'U<<': ('27', 'Subtensão Baixa'),
    'tU<': ('27', 'Subtensão Temporizada'),
    'V<': ('27', 'Subtensão'),
    'V<1': ('27', 'Subtensão Estágio 1'),
    'V<2': ('27', 'Subtensão Estágio 2'),
    
    # Sobretensão
    'U>': ('59', 'Sobretensão'),
    'U>>': ('59', 'Sobretensão Alta'),
    'tU>': ('59', 'Sobretensão Temporizada'),
    'V>': ('59', 'Sobretensão'),
    
    # Sobretensão residual/neutro
    'Vo>': ('59N', 'Sobretensão de Neutro'),
    'Vo>>': ('59N', 'Sobretensão de Neutro Alta'),
    'tVo>': ('59N', 'Sobretensão de Neutro Temporizada'),
    
    # Sobretensão sequência negativa
    'V2>': ('47', 'Sobretensão de Sequência Negativa'),
    'tV2>': ('47', 'Sobretensão de Sequência Negativa Temporizada'),
    
    # Proteção de motor (P241)
    'Thermal Overload': ('49', 'Sobrecarga Térmica'),
    'Short Circuit': ('50', 'Curto-Circuito'),
    'Stall Detection': ('48/51LR', 'Rotor Travado'),
    'Prolonged Start': ('48', 'Partida Prolongada'),
    'I<': ('37', 'Subcorrente'),
}

# Relés a processar (dos 13 identificados)
RELAYS_TO_PROCESS = [
    'P122 52-MF-02A_2021-03-08',
    'P122 52-MF-03A1_2021-03-11',
    'P122_204-PN-04_2014-08-02',
    'P122_204-PN-05_2014-08-09',
    'P122_204-PN-06_LADO_A_2014-08-01',
    'P122_204-PN-06_LADO_B_2014-08-09',
    'P122_205-TF-3B_2018-06-13',
    'P122_52-MP-20_2018-08-20',
    'P122_52-Z-08_L_REATOR_2014-08-07',
    'P_122 52-MF-03B1_2021-03-17',
    'P241_52-MP-20_2019-08-15',
    'P241_53-MK-01_2019-08-15',
    'P922 52-MF-02AC',
]

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

def find_relay_csv(relay_tag: str, csv_dir: Path) -> Path:
    """Encontra CSV _active_setup.csv do relé"""
    # Buscar arquivo _active_setup.csv
    csv_file = csv_dir / f"{relay_tag}_active_setup.csv"
    if csv_file.exists():
        return csv_file
    
    # Buscar com glob
    matches = list(csv_dir.glob(f"{relay_tag}*_active_setup.csv"))
    if matches:
        return matches[0]
    
    return None

def detect_iec_functions_in_csv(csv_path: Path) -> List[Tuple[str, str]]:
    """Detecta funções IEC ativas no CSV extraído"""
    functions_found = []
    
    try:
        # Ler CSV
        df = pd.read_csv(csv_path)
        
        # Filtrar apenas parâmetros ativos
        if 'is_active' in df.columns:
            active_df = df[df['is_active'] == True]
            
            # Buscar códigos IEC nas colunas Code, Description e Value
            for _, row in active_df.iterrows():
                code = str(row.get('Code', ''))
                description = str(row.get('Description', ''))
                value = str(row.get('Value', ''))
                
                # Buscar códigos IEC na Description (formato: "tI>:" ou "I>>:")
                for iec_code, (ansi, desc) in IEC_TO_ANSI.items():
                    # Match exato do código IEC (com ou sem :, com ou sem "Function" prefix)
                    pattern = rf'^(Function\s+)?{re.escape(iec_code)}:?\s*$'
                    if re.match(pattern, description.strip(), re.IGNORECASE):
                        functions_found.append((ansi, desc))
                        break
    
    except Exception as e:
        print(f"   ⚠️ Erro lendo CSV {csv_path.name}: {e}")
    
    return functions_found

def detect_checkbox_iec_functions(content: str) -> List[Tuple[str, str]]:
    """Detecta funções IEC com checkboxes marcados (P122/P922)"""
    functions = []
    
    # Padrões de checkbox marcado: ☒, ⊠, ✓, [X], (X)
    checkbox_patterns = [
        r'[☒⊠✓✗✘]\s*([IUV]e?[><]{1,3}|t[IUV]e?[><]|Vo[><]{1,2}|V2[><])',
        r'\[X\]\s*([IUV]e?[><]{1,3}|t[IUV]e?[><]|Vo[><]{1,2}|V2[><])',
        r'\(X\)\s*([IUV]e?[><]{1,3}|t[IUV]e?[><]|Vo[><]{1,2}|V2[><])',
    ]
    
    for pattern in checkbox_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            iec_code = match.group(1)
            if iec_code in IEC_TO_ANSI:
                ansi_code, description = IEC_TO_ANSI[iec_code]
                functions.append((ansi_code, description))
    
    return functions

def detect_p241_functions(content: str) -> List[Tuple[str, str]]:
    """Detecta funções P241 por padrões 'Enabled'"""
    functions = []
    
    # Padrões específicos do P241
    p241_patterns = {
        r'Trip\s+Enabled': [('50', 'Short Circuit'), ('49', 'Thermal Overload')],
        r'Thermal.*Enabled': [('49', 'Sobrecarga Térmica')],
        r'Short\s+Circuit.*Enabled': [('50', 'Curto-Circuito')],
        r'Sensitive\s+E/F.*Enabled': [('50N/51N', 'Sobrecorrente de Terra Sensível')],
        r'ISEF>.*Enabled': [('50N/51N', 'SEF')],
        r'Neg\s+Seq.*O/C.*Enabled': [('46', 'Corrente Sequência Negativa')],
        r'I2>.*Enabled': [('46', 'Corrente Sequência Negativa')],
        r'Stall\s+Detection.*Enabled': [('48/51LR', 'Rotor Travado')],
        r'Prolonged\s+Start.*Enabled': [('48', 'Partida Prolongada')],
        r'Under-voltage|V<.*Enabled': [('27', 'Subtensão')],
        r'Over-voltage|V>.*Enabled': [('59', 'Sobretensão')],
        r'Under-current|I<': [('37', 'Subcorrente')],
        r'Limit\s+nb\s+Starts.*Enabled': [('66', 'Limite de Partidas')],
        r'RTD.*Enabled': [('49T/38', 'Temperatura RTD')],
    }
    
    for pattern, func_list in p241_patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            for ansi_code, desc in func_list:
                functions.append((ansi_code, desc))
    
    # Remover duplicatas
    return list(set(functions))

def get_relay_model(relay_tag: str) -> str:
    """Determina modelo do relé pelo tag"""
    if 'P122' in relay_tag or 'P_122' in relay_tag:
        return 'MICON_P122'
    elif 'P241' in relay_tag:
        return 'MICON_P241'
    elif 'P922' in relay_tag:
        return 'MICON_P922'
    return 'UNKNOWN'

def insert_functions_to_db(conn, relay_file: str, relay_model: str, functions: List[Tuple[str, str]]):
    """Insere funções detectadas no banco"""
    cursor = conn.cursor()
    
    inserted = 0
    for ansi_code, description in functions:
        try:
            cursor.execute("""
                INSERT INTO active_protection_functions 
                (relay_file, relay_model, function_code, function_description, detection_method)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (relay_file, relay_model, ansi_code, description, 'iec_mapping'))
            
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"      ⚠️ Erro inserindo {ansi_code}: {e}")
    
    conn.commit()
    return inserted

def main():
    print("=" * 70)
    print("🔍 DETECÇÃO DE FUNÇÕES IEC EM RELÉS P122/P241/P922")
    print("=" * 70)
    
    # Diretório dos CSVs extraídos
    base_path = Path(__file__).parent.parent
    csv_dir = base_path / 'outputs' / 'csv'
    
    if not csv_dir.exists():
        print(f"❌ Diretório não encontrado: {csv_dir}")
        return
    
    # Conectar ao banco
    conn = psycopg2.connect(**DB_CONFIG)
    print("✅ Conectado ao PostgreSQL\n")
    
    total_functions = 0
    relays_processed = 0
    
    for relay_tag in RELAYS_TO_PROCESS:
        print(f"📋 Processando: {relay_tag}")
        
        # Encontrar CSV
        csv_path = find_relay_csv(relay_tag, csv_dir)
        if not csv_path:
            print(f"   ❌ CSV não encontrado\n")
            continue
        
        print(f"   📄 Arquivo: {csv_path.name}")
        
        # Determinar modelo
        relay_model = get_relay_model(relay_tag)
        print(f"   🔧 Modelo: {relay_model}")
        
        # Detectar funções
        functions = detect_iec_functions_in_csv(csv_path)
        
        if not functions:
            print(f"   ⚠️ Nenhuma função detectada\n")
            continue
        
        print(f"   ✅ Detectadas {len(functions)} funções:")
        for ansi, desc in set(functions):
            print(f"      • {ansi}: {desc}")
        
        # Inserir no banco
        relay_filename = relay_tag + '.pdf'  # Usar nome padrão
        inserted = insert_functions_to_db(conn, relay_filename, relay_model, functions)
        print(f"   💾 Inseridas {inserted} funções no banco\n")
        
        total_functions += inserted
        relays_processed += 1
    
    conn.close()
    
    print("=" * 70)
    print(f"✅ PROCESSAMENTO CONCLUÍDO")
    print(f"   Relés processados: {relays_processed}/{len(RELAYS_TO_PROCESS)}")
    print(f"   Funções inseridas: {total_functions}")
    print("=" * 70)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
🔬 VALIDAÇÃO CRÍTICA: Extração Real vs Glossário Esperado

Compara:
1. Parâmetros extraídos dos PDFs/CSVs (no banco de dados)
2. Parâmetros esperados (no glossário)
3. Identifica: faltantes, extras, nomenclatura incorreta

CRÍTICO: Vidas dependem da precisão desses dados!
"""

import pandas as pd
import psycopg2
import json
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

# Configurações
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

GLOSSARIO_PATH = Path('inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx')
OUTPUT_PATH = Path('outputs/logs/validation_extraction_vs_glossario.json')

# Mapeamento modelo → aba do glossário
MODEL_TO_SHEET = {
    'P122': 'MICON P122_52 e P122_204',
    'P122_52': 'MICON P122_52 e P122_204',
    'P122_204': 'MICON P122_52 e P122_204',
    'P122_205': 'MICON P122_205',
    'P220': 'MICON P220',
    'P922': 'MICON P922',
    'P922S': 'MICON P922',  # Variante do P922
    'P241': 'MICON P241',
    'P143': 'MICON P143',
    'SEPAM': 'SEPAM S40',
}


def extract_glossario_parameters(sheet_name: str) -> Dict[str, Dict]:
    """Extrai parâmetros esperados de uma aba do glossário."""
    print(f"\n📖 Lendo aba: {sheet_name}")
    
    try:
        df = pd.read_excel(GLOSSARIO_PATH, sheet_name=sheet_name, header=None)
    except Exception as e:
        print(f"❌ Erro ao ler aba {sheet_name}: {e}")
        return {}
    
    parameters = {}
    current_section = None
    current_subsection = None
    
    for idx, row in df.iterrows():
        # Converter linha em lista de strings
        row_data = [str(cell) if pd.notna(cell) else '' for cell in row]
        row_text = ' '.join(row_data).strip()
        
        # Detectar seções (OP PARAMETERS, CONFIGURATION, etc)
        if any(keyword in row_text.upper() for keyword in ['PARAMETERS', 'CONFIGURATION', 'PROTECTION', 'SYSTEM DATA']):
            if ':' not in row_text and '=' not in row_text:  # Não é um parâmetro
                current_section = row_text.strip()
                continue
        
        # Detectar subseções ([50N/51N], DISPLAY, etc)
        if row_text.startswith('[') and ']' in row_text:
            current_subsection = row_text.strip()
            continue
        
        # Extrair parâmetros
        # Formato Schneider MiCOM: "0104: Frequency: 60Hz"
        # Formato GE MiCOM: "00.09: Frequency: 60 Hz"
        # Formato SEPAM: "i_nominal=600"
        
        for cell in row_data:
            cell = cell.strip()
            if not cell or cell == 'nan':
                continue
            
            # SEPAM format
            if '=' in cell and ':' not in cell:
                parts = cell.split('=')
                if len(parts) == 2:
                    param_name = parts[0].strip()
                    param_value = parts[1].strip()
                    parameters[param_name] = {
                        'name': param_name,
                        'example_value': param_value,
                        'section': current_section,
                        'subsection': current_subsection,
                        'format': 'SEPAM'
                    }
            
            # MiCOM format (Schneider/GE)
            elif ':' in cell:
                # Formato: "0104: Frequency: 60Hz" ou "00.09: Frequency: 60 Hz"
                parts = cell.split(':', 2)
                if len(parts) >= 2:
                    code = parts[0].strip()
                    
                    # Validar se é código válido
                    if code and (code.replace('.', '').isdigit() or code.isdigit()):
                        param_name = parts[1].strip() if len(parts) >= 2 else ''
                        param_value = parts[2].strip() if len(parts) >= 3 else ''
                        
                        full_key = f"{code}: {param_name}"
                        parameters[full_key] = {
                            'code': code,
                            'name': param_name,
                            'example_value': param_value,
                            'section': current_section,
                            'subsection': current_subsection,
                            'format': 'MiCOM'
                        }
    
    print(f"   ✅ Extraídos {len(parameters)} parâmetros esperados")
    return parameters


def get_database_parameters() -> Dict[str, List[Dict]]:
    """Busca parâmetros extraídos do banco de dados, agrupados por modelo."""
    print("\n🔍 Buscando parâmetros no banco de dados...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    query = """
        SELECT 
            f.nome_completo,
            rm.model_name,
            rs.parameter_name,
            rs.set_value_text,
            rs.unit_of_measure,
            re.equipment_tag,
            rs.category
        FROM protec_ai.relay_settings rs
        JOIN protec_ai.relay_equipment re ON rs.equipment_id = re.id
        JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
        JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
        WHERE rs.deleted_at IS NULL
        ORDER BY f.nome_completo, rm.model_name, rs.parameter_name
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Agrupar por modelo
    params_by_model = defaultdict(list)
    
    for row in rows:
        manufacturer, model_name, param_name, value, unit, equipment_tag, category = row
        model_key = f"{manufacturer} - {model_name}"
        params_by_model[model_key].append({
            'equipment': equipment_tag,
            'parameter': param_name,
            'value': value,
            'unit': unit,
            'category': category
        })
    
    cursor.close()
    conn.close()
    
    print(f"   ✅ {len(params_by_model)} modelos encontrados no banco")
    for model, params in params_by_model.items():
        print(f"      • {model}: {len(params)} parâmetros")
    
    return dict(params_by_model)


def normalize_parameter_name(name: str) -> str:
    """Normaliza nome de parâmetro para comparação."""
    # Remove espaços extras, converte para minúsculas
    normalized = name.lower().strip()
    # Remove caracteres especiais comuns
    normalized = normalized.replace('_', ' ').replace('-', ' ')
    # Remove espaços múltiplos
    normalized = ' '.join(normalized.split())
    return normalized


def compare_model_parameters(model_code: str, db_params: List[Dict], glossario_params: Dict) -> Dict:
    """Compara parâmetros de um modelo específico."""
    
    print(f"\n🔬 Analisando modelo: {model_code}")
    
    # Extrair apenas nomes únicos de parâmetros do banco
    db_param_names = set()
    for param in db_params:
        db_param_names.add(param['parameter'])
    
    # Extrair nomes do glossário
    glossario_param_names = set()
    glossario_param_map = {}
    
    for key, info in glossario_params.items():
        if info['format'] == 'SEPAM':
            glossario_param_names.add(info['name'])
            glossario_param_map[info['name']] = info
        else:  # MiCOM
            # Tentar com código completo
            glossario_param_names.add(key)
            glossario_param_map[key] = info
            # Também adicionar só o nome
            if info['name']:
                glossario_param_names.add(info['name'])
    
    # Normalizar para comparação fuzzy
    db_normalized = {normalize_parameter_name(p): p for p in db_param_names}
    glossario_normalized = {normalize_parameter_name(p): p for p in glossario_param_names}
    
    # Encontrar matches exatos
    exact_matches = db_param_names & glossario_param_names
    
    # Encontrar matches fuzzy (normalized)
    fuzzy_matches = set()
    for norm_db in db_normalized.keys():
        if norm_db in glossario_normalized:
            fuzzy_matches.add(db_normalized[norm_db])
    
    # Parâmetros faltantes (no glossário mas não no banco)
    missing_in_db = glossario_param_names - db_param_names
    
    # Parâmetros extras (no banco mas não no glossário)
    extra_in_db = db_param_names - glossario_param_names
    
    # Filtrar falsos positivos nos extras (podem ser matches fuzzy)
    true_extras = set()
    for extra in extra_in_db:
        norm_extra = normalize_parameter_name(extra)
        if norm_extra not in glossario_normalized:
            true_extras.add(extra)
    
    # Resultados
    total_glossario = len(glossario_param_names)
    total_db = len(db_param_names)
    coverage = (len(exact_matches) + len(fuzzy_matches)) / total_glossario * 100 if total_glossario > 0 else 0
    
    print(f"   📊 Glossário esperado: {total_glossario} parâmetros")
    print(f"   📊 Banco de dados: {total_db} parâmetros")
    print(f"   ✅ Matches exatos: {len(exact_matches)}")
    print(f"   🔄 Matches fuzzy: {len(fuzzy_matches)}")
    print(f"   ❌ Faltantes no banco: {len(missing_in_db)}")
    print(f"   ⚠️  Extras no banco: {len(true_extras)}")
    print(f"   📈 Cobertura: {coverage:.1f}%")
    
    return {
        'model_code': model_code,
        'total_expected': total_glossario,
        'total_extracted': total_db,
        'exact_matches': len(exact_matches),
        'fuzzy_matches': len(fuzzy_matches),
        'coverage_percent': round(coverage, 2),
        'missing_in_db': list(missing_in_db)[:20],  # Primeiros 20
        'extra_in_db': list(true_extras)[:20],  # Primeiros 20
        'missing_count': len(missing_in_db),
        'extra_count': len(true_extras)
    }


def main():
    """Executa validação completa."""
    
    print("="*80)
    print("🔬 VALIDAÇÃO CRÍTICA: Extração vs Glossário")
    print("="*80)
    
    # 1. Buscar parâmetros do banco
    db_params_by_model = get_database_parameters()
    
    # 2. Comparar cada modelo
    results = []
    
    for model_code, db_params in db_params_by_model.items():
        # Identificar aba do glossário correspondente
        sheet_name = None
        for key, value in MODEL_TO_SHEET.items():
            if key in model_code:
                sheet_name = value
                break
        
        if not sheet_name:
            print(f"\n⚠️  Modelo {model_code} não tem mapeamento no glossário!")
            continue
        
        # Extrair parâmetros do glossário
        glossario_params = extract_glossario_parameters(sheet_name)
        
        if not glossario_params:
            print(f"   ⚠️  Nenhum parâmetro encontrado no glossário para {model_code}")
            continue
        
        # Comparar
        comparison = compare_model_parameters(model_code, db_params, glossario_params)
        results.append(comparison)
    
    # 3. Gerar relatório final
    print("\n" + "="*80)
    print("📊 RELATÓRIO FINAL DE VALIDAÇÃO")
    print("="*80)
    
    total_coverage = sum(r['coverage_percent'] for r in results) / len(results) if results else 0
    total_missing = sum(r['missing_count'] for r in results)
    total_extra = sum(r['extra_count'] for r in results)
    
    print(f"\n📈 Cobertura média: {total_coverage:.1f}%")
    print(f"❌ Total de parâmetros faltantes: {total_missing}")
    print(f"⚠️  Total de parâmetros extras: {total_extra}")
    
    # Identificar modelos com problemas críticos
    critical_models = [r for r in results if r['coverage_percent'] < 80]
    if critical_models:
        print(f"\n🚨 MODELOS CRÍTICOS (cobertura < 80%):")
        for model in critical_models:
            print(f"   • {model['model_code']}: {model['coverage_percent']:.1f}%")
    
    # Salvar resultados
    output_data = {
        'summary': {
            'average_coverage': round(total_coverage, 2),
            'total_missing': total_missing,
            'total_extra': total_extra,
            'models_analyzed': len(results),
            'critical_models': len(critical_models)
        },
        'details': results
    }
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Relatório salvo em: {OUTPUT_PATH}")
    
    # Decisão final
    if total_coverage >= 90:
        print("\n✅ VALIDAÇÃO APROVADA: Cobertura excelente!")
    elif total_coverage >= 75:
        print("\n⚠️  VALIDAÇÃO COM RESSALVAS: Cobertura aceitável, mas precisa melhorias")
    else:
        print("\n🚨 VALIDAÇÃO REPROVADA: Cobertura insuficiente! AÇÃO URGENTE NECESSÁRIA!")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Validação CRÍTICA: Comparar parâmetros do Glossário vs Banco de Dados

Objetivo:
- Verificar se TODOS os parâmetros obrigatórios do glossário foram extraídos
- Identificar parâmetros no banco que NÃO estão no glossário (possíveis ruídos)
- Mapear gaps/problemas na extração por modelo
"""

import json
import psycopg2
from pathlib import Path
from collections import defaultdict
import pandas as pd
from typing import Dict, List, Set

# Configurações
BASE_DIR = Path(__file__).resolve().parent.parent
GLOSSARIO_PATH = BASE_DIR / "inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx"
OUTPUT_DIR = BASE_DIR / "outputs/logs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

# Mapeamento de nomes de abas para chaves de modelo no banco
MODEL_MAPPING = {
    'MICON P122_52 e P122_204': ['MiCOM P122', 'P122'],
    'MICON P122_205': ['MiCOM P122_205', 'P122_205'],
    'MICON P220': ['MiCOM P220', 'P220'],
    'MICON P922': ['MiCOM P922', 'P922', 'P922S'],
    'SEPAM S40': ['SEPAM S40', 'SEPAM 40'],
    'MICON P241': ['MiCOM P241', 'P241'],
    'MICON P143': ['MiCOM P143', 'P143']
}


def print_header(title: str):
    """Imprime cabeçalho formatado."""
    print("\n" + "=" * 80)
    print(f"🔬 {title}")
    print("=" * 80 + "\n")


def load_glossario_parameters() -> Dict[str, List[Dict]]:
    """
    Carrega TODOS os parâmetros do glossário por modelo.
    
    Returns:
        Dict com chave = nome_modelo, valor = lista de parâmetros esperados
    """
    print("📖 Carregando parâmetros do glossário...")
    
    glossario_params = {}
    
    try:
        excel_file = pd.ExcelFile(GLOSSARIO_PATH)
        
        for sheet_name in excel_file.sheet_names:
            print(f"   📄 Processando aba: {sheet_name}")
            
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
            
            params = []
            current_section = None
            current_subsection = None
            
            for idx, row in df.iterrows():
                # Converter row para lista, removendo NaN
                row_values = [str(v) if pd.notna(v) else '' for v in row]
                row_text = ' '.join(row_values).strip()
                
                # Detectar seções (CONFIGURATION, PROTECTION, etc)
                if row_text and not any(c in row_text for c in [':', '=']):
                    if row_text.isupper() or 'PARAMETERS' in row_text.upper():
                        current_section = row_text
                        continue
                
                # Detectar subseções ([50N/51N], etc)
                if '[' in row_text and ']' in row_text:
                    current_subsection = row_text
                    continue
                
                # Extrair parâmetros (linhas com : ou =)
                for val in row_values:
                    if ':' in val or '=' in val:
                        # Limpar e extrair nome do parâmetro
                        param_parts = val.split(':') if ':' in val else val.split('=')
                        if len(param_parts) >= 2:
                            param_name = param_parts[0].strip()
                            param_value = param_parts[1].strip() if len(param_parts) > 1 else ''
                            
                            # Ignorar headers e fabricante
                            if param_name and not param_name.startswith('Fabricante'):
                                params.append({
                                    'name': param_name,
                                    'example_value': param_value,
                                    'section': current_section,
                                    'subsection': current_subsection
                                })
            
            glossario_params[sheet_name] = params
            print(f"      ✅ {len(params)} parâmetros encontrados")
    
    except Exception as e:
        print(f"   ❌ Erro ao ler glossário: {e}")
        return {}
    
    print(f"\n   ✅ Total: {sum(len(p) for p in glossario_params.values())} parâmetros em {len(glossario_params)} abas")
    return glossario_params


def get_database_parameters() -> Dict[str, List[Dict]]:
    """
    Busca TODOS os parâmetros extraídos e salvos no banco de dados.
    
    Returns:
        Dict com chave = "Fabricante - Modelo", valor = lista de parâmetros
    """
    print("\n🗄️  Carregando parâmetros do banco de dados...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                f.nome_completo,
                rm.model_name,
                rs.parameter_name,
                rs.parameter_code,
                rs.set_value_text,
                rs.unit_of_measure,
                rs.category,
                re.equipment_tag,
                COUNT(*) OVER (PARTITION BY rm.model_name) as total_params
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
        model_counts = {}
        
        for row in rows:
            manufacturer, model_name, param_name, param_code, value, unit, category, equipment_tag, total = row
            
            model_key = f"{manufacturer} - {model_name}"
            
            params_by_model[model_key].append({
                'parameter_name': param_name,
                'parameter_code': param_code,
                'value': value,
                'unit': unit,
                'category': category,
                'equipment': equipment_tag
            })
            
            model_counts[model_key] = total
        
        cursor.close()
        conn.close()
        
        print(f"   ✅ {len(params_by_model)} modelos encontrados no banco")
        for model, count in model_counts.items():
            print(f"      • {model}: {count} parâmetros")
        
        return dict(params_by_model)
    
    except Exception as e:
        print(f"   ❌ Erro ao conectar ao banco: {e}")
        return {}


def normalize_param_name(name: str) -> str:
    """Normaliza nome de parâmetro para comparação."""
    # Remove espaços extras, pontuação, converte para minúsculas
    normalized = name.lower().strip()
    normalized = normalized.replace('_', ' ').replace('-', ' ').replace(':', '').replace('=', '')
    normalized = ' '.join(normalized.split())  # Remove espaços múltiplos
    return normalized


def find_model_match(glossario_sheet: str, db_model_key: str) -> bool:
    """Verifica se um modelo do banco corresponde a uma aba do glossário."""
    if glossario_sheet in MODEL_MAPPING:
        model_variants = MODEL_MAPPING[glossario_sheet]
        return any(variant in db_model_key for variant in model_variants)
    return False


def compare_parameters(glossario_params: Dict[str, List[Dict]], 
                       db_params: Dict[str, List[Dict]]) -> Dict:
    """
    Compara parâmetros do glossário vs banco de dados.
    
    Returns:
        Dict com estatísticas de cobertura, gaps e extras
    """
    print_header("COMPARAÇÃO: Glossário vs Banco de Dados")
    
    results = {
        'total_glossario': sum(len(p) for p in glossario_params.values()),
        'total_database': sum(len(p) for p in db_params.values()),
        'models': {}
    }
    
    # Para cada aba do glossário
    for sheet_name, expected_params in glossario_params.items():
        print(f"\n📋 Analisando: {sheet_name}")
        print(f"   Parâmetros esperados (glossário): {len(expected_params)}")
        
        # Encontrar modelo correspondente no banco
        matching_db_models = [
            (model_key, params) 
            for model_key, params in db_params.items() 
            if find_model_match(sheet_name, model_key)
        ]
        
        if not matching_db_models:
            print(f"   ⚠️  NENHUM modelo correspondente encontrado no banco!")
            results['models'][sheet_name] = {
                'status': 'NOT_FOUND',
                'expected': len(expected_params),
                'found': 0,
                'coverage': 0.0
            }
            continue
        
        # Normalizar parâmetros do glossário
        expected_normalized = {
            normalize_param_name(p['name']): p 
            for p in expected_params
        }
        
        # Agregar todos os parâmetros dos modelos correspondentes
        all_db_params = []
        for model_key, params in matching_db_models:
            all_db_params.extend(params)
            print(f"   🔗 Modelo no banco: {model_key} ({len(params)} parâmetros)")
        
        # Normalizar parâmetros do banco
        found_normalized = {
            normalize_param_name(p['parameter_name']): p 
            for p in all_db_params
        }
        
        # Calcular gaps
        missing_params = set(expected_normalized.keys()) - set(found_normalized.keys())
        extra_params = set(found_normalized.keys()) - set(expected_normalized.keys())
        matched_params = set(expected_normalized.keys()) & set(found_normalized.keys())
        
        coverage = (len(matched_params) / len(expected_normalized) * 100) if expected_normalized else 0
        
        print(f"\n   📊 ESTATÍSTICAS:")
        print(f"      ✅ Encontrados: {len(matched_params)} ({coverage:.1f}%)")
        print(f"      ❌ Faltando: {len(missing_params)}")
        print(f"      ➕ Extras (não no glossário): {len(extra_params)}")
        
        if missing_params:
            print(f"\n   ⚠️  PARÂMETROS FALTANDO (primeiros 10):")
            for i, param in enumerate(list(missing_params)[:10], 1):
                original = expected_normalized[param]
                print(f"      {i}. {original['name']} (Seção: {original.get('section', 'N/A')})")
        
        if extra_params and len(extra_params) <= 20:
            print(f"\n   ➕ PARÂMETROS EXTRAS (não esperados):")
            for i, param in enumerate(list(extra_params)[:10], 1):
                original = found_normalized[param]
                print(f"      {i}. {original['parameter_name']}")
        
        results['models'][sheet_name] = {
            'status': 'FOUND',
            'expected': len(expected_normalized),
            'found': len(matched_params),
            'missing': len(missing_params),
            'extra': len(extra_params),
            'coverage': coverage,
            'missing_list': list(missing_params),
            'extra_list': list(extra_params)
        }
    
    return results


def generate_report(results: Dict):
    """Gera relatório JSON com resultados da validação."""
    output_file = OUTPUT_DIR / "validation_glossario_vs_db.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Relatório salvo em: {output_file}")
    
    # Resumo final
    print_header("RESUMO FINAL")
    print(f"📊 Total de parâmetros no glossário: {results['total_glossario']}")
    print(f"📊 Total de parâmetros no banco: {results['total_database']}")
    print(f"\n📋 Por modelo:")
    
    for model, stats in results['models'].items():
        if stats['status'] == 'FOUND':
            status_icon = "✅" if stats['coverage'] >= 90 else "⚠️" if stats['coverage'] >= 70 else "❌"
            print(f"   {status_icon} {model}: {stats['coverage']:.1f}% cobertura ({stats['found']}/{stats['expected']})")
        else:
            print(f"   ❌ {model}: NÃO ENCONTRADO no banco")


def main():
    print_header("VALIDAÇÃO CRÍTICA: Glossário vs Banco de Dados")
    
    # 1. Carregar glossário
    glossario_params = load_glossario_parameters()
    
    if not glossario_params:
        print("❌ Falha ao carregar glossário. Abortando.")
        return
    
    # 2. Carregar banco
    db_params = get_database_parameters()
    
    if not db_params:
        print("❌ Falha ao carregar dados do banco. Abortando.")
        return
    
    # 3. Comparar
    results = compare_parameters(glossario_params, db_params)
    
    # 4. Gerar relatório
    generate_report(results)


if __name__ == "__main__":
    main()

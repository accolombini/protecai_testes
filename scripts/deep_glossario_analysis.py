#!/usr/bin/env python3
"""
Análise PROFUNDA do Glossário - Extração de TODAS as regras e observações
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# Configurações
GLOSSARIO_PATH = Path("inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx")
OUTPUT_PATH = Path("outputs/logs/glossario_deep_analysis.json")

def extract_parameter_structure(df, sheet_name):
    """
    Extrai estrutura de parâmetros: Categoria → Parâmetro → Exemplo
    """
    parameters = []
    current_category = None
    current_subcategory = None
    
    for idx, row in df.iterrows():
        row_str = ' '.join([str(x) for x in row.values if pd.notna(x)])
        
        # Detectar categorias (em maiúsculas, sem ":")
        if any(cat in row_str.upper() for cat in ['PARAMETERS', 'CONFIGURATION', 'PROTECTION', 'DISPLAY']):
            words = row_str.split()
            for word in words:
                if word.isupper() and len(word) > 3:
                    current_category = word
                    current_subcategory = None
                    break
        
        # Detectar subcategorias (palavras seguidas por espaços)
        elif row_str and not any(char in row_str for char in [':', '=']):
            if len(row_str.split()) <= 3:
                current_subcategory = row_str.strip()
        
        # Detectar parâmetros (contém ":" ou "=")
        if ':' in row_str or '=' in row_str:
            # Separar nomenclatura e valor exemplo
            parts = row_str.replace('=', ':').split(':', 1)
            if len(parts) >= 2:
                param_name = parts[0].strip()
                example_value = parts[1].strip() if len(parts) > 1 else ''
                
                parameters.append({
                    'category': current_category,
                    'subcategory': current_subcategory,
                    'parameter': param_name,
                    'example': example_value,
                    'row_index': idx
                })
    
    return parameters

def find_observations_and_notes(df, sheet_name):
    """
    Procura observações, notas e instruções especiais
    """
    observations = []
    keywords = ['obs', 'observ', 'nota', 'note', 'atenção', 'atencion', 
                'importante', 'important', 'mesmo', 'mesma', 'similar',
                'ver', 'see', 'consultar', 'conforme', 'relé de', 'rele de']
    
    for idx, row in df.iterrows():
        for col_idx, cell in enumerate(row):
            if pd.notna(cell):
                cell_lower = str(cell).lower()
                
                # Verificar se contém palavras-chave
                if any(kw in cell_lower for kw in keywords):
                    observations.append({
                        'sheet': sheet_name,
                        'row': idx,
                        'column': col_idx,
                        'content': str(cell).strip(),
                        'context': 'observation'
                    })
    
    return observations

def extract_header_info(df, sheet_name):
    """
    Extrai informações do cabeçalho (fabricante, modelo, tipo)
    """
    header_info = {
        'sheet': sheet_name,
        'manufacturer': None,
        'model': None,
        'type': None,
        'special_notes': []
    }
    
    # Analisar primeiras 5 linhas
    for idx in range(min(5, len(df))):
        row_str = ' '.join([str(x) for x in df.iloc[idx].values if pd.notna(x)])
        
        if 'Fabricante:' in row_str or 'fabricante:' in row_str.lower():
            # Extrair fabricante e modelo
            parts = row_str.split('-')
            if len(parts) >= 2:
                manufacturer = parts[0].split(':')[-1].strip()
                model = parts[1].strip()
                header_info['manufacturer'] = manufacturer
                header_info['model'] = model
        
        # Identificar tipo de relé
        if 'Relé de' in row_str or 'relé de' in row_str.lower():
            tipo = row_str.split('(')[-1].split(')')[0] if '(' in row_str else ''
            header_info['type'] = tipo
        
        # Capturar notas especiais
        if any(word in row_str.lower() for word in ['mesmos', 'similar', 'conforme', 'ver']):
            header_info['special_notes'].append(row_str.strip())
    
    return header_info

def main():
    print("="*80)
    print("🔬 ANÁLISE PROFUNDA DO GLOSSÁRIO - EXTRAÇÃO COMPLETA")
    print("="*80)
    print()
    
    if not GLOSSARIO_PATH.exists():
        print(f"❌ Arquivo não encontrado: {GLOSSARIO_PATH}")
        return
    
    # Ler todas as abas
    excel_file = pd.ExcelFile(GLOSSARIO_PATH)
    sheet_names = excel_file.sheet_names
    
    print(f"📊 Total de abas: {len(sheet_names)}")
    print(f"📄 Abas: {', '.join(sheet_names)}")
    print()
    
    results = {
        'metadata': {
            'file': str(GLOSSARIO_PATH),
            'analysis_date': datetime.now().isoformat(),
            'total_sheets': len(sheet_names)
        },
        'sheets': {}
    }
    
    for sheet_name in sheet_names:
        print(f"\n{'='*80}")
        print(f"📋 ANALISANDO: {sheet_name}")
        print('='*80)
        
        df = pd.read_excel(GLOSSARIO_PATH, sheet_name=sheet_name)
        
        # 1. Informações do cabeçalho
        header_info = extract_header_info(df, sheet_name)
        print(f"\n📌 FABRICANTE: {header_info['manufacturer']}")
        print(f"📌 MODELO: {header_info['model']}")
        print(f"📌 TIPO: {header_info['type']}")
        
        if header_info['special_notes']:
            print(f"\n⚠️  NOTAS ESPECIAIS:")
            for note in header_info['special_notes']:
                print(f"    • {note}")
        
        # 2. Estrutura de parâmetros
        parameters = extract_parameter_structure(df, sheet_name)
        print(f"\n✅ PARÂMETROS EXTRAÍDOS: {len(parameters)}")
        
        # Mostrar primeiros 5 parâmetros como exemplo
        if parameters:
            print(f"\n📝 EXEMPLOS DE PARÂMETROS:")
            for param in parameters[:5]:
                cat = param['category'] or 'N/A'
                subcat = param['subcategory'] or 'N/A'
                print(f"    [{cat}/{subcat}] {param['parameter']}: {param['example']}")
        
        # 3. Observações e instruções
        observations = find_observations_and_notes(df, sheet_name)
        print(f"\n📎 OBSERVAÇÕES ENCONTRADAS: {len(observations)}")
        
        if observations:
            print(f"\n💡 OBSERVAÇÕES:")
            for obs in observations[:10]:  # Mostrar primeiras 10
                print(f"    [Linha {obs['row']}] {obs['content']}")
        
        # Armazenar resultados
        results['sheets'][sheet_name] = {
            'header': header_info,
            'parameters': parameters,
            'observations': observations,
            'dimensions': {
                'rows': len(df),
                'columns': len(df.columns)
            }
        }
        
        print(f"\n{'='*80}")
    
    # Salvar resultados
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Análise profunda salva em: {OUTPUT_PATH}")
    
    # Resumo final
    print(f"\n{'='*80}")
    print("📊 RESUMO GERAL")
    print('='*80)
    
    total_params = sum(len(sheet['parameters']) for sheet in results['sheets'].values())
    total_obs = sum(len(sheet['observations']) for sheet in results['sheets'].values())
    
    print(f"📋 Total de abas analisadas: {len(results['sheets'])}")
    print(f"📝 Total de parâmetros extraídos: {total_params}")
    print(f"📎 Total de observações encontradas: {total_obs}")
    print()
    
    print("📌 MODELOS IDENTIFICADOS:")
    for sheet_name, data in results['sheets'].items():
        manufacturer = data['header']['manufacturer'] or 'N/A'
        model = data['header']['model'] or 'N/A'
        tipo = data['header']['type'] or 'N/A'
        params = len(data['parameters'])
        print(f"  • {manufacturer} - {model} ({tipo}): {params} parâmetros")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

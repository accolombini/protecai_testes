#!/usr/bin/env python3
"""
Análise de Padrões para Normalização/Atomização 3FN

Analisa um arquivo CSV bruto para identificar padrões que precisam ser atomizados:
- Campos multivalorados (ex: "LED 5 part 1")
- Valores com unidades grudadas (ex: "60Hz")
- Campos que precisam ser separados em Code|Description|Part|Value|Unit
"""

import pandas as pd
from pathlib import Path
import re
from collections import defaultdict

def analyze_csv_patterns(csv_path: Path):
    """Analisa padrões em um CSV bruto"""
    
    print("="*100)
    print(f"🔍 ANÁLISE DE PADRÕES PARA NORMALIZAÇÃO - {csv_path.name}")
    print("="*100)
    
    # Ler CSV
    df = pd.read_csv(csv_path)
    
    print(f"\n📊 ESTRUTURA ATUAL:")
    print(f"   Colunas: {list(df.columns)}")
    print(f"   Total de linhas: {len(df)}")
    print(f"   Parâmetros (excluindo Page/File): {len(df[~df['Code'].isin(['Page', 'File'])])}")
    
    # Analisar padrões
    patterns = {
        'multipart': [],        # LED 5 part 1, LED 6 part 2, etc.
        'value_with_unit': [],  # 60Hz, 200A, etc.
        'compound_desc': [],    # Descrições com múltiplas partes
        'boolean_values': [],   # Yes/No
        'empty_values': [],     # Campos sem valor
        'metadata': []          # Page, File
    }
    
    print(f"\n🔍 PADRÕES IDENTIFICADOS:")
    
    for idx, row in df.iterrows():
        code = str(row['Code'])
        desc = str(row['Description'])
        value = str(row['Value']) if pd.notna(row['Value']) else ''
        
        # Metadados (Page, File)
        if code in ['Page', 'File']:
            patterns['metadata'].append({
                'code': code,
                'desc': desc,
                'value': value
            })
            continue
        
        # Padrão: "LED X part Y"
        if 'part' in desc.lower():
            match = re.search(r'(.+?)\s+part\s+(\d+)', desc, re.IGNORECASE)
            if match:
                base_desc = match.group(1).strip()
                part_num = match.group(2)
                patterns['multipart'].append({
                    'code': code,
                    'base_desc': base_desc,
                    'part': part_num,
                    'value': value,
                    'full_desc': desc
                })
        
        # Padrão: Valor com unidade grudada (60Hz, 200A, etc.)
        if value:
            # Detectar número + unidade (sem espaço)
            unit_match = re.match(r'^(\d+\.?\d*)\s*([A-Za-z]+)$', value)
            if unit_match:
                numeric_value = unit_match.group(1)
                unit = unit_match.group(2)
                patterns['value_with_unit'].append({
                    'code': code,
                    'desc': desc,
                    'raw_value': value,
                    'numeric': numeric_value,
                    'unit': unit
                })
        
        # Valores booleanos
        if value.lower() in ['yes', 'no', 'true', 'false', 'enabled', 'disabled']:
            patterns['boolean_values'].append({
                'code': code,
                'desc': desc,
                'value': value
            })
        
        # Valores vazios
        if not value or value == 'nan':
            patterns['empty_values'].append({
                'code': code,
                'desc': desc
            })
        
        # Descrições compostas (com vírgula, dois pontos, etc.)
        if any(sep in desc for sep in [',', ':', '/']):
            patterns['compound_desc'].append({
                'code': code,
                'desc': desc,
                'value': value
            })
    
    # Relatório
    print(f"\n📋 1. CAMPOS MULTIVALORADOS (part 1, part 2, etc.):")
    print(f"   Total: {len(patterns['multipart'])}")
    if patterns['multipart']:
        # Agrupar por base_desc
        grouped = defaultdict(list)
        for item in patterns['multipart']:
            grouped[item['base_desc']].append(item)
        
        for base_desc, items in sorted(grouped.items()):
            print(f"\n   📦 {base_desc}:")
            for item in sorted(items, key=lambda x: int(x['part'])):
                print(f"      Code {item['code']} (part {item['part']}): value='{item['value']}'")
            
            print(f"\n      💡 ATOMIZAÇÃO SUGERIDA:")
            print(f"         Criar 1 linha por LED com colunas:")
            print(f"         - led_base: '{base_desc}'")
            print(f"         - led_number: {base_desc.split()[-1] if base_desc.split() else 'N/A'}")
            for item in sorted(items, key=lambda x: int(x['part'])):
                print(f"         - part_{item['part']}_code: {item['code']}")
                print(f"         - part_{item['part']}_value: {item['value']}")
    
    print(f"\n📋 2. VALORES COM UNIDADE GRUDADA:")
    print(f"   Total: {len(patterns['value_with_unit'])}")
    for item in patterns['value_with_unit'][:10]:  # Primeiros 10
        print(f"   • Code {item['code']}: '{item['raw_value']}' → valor={item['numeric']}, unidade={item['unit']}")
        print(f"      💡 ATOMIZAR: Value='{item['numeric']}', Unit='{item['unit']}'")
    
    print(f"\n📋 3. VALORES BOOLEANOS:")
    print(f"   Total: {len(patterns['boolean_values'])}")
    for item in patterns['boolean_values'][:10]:
        print(f"   • Code {item['code']}: {item['desc']} = {item['value']}")
        print(f"      💡 MANTER: tipo boolean (converter Yes/No → True/False)")
    
    print(f"\n📋 4. VALORES VAZIOS:")
    print(f"   Total: {len(patterns['empty_values'])}")
    print(f"   💡 MANTER: mas marcar como NULL/None no banco")
    
    print(f"\n📋 5. METADADOS (Page, File):")
    print(f"   Total: {len(patterns['metadata'])}")
    for item in patterns['metadata'][:5]:
        print(f"   • {item['code']}: {item['desc']} = {item['value']}")
    print(f"   💡 DECISÃO: Manter como metadados separados ou remover?")
    
    print(f"\n📋 6. DESCRIÇÕES COMPOSTAS:")
    print(f"   Total: {len(patterns['compound_desc'])}")
    for item in patterns['compound_desc'][:10]:
        print(f"   • Code {item['code']}: '{item['desc']}'")
    
    # Propor estrutura 3FN
    print(f"\n{'='*100}")
    print(f"💡 PROPOSTA DE ESTRUTURA 3FN (ATOMIZADA)")
    print(f"{'='*100}")
    
    print(f"""
📊 TABELA 1: relay_parameters (parâmetros simples)
   Colunas:
   - id (PK)
   - relay_file (FK)
   - page_number
   - parameter_code
   - parameter_description
   - parameter_value
   - value_unit
   - value_type (text/numeric/boolean/null)
   - is_active (boolean - vem do checkbox detection)
   
📊 TABELA 2: relay_multipart_parameters (LEDs e campos compostos)
   Colunas:
   - id (PK)
   - relay_file (FK)
   - base_name (ex: "LED 5")
   - part_1_code
   - part_1_value
   - part_2_code
   - part_2_value
   - part_3_code
   - part_3_value
   - part_4_code
   - part_4_value
   - is_active (boolean)

📊 TABELA 3: relay_metadata
   Colunas:
   - id (PK)
   - file_name
   - relay_model
   - extraction_date
   - total_pages
   - total_parameters
""")
    
    # Estatísticas finais
    print(f"\n{'='*100}")
    print(f"📊 RESUMO ESTATÍSTICO")
    print(f"{'='*100}")
    total = len(df)
    print(f"   Total de linhas: {total}")
    print(f"   Metadados (Page/File): {len(patterns['metadata'])} ({len(patterns['metadata'])/total*100:.1f}%)")
    print(f"   Campos multipart: {len(patterns['multipart'])} ({len(patterns['multipart'])/total*100:.1f}%)")
    print(f"   Valores com unidade: {len(patterns['value_with_unit'])} ({len(patterns['value_with_unit'])/total*100:.1f}%)")
    print(f"   Valores booleanos: {len(patterns['boolean_values'])} ({len(patterns['boolean_values'])/total*100:.1f}%)")
    print(f"   Valores vazios: {len(patterns['empty_values'])} ({len(patterns['empty_values'])/total*100:.1f}%)")
    print(f"   Descrições compostas: {len(patterns['compound_desc'])} ({len(patterns['compound_desc'])/total*100:.1f}%)")
    
    return patterns


def main():
    """Execução principal"""
    # Analisar P122
    csv_path = Path("outputs/csv/P122 52-MF-02A_2021-03-08_params.csv")
    
    if not csv_path.exists():
        print(f"❌ Arquivo não encontrado: {csv_path}")
        return
    
    patterns = analyze_csv_patterns(csv_path)
    
    print(f"\n{'='*100}")
    print(f"✅ ANÁLISE CONCLUÍDA")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    main()

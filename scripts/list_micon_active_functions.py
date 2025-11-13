#!/usr/bin/env python3
"""
Lista as funções de proteção ATIVAS nos arquivos MICON/EASERGY

Analisa os arquivos _active_setup.csv e usa o mapeamento do glossário
para identificar quais funções ANSI estão configuradas
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict
import sys
sys.path.append('scripts')
from map_parameters_to_functions import get_function_code_and_category, MICON_CODE_RANGES

def analyze_micon_active_setup(csv_path: Path) -> dict:
    """
    Analisa arquivo _active_setup.csv de relé MICON/EASERGY
    
    Returns:
        dict: {
            'active_functions': {function_code: count},
            'total_params': int,
            'active_params': int
        }
    """
    df = pd.read_csv(csv_path)
    
    # Detectar tipo de relé pelo nome do arquivo
    filename = csv_path.stem.upper()
    if 'P122' in filename or 'P_122' in filename:
        model_type = 'MICON_P122'
    elif 'P220' in filename:
        model_type = 'MICON_P220'
    elif 'P922' in filename:
        model_type = 'MICON_P922'
    elif 'P241' in filename or 'P143' in filename:
        model_type = 'MICOM'
    else:
        model_type = 'MICON'
    
    # Contar funções ativas
    function_counts = defaultdict(int)
    total_params = len(df)
    active_params = 0
    
    for idx, row in df.iterrows():
        code = str(row.get('Code', ''))
        is_active = row.get('is_active', False)
        
        if is_active:
            active_params += 1
            # Mapear código para função ANSI
            function_code, category = get_function_code_and_category(code, model_type)
            if function_code and category == 'protection':
                function_counts[function_code] += 1
    
    return {
        'active_functions': dict(function_counts),
        'total_params': total_params,
        'active_params': active_params,
        'model_type': model_type
    }

def main():
    # Localizar arquivos _active_setup.csv (excluindo SEPAM)
    csv_dir = Path('outputs/csv')
    active_setup_files = sorted([
        f for f in csv_dir.glob('*_active_setup.csv')
        if not f.name.startswith('00-MF-')  # Excluir SEPAM
    ])
    
    if not active_setup_files:
        print("❌ Nenhum arquivo _active_setup.csv encontrado")
        return
    
    print("=" * 80)
    print("🔍 FUNÇÕES DE PROTEÇÃO ATIVAS - MICON/EASERGY")
    print("=" * 80)
    
    all_functions = defaultdict(int)
    total_files = 0
    total_with_functions = 0
    
    # Agrupar por modelo
    by_model = defaultdict(list)
    
    for csv_path in active_setup_files:
        result = analyze_micon_active_setup(csv_path)
        model = result['model_type']
        by_model[model].append((csv_path.stem.replace('_active_setup', ''), result))
        total_files += 1
        if result['active_functions']:
            total_with_functions += 1
    
    # Mostrar por modelo
    for model in sorted(by_model.keys()):
        files = by_model[model]
        print(f"\n{'='*80}")
        print(f"📘 MODELO: {model}")
        print(f"{'='*80}")
        print(f"Total de arquivos: {len(files)}\n")
        
        for filename, result in files[:5]:  # Mostrar apenas 5 primeiros
            print(f"📄 {filename}")
            print(f"   Parâmetros: {result['active_params']}/{result['total_params']} ativos " +
                  f"({result['active_params']/result['total_params']*100:.1f}%)")
            
            if result['active_functions']:
                print(f"   ✅ Funções detectadas:")
                for func, count in sorted(result['active_functions'].items()):
                    print(f"      • {func}: {count} parâmetros")
                    all_functions[func] += count
            else:
                print(f"   ⚠️  Nenhuma função de proteção detectada")
            print()
        
        if len(files) > 5:
            print(f"   ... e mais {len(files)-5} arquivos\n")
    
    print("=" * 80)
    print(f"📋 RESUMO GERAL")
    print("=" * 80)
    print(f"Total de arquivos MICON/EASERGY: {total_files}")
    print(f"Arquivos com funções detectadas: {total_with_functions}")
    print(f"Funções únicas encontradas: {len(all_functions)}")
    
    if all_functions:
        print(f"\n🎯 Funções ANSI encontradas (total de parâmetros):")
        for func in sorted(all_functions.keys()):
            print(f"  • {func}: {all_functions[func]} parâmetros")
    else:
        print("\n⚠️  ATENÇÃO: Nenhuma função de proteção foi detectada!")
        print("   Possíveis causas:")
        print("   1. Mapeamento em map_parameters_to_functions.py incompleto")
        print("   2. Checkboxes não detectados corretamente")
        print("   3. Códigos hex no CSV não correspondem aos ranges esperados")

if __name__ == '__main__':
    main()

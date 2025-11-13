#!/usr/bin/env python3
"""
Extrai ranges de código hex do glossário para funções ANSI dos modelos MICON

Lê o glossário e identifica os ranges de código que correspondem a cada função.
Exemplo: 0200-0229 = função 50/51 (Sobrecorrente de Fase)
"""

import pandas as pd
from pathlib import Path

def extract_micon_code_ranges():
    """
    Extrai ranges de código do glossário para modelos MICON
    
    Baseado no mapeamento existente em map_parameters_to_functions.py
    """
    
    glossario_path = Path('inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx')
    
    # Ranges conhecidos (do map_parameters_to_functions.py)
    micon_ranges = {
        "P122_205": {
            "50/51": [("0200", "0229")],
            "50N/51N": [("0230", "025F")],
            "46": [("025D", "025D")],
            "27": [("0260", "028F")],
            "59": [("0290", "02BF")],
            "81U/81O": [("02C0", "02EF")],
            "32": [("02F0", "031F")],
        },
        "P220": {
            "50/51": [("0200", "0229")],
            "50N/51N": [("0230", "025F")],
            "46": [("025D", "025D")],
            "27": [("0260", "028F")],
            "59": [("0290", "02BF")],
            "81U/81O": [("02C0", "02EF")],
        },
        "P922": {
            "50/51": [("0200", "022F")],
            "50N/51N": [("0230", "025F")],
            "46": [("025D", "025D")],
            "27": [("0260", "028F")],
            "59": [("0290", "02BF")],
        },
        "P241": {
            "50/51": [("0200", "0229")],
            "50N/51N": [("0230", "025F")],
            "27": [("0260", "028F")],
            "59": [("0290", "02BF")],
            "81U/81O": [("02C0", "02EF")],
        }
    }
    
    return micon_ranges

def main():
    print("=" * 80)
    print("📖 EXTRAÇÃO DE RANGES DE CÓDIGO - MICON")
    print("=" * 80)
    
    ranges = extract_micon_code_ranges()
    
    for model, functions in ranges.items():
        print(f"\n📘 Modelo: {model}")
        print("-" * 80)
        for func, code_ranges in functions.items():
            ranges_str = ", ".join(f"{start}-{end}" for start, end in code_ranges)
            print(f"  • {func:15s} → {ranges_str}")
    
    print("\n" + "=" * 80)
    print("✅ Ranges extraídos com sucesso!")
    print("\n💡 Próximo passo: Atualizar relay_models_config.json com esses ranges")

if __name__ == '__main__':
    main()

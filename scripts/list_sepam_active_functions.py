#!/usr/bin/env python3
"""
Lista as funções de proteção ATIVAS nos arquivos SEPAM S40

Lê os arquivos .S40 e identifica quais funções de proteção (seções [ProtectionXXX])
têm pelo menos um grupo ativo (activite_X=1)
"""

import configparser
from pathlib import Path
from collections import defaultdict

# Mapeamento de seções para códigos ANSI
SECTION_TO_ANSI = {
    'Protection27': '27',        # Subvoltagem
    'Protection59': '59',        # Sobrevoltagem
    'Protection59N': '59N',      # Sobrevoltagem de neutro
    'Protection67N': '67N',      # Direcional de terra
    'Protection50': '50',        # Sobrecorrente instantânea
    'Protection51': '51',        # Sobrecorrente temporizada
    'Protection50N': '50N',      # Sobrecorrente de terra instantânea
    'Protection51N': '51N',      # Sobrecorrente de terra temporizada
    'Protection46': '46',        # Sequência negativa
    'Protection37': '37',        # Subcorrente
    'Protection81O': '81O',      # Sobrefrequência
    'Protection81U': '81U',      # Subfrequência
    'Protection87': '87',        # Diferencial
    'Protection49': '49',        # Térmica
    'Protection32': '32',        # Potência reversa
    'Protection40': '40',        # Perda de excitação
}

def analyze_s40_file(s40_path: Path) -> dict:
    """
    Analisa arquivo .S40 e retorna funções de proteção ativas
    
    Returns:
        dict: {
            'active_functions': [('27', 'Protection27', [0, 1])],  # (ansi_code, section, active_indices)
            'total_functions': 15,
            'active_count': 3
        }
    """
    config = configparser.ConfigParser()
    config.read(s40_path, encoding='latin-1')
    
    # Para cada seção Protection, verificar quais activite estão em 1
    active_functions = []
    
    for section in config.sections():
        if not section.startswith('Protection'):
            continue
        
        # Coletar todos os activite_X
        active_indices = []
        for key in config[section]:
            if key.startswith('activite_'):
                value = config[section][key]
                if value == '1':
                    # Extrair índice
                    parts = key.split('_')
                    if len(parts) >= 2 and parts[-1].isdigit():
                        index = int(parts[-1])
                        active_indices.append(index)
        
        # Se há pelo menos um grupo ativo, função está ativa
        if active_indices:
            ansi_code = SECTION_TO_ANSI.get(section, section.replace('Protection', 'ANSI-'))
            active_functions.append((ansi_code, section, sorted(active_indices)))
    
    return {
        'active_functions': active_functions,
        'total_sections': len([s for s in config.sections() if s.startswith('Protection')]),
        'active_count': len(active_functions)
    }

def main():
    # Localizar arquivos SEPAM
    txt_dir = Path('inputs/txt')
    s40_files = sorted(txt_dir.glob('*.S40'))
    
    if not s40_files:
        print("❌ Nenhum arquivo .S40 encontrado em inputs/txt/")
        return
    
    print("=" * 80)
    print("🔍 FUNÇÕES DE PROTEÇÃO ATIVAS - SEPAM S40")
    print("=" * 80)
    
    all_functions = set()
    
    for s40_path in s40_files:
        print(f"\n📘 {s40_path.name}")
        print("-" * 80)
        
        result = analyze_s40_file(s40_path)
        
        print(f"📊 Seções Protection encontradas: {result['total_sections']}")
        print(f"✅ Funções ATIVAS: {result['active_count']}")
        
        if result['active_functions']:
            print(f"\n🎯 FUNÇÕES DE PROTEÇÃO CONFIGURADAS:")
            for ansi_code, section, indices in result['active_functions']:
                indices_str = ', '.join(str(i) for i in indices)
                print(f"  ✅ {ansi_code:6s} - {section:20s} (grupos ativos: {indices_str})")
                all_functions.add(ansi_code)
        else:
            print("  ⚠️  Nenhuma função de proteção ativa encontrada")
    
    print("\n" + "=" * 80)
    print(f"📋 RESUMO GERAL")
    print("=" * 80)
    print(f"Total de arquivos SEPAM: {len(s40_files)}")
    print(f"Funções únicas encontradas: {len(all_functions)}")
    print(f"\n🎯 Funções ANSI encontradas nos arquivos:")
    for func in sorted(all_functions):
        print(f"  • {func}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Valida todas as correções feitas na pipeline antes de re-processar

Verifica:
1. detect_active_setup_sepam() - lê activite corretamente?
2. normalize_to_3nf.py - filtra is_active==True?
3. import_normalized_data_to_db.py - mapeia function_id?
4. map_parameters_to_functions.py - tem mapeamentos completos?
"""

import sys
from pathlib import Path
import pandas as pd

print("=" * 80)
print("🔍 VALIDAÇÃO DA PIPELINE - DIAGNÓSTICO COMPLETO")
print("=" * 80)

issues = []

# ============================================================================
# 1. VALIDAR detect_active_setup_sepam()
# ============================================================================
print("\n📘 1. VALIDANDO detect_active_setup_sepam()")
print("-" * 80)

try:
    from src.universal_setup_detector import UniversalSetupDetector
    
    # Testar com arquivo SEPAM
    csv_path = Path('outputs/csv/00-MF-12_2016-03-31_params.csv')
    if csv_path.exists():
        detector = UniversalSetupDetector()
        params = detector.detect_active_setup_sepam(csv_path)
        
        active = sum(1 for p in params if p.is_active)
        inactive = sum(1 for p in params if not p.is_active)
        total = len(params)
        
        print(f"✅ Método funciona")
        print(f"   Total: {total} | Ativos: {active} ({active/total*100:.1f}%) | Inativos: {inactive} ({inactive/total*100:.1f}%)")
        
        # Verificar se há variação (não pode ser 100% ativo ou 100% inativo)
        if active == 0:
            issues.append("❌ SEPAM: 0% ativos - lógica pode estar invertida")
        elif inactive == 0:
            issues.append("❌ SEPAM: 0% inativos - não está filtrando activite=0")
        elif active > total * 0.9:
            issues.append("⚠️  SEPAM: >90% ativos - pode ter problema (esperado ~20-40%)")
        else:
            print(f"   ✅ Distribuição parece correta")
    else:
        issues.append("❌ Arquivo teste SEPAM não encontrado")
except Exception as e:
    issues.append(f"❌ Erro ao testar detect_active_setup_sepam: {e}")

# ============================================================================
# 2. VALIDAR map_parameters_to_functions.py
# ============================================================================
print("\n📘 2. VALIDANDO map_parameters_to_functions.py")
print("-" * 80)

try:
    sys.path.append('scripts')
    from map_parameters_to_functions import (
        get_function_code_and_category,
        MICON_CODE_RANGES,
        MICON_P220_RANGES,
        MICON_P922_RANGES,
        SEPAM_PARAM_PREFIXES
    )
    
    # Testar alguns códigos conhecidos
    test_cases = [
        ('0201', 'MICON', '50/51', 'protection'),
        ('0231', 'MICON', '50N/51N', 'protection'),
        ('025D', 'MICON', '46', 'protection'),
        ('0120', 'MICON', None, 'configuration'),
        ('courant_seuil_1', 'SEPAM', '50/51', 'protection'),
        ('frequence_seuil_1', 'SEPAM', '81O/81U', 'protection'),
    ]
    
    all_ok = True
    for code, model, expected_func, expected_cat in test_cases:
        func, cat = get_function_code_and_category(code, model)
        if func != expected_func or cat != expected_cat:
            issues.append(f"❌ Mapeamento incorreto: {code} ({model}) → esperado {expected_func}/{expected_cat}, obteve {func}/{cat}")
            all_ok = False
    
    if all_ok:
        print(f"✅ Todos os 6 casos de teste passaram")
        print(f"   MICON ranges: {len(MICON_CODE_RANGES)} funções")
        print(f"   P220 ranges: {len(MICON_P220_RANGES)} funções")
        print(f"   P922 ranges: {len(MICON_P922_RANGES)} funções")
        print(f"   SEPAM prefixes: {len(SEPAM_PARAM_PREFIXES)} padrões")
    
except Exception as e:
    issues.append(f"❌ Erro ao validar mapeamento: {e}")

# ============================================================================
# 3. VALIDAR normalize_to_3nf.py
# ============================================================================
print("\n📘 3. VALIDANDO normalize_to_3nf.py - linha 138")
print("-" * 80)

try:
    normalize_file = Path('scripts/normalize_to_3nf.py')
    if normalize_file.exists():
        content = normalize_file.read_text()
        
        # Verificar se tem o filtro correto
        if "df_active[df_active['is_active']==True]" in content or "df_active[df_active['is_active'] == True]" in content:
            print("✅ Filtro is_active==True encontrado")
        elif "df_active['is_active']==True" in content or "df_active['is_active'] == True" in content:
            print("✅ Filtro is_active==True encontrado (variante)")
        else:
            issues.append("❌ normalize_to_3nf.py: Filtro is_active==True NÃO encontrado na linha 138")
    else:
        issues.append("❌ Arquivo normalize_to_3nf.py não encontrado")
except Exception as e:
    issues.append(f"❌ Erro ao validar normalize_to_3nf.py: {e}")

# ============================================================================
# 4. VALIDAR import_normalized_data_to_db.py
# ============================================================================
print("\n📘 4. VALIDANDO import_normalized_data_to_db.py")
print("-" * 80)

try:
    import_file = Path('scripts/import_normalized_data_to_db.py')
    if import_file.exists():
        content = import_file.read_text()
        
        checks = [
            ("from map_parameters_to_functions import get_function_code_and_category", "Import do mapeamento"),
            ("self.function_map", "Dicionário function_map"),
            ("get_function_code_and_category(", "Chamada do mapeamento"),
            ("function_id = self.function_map.get(", "Uso do function_map"),
        ]
        
        all_ok = True
        for pattern, description in checks:
            if pattern in content:
                print(f"   ✅ {description}")
            else:
                issues.append(f"❌ import_normalized_data_to_db.py: {description} NÃO encontrado")
                all_ok = False
        
        if all_ok:
            print("✅ Todas as modificações estão presentes")
    else:
        issues.append("❌ Arquivo import_normalized_data_to_db.py não encontrado")
except Exception as e:
    issues.append(f"❌ Erro ao validar import_normalized_data_to_db.py: {e}")

# ============================================================================
# 5. VERIFICAR ARQUIVOS CSV EXISTENTES
# ============================================================================
print("\n📘 5. VERIFICANDO ESTRUTURA DOS CSVs")
print("-" * 80)

csv_dir = Path('outputs/csv')
params_files = list(csv_dir.glob('*_params.csv'))
active_files = list(csv_dir.glob('*_active_setup.csv'))

print(f"   Arquivos *_params.csv: {len(params_files)}")
print(f"   Arquivos *_active_setup.csv: {len(active_files)}")

if len(params_files) == 0:
    issues.append("❌ Nenhum arquivo *_params.csv encontrado - pipeline de extração pode ter falhado")

# Verificar um arquivo active_setup de exemplo
if active_files:
    sample = active_files[0]
    try:
        df = pd.read_csv(sample)
        cols = df.columns.tolist()
        print(f"   Colunas em {sample.name}: {cols}")
        
        if 'is_active' not in cols:
            issues.append(f"❌ Coluna 'is_active' ausente em {sample.name}")
        else:
            true_count = (df['is_active'] == True).sum()
            false_count = (df['is_active'] == False).sum()
            print(f"   Distribuição is_active: True={true_count}, False={false_count}")
    except Exception as e:
        issues.append(f"❌ Erro ao ler {sample.name}: {e}")

# ============================================================================
# RELATÓRIO FINAL
# ============================================================================
print("\n" + "=" * 80)
print("📊 RELATÓRIO FINAL")
print("=" * 80)

if issues:
    print(f"\n❌ {len(issues)} PROBLEMA(S) ENCONTRADO(S):\n")
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue}")
    print("\n⚠️  CORREÇÃO NECESSÁRIA ANTES DE RE-PROCESSAR!")
    sys.exit(1)
else:
    print("\n✅ TODAS AS VALIDAÇÕES PASSARAM!")
    print("\n🎯 PRONTO PARA RE-PROCESSAR A PIPELINE:")
    print("   1. batch_detect_active_setups.py (50 arquivos)")
    print("   2. normalize_to_3nf.py")
    print("   3. import_normalized_data_to_db.py")
    sys.exit(0)

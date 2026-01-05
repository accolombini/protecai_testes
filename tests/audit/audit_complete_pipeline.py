#!/usr/bin/env python3
"""
AUDITORIA COMPLETA DO PIPELINE DE DADOS
Objetivo: Mapear TODOS os arquivos e identificar o que está faltando/quebrado
"""

import os
import json
from pathlib import Path
from collections import defaultdict
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

def audit_inputs():
    """Audita arquivos de entrada."""
    print("=" * 80)
    print("📥 AUDITANDO INPUTS")
    print("=" * 80)
    
    input_dirs = {
        'pdf': BASE_DIR / 'inputs/pdf',
        'txt': BASE_DIR / 'inputs/txt',
        'csv': BASE_DIR / 'inputs/csv',
        'xlsx': BASE_DIR / 'inputs/xlsx',
        'glossario': BASE_DIR / 'inputs/glossario'
    }
    
    inputs = {}
    
    for name, path in input_dirs.items():
        if path.exists():
            files = list(path.glob('*'))
            files = [f for f in files if f.is_file()]
            inputs[name] = {
                'count': len(files),
                'files': [f.name for f in files]
            }
            print(f"\n📁 {name}: {len(files)} arquivos")
            if len(files) <= 10:
                for f in files:
                    print(f"   • {f.name}")
        else:
            inputs[name] = {'count': 0, 'files': []}
            print(f"\n⚠️  {name}: Diretório não existe!")
    
    return inputs


def audit_outputs_csv():
    """Audita CSVs extraídos."""
    print("\n" + "=" * 80)
    print("📤 AUDITANDO OUTPUTS/CSV (Dados Brutos Extraídos)")
    print("=" * 80)
    
    csv_dir = BASE_DIR / 'outputs/csv'
    
    if not csv_dir.exists():
        print("⚠️  Diretório não existe!")
        return {'count': 0, 'files': []}
    
    csv_files = list(csv_dir.glob('*.csv'))
    
    print(f"\n📊 Total de CSVs: {len(csv_files)}")
    
    # Agrupar por padrão de nome
    patterns = defaultdict(list)
    for f in csv_files:
        if 'P122' in f.name:
            patterns['P122'].append(f.name)
        elif 'P143' in f.name:
            patterns['P143'].append(f.name)
        elif 'P220' in f.name:
            patterns['P220'].append(f.name)
        elif 'P241' in f.name:
            patterns['P241'].append(f.name)
        elif 'P922' in f.name:
            patterns['P922'].append(f.name)
        elif 'SEPAM' in f.name or 'MF' in f.name:
            patterns['SEPAM'].append(f.name)
        else:
            patterns['OUTROS'].append(f.name)
    
    for pattern, files in patterns.items():
        print(f"\n   {pattern}: {len(files)} arquivos")
        if len(files) <= 5:
            for f in files:
                print(f"      • {f}")
    
    return {'count': len(csv_files), 'files': [f.name for f in csv_files]}


def audit_outputs_excel():
    """Audita Excels gerados."""
    print("\n" + "=" * 80)
    print("📊 AUDITANDO OUTPUTS/EXCEL (Planilhas Geradas)")
    print("=" * 80)
    
    excel_dir = BASE_DIR / 'outputs/excel'
    
    if not excel_dir.exists():
        print("⚠️  Diretório não existe!")
        return {'count': 0, 'files': []}
    
    excel_files = list(excel_dir.glob('*.xlsx'))
    
    print(f"\n📊 Total de Excels: {len(excel_files)}")
    for f in excel_files:
        print(f"   • {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    
    return {'count': len(excel_files), 'files': [f.name for f in excel_files]}


def audit_normalized_outputs():
    """Audita arquivos normalizados."""
    print("\n" + "=" * 80)
    print("✨ AUDITANDO OUTPUTS NORMALIZADOS")
    print("=" * 80)
    
    norm_csv_dir = BASE_DIR / 'outputs/norm_csv'
    norm_excel_dir = BASE_DIR / 'outputs/norm_excel'
    
    result = {}
    
    # CSV Normalizado
    if norm_csv_dir.exists():
        norm_csv = list(norm_csv_dir.glob('*.csv'))
        result['norm_csv'] = {
            'count': len(norm_csv),
            'files': [f.name for f in norm_csv]
        }
        print(f"\n📁 NORM_CSV: {len(norm_csv)} arquivos")
        
        # Amostra de 1 arquivo para ver estrutura
        if norm_csv:
            sample = norm_csv[0]
            print(f"\n   📄 Amostra: {sample.name}")
            try:
                df = pd.read_csv(sample, nrows=3)
                print(f"   Colunas: {', '.join(df.columns.tolist())}")
                print(f"   Linhas (amostra): {len(df)}")
            except Exception as e:
                print(f"   ⚠️  Erro ao ler: {e}")
    else:
        result['norm_csv'] = {'count': 0, 'files': []}
        print("\n⚠️  NORM_CSV: Diretório não existe!")
    
    # Excel Normalizado
    if norm_excel_dir.exists():
        norm_excel = list(norm_excel_dir.glob('*.xlsx'))
        result['norm_excel'] = {
            'count': len(norm_excel),
            'files': [f.name for f in norm_excel]
        }
        print(f"\n📁 NORM_EXCEL: {len(norm_excel)} arquivos")
    else:
        result['norm_excel'] = {'count': 0, 'files': []}
        print("\n⚠️  NORM_EXCEL: Diretório não existe!")
    
    return result


def compare_coverage():
    """Compara cobertura entre inputs e outputs."""
    print("\n" + "=" * 80)
    print("🔍 ANÁLISE DE COBERTURA")
    print("=" * 80)
    
    # Contar PDFs/S40
    pdf_dir = BASE_DIR / 'inputs/pdf'
    txt_dir = BASE_DIR / 'inputs/txt'
    
    total_inputs = 0
    if pdf_dir.exists():
        total_inputs += len(list(pdf_dir.glob('*.pdf')))
    if txt_dir.exists():
        total_inputs += len(list(txt_dir.glob('*.S40')))
    
    # Contar outputs
    csv_count = len(list((BASE_DIR / 'outputs/csv').glob('*.csv'))) if (BASE_DIR / 'outputs/csv').exists() else 0
    norm_csv_count = len(list((BASE_DIR / 'outputs/norm_csv').glob('*.csv'))) if (BASE_DIR / 'outputs/norm_csv').exists() else 0
    norm_excel_count = len(list((BASE_DIR / 'outputs/norm_excel').glob('*.xlsx'))) if (BASE_DIR / 'outputs/norm_excel').exists() else 0
    
    print(f"\n📊 TOTAIS:")
    print(f"   Arquivos de entrada (PDF/S40): {total_inputs}")
    print(f"   CSVs extraídos: {csv_count}")
    print(f"   CSVs normalizados: {norm_csv_count}")
    print(f"   Excels normalizados: {norm_excel_count}")
    
    print(f"\n🎯 COBERTURA:")
    print(f"   CSV extraído: {csv_count}/{total_inputs} ({csv_count/total_inputs*100:.1f}%)")
    print(f"   CSV normalizado: {norm_csv_count}/{total_inputs} ({norm_csv_count/total_inputs*100:.1f}%)")
    print(f"   Excel normalizado: {norm_excel_count}/{total_inputs} ({norm_excel_count/total_inputs*100:.1f}%)")
    
    if csv_count < total_inputs:
        print(f"\n   ❌ FALTAM {total_inputs - csv_count} CSVs extraídos!")
    
    if norm_csv_count < csv_count:
        print(f"   ❌ FALTAM {csv_count - norm_csv_count} CSVs normalizados!")
    
    if norm_excel_count < csv_count:
        print(f"   ❌ FALTAM {csv_count - norm_excel_count} Excels normalizados!")
    
    return {
        'total_inputs': total_inputs,
        'csv_extracted': csv_count,
        'csv_normalized': norm_csv_count,
        'excel_normalized': norm_excel_count
    }


def find_missing_files():
    """Identifica arquivos que foram extraídos mas não normalizados."""
    print("\n" + "=" * 80)
    print("🔎 IDENTIFICANDO ARQUIVOS FALTANTES")
    print("=" * 80)
    
    csv_dir = BASE_DIR / 'outputs/csv'
    norm_csv_dir = BASE_DIR / 'outputs/norm_csv'
    norm_excel_dir = BASE_DIR / 'outputs/norm_excel'
    
    if not csv_dir.exists():
        print("⚠️  outputs/csv não existe!")
        return
    
    csv_files = {f.stem for f in csv_dir.glob('*.csv')}
    norm_csv_files = {f.stem.replace('_params_normalized', '') for f in norm_csv_dir.glob('*.csv')} if norm_csv_dir.exists() else set()
    norm_excel_files = {f.stem.replace('_params_normalized', '') for f in norm_excel_dir.glob('*.xlsx')} if norm_excel_dir.exists() else set()
    
    missing_norm_csv = csv_files - norm_csv_files
    missing_norm_excel = csv_files - norm_excel_files
    
    if missing_norm_csv:
        print(f"\n❌ FALTAM {len(missing_norm_csv)} NORM_CSV:")
        for i, f in enumerate(list(missing_norm_csv)[:10], 1):
            print(f"   {i}. {f}")
        if len(missing_norm_csv) > 10:
            print(f"   ... e mais {len(missing_norm_csv) - 10}")
    
    if missing_norm_excel:
        print(f"\n❌ FALTAM {len(missing_norm_excel)} NORM_EXCEL:")
        for i, f in enumerate(list(missing_norm_excel)[:10], 1):
            print(f"   {i}. {f}")
        if len(missing_norm_excel) > 10:
            print(f"   ... e mais {len(missing_norm_excel) - 10}")
    
    return {
        'missing_norm_csv': list(missing_norm_csv),
        'missing_norm_excel': list(missing_norm_excel)
    }


def main():
    print("=" * 80)
    print("🔬 AUDITORIA COMPLETA DO PIPELINE DE DADOS - ProtecAI")
    print("=" * 80)
    
    results = {}
    
    # 1. Inputs
    results['inputs'] = audit_inputs()
    
    # 2. Outputs CSV
    results['outputs_csv'] = audit_outputs_csv()
    
    # 3. Outputs Excel
    results['outputs_excel'] = audit_outputs_excel()
    
    # 4. Normalizados
    results['normalized'] = audit_normalized_outputs()
    
    # 5. Cobertura
    results['coverage'] = compare_coverage()
    
    # 6. Faltantes
    results['missing'] = find_missing_files()
    
    # Salvar relatório
    output_file = BASE_DIR / 'outputs/logs/pipeline_audit_report.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print(f"✅ Relatório completo salvo em: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()

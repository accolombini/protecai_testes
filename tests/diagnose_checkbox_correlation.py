#!/usr/bin/env python3
"""
Diagnóstico CRÍTICO: Checkbox Detection vs CSV Correlation

Objetivo: Identificar discrepâncias entre checkboxes detectados e parâmetros no CSV
para garantir 100% de captura (VIDAS EM RISCO).

Saída:
- Relatório detalhado com counts por página
- Lista de checkboxes marcados sem correspondência no CSV
- Lista de parâmetros com valores mas sem checkbox marcado
- Recomendações para política de decisão
"""

import sys
from pathlib import Path
import pandas as pd
from collections import defaultdict

# Adicionar diretório scripts ao path
sys.path.insert(0, str(Path(__file__).parent))

from universal_checkbox_detector import UniversalCheckboxDetector


def diagnose_p122():
    """Diagnóstico completo do P122"""
    
    print("="*100)
    print("🔍 DIAGNÓSTICO CRÍTICO: P122 52-MF-02A_2021-03-08")
    print("="*100)
    
    # Arquivos
    pdf_path = Path("inputs/pdf/P122 52-MF-02A_2021-03-08.pdf")
    csv_path = Path("outputs/norm_csv/P122 52-MF-02A_2021-03-08_params.csv")
    
    if not pdf_path.exists():
        print(f"❌ PDF não encontrado: {pdf_path}")
        return
    
    if not csv_path.exists():
        print(f"❌ CSV não encontrado: {csv_path}")
        return
    
    # 1. CARREGAR CSV
    print(f"\n📋 1. CARREGANDO CSV...")
    df = pd.read_csv(csv_path)
    print(f"   ✅ {len(df)} parâmetros no CSV")
    
    # Analisar CSV
    params_with_values = df[df['Value'].notna() & (df['Value'] != '') & (df['Value'] != 'nan')]
    params_without_values = df[~df.index.isin(params_with_values.index)]
    
    print(f"   📊 Parâmetros COM valores: {len(params_with_values)}")
    print(f"   📊 Parâmetros SEM valores: {len(params_without_values)}")
    
    # 2. DETECTAR CHECKBOXES
    print(f"\n☑️  2. DETECTANDO CHECKBOXES...")
    detector = UniversalCheckboxDetector(str(pdf_path), debug=False)
    
    all_checkboxes = []
    marked_by_page = defaultdict(list)
    empty_by_page = defaultdict(list)
    
    num_pages = len(detector.doc)
    print(f"   📄 Processando {num_pages} páginas...")
    
    for page_num in range(1, num_pages + 1):
        try:
            result = detector.analyze_page(page_num, output_dir=None, save_visualization=False)
            checkboxes = result.get('results', [])
            
            marked = [cb for cb in checkboxes if cb.get('is_marked', False)]
            empty = [cb for cb in checkboxes if not cb.get('is_marked', False)]
            
            all_checkboxes.extend(checkboxes)
            marked_by_page[page_num] = marked
            empty_by_page[page_num] = empty
            
            print(f"   📄 Página {page_num:2d}: {len(checkboxes):3d} total (☑️ {len(marked):3d} marcados, ☐ {len(empty):3d} vazios)")
            
        except Exception as e:
            print(f"   ❌ Erro página {page_num}: {e}")
    
    # 3. ESTATÍSTICAS GERAIS
    total_marked = sum(len(m) for m in marked_by_page.values())
    total_empty = sum(len(e) for e in empty_by_page.values())
    
    print(f"\n📊 3. ESTATÍSTICAS GERAIS:")
    print(f"   ✅ Total de checkboxes detectados: {len(all_checkboxes)}")
    print(f"   ☑️  Checkboxes MARCADOS: {total_marked}")
    print(f"   ☐  Checkboxes VAZIOS: {total_empty}")
    
    # 4. ANÁLISE DE CORRELAÇÃO
    print(f"\n🔗 4. ANÁLISE DE CORRELAÇÃO:")
    
    # Coletar códigos únicos dos checkboxes marcados
    marked_param_codes = set()
    marked_details = []
    
    for page_num, marked_list in marked_by_page.items():
        for cb in marked_list:
            param_code = cb.get('param_code', 'UNKNOWN')
            marked_param_codes.add(param_code)
            marked_details.append({
                'page': page_num,
                'code': param_code,
                'density': cb.get('density', 0),
                'x': cb.get('x_pdf', 0),
                'y': cb.get('y_pdf', 0)
            })
    
    print(f"   ☑️  Códigos únicos com checkbox MARCADO: {len(marked_param_codes)}")
    print(f"   📋 Códigos: {sorted(marked_param_codes)}")
    
    # 5. CRUZAMENTO CSV ↔ CHECKBOXES
    print(f"\n🔍 5. CRUZAMENTO CSV ↔ CHECKBOXES:")
    
    # Caso 1: Checkboxes marcados que NÃO existem no CSV
    codes_in_csv = set(df['Code'].astype(str))
    missing_in_csv = marked_param_codes - codes_in_csv - {'UNKNOWN'}
    
    if missing_in_csv:
        print(f"   ⚠️  ATENÇÃO: {len(missing_in_csv)} códigos marcados NÃO ENCONTRADOS no CSV:")
        for code in sorted(missing_in_csv):
            print(f"      - {code}")
    else:
        print(f"   ✅ Todos os códigos marcados existem no CSV")
    
    # Caso 2: Checkboxes marcados que existem no CSV mas SEM valor
    marked_without_value = []
    for code in marked_param_codes:
        if code in codes_in_csv:
            param_row = df[df['Code'].astype(str) == code]
            if not param_row.empty:
                value = str(param_row.iloc[0]['Value']).strip()
                if value in ['', 'nan', 'None']:
                    marked_without_value.append(code)
    
    if marked_without_value:
        print(f"\n   🚨 CRÍTICO: {len(marked_without_value)} checkboxes MARCADOS com parâmetro SEM VALOR:")
        for code in sorted(marked_without_value):
            param_row = df[df['Code'].astype(str) == code]
            desc = param_row.iloc[0]['Description'] if not param_row.empty else 'N/A'
            print(f"      - {code}: {desc}")
    else:
        print(f"\n   ✅ Todos checkboxes marcados têm valores no CSV")
    
    # Caso 3: Parâmetros COM valor mas SEM checkbox marcado
    params_with_value_codes = set(params_with_values['Code'].astype(str))
    has_value_not_marked = params_with_value_codes - marked_param_codes
    
    if has_value_not_marked:
        print(f"\n   ⚠️  {len(has_value_not_marked)} parâmetros COM VALOR mas SEM checkbox marcado:")
        for code in sorted(list(has_value_not_marked)[:20]):  # Mostrar apenas primeiros 20
            param_row = df[df['Code'].astype(str) == code]
            if not param_row.empty:
                value = param_row.iloc[0]['Value']
                desc = param_row.iloc[0]['Description']
                print(f"      - {code}: {desc} = {value}")
        if len(has_value_not_marked) > 20:
            print(f"      ... e mais {len(has_value_not_marked) - 20} parâmetros")
    else:
        print(f"\n   ✅ Todos parâmetros com valor têm checkbox marcado")
    
    # 6. RECOMENDAÇÕES
    print(f"\n💡 6. RECOMENDAÇÕES:")
    
    if marked_without_value:
        print(f"   🚨 AÇÃO NECESSÁRIA:")
        print(f"      - Checkboxes marcados SEM valor provavelmente indicam:")
        print(f"        (a) Valores booleanos implícitos (checkbox = Yes/No)")
        print(f"        (b) Parâmetros habilitados com valor default")
        print(f"      - SOLUÇÃO: Marcar como ATIVOS mesmo sem valor explícito")
        print(f"      - Confidence: 0.95 (checkbox marcado = evidência forte)")
    
    if has_value_not_marked:
        print(f"\n   ⚠️  REVISAR:")
        print(f"      - Parâmetros com valor mas sem checkbox podem ser:")
        print(f"        (a) Valores default (não configurados pelo usuário)")
        print(f"        (b) Parâmetros que não usam checkboxes")
        print(f"      - SOLUÇÃO: Marcar como ATIVOS com confidence mais baixa")
        print(f"      - Confidence: 0.80 (valor presente mas sem confirmação visual)")
    
    print(f"\n{'='*100}")
    print(f"✅ DIAGNÓSTICO CONCLUÍDO")
    print(f"{'='*100}\n")
    
    # Salvar relatório detalhado
    report_path = Path("outputs/reports/checkbox_correlation_diagnosis_P122.txt")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write("DIAGNÓSTICO CHECKBOX CORRELATION - P122\n")
        f.write("="*100 + "\n\n")
        f.write(f"Total checkboxes: {len(all_checkboxes)}\n")
        f.write(f"Marcados: {total_marked}\n")
        f.write(f"Vazios: {total_empty}\n\n")
        f.write(f"Códigos marcados: {len(marked_param_codes)}\n")
        f.write(f"Parâmetros no CSV: {len(df)}\n")
        f.write(f"Parâmetros com valor: {len(params_with_values)}\n\n")
        f.write("CHECKBOXES MARCADOS:\n")
        for detail in marked_details:
            f.write(f"  Página {detail['page']}: {detail['code']} (density={detail['density']:.3f})\n")
    
    print(f"📄 Relatório salvo em: {report_path}")


if __name__ == '__main__':
    diagnose_p122()

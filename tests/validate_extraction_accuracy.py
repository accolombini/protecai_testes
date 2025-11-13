"""
VALIDAÇÃO DE PRECISÃO DA EXTRAÇÃO - DE-PARA 100%

OBJETIVO: Verificar se TODOS os parâmetros dos PDFs/S40 foram extraídos CORRETAMENTE para os CSVs

CRÍTICO: VIDAS EM RISCO - Validação 100% precisa é obrigatória
"""

import PyPDF2
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Tuple

def extract_parameters_from_pdf(pdf_path: Path) -> List[Tuple[str, str, str]]:
    """
    Extrai TODOS os parâmetros do PDF usando os mesmos padrões do conversor
    
    Returns:
        Lista de tuplas (código, descrição, valor)
    """
    parameters = []
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        
        # Padrões (mesmos do universal_format_converter.py)
        re_micom = re.compile(r'([0-9A-F]{2}\.[0-9A-F]{2}):\s*([^:]+?):\s*(.+?)(?=\n|$)')
        re_easergy_colon = re.compile(r'([0-9A-F]{4}):\s*([^:]+?):\s*(.+?)(?=\n|$)')
        re_easergy_equals = re.compile(r'([0-9A-F]{4}):\s*([^=]+?)\s*=\s*(.+?)(?=\n|$)')
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Tentar MiCOM primeiro
            match = re_micom.search(line)
            if match:
                code, desc, value = match.groups()
                parameters.append((code.strip(), desc.strip(), value.strip()))
                continue
            
            # Tentar Easergy com =
            match = re_easergy_equals.search(line)
            if match:
                code, desc, value = match.groups()
                parameters.append((code.strip(), desc.strip(), value.strip()))
                continue
            
            # Tentar Easergy com :
            match = re_easergy_colon.search(line)
            if match:
                code, desc, value = match.groups()
                parameters.append((code.strip(), desc.strip(), value.strip()))
                continue
        
        return parameters
        
    except Exception as e:
        print(f"❌ Erro ao ler {pdf_path.name}: {e}")
        return []


def extract_parameters_from_s40(s40_path: Path) -> List[Tuple[str, str]]:
    """
    Extrai TODOS os parâmetros do arquivo .S40
    
    Returns:
        Lista de tuplas (parâmetro, valor)
    """
    parameters = []
    
    try:
        encodings = ['latin-1', 'cp1252', 'utf-8']
        content = None
        
        for encoding in encodings:
            try:
                with open(s40_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                break
            except:
                continue
        
        if not content:
            return []
        
        # Pattern SEPAM: parametro=valor
        re_sepam = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)=(.+)$', re.MULTILINE)
        
        for match in re_sepam.finditer(content):
            param, value = match.groups()
            parameters.append((param.strip(), value.strip()))
        
        return parameters
        
    except Exception as e:
        print(f"❌ Erro ao ler {s40_path.name}: {e}")
        return []


def validate_csv_against_original(original_path: Path, csv_path: Path) -> Dict:
    """
    Valida se o CSV contém EXATAMENTE os mesmos parâmetros do original
    
    Returns:
        Dicionário com resultado da validação
    """
    result = {
        'file': original_path.name,
        'total_original': 0,
        'total_csv': 0,
        'matched': 0,
        'missing_in_csv': [],
        'extra_in_csv': [],
        'mismatched_values': [],
        'accuracy': 0.0
    }
    
    # Extrair parâmetros do original
    if original_path.suffix.upper() == '.S40':
        original_params = extract_parameters_from_s40(original_path)
        # Converter para formato compatível (código, desc, valor)
        original_params = [(p, p, v) for p, v in original_params]
    else:
        original_params = extract_parameters_from_pdf(original_path)
    
    result['total_original'] = len(original_params)
    
    # Ler CSV
    try:
        df = pd.read_csv(csv_path)
        result['total_csv'] = len(df)
    except Exception as e:
        print(f"❌ Erro ao ler CSV {csv_path.name}: {e}")
        return result
    
    # Criar dicionários para comparação
    original_dict = {code: (desc, value) for code, desc, value in original_params}
    csv_dict = {row['Code']: (row['Description'], row['Value']) for _, row in df.iterrows()}
    
    # Verificar parâmetros que estão no original
    for code, (desc_orig, value_orig) in original_dict.items():
        if code in csv_dict:
            desc_csv, value_csv = csv_dict[code]
            
            # Normalizar valores para comparação
            value_orig_norm = str(value_orig).strip().lower()
            value_csv_norm = str(value_csv).strip().lower()
            
            if value_orig_norm == value_csv_norm or value_orig_norm in value_csv_norm or value_csv_norm in value_orig_norm:
                result['matched'] += 1
            else:
                result['mismatched_values'].append({
                    'code': code,
                    'original': value_orig,
                    'csv': value_csv
                })
        else:
            result['missing_in_csv'].append(code)
    
    # Verificar parâmetros extras no CSV
    for code in csv_dict.keys():
        if code not in original_dict:
            result['extra_in_csv'].append(code)
    
    # Calcular precisão
    if result['total_original'] > 0:
        result['accuracy'] = (result['matched'] / result['total_original']) * 100
    
    return result


def main():
    print("="*80)
    print("🎯 VALIDAÇÃO DE PRECISÃO DA EXTRAÇÃO - DE-PARA 100%")
    print("="*80)
    
    # Arquivos de amostra
    samples = [
        ('inputs/pdf/P122 52-MF-02A_2021-03-08.pdf', 'outputs/csv/P122 52-MF-02A_2021-03-08_params.csv'),
        ('inputs/pdf/P143 52-MF-03A.pdf', 'outputs/csv/P143 52-MF-03A_params.csv'),
        ('inputs/pdf/P220 52-MP-01A.pdf', 'outputs/csv/P220 52-MP-01A_params.csv'),
        ('inputs/pdf/P241_52-MP-20_2019-08-15.pdf', 'outputs/csv/P241_52-MP-20_2019-08-15_params.csv'),
        ('inputs/pdf/P922 52-MF-01BC.pdf', 'outputs/csv/P922 52-MF-01BC_params.csv'),
        ('inputs/txt/00-MF-12_2016-03-31.S40', 'outputs/csv/00-MF-12_2016-03-31_params.csv'),
    ]
    
    total_accuracy = 0
    total_files = 0
    all_passed = True
    
    for original_file, csv_file in samples:
        original_path = Path(original_file)
        csv_path = Path(csv_file)
        
        if not original_path.exists():
            print(f"\n⚠️  Original não encontrado: {original_path.name}")
            continue
        
        if not csv_path.exists():
            print(f"\n⚠️  CSV não encontrado: {csv_path.name}")
            continue
        
        print(f"\n{'='*80}")
        print(f"📄 VALIDANDO: {original_path.name}")
        print(f"{'='*80}")
        
        result = validate_csv_against_original(original_path, csv_path)
        
        print(f"\n📊 RESULTADO:")
        print(f"   Original:  {result['total_original']} parâmetros")
        print(f"   CSV:       {result['total_csv']} parâmetros")
        print(f"   Matched:   {result['matched']} parâmetros")
        print(f"   Precisão:  {result['accuracy']:.1f}%")
        
        if result['missing_in_csv']:
            print(f"\n⚠️  FALTANDO {len(result['missing_in_csv'])} parâmetros no CSV:")
            for code in result['missing_in_csv'][:10]:
                print(f"      - {code}")
            if len(result['missing_in_csv']) > 10:
                print(f"      ... e mais {len(result['missing_in_csv']) - 10}")
            all_passed = False
        
        if result['extra_in_csv']:
            print(f"\n⚠️  {len(result['extra_in_csv'])} parâmetros EXTRAS no CSV (não no original):")
            for code in result['extra_in_csv'][:10]:
                print(f"      - {code}")
            if len(result['extra_in_csv']) > 10:
                print(f"      ... e mais {len(result['extra_in_csv']) - 10}")
        
        if result['mismatched_values']:
            print(f"\n⚠️  {len(result['mismatched_values'])} valores DIFERENTES:")
            for item in result['mismatched_values'][:5]:
                print(f"      - {item['code']}: '{item['original']}' → '{item['csv']}'")
            if len(result['mismatched_values']) > 5:
                print(f"      ... e mais {len(result['mismatched_values']) - 5}")
            all_passed = False
        
        if result['accuracy'] == 100.0:
            print("\n✅ EXTRAÇÃO 100% PRECISA!")
        elif result['accuracy'] >= 95.0:
            print("\n⚠️  Extração quase perfeita (95%+)")
        else:
            print("\n❌ EXTRAÇÃO COM PROBLEMAS!")
            all_passed = False
        
        total_accuracy += result['accuracy']
        total_files += 1
    
    print(f"\n{'='*80}")
    print(f"📊 RESUMO FINAL")
    print(f"{'='*80}")
    print(f"Arquivos validados: {total_files}")
    print(f"Precisão média:     {total_accuracy / total_files if total_files > 0 else 0:.1f}%")
    
    if all_passed:
        print("\n✅ TODOS OS ARQUIVOS COM EXTRAÇÃO 100% PRECISA!")
    else:
        print("\n⚠️  ALGUNS ARQUIVOS COM PROBLEMAS - VERIFICAR ACIMA")
    
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

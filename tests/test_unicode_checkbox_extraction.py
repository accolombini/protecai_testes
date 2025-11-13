#!/usr/bin/env python3
"""
🎯 TESTE: Extração de Checkboxes via Unicode (PyPDF2)
ESTRATÉGIA: Detectar caracteres ☒ e ☑ no texto extraído
OBJETIVO: 100% de precisão
"""

import sys
from pathlib import Path
from PyPDF2 import PdfReader
import re

# Adicionar diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Diretórios
INPUT_PDF_DIR = ROOT_DIR / "inputs" / "pdf"

def extract_text_from_page(pdf_path: Path, page_num: int = 0) -> str:
    """Extrai texto de uma página específica do PDF"""
    try:
        reader = PdfReader(str(pdf_path))
        if page_num >= len(reader.pages):
            print(f"❌ Erro: PDF tem apenas {len(reader.pages)} páginas")
            return ""
        
        page = reader.pages[page_num]
        text = page.extract_text()
        return text
    except Exception as e:
        print(f"❌ Erro ao ler PDF: {e}")
        return ""

def analyze_checkboxes_in_text(text: str) -> dict:
    """Analisa checkboxes no texto extraído"""
    
    # Caracteres Unicode de checkbox
    CHECKBOX_MARKED = ['☒', '☑', '✓', '✔', 'X', '×']  # Possíveis representações
    CHECKBOX_EMPTY = ['☐', '□', '▢']
    
    results = {
        'marked_checkboxes': [],
        'empty_checkboxes': [],
        'total_marked': 0,
        'total_empty': 0,
        'lines_with_marked': []
    }
    
    lines = text.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        # Buscar checkboxes marcados
        for checkbox_char in CHECKBOX_MARKED:
            if checkbox_char in line:
                results['marked_checkboxes'].append({
                    'line_num': line_num,
                    'char': checkbox_char,
                    'content': line.strip()
                })
                results['lines_with_marked'].append(line.strip())
        
        # Buscar checkboxes vazios
        for checkbox_char in CHECKBOX_EMPTY:
            if checkbox_char in line:
                results['empty_checkboxes'].append({
                    'line_num': line_num,
                    'char': checkbox_char,
                    'content': line.strip()
                })
    
    results['total_marked'] = len(results['marked_checkboxes'])
    results['total_empty'] = len(results['empty_checkboxes'])
    
    return results

def extract_parameters_from_checkboxes(text: str) -> list:
    """Extrai parâmetros com checkboxes marcados"""
    
    parameters = []
    
    # Padrões de parâmetros nos PDFs de relés
    patterns = [
        # P122/P220 Easergy: "0104: Frequency:60Hz"
        r'(\d{4}):\s*([^:]+?):\s*(.+)',
        # P143/P241 MiCOM: "00.01: Language: English"
        r'(\d{2}\.\d{2}):\s*([^:]+?):\s*(.+)',
    ]
    
    lines = text.split('\n')
    
    for line in lines:
        # Verificar se linha tem checkbox marcado
        if any(char in line for char in ['☒', '☑', 'X', '✓', '✔']):
            # Tentar extrair parâmetro com os padrões conhecidos
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    code = match.group(1)
                    description = match.group(2).strip()
                    value = match.group(3).strip()
                    
                    parameters.append({
                        'code': code,
                        'description': description,
                        'value': value,
                        'raw_line': line.strip()
                    })
                    break
            else:
                # Se não matchou nenhum padrão, mas tem checkbox, armazenar a linha
                parameters.append({
                    'code': '',
                    'description': line.strip(),
                    'value': '',
                    'raw_line': line.strip()
                })
    
    return parameters

def main():
    """Teste em uma página específica"""
    
    # PDF de teste
    pdf_filename = "P_122 52-MF-03B1_2021-03-17.pdf"
    page_num = 0  # Página 1 (índice 0)
    
    pdf_path = INPUT_PDF_DIR / pdf_filename
    
    if not pdf_path.exists():
        print(f"❌ Erro: PDF não encontrado: {pdf_path}")
        return
    
    print("=" * 80)
    print(f"🔬 TESTE: {pdf_filename}")
    print(f"📄 Analisando página {page_num + 1}")
    print("=" * 80)
    
    # Extrair texto
    print("\n🔄 Extraindo texto da página...")
    text = extract_text_from_page(pdf_path, page_num)
    
    if not text:
        print("❌ Nenhum texto extraído!")
        return
    
    print(f"✅ Texto extraído: {len(text)} caracteres")
    
    # Analisar checkboxes
    print("\n🔍 Analisando checkboxes no texto...")
    results = analyze_checkboxes_in_text(text)
    
    print(f"\n📊 RESULTADOS:")
    print(f"   ✅ Checkboxes marcados: {results['total_marked']}")
    print(f"   ☐ Checkboxes vazios: {results['total_empty']}")
    
    # Mostrar checkboxes marcados
    if results['marked_checkboxes']:
        print(f"\n📋 CHECKBOXES MARCADOS DETECTADOS:")
        print("=" * 80)
        for i, checkbox in enumerate(results['marked_checkboxes'][:20], 1):  # Primeiros 20
            print(f"{i}. Linha {checkbox['line_num']}: [{checkbox['char']}] {checkbox['content'][:70]}")
        
        if len(results['marked_checkboxes']) > 20:
            print(f"   ... e mais {len(results['marked_checkboxes']) - 20} checkboxes")
    
    # Extrair parâmetros
    print(f"\n🔍 Extraindo parâmetros com checkboxes marcados...")
    parameters = extract_parameters_from_checkboxes(text)
    
    print(f"\n📊 PARÂMETROS EXTRAÍDOS: {len(parameters)}")
    if parameters:
        print("=" * 80)
        for i, param in enumerate(parameters[:20], 1):  # Primeiros 20
            if param['code']:
                print(f"{i}. {param['code']}: {param['description']}: {param['value']}")
            else:
                print(f"{i}. {param['raw_line'][:70]}")
        
        if len(parameters) > 20:
            print(f"   ... e mais {len(parameters) - 20} parâmetros")
    
    # Mostrar amostra do texto bruto
    print(f"\n📄 AMOSTRA DO TEXTO EXTRAÍDO (primeiros 500 caracteres):")
    print("=" * 80)
    print(text[:500])
    print("=" * 80)
    
    # Estatísticas finais
    print(f"\n✅ ESPERADO (contagem manual): 3 checkboxes marcados")
    print(f"📊 DETECTADO: {results['total_marked']} checkboxes marcados")
    if results['total_marked'] > 0:
        accuracy = (3 / results['total_marked']) * 100 if results['total_marked'] >= 3 else (results['total_marked'] / 3) * 100
        print(f"📈 Precisão aproximada: {accuracy:.1f}%")

if __name__ == "__main__":
    main()

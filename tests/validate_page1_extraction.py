#!/usr/bin/env python3
"""
Validação de extração - Página 1
Objetivo: Provar que conseguimos extrair TODOS os parâmetros corretamente
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyPDF2 import PdfReader
import re
import pandas as pd

# Arquivo de teste
PDF_PATH = Path("inputs/pdf/P_122 52-MF-03B1_2021-03-17.pdf")

def extract_page1_text():
    """Extrai texto apenas da página 1"""
    reader = PdfReader(str(PDF_PATH))
    page1 = reader.pages[0]
    return page1.extract_text()

def parse_easergy_params(text):
    """
    Parse parâmetros formato Easergy (P122)
    Padrão: 0104: Frequency:60Hz
    """
    pattern = r'(\d{4}):\s*([^:]+?)(?::(.+?))?(?=\n\d{4}:|\Z)'
    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
    
    params = []
    for code, desc, value in matches:
        params.append({
            'Code': code,
            'Description': desc.strip(),
            'Value': value.strip() if value else ''
        })
    
    return params

def extract_checkbox_params(text):
    """
    Extrai parâmetros que aparecem em listas (checkbox implícito)
    Exemplo na página 1:
    
    0150: LED 5 part 1:
       I>
       tI>    ← Este aparece, então checkbox está marcado
       I>>
       ...
    """
    # Buscar blocos de listas após parâmetros
    checkbox_params = []
    
    # Padrão: linha com código seguida de linhas indentadas
    lines = text.split('\n')
    current_section = None
    
    for i, line in enumerate(lines):
        # Detectar início de seção com código
        if re.match(r'\d{4}:', line):
            current_section = line
        # Linhas indentadas após seção = possíveis checkboxes
        elif current_section and line.strip() and not line.strip().startswith('0'):
            # Se a linha tem texto (não vazio), checkbox está marcado
            checkbox_params.append({
                'Section': current_section,
                'Parameter': line.strip(),
                'Type': 'checkbox_marked'
            })
    
    return checkbox_params

def main():
    print("=" * 80)
    print("🔬 VALIDAÇÃO: Página 1 de P_122 52-MF-03B1_2021-03-17.pdf")
    print("=" * 80)
    print()
    
    # Extrair texto
    text = extract_page1_text()
    print(f"✅ Texto extraído: {len(text)} caracteres")
    print()
    
    # Parse parâmetros formato Easergy
    params = parse_easergy_params(text)
    print("📊 PARÂMETROS TEXTUAIS (formato 0104: Frequency: 60Hz):")
    print("-" * 80)
    for p in params:
        print(f"   {p['Code']}: {p['Description']}: {p['Value']}")
    print(f"\n✅ Total de parâmetros textuais: {len(params)}")
    print()
    
    # Parâmetros checkbox
    checkbox_params = extract_checkbox_params(text)
    print("📋 PARÂMETROS COM CHECKBOX (linhas indentadas):")
    print("-" * 80)
    sections = {}
    for cp in checkbox_params:
        section = cp['Section']
        if section not in sections:
            sections[section] = []
        sections[section].append(cp['Parameter'])
    
    for section, items in sections.items():
        print(f"\n   {section}")
        for item in items:
            print(f"      ☒ {item}")
    
    print(f"\n✅ Total de checkboxes marcados: {len(checkbox_params)}")
    print()
    
    # Validação manual
    print("=" * 80)
    print("📊 VALIDAÇÃO MANUAL:")
    print("=" * 80)
    print("Esperado (contagem manual): 3 checkboxes marcados")
    print("   ☒ tI> (LED 5)")
    print("   ☒ tIe> (LED 5)")
    print("   ☒ tIe> (LED 5 - duplicado)")
    print()
    print(f"Detectado: {len(checkbox_params)} checkboxes marcados")
    print()
    
    # Mostrar texto bruto para debug
    print("=" * 80)
    print("📄 TEXTO BRUTO DA PÁGINA 1:")
    print("=" * 80)
    print(text[:1500])
    print("\n... (texto truncado)")
    print()

if __name__ == "__main__":
    main()

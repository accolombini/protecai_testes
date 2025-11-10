#!/usr/bin/env python3
"""
Debug: Extração manual da página 1 do P122 para identificar códigos faltantes

Objetivo: Entender por que códigos 0150, 0153, 010D, 0180, 018C, 0171, 0166, 52b
não foram extraídos pelo IntelligentRelayExtractor
"""

import fitz  # PyMuPDF
from pathlib import Path
import re

def extract_page1_raw_text():
    """Extrai texto bruto da página 1"""
    pdf_path = Path("inputs/pdf/P122 52-MF-02A_2021-03-08.pdf")
    
    print("="*100)
    print("🔍 EXTRAÇÃO BRUTA - Página 1 do P122")
    print("="*100)
    
    doc = fitz.open(pdf_path)
    page = doc[0]  # Página 1 (índice 0)
    
    # Extrair texto completo
    text = page.get_text()
    
    print("\n📄 TEXTO COMPLETO DA PÁGINA:")
    print("-"*100)
    print(text)
    print("-"*100)
    
    # Buscar códigos específicos
    print("\n🔍 PROCURANDO CÓDIGOS FALTANTES:")
    missing_codes = ['0150', '0153', '010D', '0180', '018C', '0171', '0166', '52b']
    
    for code in missing_codes:
        if code in text:
            # Encontrar contexto (50 chars antes e depois)
            idx = text.find(code)
            start = max(0, idx - 50)
            end = min(len(text), idx + len(code) + 50)
            context = text[start:end].replace('\n', ' ')
            print(f"   ✅ ENCONTRADO: {code}")
            print(f"      Contexto: ...{context}...")
        else:
            print(f"   ❌ NÃO ENCONTRADO: {code}")
    
    # Extrair todos os códigos que parecem parâmetros (padrão: 4 dígitos ou código alfanumérico)
    print("\n📋 TODOS OS CÓDIGOS NA PÁGINA:")
    
    # Padrão 1: Códigos de 4 dígitos (0150, 010D, etc.)
    pattern1 = r'\b[0-9][0-9A-Fa-f]{2,3}\b'
    codes_pattern1 = re.findall(pattern1, text)
    
    # Padrão 2: Códigos curtos alfanuméricos (52b, etc.)
    pattern2 = r'\b[0-9]{2}[a-z]\b'
    codes_pattern2 = re.findall(pattern2, text)
    
    all_codes = set(codes_pattern1 + codes_pattern2)
    
    print(f"   Total de códigos únicos encontrados: {len(all_codes)}")
    for code in sorted(all_codes):
        in_missing = "⚠️ FALTANTE" if code in missing_codes else ""
        print(f"      {code} {in_missing}")
    
    # Extrair texto com coordenadas (pode ajudar a entender layout)
    print("\n📍 TEXTO COM COORDENADAS (primeiros 30 blocos):")
    text_dict = page.get_text("dict")
    
    block_count = 0
    for block in text_dict.get('blocks', []):
        if block.get('type') == 0:  # Tipo texto
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    span_text = span.get('text', '').strip()
                    if span_text and block_count < 30:
                        bbox = span.get('bbox', [0, 0, 0, 0])
                        print(f"   [{bbox[1]:.1f}y] {span_text}")
                        block_count += 1
    
    doc.close()
    
    print("\n" + "="*100)
    print("✅ ANÁLISE CONCLUÍDA")
    print("="*100)


if __name__ == '__main__':
    extract_page1_raw_text()

#!/usr/bin/env python3
"""
Debug: Extrair manualmente códigos 010D, 018C, 52b das páginas especificadas

010D: página 4
018C: página 6  
52b: página 12
"""

import fitz
from pathlib import Path
import re

def extract_specific_pages():
    """Extrai texto das páginas onde estão os códigos faltantes"""
    pdf_path = Path("inputs/pdf/P122 52-MF-02A_2021-03-08.pdf")
    
    print("="*100)
    print("🔍 EXTRAÇÃO DOS CÓDIGOS FALTANTES")
    print("="*100)
    
    doc = fitz.open(pdf_path)
    
    targets = {
        '010D': 4,   # Página 4 (índice 3)
        '018C': 6,   # Página 6 (índice 5)
        '52b': 12    # Página 12 (índice 11)
    }
    
    for code, page_num in targets.items():
        print(f"\n{'='*100}")
        print(f"📄 PÁGINA {page_num} - Procurando código: {code}")
        print(f"{'='*100}")
        
        page = doc[page_num - 1]
        text = page.get_text()
        
        # Procurar o código
        if code in text:
            # Encontrar contexto (200 chars antes e depois)
            idx = text.find(code)
            start = max(0, idx - 200)
            end = min(len(text), idx + len(code) + 200)
            context = text[start:end]
            
            print(f"✅ CÓDIGO ENCONTRADO: {code}")
            print(f"\n📋 CONTEXTO:")
            print("-"*100)
            print(context)
            print("-"*100)
            
            # Tentar extrair linha completa do parâmetro
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if code in line:
                    print(f"\n✨ LINHA COMPLETA:")
                    print(f"   {line}")
                    
                    # Tentar identificar padrão
                    # Padrão típico: "010D: Description: Value"
                    match = re.search(rf'{code}:\s*([^:]+):\s*(.+)', line)
                    if match:
                        desc = match.group(1).strip()
                        val = match.group(2).strip()
                        print(f"\n   📝 Extraído:")
                        print(f"      Code: {code}")
                        print(f"      Description: {desc}")
                        print(f"      Value: {val}")
                    else:
                        # Padrão alternativo: próximas linhas
                        print(f"\n   📝 Contexto ao redor:")
                        for j in range(max(0, i-2), min(len(lines), i+3)):
                            print(f"      [{j}] {lines[j]}")
        else:
            print(f"❌ CÓDIGO NÃO ENCONTRADO: {code}")
            print(f"\n📋 Texto completo da página (primeiras 500 chars):")
            print(text[:500])
    
    doc.close()
    
    print(f"\n{'='*100}")
    print("✅ ANÁLISE CONCLUÍDA")
    print(f"{'='*100}")


if __name__ == '__main__':
    extract_specific_pages()

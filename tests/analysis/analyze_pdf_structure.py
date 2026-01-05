"""
Análise da estrutura REAL dos PDFs para entender como extrair corretamente
"""

import PyPDF2
from pathlib import Path

def analyze_pdf(pdf_path):
    """Analisa estrutura de um PDF"""
    print("="*80)
    print(f"📄 {pdf_path.name}")
    print("="*80)
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # Primeira página
            text = reader.pages[0].extract_text()
            lines = text.split('\n')
            
            print(f"Total de linhas na página 1: {len(lines)}")
            print("\n🔍 Primeiras 100 linhas:")
            print("-"*80)
            
            for i, line in enumerate(lines[:100], 1):
                if line.strip():
                    print(f"{i:3d}: {line[:120]}")
            
            print("\n" + "="*80 + "\n")
            
    except Exception as e:
        print(f"❌ Erro: {e}\n")


# Analisar um PDF de cada modelo
pdfs_to_analyze = [
    "inputs/pdf/P122 52-MF-02A_2021-03-08.pdf",
    "inputs/pdf/P143 52-MF-03A.pdf", 
    "inputs/pdf/P220 52-MP-01A.pdf",
    "inputs/pdf/P241_52-MP-20_2019-08-15.pdf",
    "inputs/pdf/P922 52-MF-01BC.pdf",
]

print("\n" + "="*80)
print("🔍 ANÁLISE DA ESTRUTURA REAL DOS PDFs")
print("="*80 + "\n")

for pdf in pdfs_to_analyze:
    pdf_path = Path(pdf)
    if pdf_path.exists():
        analyze_pdf(pdf_path)
    else:
        print(f"⚠️  Arquivo não encontrado: {pdf}\n")

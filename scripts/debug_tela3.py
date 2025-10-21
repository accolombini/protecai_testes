from PyPDF2 import PdfReader
from pathlib import Path
import re

def analyze_tela3_content():
    """Analisa o conteúdo do tela3.pdf para entender o padrão."""
    pdf_path = Path("inputs/pdf/tela3.pdf")
    
    if not pdf_path.exists():
        print("Arquivo não encontrado!")
        return
    
    reader = PdfReader(str(pdf_path))
    
    # Extrair primeiras 50 linhas da primeira página
    first_page_text = reader.pages[0].extract_text() or ""
    lines = first_page_text.splitlines()
    
    print("=== PRIMEIRAS 30 LINHAS DO TELA3.PDF ===")
    for i, line in enumerate(lines[:30], 1):
        line = line.strip()
        if line:
            print(f"{i:2d}: {line}")
    
    print("\n=== ANÁLISE DE PADRÕES ===")
    
    # Testar diferentes regex
    patterns = {
        "MiCOM": re.compile(r"^([0-9A-F]{2}\.[0-9A-F]{2}):\s*([^:]+):\s*(.*)$"),
        "Easergy": re.compile(r"^([0-9A-F]{4}):\s*([^=:]+)=:\s*(.*)$"),
        "Generic": re.compile(r"^([^:]+):\s*(.+)$")
    }
    
    for pattern_name, pattern in patterns.items():
        matches = 0
        for line in lines:
            if pattern.match(line.strip()):
                matches += 1
        print(f"{pattern_name} pattern: {matches} matches")
    
    # Mostrar linhas que contêm dois pontos
    print(f"\nLinhas com ':': {sum(1 for line in lines if ':' in line)}")
    print(f"Linhas com '=': {sum(1 for line in lines if '=' in line)}")
    print(f"Linhas com números: {sum(1 for line in lines if any(c.isdigit() for c in line))}")

analyze_tela3_content()

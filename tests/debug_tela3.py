from PyPDF2 import PdfReader
from pathlib import Path
import re

def debug_pdf_content():
    """Analisa o conteúdo de PDFs disponíveis para entender padrões."""
    
    # DESCOBERTA DINÂMICA - busca qualquer PDF
    base_dir = Path("inputs")
    pdf_files = list(base_dir.glob("**/*.pdf"))
    
    if not pdf_files:
        print("❌ Nenhum arquivo PDF encontrado no diretório inputs/")
        return
        
    # Analisa o primeiro PDF encontrado (ou todos se quiser)
    pdf_path = pdf_files[0]  # Pode iterar por todos se necessário
    print(f"📄 Analisando: {pdf_path}")
    
    if not pdf_path.exists():
        print("Arquivo não encontrado!")
        return
    
    reader = PdfReader(str(pdf_path))
    
    # Extrair primeiras 50 linhas da primeira página
    first_page_text = reader.pages[0].extract_text() or ""
    lines = first_page_text.splitlines()
    
    print(f"=== PRIMEIRAS 30 LINHAS DO {pdf_path.name.upper()} ===")
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

debug_pdf_content()

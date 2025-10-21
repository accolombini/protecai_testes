from PyPDF2 import PdfReader
from pathlib import Path
import re

def analyze_all_patterns():
    """Analisa todos os padrões do tela3.pdf para encontrar o que está sendo perdido."""
    pdf_path = Path("inputs/pdf/tela3.pdf")
    
    reader = PdfReader(str(pdf_path))
    all_text = ""
    for page in reader.pages:
        all_text += page.extract_text() + "\n"
    
    lines = [line.strip() for line in all_text.splitlines() if line.strip()]
    
    print(f"=== ANÁLISE COMPLETA DO TELA3.PDF ===")
    print(f"Total de linhas não vazias: {len(lines)}")
    
    # Padrões atuais
    RE_EASERGY_EQUALS = re.compile(r"^([0-9A-F]{4}):\s*([^=:]+)=:\s*(.*)$")
    RE_EASERGY_COLON = re.compile(r"^([0-9A-F]{4}):\s*([^:]+):\s*(.*)$")
    
    matched_equals = 0
    matched_colon = 0
    unmatched = []
    
    for line in lines:
        if RE_EASERGY_EQUALS.match(line):
            matched_equals += 1
        elif RE_EASERGY_COLON.match(line):
            matched_colon += 1
        else:
            unmatched.append(line)
    
    print(f"\nPadrão =: (EQUALS): {matched_equals} matches")
    print(f"Padrão :: (COLON): {matched_colon} matches") 
    print(f"Total matched: {matched_equals + matched_colon}")
    print(f"Unmatched: {len(unmatched)}")
    
    # Mostrar exemplos de linhas não capturadas
    print(f"\n=== PRIMEIROS 20 EXEMPLOS NÃO CAPTURADOS ===")
    for i, line in enumerate(unmatched[:20], 1):
        print(f"{i:2d}: {line}")
    
    # Analisar padrões das linhas não capturadas
    print(f"\n=== ANÁLISE DAS LINHAS NÃO CAPTURADAS ===")
    
    patterns = {
        "Começam com números": sum(1 for line in unmatched if line and line[0].isdigit()),
        "Contêm dois pontos": sum(1 for line in unmatched if ':' in line),
        "Contêm equals": sum(1 for line in unmatched if '=' in line),
        "Só texto (sem números)": sum(1 for line in unmatched if not any(c.isdigit() for c in line)),
        "Linhas curtas (<10 chars)": sum(1 for line in unmatched if len(line) < 10),
        "Headers/Títulos": sum(1 for line in unmatched if line.isupper() and len(line) > 3),
    }
    
    for pattern_name, count in patterns.items():
        print(f"{pattern_name}: {count}")

analyze_all_patterns()

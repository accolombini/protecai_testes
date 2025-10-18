from PyPDF2 import PdfReader
from pathlib import Path

def count_pdf_lines(pdf_path):
    """Conta linhas de texto extraídas de um PDF."""
    try:
        reader = PdfReader(str(pdf_path))
        all_text = ""
        
        print(f"\n=== ANÁLISE DE {pdf_path.name} ===")
        print(f"Número de páginas: {len(reader.pages)}")
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text() or ""
            all_text += page_text + "\n"
            print(f"Página {page_num}: {len(page_text.splitlines())} linhas")
        
        total_lines = len(all_text.splitlines())
        non_empty_lines = len([line for line in all_text.splitlines() if line.strip()])
        
        print(f"Total de linhas: {total_lines}")
        print(f"Linhas não vazias: {non_empty_lines}")
        
        return total_lines, non_empty_lines, all_text
        
    except Exception as e:
        print(f"Erro ao processar {pdf_path}: {e}")
        return 0, 0, ""

# Analisar os PDFs
pdf_files = [
    Path("inputs/pdf/tela1.pdf"),
    Path("inputs/pdf/tela3.pdf")
]

for pdf_file in pdf_files:
    if pdf_file.exists():
        count_pdf_lines(pdf_file)
    else:
        print(f"Arquivo não encontrado: {pdf_file}")

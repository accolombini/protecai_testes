#!/usr/bin/env python3
"""
Análise de checkboxes marcados em PDFs de configuração de relés.
OBJETIVO: Detectar visualmente quais parâmetros estão ativos (checkbox marcado com X).

VIDAS EM RISCO - 100% de precisão necessária.
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageDraw
import re

# Configuração de paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

INPUT_PDF_DIR = PROJECT_ROOT / "inputs" / "pdf"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "checkbox_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def detect_checkboxes_in_image(image_path: Path, page_num: int) -> dict:
    """
    Detecta checkboxes marcados em uma imagem de página PDF.
    
    Estratégia:
    1. Converter para escala de cinza
    2. Aplicar threshold para binarização
    3. Detectar contornos quadrados (checkboxes)
    4. Verificar se há marca 'X' dentro do checkbox
    5. Extrair texto próximo ao checkbox marcado
    
    Returns:
        dict: {
            'marked_checkboxes': [(x, y, w, h), ...],
            'parameters': ['0104: Frequency:60Hz', ...],
            'page_num': int
        }
    """
    print(f"\n{'='*80}")
    print(f"🔍 Analisando imagem: {image_path.name} (Página {page_num})")
    print(f"{'='*80}")
    
    # Carregar imagem
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"❌ Erro ao carregar imagem: {image_path}")
        return {'marked_checkboxes': [], 'parameters': [], 'page_num': page_num}
    
    height, width = img.shape[:2]
    print(f"📐 Dimensões: {width}x{height} pixels")
    
    # Converter para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Aplicar threshold adaptativo (melhor para PDFs com variações de iluminação)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Detectar contornos
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    print(f"📦 Total de contornos detectados: {len(contours)}")
    
    marked_checkboxes = []
    checkbox_candidates = 0
    
    # Filtrar contornos que parecem checkboxes (quadrados pequenos ~10-30 pixels)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        # Critérios para ser um checkbox:
        # 1. Formato aproximadamente quadrado (razão aspecto ~1.0)
        # 2. Tamanho entre 10 e 40 pixels (checkboxes típicos)
        # 3. Área suficiente
        aspect_ratio = float(w) / h if h > 0 else 0
        area = cv2.contourArea(contour)
        
        if (0.7 <= aspect_ratio <= 1.3 and  # Quase quadrado
            10 <= w <= 40 and 10 <= h <= 40 and  # Tamanho de checkbox
            area > 50):  # Área mínima
            
            checkbox_candidates += 1
            
            # Extrair região do checkbox
            checkbox_region = binary[y:y+h, x:x+w]
            
            # Verificar se há marca 'X' dentro (densidade de pixels brancos)
            white_pixel_ratio = np.sum(checkbox_region == 255) / (w * h)
            
            # Se >30% da área do checkbox está preenchida, provavelmente está marcado
            if white_pixel_ratio > 0.3:
                marked_checkboxes.append((x, y, w, h))
                # Desenhar retângulo verde ao redor dos checkboxes marcados
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
    print(f"✅ Candidatos a checkbox: {checkbox_candidates}")
    print(f"✅ Checkboxes MARCADOS detectados: {len(marked_checkboxes)}")
    
    # Salvar imagem com checkboxes marcados destacados
    output_img_path = OUTPUT_DIR / f"{image_path.stem}_marked.png"
    cv2.imwrite(str(output_img_path), img)
    print(f"💾 Imagem com marcações salva: {output_img_path}")
    
    # Extrair texto da página completa com OCR
    pil_img = Image.open(image_path)
    full_text = pytesseract.image_to_string(pil_img, lang='eng')
    
    # Extrair parâmetros próximos aos checkboxes marcados
    parameters = []
    
    # Padrões de parâmetros conhecidos
    patterns = [
        r'\d{4}:\s*.+',  # Easergy: 0104: Frequency:60Hz
        r'\d{2}\.\d{2}:\s*.+',  # MiCOM: 00.01: Language: English
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, full_text, re.MULTILINE)
        parameters.extend(matches)
    
    print(f"📝 Parâmetros extraídos via OCR: {len(parameters)}")
    
    # Para cada checkbox marcado, tentar encontrar texto próximo
    for (x, y, w, h) in marked_checkboxes:
        # Expandir região para capturar texto ao lado do checkbox
        text_region_x = x + w + 5  # 5 pixels à direita do checkbox
        text_region_y = y - 5
        text_region_w = width - text_region_x - 10
        text_region_h = h + 10
        
        if text_region_x + text_region_w <= width and text_region_y >= 0:
            text_region = gray[text_region_y:text_region_y+text_region_h, 
                             text_region_x:text_region_x+text_region_w]
            
            # OCR na região de texto
            text_pil = Image.fromarray(text_region)
            text_content = pytesseract.image_to_string(text_pil, lang='eng').strip()
            
            if text_content:
                print(f"  ✓ Checkbox em ({x},{y}): '{text_content[:50]}...'")
    
    return {
        'marked_checkboxes': marked_checkboxes,
        'parameters': parameters,
        'page_num': page_num,
        'total_text_lines': len(full_text.split('\n'))
    }


def analyze_pdf_with_ocr(pdf_path: Path, max_pages: int = None) -> dict:
    """
    Analisa PDF completo detectando checkboxes marcados em todas as páginas.
    
    Args:
        pdf_path: Caminho para o PDF
        max_pages: Número máximo de páginas a processar (None = todas)
    
    Returns:
        dict: Resultados da análise por página
    """
    print(f"\n{'#'*80}")
    print(f"📄 ANALISANDO PDF: {pdf_path.name}")
    print(f"{'#'*80}")
    
    # Converter PDF para imagens (uma por página)
    print(f"🔄 Convertendo PDF para imagens...")
    images = convert_from_path(str(pdf_path), dpi=300)  # Alta resolução para OCR
    
    total_pages = len(images)
    pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
    
    print(f"📊 Total de páginas: {total_pages}")
    print(f"📊 Páginas a processar: {pages_to_process}")
    
    results = {}
    
    for i, image in enumerate(images[:pages_to_process], start=1):
        # Salvar imagem temporária
        temp_img_path = OUTPUT_DIR / f"{pdf_path.stem}_page_{i}.png"
        image.save(temp_img_path, 'PNG')
        
        # Detectar checkboxes
        page_result = detect_checkboxes_in_image(temp_img_path, i)
        results[f'page_{i}'] = page_result
        
        print(f"\n📄 Página {i}/{pages_to_process}:")
        print(f"   ✅ Checkboxes marcados: {len(page_result['marked_checkboxes'])}")
        print(f"   📝 Parâmetros extraídos: {len(page_result['parameters'])}")
    
    return results


def main():
    """Análise exploratória de checkboxes em PDFs."""
    
    print("\n" + "="*80)
    print("🔬 ANÁLISE DE CHECKBOXES EM PDFs DE RELÉS")
    print("OBJETIVO: Detectar parâmetros ativos com 100% de precisão")
    print("="*80)
    
    # Testar com o primeiro PDF P122
    test_pdfs = [
        "P_122 52-MF-03B1_2021-03-17.pdf",
        "P122 52-MF-02A_2021-03-08.pdf",
    ]
    
    for pdf_name in test_pdfs:
        pdf_path = INPUT_PDF_DIR / pdf_name
        
        if not pdf_path.exists():
            print(f"❌ PDF não encontrado: {pdf_path}")
            continue
        
        # Analisar primeiras 5 páginas para teste
        results = analyze_pdf_with_ocr(pdf_path, max_pages=5)
        
        # Resumo
        print(f"\n{'='*80}")
        print(f"📊 RESUMO: {pdf_name}")
        print(f"{'='*80}")
        
        total_checkboxes = sum(len(r['marked_checkboxes']) for r in results.values())
        total_params = sum(len(r['parameters']) for r in results.values())
        
        print(f"✅ Total de checkboxes marcados: {total_checkboxes}")
        print(f"📝 Total de parâmetros extraídos: {total_params}")
        print(f"📄 Páginas analisadas: {len(results)}")
        
        print(f"\n💾 Imagens com marcações salvas em: {OUTPUT_DIR}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

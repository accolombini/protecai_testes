#!/usr/bin/env python3
"""
Script MINIMALISTA para análise de densidade de checkboxes.
OBJETIVO: Extrair APENAS checkboxes e suas densidades (sem OCR, sem imagens).
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from pdf2image import convert_from_path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def analyze_checkboxes_on_page(image, page_num: int) -> list:
    """
    Detecta checkboxes em uma página e retorna suas densidades.
    
    Returns:
        list: [(x, y, w, h, density, page_num), ...]
    """
    # Converter PIL Image para numpy array
    img = np.array(image)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    # Converter para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Aplicar threshold adaptativo
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Detectar contornos
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    checkboxes = []
    
    # Filtrar contornos que parecem checkboxes
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(w) / h if h > 0 else 0
        area = cv2.contourArea(contour)
        
        # Critérios: quadrado, tamanho 10-40px, área >50
        if (0.7 <= aspect_ratio <= 1.3 and 
            10 <= w <= 40 and 10 <= h <= 40 and 
            area > 50):
            
            # Extrair região do checkbox
            checkbox_region = binary[y:y+h, x:x+w]
            
            # Calcular densidade de pixels brancos
            white_pixel_ratio = np.sum(checkbox_region == 255) / (w * h)
            
            checkboxes.append({
                'x': x,
                'y': y,
                'w': w,
                'h': h,
                'density': round(white_pixel_ratio, 4),
                'page': page_num
            })
    
    return checkboxes


def main():
    """Análise focada nas páginas 1, 4, 5, 7 do P922 52-MF-01BC.pdf"""
    
    print("=" * 80)
    print("🔬 ANÁLISE DE DENSIDADE DE CHECKBOXES - P922 52-MF-01BC.pdf")
    print("=" * 80)
    print("📄 Páginas: 1, 4, 5, 7 (onde você identificou os 9 checkboxes)")
    print()
    
    pdf_path = PROJECT_ROOT / "inputs/pdf/P922 52-MF-01BC.pdf"
    
    if not pdf_path.exists():
        print(f"❌ PDF não encontrado: {pdf_path}")
        return
    
    # Converter PDF para imagens
    print("🔄 Convertendo PDF para imagens (300 DPI)...")
    images = convert_from_path(str(pdf_path), dpi=300)
    
    # Analisar apenas páginas 1, 4, 5, 7
    target_pages = [1, 4, 5, 7]
    all_checkboxes = []
    
    for page_num in target_pages:
        if page_num > len(images):
            print(f"⚠️  Página {page_num} não existe no PDF")
            continue
        
        print(f"\n{'='*80}")
        print(f"📄 PÁGINA {page_num}")
        print(f"{'='*80}")
        
        image = images[page_num - 1]  # índice 0-based
        checkboxes = analyze_checkboxes_on_page(image, page_num)
        
        print(f"✅ Checkboxes detectados: {len(checkboxes)}")
        print()
        print("  ID  |  X    |  Y    | Densidade | Threshold 45%")
        print("------|-------|-------|-----------|---------------")
        
        for i, cb in enumerate(checkboxes, 1):
            status = "☑ MARCADO" if cb['density'] > 0.45 else "☐ VAZIO"
            print(f"  {i:3d} | {cb['x']:5d} | {cb['y']:5d} | {cb['density']:.4f}    | {status}")
        
        all_checkboxes.extend(checkboxes)
    
    # RESUMO ESTATÍSTICO
    print(f"\n{'='*80}")
    print("📊 RESUMO ESTATÍSTICO")
    print(f"{'='*80}")
    
    densities = [cb['density'] for cb in all_checkboxes]
    
    print(f"Total de checkboxes: {len(all_checkboxes)}")
    print(f"Densidade mínima: {min(densities):.4f}")
    print(f"Densidade máxima: {max(densities):.4f}")
    print(f"Densidade média: {np.mean(densities):.4f}")
    print(f"Densidade mediana: {np.median(densities):.4f}")
    print()
    
    # Contagem por threshold
    for threshold in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
        count = sum(1 for d in densities if d > threshold)
        print(f"Threshold {threshold:.2f}: {count:3d} checkboxes marcados")
    
    print(f"\n{'='*80}")
    print("🎯 PRÓXIMO PASSO:")
    print("   1. Você identifica quais dos checkboxes acima são os 9 corretos")
    print("   2. Anoto as densidades dos 9 corretos")
    print("   3. Calculo o threshold perfeito")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

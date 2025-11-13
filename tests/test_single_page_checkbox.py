#!/usr/bin/env python3
"""
🔬 TESTE DE DETECÇÃO DE CHECKBOX - UMA PÁGINA
Analisa APENAS a página 1 de um PDF específico
Gera imagem DEBUG mostrando o que está sendo detectado
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from pdf2image import convert_from_path

# Diretórios
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_PDF_DIR = PROJECT_ROOT / "inputs" / "pdf"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "checkbox_debug"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def detect_checkboxes_with_debug(image, page_num=1):
    """
    Detecta checkboxes e gera imagem DEBUG
    Retorna: (checkboxes_marcados, imagem_debug)
    """
    # Converter para grayscale
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    
    # Binarização adaptativa para melhor contraste
    binary = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 
        11, 2
    )
    
    # Detectar contornos
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # Imagem debug (colorida)
    debug_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    checkboxes_marcados = []
    all_squares = []
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        
        # Filtrar: deve ser quadrado pequeno (checkbox típico: 10-25px)
        aspect_ratio = w / float(h) if h > 0 else 0
        
        # CRITÉRIOS MAIS RIGOROSOS
        is_square = 0.7 < aspect_ratio < 1.3  # Quase quadrado
        is_small = 8 <= w <= 30 and 8 <= h <= 30  # Tamanho de checkbox
        has_area = 50 < area < 900  # Área razoável
        
        if is_square and is_small and has_area:
            all_squares.append((x, y, w, h))
            
            # Desenhar TODOS os quadrados detectados (AZUL)
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (255, 0, 0), 1)
            
            # Extrair região do checkbox
            roi = binary[y:y+h, x:x+w]
            
            if roi.size == 0:
                continue
            
            # Verificar se está marcado (pixels brancos > threshold)
            white_pixels = np.sum(roi == 255)
            total_pixels = roi.size
            fill_ratio = white_pixels / total_pixels if total_pixels > 0 else 0
            
            # Se >30% preenchido, considerar marcado
            if fill_ratio > 0.30:
                checkboxes_marcados.append({
                    'x': x, 'y': y, 'w': w, 'h': h,
                    'fill_ratio': fill_ratio,
                    'page': page_num
                })
                
                # Desenhar checkbox MARCADO (VERDE)
                cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(debug_img, f"{fill_ratio:.0%}", (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    
    print(f"   📊 Quadrados detectados: {len(all_squares)}")
    print(f"   ✅ Checkboxes marcados: {len(checkboxes_marcados)}")
    
    return checkboxes_marcados, debug_img


def main():
    # Arquivo específico para teste
    pdf_filename = "P_122 52-MF-03B1_2021-03-17.pdf"
    pdf_path = INPUT_PDF_DIR / pdf_filename
    
    if not pdf_path.exists():
        print(f"❌ ERRO: Arquivo não encontrado: {pdf_path}")
        print(f"\n📁 Arquivos disponíveis em {INPUT_PDF_DIR}:")
        for f in sorted(INPUT_PDF_DIR.glob("P122*.pdf"))[:5]:
            print(f"   - {f.name}")
        return
    
    print("=" * 80)
    print(f"🔬 TESTE: {pdf_filename}")
    print(f"📄 Analisando APENAS página 1")
    print("=" * 80)
    
    # Converter página 1 para imagem
    print("🔄 Convertendo página 1 (300 DPI)...")
    images = convert_from_path(str(pdf_path), dpi=300, first_page=1, last_page=1)
    
    if not images:
        print("❌ ERRO: Não foi possível converter o PDF")
        return
    
    print(f"✅ Página convertida: {images[0].size}")
    
    # Detectar checkboxes
    print("\n🔍 Detectando checkboxes...")
    checkboxes, debug_img = detect_checkboxes_with_debug(images[0], page_num=1)
    
    # Salvar imagem debug
    output_image = OUTPUT_DIR / f"{pdf_path.stem}_page1_debug.jpg"
    cv2.imwrite(str(output_image), debug_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    print("\n" + "=" * 80)
    print(f"✅ RESULTADO: {len(checkboxes)} checkboxes marcados detectados")
    print(f"📊 Esperado: 3 checkboxes (contagem manual)")
    print(f"📈 Precisão: {(3/len(checkboxes)*100) if len(checkboxes) > 0 else 0:.1f}%")
    print(f"\n💾 Imagem debug salva: {output_image}")
    print("=" * 80)
    
    # Detalhes dos checkboxes
    if checkboxes:
        print(f"\n📋 CHECKBOXES DETECTADOS:")
        for i, cb in enumerate(checkboxes[:10], 1):
            print(f"   {i}. [{cb['x']},{cb['y']}] {cb['w']}x{cb['h']}px - Preenchimento: {cb['fill_ratio']:.0%}")


if __name__ == "__main__":
    main()

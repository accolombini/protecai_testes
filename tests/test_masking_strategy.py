#!/usr/bin/env python3
"""
TESTE: O que sobra após mascarar texto?
Verificar se checkboxes permanecem ou são apagados.
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import fitz

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PDF_PATH = PROJECT_ROOT / "inputs/pdf/P922 52-MF-01BC.pdf"
OUTPUT_DIR = PROJECT_ROOT / "outputs/checkbox_debug"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def test_masking_page5():
    """
    Teste na página 5 (sabemos que tem 1 checkbox marcado: tU< em Trip Part 1)
    """
    print("\n" + "="*80)
    print("🧪 TESTE DE MASCARAMENTO - PÁGINA 5")
    print("="*80)
    
    doc = fitz.open(str(PDF_PATH))
    page = doc[4]  # Página 5 (índice 4)
    
    # 1. Extrair coordenadas de texto
    print("\n📝 Extraindo coordenadas de texto...")
    text_dict = page.get_text("dict")
    
    text_bboxes = []
    for block in text_dict["blocks"]:
        if block["type"] == 0:  # Texto
            bbox = block["bbox"]
            text_bboxes.append(bbox)
    
    print(f"✅ {len(text_bboxes)} blocos de texto encontrados")
    
    # 2. Converter página para imagem (300 DPI)
    print("\n🖼️  Convertendo página para imagem (300 DPI)...")
    dpi = 300
    mat = fitz.Matrix(dpi/72, dpi/72)
    pixmap = page.get_pixmap(matrix=mat)
    
    img_original = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    img_original_np = np.array(img_original)
    img_original_bgr = cv2.cvtColor(img_original_np, cv2.COLOR_RGB2BGR)
    
    print(f"✅ Imagem: {img_original_bgr.shape[1]}x{img_original_bgr.shape[0]} pixels")
    
    # 3. Criar imagem COM mascaramento de texto
    print("\n🎭 Mascarando regiões de texto...")
    img_masked = img_original_bgr.copy()
    
    # Fator de escala: DPI/72 (coordenadas PDF são em pontos, 72 pontos = 1 polegada)
    scale = dpi / 72
    
    text_count = 0
    for bbox in text_bboxes:
        x0, y0, x1, y1 = bbox
        
        # Converter coordenadas PDF → imagem
        x0_img = int(x0 * scale)
        y0_img = int(y0 * scale)
        x1_img = int(x1 * scale)
        y1_img = int(y1 * scale)
        
        # Pintar região de BRANCO (apagar texto)
        cv2.rectangle(img_masked, (x0_img, y0_img), (x1_img, y1_img), (255, 255, 255), -1)
        text_count += 1
    
    print(f"✅ {text_count} regiões de texto mascaradas")
    
    # 4. Salvar imagens para comparação
    print("\n💾 Salvando imagens...")
    
    cv2.imwrite(str(OUTPUT_DIR / "page5_1_original.png"), img_original_bgr)
    cv2.imwrite(str(OUTPUT_DIR / "page5_2_text_masked.png"), img_masked)
    
    print(f"   ✅ Original: page5_1_original.png")
    print(f"   ✅ Mascarada: page5_2_text_masked.png")
    
    # 5. Detectar checkboxes nas DUAS imagens
    print("\n🔍 Detectando checkboxes nas duas imagens...")
    
    def detect_checkboxes(img, name):
        """Detecta checkboxes em uma imagem."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )
        
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        checkboxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filtros
            if not (10 < w < 40 and 10 < h < 40):
                continue
            
            aspect_ratio = w / float(h)
            if not (0.7 < aspect_ratio < 1.3):
                continue
            
            if cv2.contourArea(contour) < 50:
                continue
            
            checkbox_region = binary[y:y+h, x:x+w]
            density = np.sum(checkbox_region == 255) / (w * h)
            
            checkboxes.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'density': density
            })
        
        return checkboxes
    
    checkboxes_original = detect_checkboxes(img_original_bgr, "ORIGINAL")
    checkboxes_masked = detect_checkboxes(img_masked, "MASCARADA")
    
    print(f"\n📊 RESULTADOS:")
    print(f"   ORIGINAL:  {len(checkboxes_original)} checkboxes detectados")
    print(f"   MASCARADA: {len(checkboxes_masked)} checkboxes detectados")
    
    # Filtrar por densidade (> 37% = marcados)
    marcados_original = [c for c in checkboxes_original if c['density'] > 0.37]
    marcados_masked = [c for c in checkboxes_masked if c['density'] > 0.37]
    
    print(f"\n   MARCADOS (>37%):")
    print(f"   ORIGINAL:  {len(marcados_original)}")
    print(f"   MASCARADA: {len(marcados_masked)}")
    
    # Desenhar checkboxes marcados
    img_original_marked = img_original_bgr.copy()
    img_masked_marked = img_masked.copy()
    
    for cb in marcados_original:
        cv2.rectangle(img_original_marked, 
                     (cb['x'], cb['y']), 
                     (cb['x']+cb['w'], cb['y']+cb['h']), 
                     (0, 255, 0), 2)
    
    for cb in marcados_masked:
        cv2.rectangle(img_masked_marked, 
                     (cb['x'], cb['y']), 
                     (cb['x']+cb['w'], cb['y']+cb['h']), 
                     (0, 255, 0), 2)
    
    cv2.imwrite(str(OUTPUT_DIR / "page5_3_original_detected.png"), img_original_marked)
    cv2.imwrite(str(OUTPUT_DIR / "page5_4_masked_detected.png"), img_masked_marked)
    
    print(f"\n   ✅ Com detecções: page5_3_original_detected.png")
    print(f"   ✅ Com detecções: page5_4_masked_detected.png")
    
    # 6. Conclusão
    print(f"\n{'='*80}")
    print("🎯 CONCLUSÃO")
    print(f"{'='*80}")
    
    reducao = len(checkboxes_original) - len(checkboxes_masked)
    percentual = (reducao / len(checkboxes_original) * 100) if checkboxes_original else 0
    
    print(f"\n✅ Redução de detecções: {reducao} ({percentual:.1f}%)")
    print(f"✅ Checkboxes marcados ANTES: {len(marcados_original)}")
    print(f"✅ Checkboxes marcados DEPOIS: {len(marcados_masked)}")
    
    if len(marcados_masked) == 1:
        print(f"\n🎉 SUCESSO! Detectou exatamente 1 checkbox marcado (esperado)")
    elif len(marcados_masked) < len(marcados_original):
        print(f"\n✅ MELHOROU! Reduziu falsos positivos")
    else:
        print(f"\n⚠️  Ainda há falsos positivos")
    
    print(f"\n📂 Verifique as imagens em: {OUTPUT_DIR}")
    print(f"{'='*80}\n")
    
    doc.close()


if __name__ == "__main__":
    test_masking_page5()

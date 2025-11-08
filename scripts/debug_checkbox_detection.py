#!/usr/bin/env python3
"""
Debug de detecção de checkboxes - testa diferentes thresholds
"""

import cv2
import numpy as np
import fitz
from pathlib import Path

def debug_checkbox_detection():
    """Testa detecção de checkboxes com diferentes thresholds"""
    
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "inputs/pdf/P922 52-MF-01BC.pdf"
    template_path = base_dir / "outputs/checkbox_debug/templates/marcado_average.png"
    
    print("=" * 80)
    print("🔍 DEBUG: DETECÇÃO DE CHECKBOXES")
    print("=" * 80)
    print(f"📄 PDF: {pdf_path.name}")
    print(f"🎯 Template: {template_path.name}")
    print()
    
    if not template_path.exists():
        print(f"❌ Template não encontrado!")
        return
    
    # Carregar template
    template = cv2.imread(str(template_path))
    if template is None:
        print(f"❌ Erro ao carregar template!")
        return
    
    print(f"✅ Template carregado: {template.shape}")
    gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    # Abrir PDF e processar primeira página
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    
    # Converter para imagem
    mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
    pix = page.get_pixmap(matrix=mat)
    
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    
    print(f"✅ Imagem PDF (página 1): {img.shape}")
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Testar diferentes thresholds
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
    
    print()
    print("=" * 80)
    print("🎯 TESTANDO DIFERENTES THRESHOLDS")
    print("=" * 80)
    
    for threshold in thresholds:
        result = cv2.matchTemplate(gray_img, gray_template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        
        num_detections = len(locations[0])
        
        print(f"Threshold {threshold:.1f}: {num_detections:4d} detecções")
        
        if threshold == 0.5 and num_detections > 0:
            # Mostrar as 10 primeiras detecções com threshold 0.5
            print()
            print("  📌 Primeiras 10 detecções (threshold 0.5):")
            for i, (y, x) in enumerate(zip(locations[0][:10], locations[1][:10])):
                confidence = result[y, x]
                print(f"    {i+1:2d}. Posição ({x:4d}, {y:4d}) - Confiança: {confidence:.3f}")
    
    print()
    print("=" * 80)
    print("💡 RECOMENDAÇÃO:")
    print("=" * 80)
    
    # Encontrar threshold ótimo
    for threshold in thresholds:
        result = cv2.matchTemplate(gray_img, gray_template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        num_detections = len(locations[0])
        
        if 5 <= num_detections <= 50:  # Range razoável
            print(f"✅ Threshold {threshold:.1f} parece bom ({num_detections} detecções)")
            print(f"   Use: IntelligentRelayExtractor(..., threshold={threshold})")
            break
    else:
        print("⚠️  Nenhum threshold ideal encontrado!")
        print("   Possíveis problemas:")
        print("   - Template de checkbox pode estar errado")
        print("   - Resolução do template vs PDF incompatível")
        print("   - Formato de checkbox mudou no PDF")
    
    doc.close()
    
    print()
    print("=" * 80)
    print("✅ DEBUG CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    debug_checkbox_detection()

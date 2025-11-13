#!/usr/bin/env python3
"""
TESTE CORRIGIDO: Detecção do INTERIOR do checkbox (sem borda)
+ Correlação com linhas de parâmetros (SEM DUPLICAÇÃO)

CORREÇÕES:
1. Cada checkbox correlaciona APENAS com o parâmetro mais próximo
2. Sem duplicações na lista de correlacionados
3. Debug detalhado para entender as correlações
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import fitz
import re

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PDF_PATH = PROJECT_ROOT / "inputs/pdf/P922 52-MF-01BC.pdf"
OUTPUT_DIR = PROJECT_ROOT / "outputs/checkbox_debug"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def test_interior_detection_fixed():
    """
    Testa detecção do INTERIOR do checkbox (página 4: 5 checkboxes marcados)
    + Filtro de correlação com parâmetros (CORRIGIDO SEM DUPLICAÇÃO)
    """
    print("\n" + "="*80)
    print("🧪 TESTE CORRIGIDO: DETECÇÃO + CORRELAÇÃO (SEM DUPLICAÇÃO)")
    print("="*80)
    print("\nPágina 4: 5 checkboxes marcados (Input 1-5: códigos 0160-0164)")
    print("Estratégia: Interior + correlação 1:1 (checkbox ↔ parâmetro mais próximo)")
    print("="*80)
    
    doc = fitz.open(str(PDF_PATH))
    page = doc[3]  # Página 4
    
    # 1. Extrair parâmetros com coordenadas Y via pdfplumber
    print("\n📝 Extraindo linhas de parâmetros...")
    
    import pdfplumber
    pdf_plumber = pdfplumber.open(str(PDF_PATH))
    page_plumber = pdf_plumber.pages[3]  # Página 4
    
    # Extrair texto com coordenadas
    words = page_plumber.extract_words()
    
    # Detectar linhas de parâmetros (código: descrição)
    param_pattern = re.compile(r'^\d{3,4}[A-Z]?:$')
    
    param_lines_y = []
    for word in words:
        if param_pattern.match(word['text']):
            param_lines_y.append({
                'code': word['text'].rstrip(':'),
                'y': word['top'],
                'text': word['text']
            })
    
    # Ordenar parâmetros por Y (de cima para baixo)
    param_lines_y.sort(key=lambda p: p['y'])
    
    print(f"✅ {len(param_lines_y)} linhas de parâmetros detectadas")
    if param_lines_y:
        print(f"   Primeiras 10: {[p['code'] for p in param_lines_y[:10]]}")
    
    pdf_plumber.close()
    
    # 2. Converter para imagem e mascarar texto
    print("\n📝 Mascarando texto...")
    text_dict = page.get_text("dict")
    
    dpi = 300
    mat = fitz.Matrix(dpi/72, dpi/72)
    pixmap = page.get_pixmap(matrix=mat)
    
    img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    img_np = np.array(img)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    # Mascarar texto
    img_masked = img_bgr.copy()
    scale = dpi / 72
    
    for block in text_dict["blocks"]:
        if block["type"] == 0:
            bbox = block["bbox"]
            x0 = int(bbox[0] * scale)
            y0 = int(bbox[1] * scale)
            x1 = int(bbox[2] * scale)
            y1 = int(bbox[3] * scale)
            cv2.rectangle(img_masked, (x0, y0), (x1, y1), (255, 255, 255), -1)
    
    print(f"✅ Texto mascarado")
    
    # 3. Pré-processar
    print("\n🔧 Pré-processando...")
    gray = cv2.cvtColor(img_masked, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )
    
    # 4. Detectar contornos
    print("🔍 Detectando contornos...")
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # 5. Filtrar e calcular densidade do INTERIOR
    print("\n📊 Analisando checkboxes...")
    
    SHRINK_PIXELS = 3
    THRESHOLD = 0.316  # 31.6%
    MIN_DENSITY = 0.02  # 2%
    
    checkboxes_detected = []
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filtros básicos
        if not (10 < w < 40 and 10 < h < 40):
            continue
        
        aspect_ratio = w / float(h)
        if not (0.7 < aspect_ratio < 1.3):
            continue
        
        if cv2.contourArea(contour) < 50:
            continue
        
        # Calcular densidade do INTERIOR
        x_inner = x + SHRINK_PIXELS
        y_inner = y + SHRINK_PIXELS
        w_inner = w - (SHRINK_PIXELS * 2)
        h_inner = h - (SHRINK_PIXELS * 2)
        
        if w_inner <= 0 or h_inner <= 0:
            continue
        
        interior_region = binary[y_inner:y_inner+h_inner, x_inner:x_inner+w_inner]
        
        if interior_region.size == 0:
            continue
        
        white_pixels = np.sum(interior_region == 255)
        total_pixels = interior_region.size
        density_interior = white_pixels / total_pixels
        
        if density_interior < MIN_DENSITY:
            continue
        
        is_marked = density_interior > THRESHOLD
        
        checkboxes_detected.append({
            'x': x, 'y': y, 'w': w, 'h': h,
            'density_interior': density_interior,
            'is_marked': is_marked,
            'y_pdf': y / scale
        })
    
    print(f"✅ {len(checkboxes_detected)} checkboxes detectados (antes da correlação)")
    
    # 6. CORRELAÇÃO CORRIGIDA: Cada checkbox → parâmetro mais próximo
    print(f"\n🔗 Correlacionando checkboxes com parâmetros...")
    print(f"   Tolerância Y: ±30 pontos PDF")
    
    Y_TOLERANCE = 30
    
    checkboxes_correlated = []
    checkboxes_discarded = []
    
    for cb in checkboxes_detected:
        # Encontrar o parâmetro MAIS PRÓXIMO (menor distância Y)
        closest_param = None
        min_distance = float('inf')
        
        for param in param_lines_y:
            distance = abs(cb['y_pdf'] - param['y'])
            if distance < Y_TOLERANCE and distance < min_distance:
                min_distance = distance
                closest_param = param
        
        if closest_param:
            cb['param_code'] = closest_param['code']
            cb['y_distance'] = min_distance
            checkboxes_correlated.append(cb)
        else:
            checkboxes_discarded.append(cb)
    
    print(f"✅ {len(checkboxes_correlated)} checkboxes correlacionados (1:1)")
    print(f"❌ {len(checkboxes_discarded)} descartados (sem parâmetro próximo)")
    
    # Debug: Mostrar checkboxes descartados
    if checkboxes_discarded:
        print(f"\n🗑️  CHECKBOXES DESCARTADOS (sem parâmetro):")
        for idx, cb in enumerate(checkboxes_discarded, 1):
            print(f"   {idx}. Pos: ({cb['x']}, {cb['y']}) | Y_PDF: {cb['y_pdf']:.1f} | "
                  f"Densidade: {cb['density_interior']*100:.1f}% | "
                  f"Marcado: {'SIM' if cb['is_marked'] else 'NÃO'}")
    
    # 7. Resultados APÓS correlação
    total = len(checkboxes_correlated)
    marcados = sum(1 for cb in checkboxes_correlated if cb['is_marked'])
    vazios = total - marcados
    
    print(f"\n{'='*80}")
    print(f"🎯 RESULTADOS (APÓS CORRELAÇÃO 1:1)")
    print(f"{'='*80}")
    print(f"✅ Total correlacionado: {total} checkboxes")
    print(f"☑  Marcados (>{THRESHOLD*100:.1f}%): {marcados}")
    print(f"☐  Vazios (≤{THRESHOLD*100:.1f}%): {vazios}")
    print()
    
    if total == 5 and marcados == 5:
        print(f"🎉 PERFEITO! Detectou exatamente 5 checkboxes marcados!")
    else:
        print(f"⚠️  Esperado: 5 checkboxes, 5 marcados")
        print(f"   Detectado: {total} checkboxes, {marcados} marcados")
        print(f"   Diferença: {abs(5-total)} checkboxes, {abs(5-marcados)} marcados")
    
    # 8. Estatísticas
    if checkboxes_correlated:
        densities = [cb['density_interior'] for cb in checkboxes_correlated]
        print(f"\n📊 DENSIDADE (INTERIOR):")
        print(f"   Min: {min(densities)*100:.1f}% | Max: {max(densities)*100:.1f}% | Média: {np.mean(densities)*100:.1f}%")
    
    # 9. Desenhar resultados
    print(f"\n💾 Salvando visualização...")
    img_result = img_masked.copy()
    
    # Desenhar correlacionados
    for cb in checkboxes_correlated:
        color = (0, 255, 0) if cb['is_marked'] else (0, 0, 255)
        cv2.rectangle(img_result, 
                     (cb['x'], cb['y']), 
                     (cb['x']+cb['w'], cb['y']+cb['h']), 
                     color, 2)
        
        if 'param_code' in cb:
            cv2.putText(img_result, cb['param_code'],
                       (cb['x'], cb['y']-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Interior
        x_inner = cb['x'] + SHRINK_PIXELS
        y_inner = cb['y'] + SHRINK_PIXELS
        w_inner = cb['w'] - (SHRINK_PIXELS * 2)
        h_inner = cb['h'] - (SHRINK_PIXELS * 2)
        cv2.rectangle(img_result,
                     (x_inner, y_inner),
                     (x_inner+w_inner, y_inner+h_inner),
                     (255, 0, 255), 1)
    
    # Desenhar descartados (em vermelho)
    for cb in checkboxes_discarded:
        cv2.rectangle(img_result,
                     (cb['x'], cb['y']),
                     (cb['x']+cb['w'], cb['y']+cb['h']),
                     (0, 0, 255), 1)  # Vermelho tracejado
        cv2.putText(img_result, "X",
                   (cb['x'], cb['y']-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    
    output_path = OUTPUT_DIR / "page4_interior_fixed.png"
    cv2.imwrite(str(output_path), img_result)
    print(f"   ✅ {output_path}")
    
    # 10. Lista detalhada dos correlacionados
    print(f"\n📋 CHECKBOXES CORRELACIONADOS ({total}):")
    print(f"{'Nº':<4} {'Código':<8} {'Pos (x,y)':<15} {'Tam':<8} {'Dens%':<7} {'Dist_Y':<7} {'Status':<10}")
    print("-" * 70)
    
    for idx, cb in enumerate(checkboxes_correlated, 1):
        status = "☑ MARCADO" if cb['is_marked'] else "☐ VAZIO"
        print(f"{idx:<4} {cb['param_code']:<8} ({cb['x']},{cb['y']})      "
              f"{cb['w']}x{cb['h']:<4} {cb['density_interior']*100:>5.1f}% "
              f"{cb['y_distance']:>5.1f}pt {status:<10}")
    
    print(f"\n{'='*80}")
    print("✅ TESTE CONCLUÍDO!")
    print(f"{'='*80}\n")
    
    doc.close()
    
    return total == 5 and marcados == 5


if __name__ == "__main__":
    success = test_interior_detection_fixed()
    
    if success:
        print("🎉 SUCESSO TOTAL! Algoritmo funcionou perfeitamente!")
        print("   → Próximo passo: Integrar no extractor principal")
    else:
        print("⚠️  Ainda há ajustes necessários.")
        print("   → Analise a tabela detalhada e a imagem gerada")

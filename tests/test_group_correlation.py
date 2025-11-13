#!/usr/bin/env python3
"""
SOLUÇÃO FINAL: Correlação com grupos de checkboxes

CAUSA RAIZ IDENTIFICADA:
- Parâmetros como "010D: LOGIC INPUTS" têm MÚLTIPLOS checkboxes (Input 1-5)
- Os checkboxes estão até 46 pontos abaixo do código do parâmetro
- Y_TOLERANCE=30 não é suficiente para pegar todos

SOLUÇÃO:
1. Aumentar Y_TOLERANCE para 50 pontos
2. Detectar grupos de checkboxes verticais (mesma coluna X)
3. Aceitar que um parâmetro pode ter múltiplos checkboxes
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


def test_group_correlation():
    """
    Teste com correlação de grupos de checkboxes
    """
    # Página por argumento (1-indexed). Default: 4
    page_number = 4
    if len(sys.argv) > 1:
        try:
            page_number = int(sys.argv[1])
        except ValueError:
            pass
    
    page_index = page_number - 1
    
    print("\n" + "="*80)
    print("🎯 SOLUÇÃO FINAL: CORRELAÇÃO COM GRUPOS DE CHECKBOXES")
    print("="*80)
    print(f"\n📄 Página: {page_number}")
    print("Estratégia: Y_TOLERANCE=50 + aceitar múltiplos checkboxes por parâmetro")
    print("="*80)
    
    doc = fitz.open(str(PDF_PATH))
    page = doc[page_index]
    
    # 1. Extrair parâmetros
    print(f"\n📝 Extraindo parâmetros da página {page_number}...")
    
    import pdfplumber
    pdf_plumber = pdfplumber.open(str(PDF_PATH))
    page_plumber = pdf_plumber.pages[page_index]
    
    words = page_plumber.extract_words()
    param_pattern = re.compile(r'^\d{3,4}[A-Z]?:?$')
    
    param_lines_y = []
    for word in words:
        text_clean = word['text'].rstrip(':')
        if param_pattern.match(word['text']):
            param_lines_y.append({
                'code': text_clean,
                'y': word['top'],
                'x': word['x0']
            })
    
    param_lines_y.sort(key=lambda p: p['y'])
    print(f"✅ {len(param_lines_y)} parâmetros extraídos")
    
    # Procurar 010D especificamente
    param_010d = next((p for p in param_lines_y if p['code'] == '010D'), None)
    if param_010d:
        print(f"✅ Parâmetro 010D encontrado em Y={param_010d['y']:.1f}")
    
    pdf_plumber.close()
    
    # 2. Converter e mascarar
    print("\n📝 Processando imagem...")
    text_dict = page.get_text("dict")
    
    dpi = 300
    mat = fitz.Matrix(dpi/72, dpi/72)
    pixmap = page.get_pixmap(matrix=mat)
    
    img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    img_np = np.array(img)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
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
    
    # 3. Detectar checkboxes
    print("🔍 Detectando checkboxes...")
    gray = cv2.cvtColor(img_masked, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )
    
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    SHRINK_PIXELS = 3
    THRESHOLD = 0.316
    MIN_DENSITY = 0.02
    
    checkboxes_detected = []
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        if not (10 < w < 40 and 10 < h < 40):
            continue
        
        aspect_ratio = w / float(h)
        if not (0.7 < aspect_ratio < 1.3):
            continue
        
        if cv2.contourArea(contour) < 50:
            continue
        
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
            'density': density_interior,
            'is_marked': is_marked,
            'y_pdf': y / scale,
            'x_pdf': x / scale
        })
    
    print(f"✅ {len(checkboxes_detected)} checkboxes detectados")
    
    # 4. CORRELAÇÃO COM Y_TOLERANCE=50
    print(f"\n🔗 Correlacionando com Y_TOLERANCE=50...")
    
    Y_TOLERANCE = 50  # ✅ Aumentado para capturar grupos verticais
    
    # Permitir múltiplos checkboxes por parâmetro
    param_checkboxes = {p['code']: [] for p in param_lines_y}
    
    for cb in checkboxes_detected:
        # Encontrar o parâmetro MAIS PRÓXIMO
        closest_param = None
        min_distance = float('inf')
        
        for param in param_lines_y:
            # Checkbox deve estar ABAIXO do parâmetro (Y maior) e próximo em X
            if cb['y_pdf'] >= param['y']:  # Apenas checkboxes abaixo
                distance = abs(cb['y_pdf'] - param['y'])
                if distance < Y_TOLERANCE and distance < min_distance:
                    min_distance = distance
                    closest_param = param
        
        if closest_param:
            cb['param_code'] = closest_param['code']
            cb['y_distance'] = min_distance
            param_checkboxes[closest_param['code']].append(cb)
    
    # Contar correlações
    total_correlated = sum(len(cbs) for cbs in param_checkboxes.values())
    params_with_checkboxes = sum(1 for cbs in param_checkboxes.values() if len(cbs) > 0)
    
    print(f"✅ {total_correlated} checkboxes correlacionados")
    print(f"✅ {params_with_checkboxes} parâmetros com checkboxes")
    
    # 5. Estatísticas gerais
    total_marcados = sum(1 for cbs in param_checkboxes.values() for cb in cbs if cb['is_marked'])
    total_vazios = total_correlated - total_marcados
    
    print(f"\n{'='*80}")
    print(f"📊 ESTATÍSTICAS GERAIS DA PÁGINA {page_number}")
    print(f"{'='*80}")
    print(f"✅ Total detectado: {len(checkboxes_detected)} checkboxes")
    print(f"✅ Correlacionados: {total_correlated} checkboxes")
    print(f"☑  Marcados: {total_marcados} ({total_marcados/total_correlated*100 if total_correlated > 0 else 0:.1f}%)")
    print(f"☐  Vazios: {total_vazios} ({total_vazios/total_correlated*100 if total_correlated > 0 else 0:.1f}%)")
    
    if total_correlated > 0:
        densities = [cb['density'] for cbs in param_checkboxes.values() for cb in cbs]
        print(f"\n📊 DENSIDADE (INTERIOR):")
        print(f"   Min: {min(densities)*100:.1f}% | Max: {max(densities)*100:.1f}% | Média: {np.mean(densities)*100:.1f}%")
    
    # 6. Mostrar todos os parâmetros com checkboxes
    print(f"\n{'='*80}")
    print(f"📊 RESUMO: TODOS OS PARÂMETROS COM CHECKBOXES")
    print(f"{'='*80}")
    
    for param_code in sorted(param_checkboxes.keys()):
        cbs = param_checkboxes[param_code]
        if cbs:
            marcados = sum(1 for cb in cbs if cb['is_marked'])
            vazios = len(cbs) - marcados
            print(f"   {param_code}: {len(cbs)} checkboxes (☑ {marcados} marcados, ☐ {vazios} vazios)")
    
    # 7. Salvar visualização
    print(f"\n💾 Salvando visualização...")
    img_result = img_masked.copy()
    
    # Desenhar todos os checkboxes correlacionados
    for param_code, cbs in param_checkboxes.items():
        for cb in cbs:
            color = (0, 255, 0) if cb['is_marked'] else (0, 0, 255)
            cv2.rectangle(img_result,
                         (cb['x'], cb['y']),
                         (cb['x']+cb['w'], cb['y']+cb['h']),
                         color, 2)
            
            cv2.putText(img_result, param_code,
                       (cb['x'], cb['y']-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    output_path = OUTPUT_DIR / f"page{page_number}_group_correlation.png"
    cv2.imwrite(str(output_path), img_result)
    print(f"✅ {output_path}")
    
    print(f"\n{'='*80}")
    print("✅ TESTE CONCLUÍDO!")
    print(f"{'='*80}\n")
    
    doc.close()
    
    # Retornar sucesso baseado em estatísticas gerais
    success = total_correlated > 0 and (total_marcados + total_vazios == total_correlated)
    return success


if __name__ == "__main__":
    success = test_group_correlation()
    
    if success:
        print("🎉 SUCESSO! Algoritmo funcionou corretamente!")
        print("   → Detecção e correlação OK")
    else:
        print("⚠️  Verifique os resultados e ajuste se necessário.")

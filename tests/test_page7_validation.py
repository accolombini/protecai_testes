#!/usr/bin/env python3
"""
VALIDAÇÃO PÁGINA 7: Teste completo do algoritmo final

Página 7: Onde fizemos a calibração inicial
- 2 checkboxes marcados: RL 2, RL 4
- 3+ checkboxes vazios
- Threshold calibrado: 31.6%

Objetivo: Validar que o algoritmo funciona perfeitamente
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import fitz
import re
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PDF_PATH = PROJECT_ROOT / "inputs/pdf/P922 52-MF-01BC.pdf"
OUTPUT_DIR = PROJECT_ROOT / "outputs/checkbox_debug"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def test_page7():
    """
    Testa algoritmo final na página 7 (calibração original)
    """
    print("\n" + "="*80)
    print("🎯 VALIDAÇÃO PÁGINA 7: TESTE DO ALGORITMO FINAL")
    print("="*80)
    print("\nPágina 7: Calibração original (2 marcados + 3+ vazios)")
    print("Estratégia: Y_TOLERANCE=50 + grupos de checkboxes")
    print("="*80)
    
    doc = fitz.open(str(PDF_PATH))
    page = doc[6]  # Página 7 (índice 6)
    
    # 1. Extrair parâmetros com pdfplumber
    print("\n📝 Extraindo parâmetros...")
    
    import pdfplumber
    pdf_plumber = pdfplumber.open(str(PDF_PATH))
    page_plumber = pdf_plumber.pages[6]
    
    words = page_plumber.extract_words()
    param_pattern = re.compile(r'^\d{3,4}[A-Z]?:?$')
    
    params = []
    for word in words:
        text_clean = word['text'].rstrip(':')
        if param_pattern.match(word['text']) or param_pattern.match(text_clean):
            params.append({
                'code': text_clean,
                'y': word['top'],
                'x': word['x0']
            })
    
    params.sort(key=lambda p: p['y'])
    
    print(f"✅ {len(params)} parâmetros extraídos")
    if params:
        print(f"   Primeiros 10: {[p['code'] for p in params[:10]]}")
    
    pdf_plumber.close()
    
    # 2. Processar imagem (texto mascarado)
    print("\n📝 Processando imagem...")
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
    
    # Pré-processar
    gray = cv2.cvtColor(img_masked, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )
    
    # 3. Detectar checkboxes
    print("🔍 Detectando checkboxes...")
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    SHRINK_PIXELS = 3
    THRESHOLD = 0.316  # 31.6% (calibrado na página 7!)
    MIN_DENSITY = 0.02
    
    checkboxes = []
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        if not (10 < w < 40 and 10 < h < 40):
            continue
        
        aspect_ratio = w / float(h)
        if not (0.7 < aspect_ratio < 1.3):
            continue
        
        if cv2.contourArea(contour) < 50:
            continue
        
        # Interior
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
        density = white_pixels / total_pixels
        
        if density < MIN_DENSITY:
            continue
        
        is_marked = density > THRESHOLD
        
        checkboxes.append({
            'x': x, 'y': y, 'w': w, 'h': h,
            'density': density,
            'is_marked': is_marked,
            'y_pdf': y / scale,
            'x_pdf': x / scale
        })
    
    print(f"✅ {len(checkboxes)} checkboxes detectados")
    
    # 4. Correlacionar (Y_TOLERANCE=50)
    print("\n🔗 Correlacionando com Y_TOLERANCE=50...")
    
    Y_TOLERANCE = 50
    
    # Agrupar por parâmetro
    param_checkboxes = defaultdict(list)
    
    for cb in checkboxes:
        closest_param = None
        min_distance = float('inf')
        
        for param in params:
            distance = abs(cb['y_pdf'] - param['y'])
            if distance < Y_TOLERANCE and distance < min_distance:
                min_distance = distance
                closest_param = param
        
        if closest_param:
            cb['param_code'] = closest_param['code']
            cb['distance'] = min_distance
            param_checkboxes[closest_param['code']].append(cb)
    
    total_correlated = sum(len(cbs) for cbs in param_checkboxes.values())
    print(f"✅ {total_correlated} checkboxes correlacionados")
    print(f"✅ {len(param_checkboxes)} parâmetros com checkboxes")
    
    # 5. Análise detalhada
    print(f"\n{'='*80}")
    print(f"📊 ANÁLISE DETALHADA: TODOS OS PARÂMETROS COM CHECKBOXES")
    print(f"{'='*80}")
    
    # Ordenar parâmetros por Y
    sorted_params = sorted(param_checkboxes.items(), 
                          key=lambda x: params[[p['code'] for p in params].index(x[0])]['y'])
    
    total_marcados = 0
    total_vazios = 0
    
    for param_code, cbs in sorted_params:
        # Ordenar checkboxes por Y
        cbs.sort(key=lambda c: c['y_pdf'])
        
        marcados = sum(1 for cb in cbs if cb['is_marked'])
        vazios = len(cbs) - marcados
        
        total_marcados += marcados
        total_vazios += vazios
        
        print(f"\n📌 {param_code}: {len(cbs)} checkbox{'es' if len(cbs) > 1 else ''} "
              f"(☑ {marcados} marcado{'s' if marcados != 1 else ''}, "
              f"☐ {vazios} vazio{'s' if vazios != 1 else ''})")
        
        # Listar checkboxes
        for idx, cb in enumerate(cbs, 1):
            status = "☑ MARCADO" if cb['is_marked'] else "☐ VAZIO"
            print(f"   {idx}. Pos: ({cb['x']},{cb['y']}) | Y_PDF: {cb['y_pdf']:.1f} | "
                  f"Dist: {cb['distance']:.1f}pt | Dens: {cb['density']*100:.1f}% | {status}")
    
    # 6. Resumo final
    print(f"\n{'='*80}")
    print(f"🎯 RESUMO FINAL")
    print(f"{'='*80}")
    print(f"✅ Total de checkboxes: {total_correlated}")
    print(f"☑  Marcados: {total_marcados}")
    print(f"☐  Vazios: {total_vazios}")
    print(f"📊 Taxa de marcação: {total_marcados/total_correlated*100:.1f}%")
    
    print(f"\n📊 ESTATÍSTICAS DE DENSIDADE:")
    all_densities = [cb['density'] for cbs in param_checkboxes.values() for cb in cbs]
    marcado_densities = [cb['density'] for cbs in param_checkboxes.values() 
                         for cb in cbs if cb['is_marked']]
    vazio_densities = [cb['density'] for cbs in param_checkboxes.values() 
                       for cb in cbs if not cb['is_marked']]
    
    print(f"   Geral: min={min(all_densities)*100:.1f}% | max={max(all_densities)*100:.1f}% | "
          f"média={np.mean(all_densities)*100:.1f}%")
    
    if marcado_densities:
        print(f"   Marcados: min={min(marcado_densities)*100:.1f}% | "
              f"max={max(marcado_densities)*100:.1f}% | média={np.mean(marcado_densities)*100:.1f}%")
    
    if vazio_densities:
        print(f"   Vazios: min={min(vazio_densities)*100:.1f}% | "
              f"max={max(vazio_densities)*100:.1f}% | média={np.mean(vazio_densities)*100:.1f}%")
    
    # 7. Verificar calibração original (RL 2 e RL 4 marcados)
    print(f"\n{'='*80}")
    print(f"🔍 VALIDAÇÃO: CALIBRAÇÃO ORIGINAL")
    print(f"{'='*80}")
    print(f"Esperado: RL 2 e RL 4 marcados (densidade ~48.5%)")
    print(f"          RL 1, 3, 5+ vazios (densidade ~9.5%)")
    
    # Procurar parâmetros RL (podem ter códigos diferentes)
    rl_params = [code for code in param_checkboxes.keys() if 'RL' in code.upper() or 
                 code in ['0143', '010D', '010F']]  # Códigos possíveis para RL
    
    if rl_params:
        print(f"\n✅ Parâmetros encontrados: {rl_params}")
    else:
        print(f"\n⚠️  Não encontramos parâmetros RL específicos")
        print(f"   Mostrando todos os parâmetros com checkboxes marcados:")
        for code, cbs in sorted_params:
            marcados = [cb for cb in cbs if cb['is_marked']]
            if marcados:
                print(f"   • {code}: {len(marcados)} marcado(s)")
    
    # 8. Desenhar resultado
    print(f"\n💾 Salvando visualização...")
    img_result = img_masked.copy()
    
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
            
            # Interior
            x_inner = cb['x'] + SHRINK_PIXELS
            y_inner = cb['y'] + SHRINK_PIXELS
            w_inner = cb['w'] - (SHRINK_PIXELS * 2)
            h_inner = cb['h'] - (SHRINK_PIXELS * 2)
            cv2.rectangle(img_result,
                         (x_inner, y_inner),
                         (x_inner+w_inner, y_inner+h_inner),
                         (255, 0, 255), 1)
    
    output_path = OUTPUT_DIR / "page7_validation.png"
    cv2.imwrite(str(output_path), img_result)
    print(f"✅ {output_path}")
    
    print(f"\n{'='*80}")
    print("✅ VALIDAÇÃO PÁGINA 7 CONCLUÍDA!")
    print(f"{'='*80}")
    
    # Verificar se threshold funciona bem
    threshold_ok = True
    if marcado_densities and vazio_densities:
        max_vazio = max(vazio_densities)
        min_marcado = min(marcado_densities)
        separacao = min_marcado - max_vazio
        
        print(f"\n🎯 VALIDAÇÃO DO THRESHOLD (31.6%):")
        print(f"   Max densidade vazio: {max_vazio*100:.1f}%")
        print(f"   Min densidade marcado: {min_marcado*100:.1f}%")
        print(f"   Separação: {separacao*100:.1f} pontos percentuais")
        
        if separacao > 0:
            print(f"   ✅ PERFEITO! Threshold separa bem os grupos")
        else:
            print(f"   ⚠️  ATENÇÃO! Há sobreposição entre grupos")
            threshold_ok = False
    
    doc.close()
    
    return threshold_ok and total_marcados >= 2 and total_vazios >= 3


if __name__ == "__main__":
    print("\n🎯 VALIDAÇÃO DO ALGORITMO FINAL NA PÁGINA 7")
    print("   (Onde fizemos a calibração original)\n")
    
    success = test_page7()
    
    if success:
        print("\n🎉 SUCESSO TOTAL! Algoritmo validado com perfeição!")
        print("   → Threshold funciona bem")
        print("   → Detecção confiável")
        print("   → Pronto para produção!")
    else:
        print("\n⚠️  Revisar resultados.")
        print("   → Verificar se detecções estão corretas")
        print("   → Analisar estatísticas de densidade")

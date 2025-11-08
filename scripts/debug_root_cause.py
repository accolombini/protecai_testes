#!/usr/bin/env python3
"""
DEBUG FORENSE: INVESTIGAÇÃO DA CAUSA RAIZ

Objetivo: Descobrir por que os checkboxes dos Inputs (0160-0164) não aparecem
Estratégia:
1. Listar TODOS os parâmetros extraídos (com Y)
2. Procurar especificamente por 0160-0164
3. Analisar TODOS os checkboxes detectados (não só correlacionados)
4. Verificar se há mascaramento indevido
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


def debug_root_cause():
    """
    Debug forense para encontrar a causa raiz
    """
    print("\n" + "="*80)
    print("🔬 DEBUG FORENSE: INVESTIGAÇÃO DA CAUSA RAIZ")
    print("="*80)
    print("\nObjetivo: Encontrar os checkboxes dos Inputs 1-5 (códigos 0160-0164)")
    print("="*80)
    
    doc = fitz.open(str(PDF_PATH))
    page = doc[3]  # Página 4
    
    # ===========================================================================
    # PARTE 1: EXTRAIR TODOS OS PARÂMETROS E PROCURAR 0160-0164
    # ===========================================================================
    print("\n" + "="*80)
    print("📝 PARTE 1: EXTRAINDO TODOS OS PARÂMETROS DA PÁGINA")
    print("="*80)
    
    import pdfplumber
    pdf_plumber = pdfplumber.open(str(PDF_PATH))
    page_plumber = pdf_plumber.pages[3]  # Página 4
    
    # Extrair TODAS as palavras com coordenadas
    words = page_plumber.extract_words()
    
    # Procurar parâmetros (padrão: 4 dígitos + letra opcional + :)
    param_pattern = re.compile(r'^\d{3,4}[A-Z]?:?$')
    
    all_params = []
    for word in words:
        # Tentar match com e sem ":"
        text_clean = word['text'].rstrip(':')
        if param_pattern.match(word['text']):
            all_params.append({
                'code': text_clean,
                'y': word['top'],
                'x': word['x0'],
                'text': word['text']
            })
    
    # Ordenar por Y
    all_params.sort(key=lambda p: p['y'])
    
    print(f"\n✅ Total de parâmetros encontrados: {len(all_params)}")
    print(f"\n📋 LISTA COMPLETA DE PARÂMETROS (primeiros 20):")
    print(f"{'#':<4} {'Código':<8} {'X':<8} {'Y':<8}")
    print("-" * 35)
    for idx, p in enumerate(all_params[:20], 1):
        print(f"{idx:<4} {p['code']:<8} {p['x']:<8.1f} {p['y']:<8.1f}")
    
    # PROCURAR ESPECIFICAMENTE POR 0160-0164
    print(f"\n🔍 PROCURANDO CÓDIGOS 0160-0164 (Input 1-5):")
    target_codes = ['0160', '0161', '0162', '0163', '0164']
    found_targets = [p for p in all_params if p['code'] in target_codes]
    
    if found_targets:
        print(f"✅ ENCONTRADOS {len(found_targets)} códigos alvo!")
        for p in found_targets:
            print(f"   • {p['code']} → X={p['x']:.1f}, Y={p['y']:.1f}")
    else:
        print(f"❌ NENHUM código 0160-0164 encontrado na lista de parâmetros!")
        print(f"\n🔍 Procurando no texto bruto da página...")
        
        # Buscar no texto bruto
        text_raw = page_plumber.extract_text()
        for code in target_codes:
            if code in text_raw:
                print(f"   ✅ '{code}' EXISTE no texto bruto da página")
                # Encontrar contexto
                lines = text_raw.split('\n')
                for line in lines:
                    if code in line:
                        print(f"      Linha: {line[:80]}")
                        break
            else:
                print(f"   ❌ '{code}' NÃO existe no texto da página")
    
    pdf_plumber.close()
    
    # ===========================================================================
    # PARTE 2: DETECTAR TODOS OS CHECKBOXES (SEM FILTRO DE CORRELAÇÃO)
    # ===========================================================================
    print(f"\n" + "="*80)
    print("🔍 PARTE 2: DETECTANDO TODOS OS CHECKBOXES (SEM FILTRO)")
    print("="*80)
    
    # Converter para imagem
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
    
    masked_regions = []
    for block in text_dict["blocks"]:
        if block["type"] == 0:
            bbox = block["bbox"]
            x0 = int(bbox[0] * scale)
            y0 = int(bbox[1] * scale)
            x1 = int(bbox[2] * scale)
            y1 = int(bbox[3] * scale)
            cv2.rectangle(img_masked, (x0, y0), (x1, y1), (255, 255, 255), -1)
            masked_regions.append({
                'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                'x0_pdf': bbox[0], 'y0_pdf': bbox[1],
                'x1_pdf': bbox[2], 'y1_pdf': bbox[3]
            })
    
    print(f"✅ {len(masked_regions)} regiões de texto mascaradas")
    
    # Verificar se checkboxes dos Inputs foram mascarados
    if found_targets:
        print(f"\n🔍 Verificando se checkboxes dos Inputs foram mascarados...")
        for target in found_targets:
            # Checkbox deve estar próximo ao código (mesma linha Y, X maior)
            checkbox_x_expected = target['x'] + 50  # ~50 pontos à direita
            checkbox_y_expected = target['y']
            
            # Verificar se há máscara nessa região
            for mask in masked_regions:
                if (mask['x0_pdf'] <= checkbox_x_expected <= mask['x1_pdf'] and
                    mask['y0_pdf'] <= checkbox_y_expected <= mask['y1_pdf']):
                    print(f"   ⚠️  {target['code']}: Checkbox PODE ter sido mascarado!")
                    print(f"      Esperado: X≈{checkbox_x_expected:.1f}, Y≈{checkbox_y_expected:.1f}")
                    print(f"      Máscara: X=[{mask['x0_pdf']:.1f}, {mask['x1_pdf']:.1f}], Y=[{mask['y0_pdf']:.1f}, {mask['y1_pdf']:.1f}]")
                    break
    
    # Pré-processar
    gray = cv2.cvtColor(img_masked, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )
    
    # Detectar contornos
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # Analisar TODOS os contornos que parecem checkboxes
    SHRINK_PIXELS = 3
    MIN_DENSITY = 0.02
    
    all_checkboxes = []
    
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
        
        all_checkboxes.append({
            'x': x, 'y': y, 'w': w, 'h': h,
            'density': density_interior,
            'x_pdf': x / scale,
            'y_pdf': y / scale
        })
    
    print(f"\n✅ {len(all_checkboxes)} checkboxes detectados (ANTES da correlação)")
    
    # Ordenar por Y
    all_checkboxes.sort(key=lambda c: c['y'])
    
    print(f"\n📋 LISTA COMPLETA DE CHECKBOXES DETECTADOS:")
    print(f"{'#':<4} {'Pos (x,y)':<20} {'Tam':<10} {'Dens%':<8} {'X_PDF':<8} {'Y_PDF':<8}")
    print("-" * 70)
    for idx, cb in enumerate(all_checkboxes, 1):
        print(f"{idx:<4} ({cb['x']},{cb['y']})        "
              f"{cb['w']}x{cb['h']:<6} {cb['density']*100:>6.1f}% "
              f"{cb['x_pdf']:<8.1f} {cb['y_pdf']:<8.1f}")
    
    # ===========================================================================
    # PARTE 3: VERIFICAR SE CHECKBOXES DOS INPUTS FORAM DETECTADOS
    # ===========================================================================
    print(f"\n" + "="*80)
    print("🎯 PARTE 3: PROCURANDO CHECKBOXES DOS INPUTS NA LISTA DETECTADA")
    print("="*80)
    
    if found_targets:
        print(f"\n✅ Temos {len(found_targets)} códigos alvo (0160-0164)")
        print(f"   Vamos procurar checkboxes próximos a cada um:")
        print()
        
        for target in found_targets:
            # Checkbox deve estar na mesma linha Y (±5 pontos) e X maior
            checkbox_y_expected = target['y']
            checkbox_x_min = target['x'] + 30  # Pelo menos 30 pontos à direita
            
            # Procurar checkboxes próximos
            nearby = []
            for cb in all_checkboxes:
                if (abs(cb['y_pdf'] - checkbox_y_expected) < 10 and
                    cb['x_pdf'] > checkbox_x_min):
                    nearby.append(cb)
            
            if nearby:
                print(f"   ✅ {target['code']} (X={target['x']:.1f}, Y={target['y']:.1f}):")
                for cb in nearby:
                    print(f"      → Checkbox em X={cb['x_pdf']:.1f}, Y={cb['y_pdf']:.1f} "
                          f"| Densidade={cb['density']*100:.1f}%")
            else:
                print(f"   ❌ {target['code']} (X={target['x']:.1f}, Y={target['y']:.1f}): "
                      f"NENHUM checkbox próximo detectado!")
    else:
        print(f"\n❌ PROBLEMA CRÍTICO: Códigos 0160-0164 NÃO foram extraídos!")
        print(f"   Isso significa que o pdfplumber não está encontrando esses parâmetros.")
        print(f"   Possíveis causas:")
        print(f"   1. Formato diferente (ex: '0160' sem ':' no final)")
        print(f"   2. Texto em fonte/camada diferente (imagem, OCR necessário)")
        print(f"   3. Parâmetros em outra página (verificar se página 4 está correta)")
    
    # ===========================================================================
    # PARTE 4: SALVAR IMAGEM COM TODOS OS CHECKBOXES MARCADOS
    # ===========================================================================
    print(f"\n" + "="*80)
    print("💾 SALVANDO VISUALIZAÇÃO COMPLETA")
    print("="*80)
    
    img_debug = img_masked.copy()
    
    # Desenhar TODOS os checkboxes detectados
    for idx, cb in enumerate(all_checkboxes, 1):
        # Cor baseada na densidade
        if cb['density'] > 0.316:
            color = (0, 255, 0)  # Verde = marcado
        else:
            color = (0, 0, 255)  # Azul = vazio
        
        cv2.rectangle(img_debug,
                     (cb['x'], cb['y']),
                     (cb['x']+cb['w'], cb['y']+cb['h']),
                     color, 2)
        
        # Numerar
        cv2.putText(img_debug, f"#{idx}",
                   (cb['x']-20, cb['y']+15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Marcar posições esperadas dos Inputs (se encontrados)
    if found_targets:
        for target in found_targets:
            x_text = int(target['x'] * scale)
            y_text = int(target['y'] * scale)
            
            # Marcar posição do código
            cv2.circle(img_debug, (x_text, y_text), 5, (255, 0, 255), -1)
            cv2.putText(img_debug, target['code'],
                       (x_text, y_text-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
    
    output_path = OUTPUT_DIR / "page4_forensic_debug.png"
    cv2.imwrite(str(output_path), img_debug)
    print(f"✅ Imagem salva: {output_path}")
    print(f"   • Verde = checkboxes marcados (>31.6%)")
    print(f"   • Azul = checkboxes vazios (≤31.6%)")
    print(f"   • Magenta = posições dos códigos alvo (0160-0164)")
    
    print(f"\n" + "="*80)
    print("✅ DEBUG FORENSE CONCLUÍDO!")
    print("="*80)
    print(f"\n💡 PRÓXIMOS PASSOS:")
    print(f"   1. Abra a imagem gerada: {output_path.name}")
    print(f"   2. Verifique visualmente onde estão os checkboxes dos Inputs")
    print(f"   3. Compare com as posições detectadas (#1, #2, #3...)")
    print(f"   4. Identifique a causa raiz do problema\n")
    
    doc.close()


if __name__ == "__main__":
    debug_root_cause()

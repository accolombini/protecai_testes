#!/usr/bin/env python3
"""
TESTE: Detecção do INTERIOR do checkbox (sem borda)
+ Correlação com linhas de parâmetros
Estratégia: Encolher região + filtrar por proximidade com texto
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


def extract_parameter_lines_page4(page):
    """Extrai linhas de parâmetros da página (código: descrição)"""
    text = page.get_text()
    lines = text.split('\n')
    
    # Regex para detectar linhas de parâmetro (4 dígitos + letra opcional + :)
    param_pattern = re.compile(r'^\s*(\d{3,4}[A-Z]?):\s*(.+)', re.IGNORECASE)
    
    parameters = []
    for line in lines:
        match = param_pattern.match(line)
        if match:
            code = match.group(1)
            description = match.group(2).strip()
            parameters.append({
                'code': code,
                'description': description,
                'line': line
            })
    
    return parameters


def test_interior_detection():
    """
    Testa detecção do INTERIOR do checkbox (página 4: 5 checkboxes marcados)
    + Filtro de correlação com parâmetros
    """
    print("\n" + "="*80)
    print("🧪 TESTE: DETECÇÃO DO INTERIOR + CORRELAÇÃO COM PARÂMETROS")
    print("="*80)
    print("\nPágina 4: 5 checkboxes marcados (Input 1-5)")
    print("Estratégia: Encolher caixa + correlacionar com linhas de parâmetro")
    print("="*80)
    
    doc = fitz.open(str(PDF_PATH))
    page = doc[3]  # Página 4
    
    # 1. Extrair parâmetros (com coordenadas Y via pdfplumber)
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
            # Encontrou código de parâmetro
            param_lines_y.append({
                'code': word['text'].rstrip(':'),
                'y': word['top'],  # Coordenada Y em pontos PDF
                'text': word['text']
            })
    
    print(f"✅ {len(param_lines_y)} linhas de parâmetros detectadas")
    
    if param_lines_y:
        print(f"   Exemplos: {[p['code'] for p in param_lines_y[:5]]}...")
    
    pdf_plumber.close()
    
    # 2. Extrair e mascarar texto
    print("\n📝 Mascarando texto...")
    text_dict = page.get_text("dict")
    
    # 2. Converter para imagem
    print("🖼️  Convertendo página (300 DPI)...")
    dpi = 300
    mat = fitz.Matrix(dpi/72, dpi/72)
    pixmap = page.get_pixmap(matrix=mat)
    
    img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    img_np = np.array(img)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    # 3. Mascarar texto
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
    
    # 4. Pré-processar
    print("\n🔧 Pré-processando...")
    gray = cv2.cvtColor(img_masked, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )
    
    # 5. Detectar contornos
    print("🔍 Detectando contornos...")
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # 6. Filtrar e calcular densidade do INTERIOR
    print("\n📊 Analisando checkboxes...")
    
    SHRINK_PIXELS = 3  # Encolher 3 pixels de cada lado
    THRESHOLD = 0.316  # 31.6% (calibrado)
    
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
        
        # CRÍTICO: Calcular densidade do INTERIOR (sem borda)
        # Encolher região em SHRINK_PIXELS pixels de cada lado
        x_inner = x + SHRINK_PIXELS
        y_inner = y + SHRINK_PIXELS
        w_inner = w - (SHRINK_PIXELS * 2)
        h_inner = h - (SHRINK_PIXELS * 2)
        
        # Verificar se região interna é válida
        if w_inner <= 0 or h_inner <= 0:
            continue
        
        # Extrair APENAS o interior
        interior_region = binary[y_inner:y_inner+h_inner, x_inner:x_inner+w_inner]
        
        if interior_region.size == 0:
            continue
        
        # Calcular densidade do INTERIOR
        white_pixels = np.sum(interior_region == 255)
        total_pixels = interior_region.size
        density_interior = white_pixels / total_pixels
        
        # FILTRO CRÍTICO: Densidade mínima para ser checkbox real
        # Checkboxes vazios têm pelo menos ~2-5% de densidade (borda interna)
        # Abaixo disso são artefatos, intersecções de linhas, ruído
        MIN_DENSITY = 0.02  # 2%
        
        if density_interior < MIN_DENSITY:
            continue  # Não é checkbox, é artefato
        
        # Classificar: marcado se densidade > threshold
        is_marked = density_interior > THRESHOLD
        
        checkboxes_detected.append({
            'x': x, 'y': y, 'w': w, 'h': h,
            'density_interior': density_interior,
            'is_marked': is_marked,
            'y_pdf': y / scale  # Converter Y da imagem para coordenadas PDF
        })
    
    # 7. FILTRO DE CORRELAÇÃO: Manter apenas checkboxes próximos de parâmetros
    print(f"\n🔗 Correlacionando checkboxes com parâmetros...")
    
    Y_TOLERANCE = 30  # ±30 pontos PDF de tolerância (era 10, muito restritivo)
    
    checkboxes_correlated = []
    for cb in checkboxes_detected:
        # Verificar se há algum parâmetro na mesma linha Y
        for param in param_lines_y:
            if abs(cb['y_pdf'] - param['y']) < Y_TOLERANCE:
                cb['param_code'] = param['code']
                checkboxes_correlated.append(cb)
                break
    
    print(f"✅ {len(checkboxes_detected)} checkboxes detectados")
    print(f"✅ {len(checkboxes_correlated)} correlacionados com parâmetros")
    print(f"❌ {len(checkboxes_detected) - len(checkboxes_correlated)} descartados (sem parâmetro)")
    
    # 8. Resultados APÓS correlação
    total = len(checkboxes_correlated)
    marcados = sum(1 for cb in checkboxes_correlated if cb['is_marked'])
    vazios = total - marcados
    
    print(f"\n{'='*80}")
    print(f"🎯 RESULTADOS (APÓS CORRELAÇÃO)")
    print(f"{'='*80}")
    print(f"✅ Total detectado E correlacionado: {total} checkboxes")
    print(f"☑  Marcados (>{THRESHOLD*100:.1f}%): {marcados}")
    print(f"☐  Vazios (≤{THRESHOLD*100:.1f}%): {vazios}")
    print()
    
    if total == 5:
        print(f"✅ PERFEITO! Detectou exatamente 5 checkboxes (esperado)")
    else:
        print(f"⚠️  Esperado: 5 | Detectado: {total} | Diferença: {abs(5-total)}")
    
    if marcados == 5:
        print(f"✅ PERFEITO! Detectou exatamente 5 marcados (esperado)")
    else:
        print(f"⚠️  Esperado: 5 marcados | Detectado: {marcados} | Diferença: {abs(5-marcados)}")
    
    # 9. Estatísticas de densidade
    if checkboxes_correlated:
        densities = [cb['density_interior'] for cb in checkboxes_correlated]
        densities_marcados = [cb['density_interior'] for cb in checkboxes_correlated if cb['is_marked']]
        densities_vazios = [cb['density_interior'] for cb in checkboxes_correlated if not cb['is_marked']]
        
        print(f"\n📊 ESTATÍSTICAS DE DENSIDADE (INTERIOR):")
        print(f"   Geral: min={min(densities)*100:.1f}% | max={max(densities)*100:.1f}% | média={np.mean(densities)*100:.1f}%")
        
        if densities_marcados:
            print(f"   Marcados: min={min(densities_marcados)*100:.1f}% | max={max(densities_marcados)*100:.1f}% | média={np.mean(densities_marcados)*100:.1f}%")
        
        if densities_vazios:
            print(f"   Vazios: min={min(densities_vazios)*100:.1f}% | max={max(densities_vazios)*100:.1f}% | média={np.mean(densities_vazios)*100:.1f}%")
    
    # 10. Desenhar resultados (APENAS correlacionados)
    print(f"\n💾 Salvando visualização...")
    img_result = img_masked.copy()
    
    for cb in checkboxes_correlated:
        color = (0, 255, 0) if cb['is_marked'] else (0, 0, 255)  # Verde=marcado, Azul=vazio
        cv2.rectangle(img_result, 
                     (cb['x'], cb['y']), 
                     (cb['x']+cb['w'], cb['y']+cb['h']), 
                     color, 2)
        
        # Desenhar código do parâmetro
        if 'param_code' in cb:
            cv2.putText(img_result, cb['param_code'],
                       (cb['x'], cb['y']-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Desenhar região interior analisada
        x_inner = cb['x'] + SHRINK_PIXELS
        y_inner = cb['y'] + SHRINK_PIXELS
        w_inner = cb['w'] - (SHRINK_PIXELS * 2)
        h_inner = cb['h'] - (SHRINK_PIXELS * 2)
        cv2.rectangle(img_result,
                     (x_inner, y_inner),
                     (x_inner+w_inner, y_inner+h_inner),
                     (255, 0, 255), 1)  # Magenta para interior
    
    output_path = OUTPUT_DIR / "page4_interior_detection.png"
    cv2.imwrite(str(output_path), img_result)
    print(f"   ✅ {output_path}")
    
    # 11. Lista dos marcados
    if marcados > 0:
        print(f"\n☑  CHECKBOXES MARCADOS DETECTADOS ({marcados}):")
        for idx, cb in enumerate([c for c in checkboxes_correlated if c['is_marked']], 1):
            param = cb.get('param_code', '????')
            print(f"   {idx}. {param} | Pos: ({cb['x']}, {cb['y']}) | "
                  f"Tamanho: {cb['w']}x{cb['h']} | "
                  f"Densidade interior: {cb['density_interior']*100:.1f}%")
    
    print(f"\n{'='*80}")
    print("✅ TESTE CONCLUÍDO!")
    print(f"{'='*80}\n")
    
    doc.close()
    
    return total == 5 and marcados == 5


if __name__ == "__main__":
    success = test_interior_detection()
    
    if success:
        print("🎉 SUCESSO! Algoritmo funcionou perfeitamente!")
        print("   Próximo passo: Implementar no extractor principal")
    else:
        print("⚠️  Ajustes necessários. Analise os resultados e refine os parâmetros.")



if __name__ == "__main__":
    success = test_interior_detection()
    
    if success:
        print("🎉 SUCESSO! Algoritmo funcionou perfeitamente!")
        print("   Próximo passo: Implementar no extractor principal")
    else:
        print("⚠️  Ajustes necessários. Analise os resultados e refine os parâmetros.")

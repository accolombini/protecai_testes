#!/usr/bin/env python3
"""
Teste cego: Detecta checkboxes marcados na página 4 do PDF P122_205-TF-3B_2018-06-13.pdf
Usuário não revelou quantos checkboxes marcados existem
"""

import cv2
import numpy as np
from pathlib import Path
import fitz  # PyMuPDF

# Configurações
PDF_PATH = Path("inputs/pdf/P122_205-TF-3B_2018-06-13.pdf")
PAGE_NUM = 3  # Página 4 (índice 3)
TEMPLATE_MARCADO = Path("outputs/checkbox_debug/templates/marcado_average.png")
OUTPUT_DIR = Path("outputs/checkbox_debug")

# Threshold para matching
MATCH_THRESHOLD = 0.70

def pdf_page_to_image(pdf_path, page_num=0, dpi=300):
    """Converte página do PDF para imagem"""
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]
    
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat)
    
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 1:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    
    doc.close()
    return img

def extract_text_with_positions(pdf_path, page_num=0):
    """Extrai texto com posições"""
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]
    words = page.get_text("words")
    doc.close()
    return words

def find_text_near_checkbox(words, checkbox_x, checkbox_y, max_distance=100):
    """Encontra texto próximo ao checkbox"""
    scale = 72 / 300
    pdf_x = checkbox_x * scale
    pdf_y = checkbox_y * scale
    
    nearest_text = []
    
    for word in words:
        x0, y0, x1, y1, text, *_ = word
        word_x = (x0 + x1) / 2
        word_y = (y0 + y1) / 2
        distance = np.sqrt((word_x - pdf_x)**2 + (word_y - pdf_y)**2)
        
        if distance < max_distance * scale:
            nearest_text.append({
                'text': text,
                'distance': distance,
                'x': word_x,
                'y': word_y
            })
    
    nearest_text.sort(key=lambda x: x['distance'])
    return nearest_text

def template_matching(image, template, threshold):
    """Realiza template matching"""
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    result = cv2.matchTemplate(gray_image, gray_template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)
    
    h, w = gray_template.shape
    
    matches = []
    for pt in zip(*locations[::-1]):
        matches.append({
            'x': pt[0] + w//2,
            'y': pt[1] + h//2,
            'confidence': result[pt[1], pt[0]],
            'bbox': (pt[0], pt[1], pt[0]+w, pt[1]+h)
        })
    
    if matches:
        matches = non_max_suppression(matches, min_distance=10)
    
    return matches

def non_max_suppression(matches, min_distance=10):
    """Remove matches duplicados"""
    if not matches:
        return []
    
    matches = sorted(matches, key=lambda x: x['confidence'], reverse=True)
    
    filtered = []
    for match in matches:
        is_far = True
        for existing in filtered:
            dist = np.sqrt((match['x'] - existing['x'])**2 + 
                          (match['y'] - existing['y'])**2)
            if dist < min_distance:
                is_far = False
                break
        
        if is_far:
            filtered.append(match)
    
    return filtered

def main():
    print("=" * 80)
    print("🔬 TESTE CEGO - Página 4 de P122_205-TF-3B_2018-06-13.pdf")
    print("=" * 80)
    print()
    
    if not PDF_PATH.exists():
        print(f"❌ ERRO: PDF não encontrado: {PDF_PATH}")
        return
    
    if not TEMPLATE_MARCADO.exists():
        print(f"❌ ERRO: Template não encontrado: {TEMPLATE_MARCADO}")
        return
    
    # Converter página
    print(f"🔄 Convertendo página {PAGE_NUM + 1} para imagem (300 DPI)...")
    image = pdf_page_to_image(PDF_PATH, page_num=PAGE_NUM, dpi=300)
    print(f"   ✅ Imagem: {image.shape[1]}x{image.shape[0]} pixels")
    
    # Extrair texto
    print("📝 Extraindo texto...")
    words = extract_text_with_positions(PDF_PATH, page_num=PAGE_NUM)
    print(f"   ✅ {len(words)} palavras extraídas")
    print()
    
    # Carregar template
    template_marcado = cv2.imread(str(TEMPLATE_MARCADO))
    print(f"📂 Template carregado: {template_marcado.shape[1]}x{template_marcado.shape[0]}")
    print()
    
    # Detectar checkboxes
    print("=" * 80)
    print("🔴 DETECTANDO CHECKBOXES MARCADOS")
    print("=" * 80)
    print(f"Threshold: {MATCH_THRESHOLD}")
    print()
    
    matches = template_matching(image, template_marcado, MATCH_THRESHOLD)
    print(f"✅ {len(matches)} checkboxes MARCADOS detectados")
    print()
    
    # Mostrar resultados
    if matches:
        print("📋 CHECKBOXES MARCADOS ENCONTRADOS:")
        print("-" * 80)
        
        for i, match in enumerate(matches, 1):
            nearby_text = find_text_near_checkbox(words, match['x'], match['y'], max_distance=150)
            text_description = " ".join([t['text'] for t in nearby_text[:5]]) if nearby_text else "?"
            
            print(f"   {i:2d}. ({match['x']:4d}, {match['y']:4d}) "
                  f"[confiança: {match['confidence']:.3f}] "
                  f"→ {text_description}")
    
    print()
    
    # Criar imagem anotada
    print("🎨 Criando imagem anotada...")
    annotated = image.copy()
    
    for match in matches:
        x1, y1, x2, y2 = match['bbox']
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(annotated, "X", (match['x']-10, match['y']+5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    output_path = OUTPUT_DIR / "page4_detection_result.png"
    cv2.imwrite(str(output_path), annotated)
    print(f"✅ Imagem salva: {output_path}")
    
    print()
    print("=" * 80)
    print("📊 RESULTADO FINAL")
    print("=" * 80)
    print(f"✅ Total de checkboxes MARCADOS detectados: {len(matches)}")
    print()
    print("❓ Usuário NÃO revelou o número esperado - aguardando validação manual")
    print("=" * 80)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Testa detecção de checkboxes usando template matching
Usa os templates extraídos para encontrar todos os checkboxes marcados na página
"""

import cv2
import numpy as np
from pathlib import Path
import fitz  # PyMuPDF

# Configurações
PDF_PATH = Path("inputs/pdf/P_122 52-MF-03B1_2021-03-17.pdf")
TEMPLATE_MARCADO = Path("outputs/checkbox_debug/templates/marcado_average.png")
TEMPLATE_VAZIO = Path("outputs/checkbox_debug/templates/vazio_average.png")
OUTPUT_DIR = Path("outputs/checkbox_debug")

# Threshold para matching (0.0 a 1.0, quanto maior mais restritivo)
MATCH_THRESHOLD = 0.70

def pdf_page_to_image(pdf_path, page_num=0, dpi=300):
    """Converte página do PDF para imagem"""
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]
    
    # Renderizar em alta resolução
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat)
    
    # Converter para numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    
    # Converter RGBA para BGR se necessário
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
    
    # Extrair palavras com coordenadas
    words = page.get_text("words")  # [(x0, y0, x1, y1, "word", block_no, line_no, word_no)]
    
    doc.close()
    return words

def find_text_near_checkbox(words, checkbox_x, checkbox_y, max_distance=100):
    """Encontra texto próximo ao checkbox"""
    # Converter coordenadas de imagem (DPI 300) para coordenadas PDF (72 DPI)
    scale = 72 / 300
    pdf_x = checkbox_x * scale
    pdf_y = checkbox_y * scale
    
    nearest_text = []
    
    for word in words:
        x0, y0, x1, y1, text, *_ = word
        
        # Centro da palavra
        word_x = (x0 + x1) / 2
        word_y = (y0 + y1) / 2
        
        # Distância do checkbox
        distance = np.sqrt((word_x - pdf_x)**2 + (word_y - pdf_y)**2)
        
        if distance < max_distance * scale:
            nearest_text.append({
                'text': text,
                'distance': distance,
                'x': word_x,
                'y': word_y
            })
    
    # Ordenar por distância
    nearest_text.sort(key=lambda x: x['distance'])
    
    return nearest_text

def template_matching(image, template, threshold):
    """Realiza template matching e retorna coordenadas dos matches"""
    # Converter para escala de cinza
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    # Template matching
    result = cv2.matchTemplate(gray_image, gray_template, cv2.TM_CCOEFF_NORMED)
    
    # Encontrar matches acima do threshold
    locations = np.where(result >= threshold)
    
    # Obter dimensões do template
    h, w = gray_template.shape
    
    # Lista de matches (com non-maximum suppression)
    matches = []
    for pt in zip(*locations[::-1]):  # Switch x and y
        matches.append({
            'x': pt[0] + w//2,  # Centro do template
            'y': pt[1] + h//2,
            'confidence': result[pt[1], pt[0]],
            'bbox': (pt[0], pt[1], pt[0]+w, pt[1]+h)
        })
    
    # Non-maximum suppression (remover duplicatas próximas)
    if matches:
        matches = non_max_suppression(matches, min_distance=10)
    
    return matches

def non_max_suppression(matches, min_distance=10):
    """Remove matches duplicados próximos"""
    if not matches:
        return []
    
    # Ordenar por confidence
    matches = sorted(matches, key=lambda x: x['confidence'], reverse=True)
    
    filtered = []
    for match in matches:
        # Verificar se está longe de todos os já filtrados
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
    print("🔬 TESTE DE TEMPLATE MATCHING - Detecção de Checkboxes")
    print("=" * 80)
    print()
    
    # Verificar arquivos
    if not PDF_PATH.exists():
        print(f"❌ ERRO: PDF não encontrado: {PDF_PATH}")
        return
    
    if not TEMPLATE_MARCADO.exists():
        print(f"❌ ERRO: Template marcado não encontrado: {TEMPLATE_MARCADO}")
        print("   Execute primeiro: python scripts/extract_checkbox_templates.py")
        return
    
    if not TEMPLATE_VAZIO.exists():
        print(f"❌ ERRO: Template vazio não encontrado: {TEMPLATE_VAZIO}")
        return
    
    # Converter página 1 para imagem
    print("🔄 Convertendo PDF página 1 para imagem (300 DPI)...")
    image = pdf_page_to_image(PDF_PATH, page_num=0, dpi=300)
    print(f"   ✅ Imagem: {image.shape[1]}x{image.shape[0]} pixels")
    
    # Extrair texto com posições
    print("📝 Extraindo texto com coordenadas...")
    words = extract_text_with_positions(PDF_PATH, page_num=0)
    print(f"   ✅ {len(words)} palavras extraídas")
    print()
    
    # Carregar templates
    print("📂 Carregando templates...")
    template_marcado = cv2.imread(str(TEMPLATE_MARCADO))
    template_vazio = cv2.imread(str(TEMPLATE_VAZIO))
    print(f"   ✅ Template MARCADO: {template_marcado.shape[1]}x{template_marcado.shape[0]}")
    print(f"   ✅ Template VAZIO: {template_vazio.shape[1]}x{template_vazio.shape[0]}")
    print()
    
    # Detectar checkboxes MARCADOS
    print("=" * 80)
    print("🔴 DETECTANDO CHECKBOXES MARCADOS")
    print("=" * 80)
    print(f"Threshold: {MATCH_THRESHOLD}")
    print()
    
    matches_marcados = template_matching(image, template_marcado, MATCH_THRESHOLD)
    print(f"✅ {len(matches_marcados)} checkboxes MARCADOS detectados")
    print()
    
    # Mostrar resultados
    if matches_marcados:
        print("📋 CHECKBOXES MARCADOS ENCONTRADOS:")
        print("-" * 80)
        
        for i, match in enumerate(matches_marcados, 1):
            # Encontrar texto próximo
            nearby_text = find_text_near_checkbox(words, match['x'], match['y'], max_distance=150)
            
            text_description = " ".join([t['text'] for t in nearby_text[:5]]) if nearby_text else "?"
            
            print(f"   {i:2d}. ({match['x']:4d}, {match['y']:4d}) "
                  f"[confiança: {match['confidence']:.3f}] "
                  f"→ {text_description}")
    
    print()
    
    # Criar imagem anotada
    print("🎨 Criando imagem anotada...")
    annotated = image.copy()
    
    # Desenhar checkboxes marcados (verde)
    for match in matches_marcados:
        x1, y1, x2, y2 = match['bbox']
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(annotated, "✓", (match['x']-10, match['y']+5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Salvar
    output_path = OUTPUT_DIR / "detection_result.png"
    cv2.imwrite(str(output_path), annotated)
    print(f"✅ Imagem salva: {output_path}")
    
    print()
    print("=" * 80)
    print("📊 RESUMO FINAL")
    print("=" * 80)
    print(f"✅ Checkboxes MARCADOS detectados: {len(matches_marcados)}")
    print(f"🎯 Esperado (contagem manual): 3")
    print()
    
    if len(matches_marcados) == 3:
        print("🎉 SUCESSO! Detecção 100% precisa!")
    elif len(matches_marcados) < 3:
        print("⚠️  Detectados MENOS que esperado - ajustar threshold para BAIXO")
        print(f"   Sugestão: threshold = {MATCH_THRESHOLD - 0.05:.2f}")
    else:
        print("⚠️  Detectados MAIS que esperado - ajustar threshold para CIMA")
        print(f"   Sugestão: threshold = {MATCH_THRESHOLD + 0.05:.2f}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()

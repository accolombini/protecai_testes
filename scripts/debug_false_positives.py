#!/usr/bin/env python3
"""
DEBUG: Visualizar TODOS os "checkboxes" detectados para identificar falsos positivos.
VIDAS EM RISCO - Precisão 100% necessária.
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from pdf2image import convert_from_path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PDF_PATH = PROJECT_ROOT / "inputs/pdf/P922 52-MF-01BC.pdf"
OUTPUT_DIR = PROJECT_ROOT / "outputs/checkbox_debug"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Parâmetros do detector (MESMO do extrator)
CHECKBOX_MIN_SIZE = 10
CHECKBOX_MAX_SIZE = 40
CHECKBOX_ASPECT_RATIO_MIN = 0.7
CHECKBOX_ASPECT_RATIO_MAX = 1.3
CHECKBOX_MIN_AREA = 50
CHECKBOX_MARKED_THRESHOLD = 0.37

def detect_and_visualize_checkboxes(page_num=1):
    """
    Detecta checkboxes em uma página e cria imagem com TODOS marcados.
    """
    print(f"\n{'='*80}")
    print(f"🔍 DETECTANDO CHECKBOXES - PÁGINA {page_num}")
    print(f"{'='*80}\n")
    
    # Converter página
    print(f"📄 Convertendo página {page_num}...")
    images = convert_from_path(str(PDF_PATH), dpi=300, first_page=page_num, last_page=page_num)
    
    if not images:
        print(f"❌ Erro ao converter página {page_num}")
        return
    
    # Preparar imagem
    img = np.array(images[0])
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    img_display = img_bgr.copy()
    
    # Pré-processar
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )
    
    # Detectar contornos
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    detected = []
    
    for idx, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filtro 1: Tamanho
        if not (CHECKBOX_MIN_SIZE < w < CHECKBOX_MAX_SIZE and 
                CHECKBOX_MIN_SIZE < h < CHECKBOX_MAX_SIZE):
            continue
        
        # Filtro 2: Aspect ratio
        aspect_ratio = w / float(h)
        if not (CHECKBOX_ASPECT_RATIO_MIN < aspect_ratio < CHECKBOX_ASPECT_RATIO_MAX):
            continue
        
        # Filtro 3: Área mínima
        if cv2.contourArea(contour) < CHECKBOX_MIN_AREA:
            continue
        
        # Calcular densidade
        checkbox_region = binary[y:y+h, x:x+w]
        white_pixels = np.sum(checkbox_region == 255)
        total_pixels = w * h
        density = white_pixels / total_pixels
        
        # Determinar status
        is_marked = density > CHECKBOX_MARKED_THRESHOLD
        
        detected.append({
            'x': x, 'y': y, 'w': w, 'h': h,
            'density': density,
            'is_marked': is_marked,
            'aspect_ratio': aspect_ratio,
            'area': cv2.contourArea(contour)
        })
    
    print(f"✅ Total detectado: {len(detected)} checkboxes")
    print(f"   - Marcados (>37%): {sum(1 for d in detected if d['is_marked'])}")
    print(f"   - Vazios (≤37%): {sum(1 for d in detected if not d['is_marked'])}")
    
    # Visualizar TODOS
    for idx, cb in enumerate(detected):
        # Cor: Verde=marcado, Vermelho=vazio
        color = (0, 255, 0) if cb['is_marked'] else (0, 0, 255)
        
        # Desenhar retângulo
        cv2.rectangle(img_display, 
                     (cb['x'], cb['y']), 
                     (cb['x']+cb['w'], cb['y']+cb['h']), 
                     color, 2)
        
        # Label com densidade
        label = f"{cb['density']*100:.0f}%"
        cv2.putText(img_display, label, 
                   (cb['x'], cb['y']-5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Salvar imagem
    output_path = OUTPUT_DIR / f"page{page_num}_all_detections.png"
    cv2.imwrite(str(output_path), img_display)
    print(f"\n💾 Imagem salva: {output_path}")
    
    # Estatísticas de densidade
    densities = [cb['density'] for cb in detected]
    if densities:
        print(f"\n📊 ESTATÍSTICAS DE DENSIDADE:")
        print(f"   Mínima: {min(densities)*100:.1f}%")
        print(f"   Máxima: {max(densities)*100:.1f}%")
        print(f"   Média: {np.mean(densities)*100:.1f}%")
        print(f"   Mediana: {np.median(densities)*100:.1f}%")
    
    # Top 10 mais densos (prováveis marcados)
    print(f"\n🔝 TOP 10 MAIS DENSOS (prováveis marcados reais):")
    sorted_by_density = sorted(detected, key=lambda x: x['density'], reverse=True)[:10]
    for idx, cb in enumerate(sorted_by_density, 1):
        status = "☑" if cb['is_marked'] else "☐"
        print(f"   {idx}. {status} Densidade: {cb['density']*100:.1f}% | "
              f"Pos: ({cb['x']}, {cb['y']}) | Tamanho: {cb['w']}x{cb['h']}")
    
    # Bottom 10 menos densos (prováveis vazios/ruído)
    print(f"\n🔻 BOTTOM 10 MENOS DENSOS (prováveis falsos positivos):")
    sorted_by_density_asc = sorted(detected, key=lambda x: x['density'])[:10]
    for idx, cb in enumerate(sorted_by_density_asc, 1):
        status = "☑" if cb['is_marked'] else "☐"
        print(f"   {idx}. {status} Densidade: {cb['density']*100:.1f}% | "
              f"Pos: ({cb['x']}, {cb['y']}) | Tamanho: {cb['w']}x{cb['h']}")
    
    # Análise de range problemático (33-40%)
    problematic = [cb for cb in detected if 0.33 <= cb['density'] <= 0.40]
    if problematic:
        print(f"\n⚠️  ZONA PROBLEMÁTICA (33-40%): {len(problematic)} detecções")
        print(f"   Estes estão na 'zona cinzenta' entre vazio e marcado:")
        for cb in problematic[:5]:
            status = "☑" if cb['is_marked'] else "☐"
            print(f"   • {status} {cb['density']*100:.1f}% | "
                  f"Pos: ({cb['x']}, {cb['y']}) | {cb['w']}x{cb['h']}")
    
    return detected


def main():
    print("\n" + "="*80)
    print("🔍 DEBUG DE FALSOS POSITIVOS - P922")
    print("   Identificar o que está sendo detectado como checkbox")
    print("="*80)
    
    if not PDF_PATH.exists():
        print(f"❌ PDF não encontrado: {PDF_PATH}")
        return
    
    # Analisar página 1 (onde estão os inputs marcados)
    print("\n📄 ANALISANDO PÁGINA 1...")
    detect_and_visualize_checkboxes(page_num=1)
    
    # Analisar página 4 (inputs 1-5)
    print("\n📄 ANALISANDO PÁGINA 4...")
    detect_and_visualize_checkboxes(page_num=4)
    
    print(f"\n{'='*80}")
    print(f"✅ DEBUG CONCLUÍDO!")
    print(f"{'='*80}")
    print(f"\n📂 Verifique as imagens em: {OUTPUT_DIR}")
    print(f"\nPróximos passos:")
    print(f"1. Abra as imagens e identifique VISUALMENTE os falsos positivos")
    print(f"2. Verifique se são: letras (O,D,B), bordas de tabela, ícones")
    print(f"3. Ajustaremos os filtros para eliminar esses padrões")
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()

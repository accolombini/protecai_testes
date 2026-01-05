#!/usr/bin/env python3
"""
CALIBRAÇÃO INTERATIVA DE CHECKBOXES - P922
Baseado no algoritmo que JÁ FUNCIONOU anteriormente.

Você clica nos checkboxes REAIS (marcados e vazios) e eu calculo o threshold perfeito.
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from pdf2image import convert_from_path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configurações
PDF_PATH = PROJECT_ROOT / "inputs/pdf/P922 52-MF-01BC.pdf"
OUTPUT_DIR = PROJECT_ROOT / "outputs/checkbox_calibration"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Armazenar cliques do usuário
clicked_checkboxes = {'marcados': [], 'vazios': []}
current_image = None
current_binary = None
current_page = None
window_name = None


def preprocess_image(image_bgr):
    """
    Pré-processamento para melhorar detecção de checkboxes.
    IGUAL ao que fizemos antes!
    """
    # Converter para escala de cinza
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    
    # Aplicar blur para reduzir ruído
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # Threshold adaptativo (melhor para PDFs)
    binary = cv2.adaptiveThreshold(
        blurred, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 
        11, 2
    )
    
    return gray, binary


def find_checkbox_at_position(x, y, binary, tolerance=20):
    """
    Encontra checkbox próximo à posição clicada.
    """
    # Buscar contornos na região próxima
    region = binary[max(0, y-tolerance):min(binary.shape[0], y+tolerance),
                    max(0, x-tolerance):min(binary.shape[1], x+tolerance)]
    
    contours, _ = cv2.findContours(region, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    best_checkbox = None
    min_distance = float('inf')
    
    for contour in contours:
        cx, cy, w, h = cv2.boundingRect(contour)
        
        # Ajustar coordenadas para imagem completa
        cx += max(0, x-tolerance)
        cy += max(0, y-tolerance)
        
        # Critérios: quadrado, tamanho razoável
        aspect_ratio = w / h if h > 0 else 0
        area = cv2.contourArea(contour)
        
        if (0.7 <= aspect_ratio <= 1.3 and  # Quase quadrado
            8 <= w <= 30 and 8 <= h <= 30 and  # Tamanho de checkbox
            area > 30):  # Área mínima
            
            # Calcular distância do clique
            center_x = cx + w // 2
            center_y = cy + h // 2
            distance = np.sqrt((center_x - x)**2 + (center_y - y)**2)
            
            if distance < min_distance:
                min_distance = distance
                
                # Extrair região do checkbox e calcular densidade
                checkbox_region = binary[cy:cy+h, cx:cx+w]
                white_pixels = np.sum(checkbox_region == 255)
                total_pixels = w * h
                density = white_pixels / total_pixels if total_pixels > 0 else 0
                
                best_checkbox = {
                    'x': cx, 'y': cy, 'w': w, 'h': h,
                    'density': density,
                    'distance': distance
                }
    
    return best_checkbox


def mouse_callback(event, x, y, flags, param):
    """Callback para cliques do mouse (OpenCV)."""
    global clicked_checkboxes, current_binary, current_image, window_name
    
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    
    # Encontrar checkbox próximo
    checkbox = find_checkbox_at_position(x, y, current_binary, tolerance=30)
    
    if checkbox is None:
        print(f"❌ Nenhum checkbox encontrado próximo a ({x}, {y})")
        return
    
    # Perguntar ao usuário se é marcado ou vazio
    print(f"\n📍 Checkbox detectado em ({checkbox['x']}, {checkbox['y']}) - Densidade: {checkbox['density']:.3f}")
    print("   [M] Marcado (☑)  [V] Vazio (☐)  [I] Ignorar")
    
    choice = input("   Sua escolha: ").strip().upper()
    
    if choice == 'M':
        clicked_checkboxes['marcados'].append(checkbox)
        color = (0, 255, 0)  # Verde
        label = 'MARCADO'
        print(f"   ✅ Adicionado como MARCADO (total: {len(clicked_checkboxes['marcados'])})")
    elif choice == 'V':
        clicked_checkboxes['vazios'].append(checkbox)
        color = (0, 0, 255)  # Vermelho
        label = 'VAZIO'
        print(f"   ✅ Adicionado como VAZIO (total: {len(clicked_checkboxes['vazios'])})")
    else:
        print("   ⏭️  Ignorado")
        return
    
    # Desenhar retângulo na imagem
    cv2.rectangle(
        current_image, 
        (checkbox['x'], checkbox['y']), 
        (checkbox['x'] + checkbox['w'], checkbox['y'] + checkbox['h']),
        color, 2
    )
    
    # Adicionar label
    cv2.putText(
        current_image,
        label,
        (checkbox['x'], checkbox['y'] - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        color,
        1
    )
    
    # Atualizar janela
    cv2.imshow(window_name, current_image)


def calibrate_page(page_num):
    """
    Calibração interativa de uma página.
    """
    global current_image, current_binary, current_page, window_name, clicked_checkboxes
    
    clicked_checkboxes = {'marcados': [], 'vazios': []}
    current_page = page_num
    window_name = f'P922 - Página {page_num} (Clique nos checkboxes - ESC para sair)'
    
    print(f"\n{'='*80}")
    print(f"📄 CALIBRANDO PÁGINA {page_num}")
    print(f"{'='*80}")
    
    # Converter página para imagem
    print("🔄 Convertendo PDF para imagem (alta resolução)...")
    images = convert_from_path(str(PDF_PATH), dpi=300, first_page=page_num, last_page=page_num)
    
    if not images:
        print(f"❌ Erro ao converter página {page_num}")
        return None
    
    img = np.array(images[0])
    # Converter RGB para BGR (OpenCV)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    current_image = img.copy()
    
    # Pré-processar
    print("🔧 Pré-processando imagem...")
    gray, binary = preprocess_image(img)
    current_binary = binary
    
    # Mostrar imagem interativa
    print("\n" + "="*80)
    print("🖱️  INSTRUÇÕES:")
    print("   1. CLIQUE em cada checkbox que você vê (marcados ☑ e vazios ☐)")
    print("   2. Quando clicar, digite [M] para marcado ou [V] para vazio")
    print("   3. Pressione ESC quando terminar")
    print("="*80 + "\n")
    
    # Redimensionar se muito grande
    height, width = current_image.shape[:2]
    max_height = 900
    if height > max_height:
        scale = max_height / height
        new_width = int(width * scale)
        display_image = cv2.resize(current_image, (new_width, max_height))
    else:
        display_image = current_image
    
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, mouse_callback)
    
    while True:
        cv2.imshow(window_name, display_image)
        key = cv2.waitKey(1) & 0xFF
        
        if key == 27:  # ESC
            break
    
    cv2.destroyAllWindows()
    
    # Calcular estatísticas
    if clicked_checkboxes['marcados'] or clicked_checkboxes['vazios']:
        print(f"\n{'='*80}")
        print(f"📊 RESULTADOS DA CALIBRAÇÃO - Página {page_num}")
        print(f"{'='*80}")
        
        # Checkboxes marcados
        if clicked_checkboxes['marcados']:
            densities_m = [cb['density'] for cb in clicked_checkboxes['marcados']]
            print(f"\n☑️  CHECKBOXES MARCADOS ({len(densities_m)}):")
            print(f"   Densidade média: {np.mean(densities_m):.3f}")
            print(f"   Densidade mín:   {np.min(densities_m):.3f}")
            print(f"   Densidade máx:   {np.max(densities_m):.3f}")
            print(f"   Desvio padrão:   {np.std(densities_m):.3f}")
        
        # Checkboxes vazios
        if clicked_checkboxes['vazios']:
            densities_v = [cb['density'] for cb in clicked_checkboxes['vazios']]
            print(f"\n☐  CHECKBOXES VAZIOS ({len(densities_v)}):")
            print(f"   Densidade média: {np.mean(densities_v):.3f}")
            print(f"   Densidade mín:   {np.min(densities_v):.3f}")
            print(f"   Densidade máx:   {np.max(densities_v):.3f}")
            print(f"   Desvio padrão:   {np.std(densities_v):.3f}")
        
        # Calcular threshold ótimo
        if clicked_checkboxes['marcados'] and clicked_checkboxes['vazios']:
            max_vazio = max(cb['density'] for cb in clicked_checkboxes['vazios'])
            min_marcado = min(cb['density'] for cb in clicked_checkboxes['marcados'])
            
            threshold_otimo = (max_vazio + min_marcado) / 2
            
            print(f"\n{'='*80}")
            print(f"🎯 THRESHOLD ÓTIMO CALCULADO")
            print(f"{'='*80}")
            print(f"   Densidade máxima (vazio):    {max_vazio:.3f}")
            print(f"   Densidade mínima (marcado):  {min_marcado:.3f}")
            print(f"   ➡️  THRESHOLD RECOMENDADO:    {threshold_otimo:.3f}")
            print(f"{'='*80}")
            
            return {
                'page': page_num,
                'marcados': clicked_checkboxes['marcados'],
                'vazios': clicked_checkboxes['vazios'],
                'threshold': threshold_otimo
            }
    
    return None


def main():
    """Calibração interativa."""
    
    print("\n" + "="*80)
    print("🎯 CALIBRAÇÃO INTERATIVA DE CHECKBOXES - P922")
    print("   Baseado no algoritmo que JÁ FUNCIONOU!")
    print("="*80)
    
    if not PDF_PATH.exists():
        print(f"❌ PDF não encontrado: {PDF_PATH}")
        return
    
    # Páginas para calibrar (onde você viu os 9 checkboxes marcados)
    pages_to_calibrate = [1, 4, 5, 7]
    
    results = []
    
    for page_num in pages_to_calibrate:
        result = calibrate_page(page_num)
        if result:
            results.append(result)
        
        # Perguntar se quer continuar
        if page_num != pages_to_calibrate[-1]:
            print(f"\n{'='*80}")
            continuar = input(f"Calibrar próxima página ({pages_to_calibrate[pages_to_calibrate.index(page_num)+1]})? [S/n]: ").strip().upper()
            if continuar == 'N':
                break
    
    # Resumo final
    if results:
        print(f"\n{'#'*80}")
        print(f"📊 RESUMO FINAL DA CALIBRAÇÃO")
        print(f"{'#'*80}")
        
        all_thresholds = [r['threshold'] for r in results]
        avg_threshold = np.mean(all_thresholds)
        
        print(f"\n🎯 THRESHOLD MÉDIO (todas as páginas): {avg_threshold:.3f}")
        print(f"\nThresholds individuais por página:")
        for r in results:
            print(f"   Página {r['page']}: {r['threshold']:.3f}")
        
        print(f"\n{'='*80}")
        print(f"✅ Use este threshold no extrator: {avg_threshold:.3f}")
        print(f"{'='*80}")


if __name__ == "__main__":
    main()

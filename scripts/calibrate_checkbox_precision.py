#!/usr/bin/env python3
"""
CALIBRAÇÃO PRECISA DE CHECKBOXES - P922
Algoritmo correto: você clica, eu calculo densidade exata.

VIDAS EM RISCO - Precisão 100% necessária.
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

# Estado global
densities = {'marcados': [], 'vazios': []}
mode = 'marcados'  # 'marcados' ou 'vazios'
image_display = None
binary_image = None
clicks_count = {'marcados': 0, 'vazios': 0}


def calculate_density_at_click(x, y, binary, box_size=15):
    """
    Calcula densidade EXATA no ponto clicado.
    Extrai uma caixa de box_size x box_size pixels centrada no clique.
    """
    half_size = box_size // 2
    
    # Coordenadas da caixa
    y1 = max(0, y - half_size)
    y2 = min(binary.shape[0], y + half_size)
    x1 = max(0, x - half_size)
    x2 = min(binary.shape[1], x + half_size)
    
    # Extrair região
    checkbox_region = binary[y1:y2, x1:x2]
    
    if checkbox_region.size == 0:
        return None, None
    
    # Calcular densidade (pixels brancos / total pixels)
    white_pixels = np.sum(checkbox_region == 255)
    total_pixels = checkbox_region.size
    density = white_pixels / total_pixels
    
    return density, (x1, y1, x2-x1, y2-y1)


def mouse_callback(event, x, y, flags, param):
    """Callback para cliques - calcula densidade na hora."""
    global densities, mode, image_display, binary_image, clicks_count
    
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    
    # Calcular densidade no ponto clicado
    density, bbox = calculate_density_at_click(x, y, binary_image, box_size=15)
    
    if density is None:
        print(f"❌ Erro ao calcular densidade em ({x}, {y})")
        return
    
    # Adicionar à lista apropriada
    densities[mode].append(density)
    clicks_count[mode] += 1
    
    # Escolher cor baseado no modo
    if mode == 'marcados':
        color = (0, 255, 0)  # Verde
        label = f"M{clicks_count['marcados']}"
    else:
        color = (0, 0, 255)  # Vermelho
        label = f"V{clicks_count['vazios']}"
    
    # Desenhar na imagem
    bx, by, bw, bh = bbox
    cv2.rectangle(image_display, (bx, by), (bx+bw, by+bh), color, 2)
    cv2.circle(image_display, (x, y), 3, color, -1)
    cv2.putText(image_display, label, (bx, by-5), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    # Mostrar informação
    print(f"{'='*80}")
    print(f"✅ Clique #{clicks_count[mode]} - Modo: {mode.upper()}")
    print(f"   Posição: ({x}, {y})")
    print(f"   Densidade: {density:.4f} ({density*100:.1f}%)")
    print(f"   Total {mode}: {len(densities[mode])} cliques")
    print(f"{'='*80}")
    
    # Atualizar display
    cv2.imshow('Calibração P922', image_display)


def calibrate_page_7():
    """
    Calibração da página 7 (2 marcados + vários vazios).
    """
    global image_display, binary_image, mode, densities, clicks_count
    
    print(f"\n{'#'*80}")
    print(f"🎯 CALIBRAÇÃO PRECISA - PÁGINA 7")
    print(f"{'#'*80}")
    print(f"Página 7 tem:")
    print(f"  ☑ 2 checkboxes MARCADOS (RL 2, RL 4)")
    print(f"  ☐ Vários checkboxes VAZIOS (RL 3, 5, 6, 7, 8...)")
    print(f"{'#'*80}\n")
    
    # Converter página 7
    print("🔄 Convertendo página 7 para imagem (DPI 300)...")
    images = convert_from_path(str(PDF_PATH), dpi=300, first_page=7, last_page=7)
    
    if not images:
        print("❌ Erro ao converter página 7")
        return None
    
    # Preparar imagem
    img = np.array(images[0])
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    image_display = img_bgr.copy()
    
    # Pré-processar para binário
    print("🔧 Pré-processando imagem...")
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary_image = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )
    
    print(f"✅ Imagem preparada: {img_bgr.shape[1]}x{img_bgr.shape[0]} pixels")
    
    # Salvar para referência
    output_path = OUTPUT_DIR / "pagina7_original.png"
    cv2.imwrite(str(output_path), img_bgr)
    print(f"💾 Imagem salva: {output_path}")
    
    # Instruções
    print(f"\n{'='*80}")
    print(f"📋 INSTRUÇÕES:")
    print(f"{'='*80}")
    print(f"1. Janela vai abrir mostrando a PÁGINA 7")
    print(f"2. CLIQUE nos 2 checkboxes MARCADOS (☑) - RL 2 e RL 4")
    print(f"3. Pressione 'M' (SEM ENTER) para mudar para vazios")
    print(f"4. CLIQUE em 3 checkboxes VAZIOS (☐) - Ex: RL 3, 5, 6")
    print(f"5. Após 3 vazios, o threshold é calculado AUTOMATICAMENTE")
    print(f"6. Ou pressione 'C' para calcular antes")
    print(f"7. ESC para sair")
    print(f"{'='*80}\n")
    
    input("Pressione ENTER para abrir a janela...")
    
    # Abrir janela
    cv2.namedWindow('Calibração P922', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Calibração P922', 1200, 1600)
    cv2.setMouseCallback('Calibração P922', mouse_callback)
    
    print(f"\n🟢 MODO: CLICANDO EM CHECKBOXES MARCADOS (☑)")
    print(f"   Clique nos 2 checkboxes marcados (RL 2, RL 4)...")
    
    while True:
        cv2.imshow('Calibração P922', image_display)
        key = cv2.waitKey(1) & 0xFF
        
        if key == 27:  # ESC
            print("\n⏹️  Calibração cancelada")
            break
        
        elif key == ord('m') or key == ord('M'):
            # Mudar para modo vazios (SEM ENTER!)
            if mode == 'marcados':
                mode = 'vazios'
                print(f"\n{'='*80}")
                print(f"🔴 MODO: CLICANDO EM CHECKBOXES VAZIOS (☐)")
                print(f"   Clique em 3 checkboxes vazios (Ex: RL 3, 5, 6)...")
                print(f"{'='*80}\n")
        
        elif key == ord('c') or key == ord('C'):
            # Calcular threshold
            cv2.destroyAllWindows()
            return calculate_threshold()
        
        # Auto-calcular após 3 vazios
        if mode == 'vazios' and len(densities['vazios']) >= 3:
            print(f"\n✅ 3 checkboxes vazios clicados - Calculando automaticamente...")
            cv2.destroyAllWindows()
            return calculate_threshold()
    
    cv2.destroyAllWindows()
    return None


def calculate_threshold():
    """
    Calcula threshold ótimo baseado nos cliques.
    """
    print(f"\n{'#'*80}")
    print(f"📊 CALCULANDO THRESHOLD ÓTIMO")
    print(f"{'#'*80}\n")
    
    if not densities['marcados']:
        print("❌ Nenhum checkbox MARCADO foi clicado!")
        return None
    
    if not densities['vazios']:
        print("❌ Nenhum checkbox VAZIO foi clicado!")
        return None
    
    # Estatísticas dos marcados
    marcados_arr = np.array(densities['marcados'])
    print(f"☑️  CHECKBOXES MARCADOS ({len(marcados_arr)} cliques):")
    print(f"   Densidade média:  {np.mean(marcados_arr):.4f} ({np.mean(marcados_arr)*100:.1f}%)")
    print(f"   Densidade mínima: {np.min(marcados_arr):.4f} ({np.min(marcados_arr)*100:.1f}%)")
    print(f"   Densidade máxima: {np.max(marcados_arr):.4f} ({np.max(marcados_arr)*100:.1f}%)")
    print(f"   Desvio padrão:    {np.std(marcados_arr):.4f}")
    print()
    
    # Estatísticas dos vazios
    vazios_arr = np.array(densities['vazios'])
    print(f"☐  CHECKBOXES VAZIOS ({len(vazios_arr)} cliques):")
    print(f"   Densidade média:  {np.mean(vazios_arr):.4f} ({np.mean(vazios_arr)*100:.1f}%)")
    print(f"   Densidade mínima: {np.min(vazios_arr):.4f} ({np.min(vazios_arr)*100:.1f}%)")
    print(f"   Densidade máxima: {np.max(vazios_arr):.4f} ({np.max(vazios_arr)*100:.1f}%)")
    print(f"   Desvio padrão:    {np.std(vazios_arr):.4f}")
    print()
    
    # Calcular threshold ótimo (média entre max vazio e min marcado)
    max_vazio = np.max(vazios_arr)
    min_marcado = np.min(marcados_arr)
    
    threshold_otimo = (max_vazio + min_marcado) / 2
    
    # Separação entre grupos
    separacao = min_marcado - max_vazio
    
    print(f"{'='*80}")
    print(f"🎯 RESULTADO FINAL")
    print(f"{'='*80}")
    print(f"   Densidade máxima (vazio):    {max_vazio:.4f} ({max_vazio*100:.1f}%)")
    print(f"   Densidade mínima (marcado):  {min_marcado:.4f} ({min_marcado*100:.1f}%)")
    print(f"   Separação entre grupos:      {separacao:.4f} ({separacao*100:.1f}%)")
    print(f"")
    print(f"   ➡️  THRESHOLD ÓTIMO: {threshold_otimo:.4f} ({threshold_otimo*100:.1f}%)")
    print(f"{'='*80}")
    
    if separacao < 0:
        print(f"\n⚠️  AVISO: Há SOBREPOSIÇÃO entre grupos!")
        print(f"   Alguns checkboxes vazios têm densidade maior que marcados.")
        print(f"   Precisão pode ser comprometida!")
    else:
        print(f"\n✅ SEPARAÇÃO PERFEITA! Precisão esperada: 100%")
    
    # Salvar resultado
    result_path = OUTPUT_DIR / "threshold_calibrado.txt"
    with open(result_path, 'w') as f:
        f.write(f"CALIBRAÇÃO DE THRESHOLD - P922 Página 7\n")
        f.write(f"{'='*80}\n\n")
        f.write(f"CHECKBOXES MARCADOS: {len(marcados_arr)} cliques\n")
        f.write(f"  Média: {np.mean(marcados_arr):.4f}\n")
        f.write(f"  Mín:   {np.min(marcados_arr):.4f}\n")
        f.write(f"  Máx:   {np.max(marcados_arr):.4f}\n\n")
        f.write(f"CHECKBOXES VAZIOS: {len(vazios_arr)} cliques\n")
        f.write(f"  Média: {np.mean(vazios_arr):.4f}\n")
        f.write(f"  Mín:   {np.min(vazios_arr):.4f}\n")
        f.write(f"  Máx:   {np.max(vazios_arr):.4f}\n\n")
        f.write(f"THRESHOLD ÓTIMO: {threshold_otimo:.4f}\n")
        f.write(f"SEPARAÇÃO: {separacao:.4f}\n")
    
    print(f"\n💾 Resultado salvo: {result_path}")
    
    return threshold_otimo


def main():
    """Execução principal."""
    
    print("\n" + "="*80)
    print("🎯 CALIBRAÇÃO PRECISA DE CHECKBOXES - P922")
    print("   VIDAS EM RISCO - Precisão 100% necessária")
    print("="*80)
    
    if not PDF_PATH.exists():
        print(f"❌ PDF não encontrado: {PDF_PATH}")
        return
    
    # Calibrar página 7
    threshold = calibrate_page_7()
    
    if threshold:
        print(f"\n{'#'*80}")
        print(f"✅ CALIBRAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"{'#'*80}")
        print(f"\n🎯 Use este threshold no extrator: {threshold:.4f}")
        print(f"\nArquivo: src/precise_parameter_extractor.py")
        print(f"Linha: CHECKBOX_MARKED_THRESHOLD = {threshold:.4f}")
        print(f"\n{'#'*80}\n")


if __name__ == "__main__":
    main()

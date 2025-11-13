q#!/usr/bin/env python3
"""
Script interativo para coletar coordenadas de checkboxes via cliques do mouse
Permite identificar checkboxes marcados vs vazios para criar template matching
"""

import cv2
import numpy as np
from pathlib import Path
from PIL import Image

# Configurações
IMAGE_PATH = Path("outputs/checkbox_debug/P_122 52-MF-03B1_2021-03-17_page1_grid.png")
OUTPUT_FILE = Path("outputs/checkbox_debug/checkbox_coordinates.txt")

# Armazenar coordenadas
clicked_points = []
current_label = "marcado"  # Começa coletando checkboxes marcados

def mouse_callback(event, x, y, flags, param):
    """Callback para capturar cliques do mouse"""
    global clicked_points, current_label
    
    if event == cv2.EVENT_LBUTTONDOWN:
        # Clique esquerdo: adicionar ponto
        clicked_points.append({
            'x': x,
            'y': y,
            'tipo': current_label
        })
        
        print(f"\n✅ Checkpoint {len(clicked_points)}: ({x}, {y}) - Tipo: {current_label}")
        
        # Desenhar círculo vermelho no ponto clicado
        cv2.circle(param['image'], (x, y), 10, (0, 0, 255), 2)
        cv2.putText(param['image'], f"{len(clicked_points)}", (x+15, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.imshow('Clique nos Checkboxes', param['image'])

def main():
    global current_label
    
    print("=" * 80)
    print("🎯 COLETOR INTERATIVO DE COORDENADAS DE CHECKBOXES")
    print("=" * 80)
    print()
    print("INSTRUÇÕES:")
    print("  1. Primeiro, clique em 3 checkboxes MARCADOS (☒)")
    print("  2. Pressione 'M' para mudar para checkboxes VAZIOS")
    print("  3. Clique em 3 checkboxes VAZIOS (☐)")
    print("  4. Pressione 'S' para salvar e sair")
    print("  5. Pressione 'Q' para sair sem salvar")
    print()
    print(f"📂 Imagem: {IMAGE_PATH}")
    print("=" * 80)
    print()
    
    if not IMAGE_PATH.exists():
        print(f"❌ ERRO: Imagem não encontrada: {IMAGE_PATH}")
        print("   Execute primeiro: python scripts/extract_page_as_image.py")
        return
    
    # Carregar imagem
    print("🔄 Carregando imagem...")
    image = cv2.imread(str(IMAGE_PATH))
    if image is None:
        print(f"❌ ERRO: Não foi possível carregar a imagem")
        return
    
    # Criar cópia para desenhar
    display_image = image.copy()
    
    print(f"✅ Imagem carregada: {image.shape[1]}x{image.shape[0]} pixels")
    print()
    print("👉 MODO ATUAL: Checkboxes MARCADOS (☒)")
    print()
    
    # Criar janela e configurar callback
    cv2.namedWindow('Clique nos Checkboxes', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Clique nos Checkboxes', 1200, 1600)
    cv2.setMouseCallback('Clique nos Checkboxes', mouse_callback, {'image': display_image})
    
    # Mostrar imagem
    cv2.imshow('Clique nos Checkboxes', display_image)
    
    # Loop principal
    while True:
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            print("\n❌ Saindo sem salvar...")
            break
        
        elif key == ord('m') or key == ord('M'):
            # Mudar modo
            if current_label == "marcado":
                current_label = "vazio"
                print("\n" + "=" * 80)
                print("👉 MODO MUDOU: Agora clique em checkboxes VAZIOS (☐)")
                print("=" * 80)
            else:
                current_label = "marcado"
                print("\n" + "=" * 80)
                print("👉 MODO MUDOU: Agora clique em checkboxes MARCADOS (☒)")
                print("=" * 80)
        
        elif key == ord('s') or key == ord('S'):
            # Salvar e sair
            if len(clicked_points) == 0:
                print("\n⚠️  Nenhum ponto coletado!")
                continue
            
            print("\n" + "=" * 80)
            print("💾 SALVANDO COORDENADAS...")
            print("=" * 80)
            
            # Salvar arquivo de texto
            OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write("# Coordenadas de Checkboxes Coletadas\n")
                f.write(f"# Imagem: {IMAGE_PATH}\n")
                f.write(f"# Total de pontos: {len(clicked_points)}\n\n")
                
                marcados = [p for p in clicked_points if p['tipo'] == 'marcado']
                vazios = [p for p in clicked_points if p['tipo'] == 'vazio']
                
                f.write(f"# Checkboxes MARCADOS: {len(marcados)}\n")
                for i, p in enumerate(marcados, 1):
                    f.write(f"marcado_{i}: x={p['x']}, y={p['y']}\n")
                
                f.write(f"\n# Checkboxes VAZIOS: {len(vazios)}\n")
                for i, p in enumerate(vazios, 1):
                    f.write(f"vazio_{i}: x={p['x']}, y={p['y']}\n")
            
            print(f"✅ Coordenadas salvas: {OUTPUT_FILE}")
            print()
            print("📊 RESUMO:")
            print(f"   • Checkboxes MARCADOS: {len(marcados)}")
            print(f"   • Checkboxes VAZIOS: {len(vazios)}")
            print(f"   • Total: {len(clicked_points)}")
            
            # Salvar imagem anotada
            annotated_path = OUTPUT_FILE.parent / "page1_annotated.png"
            cv2.imwrite(str(annotated_path), display_image)
            print(f"✅ Imagem anotada salva: {annotated_path}")
            
            print("\n🎯 PRÓXIMO PASSO:")
            print("   Execute: python scripts/extract_checkbox_templates.py")
            print("=" * 80)
            break
    
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Extrai templates de checkboxes marcados e vazios a partir das coordenadas coletadas
Cria detector por template matching com 100% de precisão
"""

import cv2
import numpy as np
from pathlib import Path

# Configurações
IMAGE_PATH = Path("outputs/checkbox_debug/P_122 52-MF-03B1_2021-03-17_page1_grid.png")
COORDS_FILE = Path("outputs/checkbox_debug/checkbox_coordinates.txt")
OUTPUT_DIR = Path("outputs/checkbox_debug/templates")

# Tamanho da região ao redor do checkbox (pixels)
TEMPLATE_SIZE = 30  # Vai extrair 30x30 pixels ao redor do ponto clicado

def load_coordinates(coords_file):
    """Carrega coordenadas do arquivo"""
    coords = {'marcado': [], 'vazio': []}
    
    with open(coords_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse: marcado_1: x=430, y=1309
            parts = line.split(':')
            if len(parts) != 2:
                continue
            
            tipo_num = parts[0].strip()
            coords_str = parts[1].strip()
            
            # Extrair tipo
            if tipo_num.startswith('marcado'):
                tipo = 'marcado'
            elif tipo_num.startswith('vazio'):
                tipo = 'vazio'
            else:
                continue
            
            # Extrair x, y
            x_part = coords_str.split(',')[0].strip()
            y_part = coords_str.split(',')[1].strip()
            
            x = int(x_part.split('=')[1])
            y = int(y_part.split('=')[1])
            
            coords[tipo].append({'x': x, 'y': y})
    
    return coords

def extract_template(image, x, y, size):
    """Extrai template ao redor de um ponto"""
    half_size = size // 2
    
    # Calcular limites
    x1 = max(0, x - half_size)
    y1 = max(0, y - half_size)
    x2 = min(image.shape[1], x + half_size)
    y2 = min(image.shape[0], y + half_size)
    
    # Extrair região
    template = image[y1:y2, x1:x2].copy()
    
    return template, (x1, y1, x2, y2)

def analyze_template(template, tipo):
    """Analisa características do template"""
    # Converter para escala de cinza
    gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    # Calcular estatísticas
    mean_intensity = np.mean(gray)
    std_intensity = np.std(gray)
    min_intensity = np.min(gray)
    max_intensity = np.max(gray)
    
    # Detectar bordas
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
    
    print(f"   📊 Análise do template {tipo}:")
    print(f"      • Intensidade média: {mean_intensity:.1f}")
    print(f"      • Desvio padrão: {std_intensity:.1f}")
    print(f"      • Min/Max: {min_intensity}/{max_intensity}")
    print(f"      • Densidade de bordas: {edge_density:.3f}")
    
    return {
        'mean': mean_intensity,
        'std': std_intensity,
        'min': min_intensity,
        'max': max_intensity,
        'edge_density': edge_density
    }

def main():
    print("=" * 80)
    print("🔬 EXTRATOR DE TEMPLATES DE CHECKBOXES")
    print("=" * 80)
    print()
    
    # Verificar arquivos
    if not IMAGE_PATH.exists():
        print(f"❌ ERRO: Imagem não encontrada: {IMAGE_PATH}")
        return
    
    if not COORDS_FILE.exists():
        print(f"❌ ERRO: Arquivo de coordenadas não encontrado: {COORDS_FILE}")
        print("   Execute primeiro: python scripts/interactive_checkbox_clicker.py")
        return
    
    # Carregar coordenadas
    print("📋 Carregando coordenadas...")
    coords = load_coordinates(COORDS_FILE)
    print(f"   ✅ Checkboxes MARCADOS: {len(coords['marcado'])}")
    print(f"   ✅ Checkboxes VAZIOS: {len(coords['vazio'])}")
    print()
    
    # Carregar imagem
    print("🔄 Carregando imagem...")
    image = cv2.imread(str(IMAGE_PATH))
    if image is None:
        print(f"❌ ERRO: Não foi possível carregar a imagem")
        return
    print(f"   ✅ Imagem: {image.shape[1]}x{image.shape[0]} pixels")
    print()
    
    # Criar diretório de saída
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Extrair templates de checkboxes MARCADOS
    print("=" * 80)
    print("🔴 EXTRAINDO TEMPLATES DE CHECKBOXES MARCADOS")
    print("=" * 80)
    
    marcado_templates = []
    marcado_stats = []
    
    for i, coord in enumerate(coords['marcado'], 1):
        print(f"\n📍 Checkbox marcado #{i}: ({coord['x']}, {coord['y']})")
        
        template, bounds = extract_template(image, coord['x'], coord['y'], TEMPLATE_SIZE)
        stats = analyze_template(template, f"marcado_{i}")
        
        # Salvar template
        template_path = OUTPUT_DIR / f"marcado_{i}.png"
        cv2.imwrite(str(template_path), template)
        print(f"   💾 Salvo: {template_path}")
        
        marcado_templates.append(template)
        marcado_stats.append(stats)
    
    # Extrair templates de checkboxes VAZIOS
    print("\n" + "=" * 80)
    print("⚪ EXTRAINDO TEMPLATES DE CHECKBOXES VAZIOS")
    print("=" * 80)
    
    vazio_templates = []
    vazio_stats = []
    
    for i, coord in enumerate(coords['vazio'], 1):
        print(f"\n📍 Checkbox vazio #{i}: ({coord['x']}, {coord['y']})")
        
        template, bounds = extract_template(image, coord['x'], coord['y'], TEMPLATE_SIZE)
        stats = analyze_template(template, f"vazio_{i}")
        
        # Salvar template
        template_path = OUTPUT_DIR / f"vazio_{i}.png"
        cv2.imwrite(str(template_path), template)
        print(f"   💾 Salvo: {template_path}")
        
        vazio_templates.append(template)
        vazio_stats.append(stats)
    
    # Criar template médio (average)
    print("\n" + "=" * 80)
    print("📊 CRIANDO TEMPLATES MÉDIOS")
    print("=" * 80)
    
    if marcado_templates:
        # Template médio de marcados
        marcado_avg = np.mean(marcado_templates, axis=0).astype(np.uint8)
        marcado_avg_path = OUTPUT_DIR / "marcado_average.png"
        cv2.imwrite(str(marcado_avg_path), marcado_avg)
        print(f"✅ Template médio MARCADO: {marcado_avg_path}")
        
        print(f"   📊 Estatísticas médias MARCADO:")
        print(f"      • Intensidade: {np.mean([s['mean'] for s in marcado_stats]):.1f}")
        print(f"      • Densidade de bordas: {np.mean([s['edge_density'] for s in marcado_stats]):.3f}")
    
    if vazio_templates:
        # Template médio de vazios
        vazio_avg = np.mean(vazio_templates, axis=0).astype(np.uint8)
        vazio_avg_path = OUTPUT_DIR / "vazio_average.png"
        cv2.imwrite(str(vazio_avg_path), vazio_avg)
        print(f"✅ Template médio VAZIO: {vazio_avg_path}")
        
        print(f"   📊 Estatísticas médias VAZIO:")
        print(f"      • Intensidade: {np.mean([s['mean'] for s in vazio_stats]):.1f}")
        print(f"      • Densidade de bordas: {np.mean([s['edge_density'] for s in vazio_stats]):.3f}")
    
    # Análise comparativa
    print("\n" + "=" * 80)
    print("🔍 ANÁLISE COMPARATIVA")
    print("=" * 80)
    
    if marcado_stats and vazio_stats:
        marcado_mean_intensity = np.mean([s['mean'] for s in marcado_stats])
        vazio_mean_intensity = np.mean([s['mean'] for s in vazio_stats])
        
        marcado_edge = np.mean([s['edge_density'] for s in marcado_stats])
        vazio_edge = np.mean([s['edge_density'] for s in vazio_stats])
        
        print(f"📊 DIFERENÇAS DETECTADAS:")
        print(f"   • Intensidade: MARCADO={marcado_mean_intensity:.1f} vs VAZIO={vazio_mean_intensity:.1f}")
        print(f"     → Diferença: {abs(marcado_mean_intensity - vazio_mean_intensity):.1f}")
        print(f"   • Densidade de bordas: MARCADO={marcado_edge:.3f} vs VAZIO={vazio_edge:.3f}")
        print(f"     → Diferença: {abs(marcado_edge - vazio_edge):.3f}")
        
        if marcado_edge > vazio_edge * 1.5:
            print(f"\n✅ PADRÃO IDENTIFICADO: Checkboxes MARCADOS têm MAIS bordas/linhas")
            print(f"   → Usar densidade de bordas como critério principal")
        elif abs(marcado_mean_intensity - vazio_mean_intensity) > 20:
            print(f"\n✅ PADRÃO IDENTIFICADO: Checkboxes têm intensidades diferentes")
            print(f"   → Usar intensidade como critério principal")
        else:
            print(f"\n⚠️  ATENÇÃO: Diferenças pequenas - pode precisar ajuste fino")
    
    print("\n" + "=" * 80)
    print("✅ TEMPLATES EXTRAÍDOS COM SUCESSO!")
    print("=" * 80)
    print(f"\n📂 Templates salvos em: {OUTPUT_DIR}/")
    print(f"\n🎯 PRÓXIMO PASSO:")
    print(f"   Execute: python scripts/test_template_matching.py")
    print("=" * 80)

if __name__ == "__main__":
    main()

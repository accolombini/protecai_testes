#!/usr/bin/env python3
"""
Script para criar imagem anotada da página 1 do PDF
Facilita identificação de coordenadas de checkboxes
"""

from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Configurações
PDF_PATH = Path("inputs/pdf/P_122 52-MF-03B1_2021-03-17.pdf")
OUTPUT_DIR = Path("outputs/checkbox_debug")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("🔬 GERADOR DE IMAGEM ANOTADA PARA IDENTIFICAÇÃO DE COORDENADAS")
print("=" * 80)

# Converter página 1 para imagem de alta resolução
print(f"\n📄 Convertendo página 1 de {PDF_PATH.name}...")
images = convert_from_path(str(PDF_PATH), dpi=300, first_page=1, last_page=1)
img = images[0]

print(f"✅ Imagem gerada: {img.size[0]}x{img.size[1]} pixels")

# Criar versão com grid para facilitar localização
draw = ImageDraw.Draw(img)

# Desenhar grid a cada 100 pixels
width, height = img.size
grid_spacing = 100

# Linhas verticais
for x in range(0, width, grid_spacing):
    draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)
    # Numerar
    draw.text((x + 5, 10), str(x), fill=(255, 0, 0))

# Linhas horizontais
for y in range(0, height, grid_spacing):
    draw.line([(0, y), (width, y)], fill=(200, 200, 200), width=1)
    # Numerar
    draw.text((10, y + 5), str(y), fill=(255, 0, 0))

# Salvar imagem
output_path = OUTPUT_DIR / f"{PDF_PATH.stem}_page1_grid.png"
img.save(output_path, "PNG")

print(f"\n✅ Imagem salva: {output_path}")
print(f"\n📋 INSTRUÇÕES:")
print("=" * 80)
print("1. Abra a imagem no Preview (ou qualquer visualizador)")
print("2. Passe o mouse sobre um CHECKBOX MARCADO (☒)")
print("3. Anote as coordenadas X,Y que aparecem no rodapé do Preview")
print("4. Repita para um CHECKBOX VAZIO (☐)")
print("5. Me passe as coordenadas no formato:")
print("   Marcado: X=XXX, Y=YYY")
print("   Vazio: X=XXX, Y=YYY")
print("=" * 80)
print(f"\n📂 Abra: {output_path.absolute()}")
print("\n💡 DICA: No Preview do Mac, as coordenadas aparecem no rodapé quando")
print("         você ativa Tools → Show Inspector (Cmd+I) e move o mouse")

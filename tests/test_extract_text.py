#!/usr/bin/env python3
"""Teste isolado de extract_text_near_checkbox"""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

import fitz
from precise_parameter_extractor import PreciseParameterExtractor, Checkbox

extractor = PreciseParameterExtractor()
pdf_path = Path('inputs/pdf/P122_204-PN-06_LADO_A_2014-08-01.pdf')
doc = fitz.open(pdf_path)
page = doc[0]

# Simular Checkbox LED5-1 (densidade: 57.4%, posição: x=98.9, y=329.3)
# EM DPI 300: x=412, y=1372
checkbox_led5_1 = Checkbox(
    x=412,  # 98.9 * (300/72)
    y=1372, # 329.3 * (300/72)
    width=60,
    height=60,
    is_marked=True,
    density=0.574
)

print("🧪 Testando extract_text_near_checkbox()...")
print(f"Checkbox: x={checkbox_led5_1.x}, y={checkbox_led5_1.y}")

text = extractor.extract_text_near_checkbox(page, checkbox_led5_1, dpi_scale=300/72)

print(f"\n✅ Texto extraído: '{text}'")
print(f"   Esperado: 'tI>>' ou 'tI>'")

doc.close()

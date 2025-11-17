#!/usr/bin/env python3
"""Teste focado APENAS na página 1 do P122"""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

import fitz
from precise_parameter_extractor import PreciseParameterExtractor

extractor = PreciseParameterExtractor()
pdf_path = Path('inputs/pdf/P122_204-PN-06_LADO_A_2014-08-01.pdf')
doc = fitz.open(pdf_path)

# Processar APENAS página 1 (índice 0)
page = doc[0]

# Detectar checkboxes com método CORRIGIDO
checkboxes = extractor.detect_checkboxes(page, dpi=300)

print(f'📦 Total checkboxes detectados: {len(checkboxes)}')
print(f'☑️  Marcados: {sum(1 for c in checkboxes if c.is_marked)}')
print(f'☐  Vazios: {sum(1 for c in checkboxes if not c.is_marked)}')
print()

# Mostrar primeiros 20 checkboxes com suas posições
print('🔍 Primeiros 20 checkboxes:')
dpi_scale = 300/72
for i, checkbox in enumerate(checkboxes[:20]):
    x_72 = checkbox.x / dpi_scale
    y_72 = checkbox.y / dpi_scale
    status = '☑' if checkbox.is_marked else '☐'
    print(f'{i+1:2d}. {status} X={x_72:5.1f}, Y={y_72:5.1f}, densidade={checkbox.density:.1%}')

doc.close()

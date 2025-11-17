#!/usr/bin/env python3
"""Debug completo do fluxo de extração"""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

from intelligent_relay_extractor import IntelligentRelayExtractor

# Patch para adicionar debug
from precise_parameter_extractor import PreciseParameterExtractor
original_extract_text = PreciseParameterExtractor.extract_text_near_checkbox

def debug_extract_text(self, page, checkbox, dpi_scale=300/72):
    result = original_extract_text(self, page, checkbox, dpi_scale)
    x_72 = checkbox.x / dpi_scale
    y_72 = checkbox.y / dpi_scale
    print(f"  🔍 Checkbox em Y={y_72:.1f}: texto='{result}'")
    return result

PreciseParameterExtractor.extract_text_near_checkbox = debug_extract_text

# Executar extração
extractor = IntelligentRelayExtractor()
pdf = Path('inputs/pdf/P122_204-PN-06_LADO_A_2014-08-01.pdf')

print("🎯 Iniciando extração com debug...")
df = extractor.extract(pdf)

print(f'\n✅ Extraído: {len(df)} parâmetros')
led5 = df[df['Code'].astype(str).str.contains('0150|0154', na=False)]
print(f'📝 LED 5: {len(led5)} linhas\n')

if not led5.empty:
    print('🎯 Resultado LED 5:')
    print(led5[['Code', 'Description', 'Value']].to_string(index=False))

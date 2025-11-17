#!/usr/bin/env python3
"""
TESTE CRÍTICO: Extrair VALORES dos checkboxes marcados
=======================================================
Para LED 5 (0150) esperamos:
  ☑ tI>  (MARCADO)
  ☑ tI>> (MARCADO)

Para LED 6 (0151) esperamos:
  ☑ tIe>  (MARCADO)
  ☑ tIe>> (MARCADO)
"""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

import fitz
from precise_parameter_extractor import PreciseParameterExtractor

def main():
    print("=" * 80)
    print("🎯 TESTE CRÍTICO: EXTRAÇÃO DE VALORES DAS CONFIGURAÇÕES")
    print("=" * 80)
    
    extractor = PreciseParameterExtractor()
    pdf_path = Path('inputs/pdf/P122_204-PN-06_LADO_A_2014-08-01.pdf')
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Detectar checkboxes
    checkboxes = extractor.detect_checkboxes(page, dpi=300)
    dpi_scale = 300/72
    
    print(f"\n📊 CHECKBOXES DETECTADOS:")
    print(f"  Total: {len(checkboxes)}")
    print(f"  Marcados: {sum(1 for c in checkboxes if c.is_marked)}")
    
    # Focar nos 4 checkboxes marcados
    marked = [c for c in checkboxes if c.is_marked]
    
    print(f"\n{'=' * 80}")
    print("☑️  CHECKBOXES MARCADOS + TEXTO EXTRAÍDO:")
    print("=" * 80)
    
    for idx, cb in enumerate(marked, 1):
        cb_y_72 = cb.y / dpi_scale
        cb_x_72 = cb.x / dpi_scale
        
        # EXTRAIR TEXTO ao lado do checkbox
        texto = extractor.extract_text_near_checkbox(page, cb, dpi_scale)
        
        print(f"\n#{idx}:")
        print(f"  Posição: Y={cb_y_72:.1f}, X={cb_x_72:.1f}")
        print(f"  Densidade: {cb.density:.1%}")
        print(f"  ➡️  TEXTO EXTRAÍDO: '{texto}'")
        
        if not texto:
            print(f"  ❌ PROBLEMA: Nenhum texto capturado!")
    
    # Verificar resultado esperado
    print(f"\n{'=' * 80}")
    print("✅ RESULTADO ESPERADO:")
    print("=" * 80)
    print("  LED 5 (0150): ☑ tI>, ☑ tI>>")
    print("  LED 6 (0151): ☑ tIe>, ☑ tIe>>")
    
    doc.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

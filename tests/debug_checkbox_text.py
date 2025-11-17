#!/usr/bin/env python3
"""Debug para ver texto ao redor dos checkboxes"""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

import fitz
import cv2
import numpy as np
from precise_parameter_extractor import PreciseParameterExtractor

def main():
    extractor = PreciseParameterExtractor()
    pdf_path = Path('inputs/pdf/P122_204-PN-06_LADO_A_2014-08-01.pdf')
    doc = fitz.open(pdf_path)
    
    # Processar primeira página
    page = doc[0]
    
    # Renderizar em 300 DPI
    mat = fitz.Matrix(300/72, 300/72)
    pix = page.get_pixmap(matrix=mat)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    enhanced = extractor.enhance_pdf_quality(gray)
    checkboxes = extractor.detect_checkboxes(enhanced)
    
    print(f'📦 Total checkboxes: {len(checkboxes)}')
    print(f'☑️  Marcados: {sum(1 for c in checkboxes if c.is_marked)}')
    print()
    
    # Primeiro, encontrar onde está o código 0150 (LED 5)
    lines = extractor.extract_parameter_lines(page)
    led5_line = [l for l in lines if '0150' in l.code]
    
    if led5_line:
        led5_y = led5_line[0].y_coordinate
        print(f'🎯 LED 5 (0150) encontrado em Y = {led5_y:.1f}')
        print()
        
        # Filtrar checkboxes próximos do LED 5 (±50px)
        dpi_scale = 300/72
        led5_checkboxes = []
        for checkbox in checkboxes:
            checkbox_y_72 = checkbox.y / dpi_scale
            if abs(checkbox_y_72 - led5_y) < 50:
                led5_checkboxes.append(checkbox)
        
        print(f'📍 Checkboxes perto do LED 5: {len(led5_checkboxes)}')
        print(f'   Marcados: {sum(1 for c in led5_checkboxes if c.is_marked)}')
        print()
        
        # Debug checkboxes marcados perto do LED 5
        for i, checkbox in enumerate([c for c in led5_checkboxes if c.is_marked]):
            x_72 = checkbox.x / dpi_scale
            y_72 = checkbox.y / dpi_scale
            w_72 = checkbox.width / dpi_scale
            
            print(f'Checkbox LED5-{i+1} (densidade: {checkbox.density:.1%}):')
            print(f'  Posição: x={x_72:.1f}, y={y_72:.1f} (distância do 0150: {y_72 - led5_y:.1f}px)')
            
            # Tentar áreas diferentes
            rect_100 = fitz.Rect(x_72 + w_72 + 1, y_72 - 3, x_72 + w_72 + 100, y_72 + 10)
            words = page.get_text('words', clip=rect_100)
            
            if words:
                print(f'  Texto à direita: {[w[4] for w in words]}')
            else:
                print(f'  Texto à direita: (vazio)')
            print()
    else:
        print('❌ LED 5 (0150) não encontrado!')
    
    doc.close()

if __name__ == '__main__':
    main()

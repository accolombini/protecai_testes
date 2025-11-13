#!/usr/bin/env python3
"""
TESTE DEFINITIVO: PyMuPDF para detectar checkboxes marcados
============================================================
PyMuPDF consegue extrair elementos gráficos (paths, rects) do PDF
"""

import fitz  # PyMuPDF
from pathlib import Path
import re

def analyze_page_with_pymupdf(pdf_path: Path, page_num: int = 0):
    """
    Analisa uma página com PyMuPDF para detectar checkboxes marcados
    
    Estratégia:
    1. Extrair texto com coordenadas
    2. Detectar elementos gráficos (paths) que formam checkboxes
    3. Detectar "X" marcado dentro dos checkboxes
    4. Associar checkbox → texto próximo
    """
    print("="*80)
    print(f"🔬 ANÁLISE COM PyMuPDF: {pdf_path.name}")
    print(f"📄 Página: {page_num + 1}")
    print("="*80)
    
    # Abrir PDF
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # 1. EXTRAIR TEXTO COM COORDENADAS
    print("\n📝 EXTRAINDO TEXTO COM COORDENADAS...")
    text_instances = page.get_text("dict")
    
    all_text_blocks = []
    for block in text_instances["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        bbox = span["bbox"]  # (x0, y0, x1, y1)
                        all_text_blocks.append({
                            "text": text,
                            "x": bbox[0],
                            "y": bbox[1],
                            "bbox": bbox
                        })
    
    print(f"   ✅ {len(all_text_blocks)} blocos de texto encontrados")
    
    # 2. DETECTAR ELEMENTOS GRÁFICOS (CHECKBOXES)
    print("\n🔍 DETECTANDO ELEMENTOS GRÁFICOS...")
    
    # PyMuPDF extrai paths como desenhos
    paths = page.get_drawings()
    print(f"   ✅ {len(paths)} elementos gráficos encontrados")
    
    # 3. IDENTIFICAR CHECKBOXES (quadrados pequenos)
    checkboxes = []
    for path in paths:
        rect = path.get("rect")
        if rect:
            x0, y0, x1, y1 = rect
            width = x1 - x0
            height = y1 - y0
            
            # Checkbox típico: 10-20 pixels, quase quadrado
            if 8 <= width <= 25 and 8 <= height <= 25:
                aspect_ratio = width / height if height > 0 else 0
                if 0.8 <= aspect_ratio <= 1.2:  # Quase quadrado
                    checkboxes.append({
                        "x": x0,
                        "y": y0,
                        "width": width,
                        "height": height,
                        "rect": rect
                    })
    
    print(f"   ✅ {len(checkboxes)} possíveis checkboxes detectados")
    
    # 4. DETECTAR CHECKBOXES MARCADOS (com X ou preenchimento)
    print("\n✅ DETECTANDO CHECKBOXES MARCADOS...")
    
    marked_checkboxes = []
    for cb in checkboxes:
        # Extrair região do checkbox
        x0, y0 = cb["x"], cb["y"]
        x1, y1 = x0 + cb["width"], y0 + cb["height"]
        
        # Verificar se há elementos dentro do checkbox (X marcado)
        has_mark = False
        for path in paths:
            path_rect = path.get("rect")
            if path_rect:
                px0, py0, px1, py1 = path_rect
                # Se o path está dentro do checkbox
                if (px0 >= x0 and px1 <= x1 and py0 >= y0 and py1 <= y1):
                    # Se o path tem área menor que o checkbox (é um X interno)
                    path_width = px1 - px0
                    path_height = py1 - py0
                    if path_width < cb["width"] * 0.9 or path_height < cb["height"] * 0.9:
                        has_mark = True
                        break
        
        if has_mark:
            # Encontrar texto próximo ao checkbox
            nearby_text = []
            for text_block in all_text_blocks:
                # Texto à direita do checkbox (mesma linha)
                if (abs(text_block["y"] - y0) < 5 and  # Mesma linha vertical
                    text_block["x"] > x1 and  # À direita
                    text_block["x"] - x1 < 200):  # Próximo (até 200px)
                    nearby_text.append(text_block["text"])
            
            marked_checkboxes.append({
                "position": (int(x0), int(y0)),
                "size": f"{int(cb['width'])}x{int(cb['height'])}",
                "text": " ".join(nearby_text) if nearby_text else "[sem texto]"
            })
    
    print(f"   ✅ {len(marked_checkboxes)} checkboxes MARCADOS detectados")
    
    # 5. MOSTRAR RESULTADOS
    print("\n" + "="*80)
    print("📊 CHECKBOXES MARCADOS DETECTADOS:")
    print("="*80)
    
    if marked_checkboxes:
        for i, cb in enumerate(marked_checkboxes, 1):
            print(f"   {i}. Pos:{cb['position']} Size:{cb['size']} → {cb['text']}")
    else:
        print("   ❌ Nenhum checkbox marcado detectado")
    
    print("\n" + "="*80)
    print(f"📊 RESUMO:")
    print(f"   Total de checkboxes marcados: {len(marked_checkboxes)}")
    print(f"   Esperado (contagem manual): 3")
    print("="*80)
    
    doc.close()
    return marked_checkboxes


def main():
    # Arquivo de teste
    pdf_path = Path("inputs/pdf/P_122 52-MF-03B1_2021-03-17.pdf")
    
    if not pdf_path.exists():
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    # Testar página 1 (índice 0)
    results = analyze_page_with_pymupdf(pdf_path, page_num=0)
    
    print(f"\n✅ Teste concluído!")


if __name__ == "__main__":
    main()

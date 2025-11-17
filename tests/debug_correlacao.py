#!/usr/bin/env python3
"""
Debug: Correlação entre Checkboxes e Parâmetros
================================================
Analisa coordenadas Y e distâncias para identificar problemas na correlação.
"""
import sys
from pathlib import Path
sys.path.insert(0, 'src')
import fitz
from precise_parameter_extractor import PreciseParameterExtractor

def main():
    print("=" * 80)
    print("🔍 DEBUG: CORRELAÇÃO CHECKBOXES ↔ PARÂMETROS")
    print("=" * 80)
    
    extractor = PreciseParameterExtractor()
    pdf_path = Path('inputs/pdf/P122_204-PN-06_LADO_A_2014-08-01.pdf')
    
    if not pdf_path.exists():
        print(f"❌ PDF não encontrado: {pdf_path}")
        return
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Detectar checkboxes e parâmetros
    checkboxes = extractor.detect_checkboxes(page, dpi=300)
    lines = extractor.extract_parameter_lines(page)
    dpi_scale = 300/72
    
    print(f"\n📊 DADOS EXTRAÍDOS:")
    print(f"  ✅ Checkboxes detectados: {len(checkboxes)}")
    print(f"  ✅ Checkboxes marcados: {sum(1 for c in checkboxes if c.is_marked)}")
    print(f"  ✅ Parâmetros extraídos: {len(lines)}")
    print(f"  ⚙️  DPI Scale: {dpi_scale:.2f} (300/72)")
    
    # Analisar checkboxes marcados
    marked_checkboxes = [c for c in checkboxes if c.is_marked]
    
    if not marked_checkboxes:
        print("\n⚠️  NENHUM CHECKBOX MARCADO ENCONTRADO!")
        doc.close()
        return
    
    print(f"\n{'=' * 80}")
    print("🎯 CHECKBOXES MARCADOS (DPI 300 → 72):")
    print("=" * 80)
    
    for idx, cb in enumerate(marked_checkboxes, 1):
        cb_y_72 = cb.y / dpi_scale
        print(f"\n📍 CHECKBOX #{idx}:")
        print(f"  Y (DPI 300): {cb.y:.1f}")
        print(f"  Y (DPI 72):  {cb_y_72:.1f} ← usado na correlação")
        print(f"  X (DPI 72):  {cb.x / dpi_scale:.1f}")
        print(f"  Densidade:   {cb.density:.1%}")
        
        # Buscar parâmetros próximos
        print(f"\n  🔎 PARÂMETROS PRÓXIMOS (tolerância < 20px):")
        found_any = False
        
        for line in sorted(lines, key=lambda l: abs(l.y_coordinate - cb_y_72)):
            distance = abs(line.y_coordinate - cb_y_72)
            
            if distance < 20:  # Tolerância aumentada para debug
                found_any = True
                status = "✅" if distance < 8 else "⚠️ "
                print(f"    {status} dist={distance:5.1f}px | Y={line.y_coordinate:6.1f} | {line.code:6} | {line.description[:40]}")
        
        if not found_any:
            print(f"    ❌ NENHUM PARÂMETRO ENCONTRADO em ±20px!")
            
            # Mostrar o parâmetro mais próximo
            closest = min(lines, key=lambda l: abs(l.y_coordinate - cb_y_72))
            dist = abs(closest.y_coordinate - cb_y_72)
            print(f"    🔍 Mais próximo: dist={dist:.1f}px | {closest.code} | {closest.description[:40]}")
    
    # Estatísticas de distâncias
    print(f"\n{'=' * 80}")
    print("📊 ESTATÍSTICAS DE DISTÂNCIAS:")
    print("=" * 80)
    
    all_distances = []
    for cb in marked_checkboxes:
        cb_y_72 = cb.y / dpi_scale
        for line in lines:
            distance = abs(line.y_coordinate - cb_y_72)
            all_distances.append(distance)
    
    all_distances.sort()
    min_distances = all_distances[:10]
    
    print(f"\n  🎯 10 menores distâncias:")
    for i, dist in enumerate(min_distances, 1):
        print(f"    {i:2}. {dist:6.1f}px")
    
    # Recomendação
    print(f"\n{'=' * 80}")
    print("💡 RECOMENDAÇÃO:")
    print("=" * 80)
    
    if min_distances[0] < 8:
        print(f"  ✅ Y-tolerance atual (8px) parece adequada")
        print(f"  ➡️  Verificar lógica de correlação em correlate_checkboxes_with_lines()")
    elif min_distances[0] < 15:
        print(f"  ⚠️  Y-tolerance atual (8px) pode estar muito restritiva")
        print(f"  ➡️  AUMENTAR para 12-15px")
    else:
        print(f"  ❌ Y-tolerance muito pequena!")
        print(f"  ➡️  AUMENTAR para 15-20px")
    
    doc.close()
    print(f"\n{'=' * 80}")
    print("✅ DEBUG COMPLETO")
    print("=" * 80)

if __name__ == "__main__":
    main()

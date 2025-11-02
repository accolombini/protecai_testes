#!/usr/bin/env python3
"""
Script de Teste: Extração de Fabricantes
Sistema ProtecAI - PETROBRAS

Testa a extração robusta de fabricantes de PDFs e TXTs
antes de reprocessar o banco de dados
"""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from universal_robust_relay_processor import UniversalRobustRelayProcessor

def test_manufacturer_extraction():
    """Testar extração de fabricantes em todos os arquivos PDF e TXT"""
    
    print("🧪 TESTE: EXTRAÇÃO DE FABRICANTES")
    print("=" * 60)
    
    processor = UniversalRobustRelayProcessor()
    
    # Testar PDFs
    pdf_dir = processor.inputs_dir / "pdf"
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    
    print(f"\n📄 TESTANDO {len(pdf_files)} PDFs:")
    print("-" * 60)
    
    manufacturer_stats = {}
    
    for pdf_file in pdf_files:
        manufacturer = processor.extract_manufacturer_from_pdf(pdf_file)
        manufacturer_stats[manufacturer] = manufacturer_stats.get(manufacturer, 0) + 1
        print(f"   {pdf_file.name[:50]:50} → {manufacturer}")
    
    # Testar TXTs
    txt_dir = processor.inputs_dir / "txt"
    txt_files = sorted(txt_dir.glob("*.txt"))
    
    if txt_files:
        print(f"\n📝 TESTANDO {len(txt_files)} TXTs:")
        print("-" * 60)
        
        for txt_file in txt_files:
            manufacturer = processor.extract_manufacturer_from_txt(txt_file)
            manufacturer_stats[manufacturer] = manufacturer_stats.get(manufacturer, 0) + 1
            print(f"   {txt_file.name[:50]:50} → {manufacturer}")
    
    # Estatísticas finais
    print("\n" + "=" * 60)
    print("📊 ESTATÍSTICAS DE FABRICANTES:")
    print("=" * 60)
    
    total_files = sum(manufacturer_stats.values())
    
    for manufacturer, count in sorted(manufacturer_stats.items(), key=lambda x: -x[1]):
        percentage = (count / total_files * 100) if total_files > 0 else 0
        print(f"   {manufacturer:15} → {count:3} arquivos ({percentage:5.1f}%)")
    
    print("\n" + "=" * 60)
    print(f"   TOTAL: {total_files} arquivos analisados")
    print("=" * 60)
    
    # Validação
    unknown_count = manufacturer_stats.get('UNKNOWN', 0)
    if unknown_count > 0:
        print(f"\n⚠️ ATENÇÃO: {unknown_count} arquivos com fabricante UNKNOWN")
        print("   Isso pode indicar PDFs sem rodapé identificável")
    else:
        print("\n✅ SUCESSO: Todos os fabricantes foram identificados!")
    
    return manufacturer_stats

if __name__ == "__main__":
    test_manufacturer_extraction()

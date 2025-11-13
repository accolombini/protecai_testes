#!/usr/bin/env python3
"""
Teste específico: Página 3 do P220 52-MP-04A.set
Validar se extrator inteligente consegue identificar checkboxes e parâmetros textuais
"""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from intelligent_relay_extractor import IntelligentRelayExtractor

def main():
    # Configurações
    pdf_path = Path("inputs/pdf/P220 52-MP-04A.set")
    template_path = Path("outputs/checkbox_debug/templates/marcado_average.png")
    
    print("=" * 80)
    print("🔬 TESTE: Página 3 de P220 52-MP-04A.set")
    print("=" * 80)
    print()
    
    # Verificar arquivos
    if not pdf_path.exists():
        # Buscar alternativas
        pdf_dir = Path("inputs/pdf")
        matches = list(pdf_dir.glob("*P220*52-MP-04A*"))
        if matches:
            pdf_path = matches[0]
            print(f"📂 Arquivo encontrado: {pdf_path.name}")
        else:
            print(f"❌ Arquivo não encontrado. Procurando P220...")
            matches = list(pdf_dir.glob("*P220*"))
            if matches:
                print(f"\n📋 Arquivos P220 disponíveis:")
                for i, f in enumerate(matches[:10], 1):
                    print(f"   {i}. {f.name}")
            return
    
    if not template_path.exists():
        print(f"❌ Template não encontrado: {template_path}")
        return
    
    # Criar extrator
    extractor = IntelligentRelayExtractor(template_checkbox_path=template_path)
    
    # Extrair parâmetros
    df = extractor.extract(pdf_path)
    
    print()
    print("=" * 80)
    print("📊 RESULTADOS DA EXTRAÇÃO")
    print("=" * 80)
    print(f"Total de parâmetros extraídos: {len(df)}")
    print()
    
    if not df.empty:
        # Separar por tipo
        checkbox_params = df[df['Value'].isin(['Yes', 'No', ''])]
        value_params = df[~df['Value'].isin(['Yes', 'No', ''])]
        
        print(f"📊 ESTATÍSTICAS:")
        print(f"   • Parâmetros com checkbox: {len(checkbox_params)}")
        print(f"   • Parâmetros com valores: {len(value_params)}")
        print()
        
        # Mostrar checkboxes detectados
        if len(checkbox_params) > 0:
            print("=" * 80)
            print("✅ CHECKBOXES MARCADOS DETECTADOS:")
            print("=" * 80)
            for i, row in checkbox_params.iterrows():
                print(f"   ☒ {row['Code']}: {row['Description']}")
        
        print()
        
        # Mostrar parâmetros com valores
        if len(value_params) > 0:
            print("=" * 80)
            print("📝 PARÂMETROS COM VALORES:")
            print("=" * 80)
            for i, row in value_params.head(15).iterrows():
                print(f"   {row['Code']}: {row['Description']}: {row['Value']}")
        
        print()
        print("=" * 80)
        print("💾 AMOSTRA COMPLETA (primeiros 20):")
        print("=" * 80)
        print(df.head(20).to_string(index=False))
        
    else:
        print("⚠️  Nenhum parâmetro extraído")
    
    print()
    print("=" * 80)
    print("✅ Teste concluído!")
    print("=" * 80)
    print()
    print("❓ VALIDAÇÃO MANUAL:")
    print("   Compare os resultados acima com a imagem da página 3")
    print("   Verifique se todos os checkboxes marcados foram detectados")
    print("=" * 80)


if __name__ == "__main__":
    main()

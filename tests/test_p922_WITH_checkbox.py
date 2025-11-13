#!/usr/bin/env python3
"""
Teste de extração P922 COM template de checkbox
Compara extração SEM template vs COM template
"""

from pathlib import Path
import sys

# Adicionar src ao path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

# Import após adicionar ao path
from intelligent_relay_extractor import IntelligentRelayExtractor  # type: ignore

def test_p922_with_checkbox():
    """Testa extração do P922 52-MF-01BC.pdf COM detecção de checkbox por densidade"""
    
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "inputs/pdf/P922 52-MF-01BC.pdf"
    # Não precisa mais de template - usa densidade-based detection
    
    print("=" * 80)
    print("🧪 TESTE DE EXTRAÇÃO COM CHECKBOX - P922 52-MF-01BC.pdf")
    print("=" * 80)
    print(f"📄 PDF: {pdf_path.name}")
    print(f"🎯 Método: DENSIDADE-BASED (30% pixels brancos = marcado)")
    print()
    
    # Teste com densidade-based detection
    print("=" * 80)
    print("📊 EXTRAÇÃO COM DENSIDADE-BASED CHECKBOX DETECTION")
    print("=" * 80)
    extractor = IntelligentRelayExtractor()  # SEM template_checkbox_path
    df = extractor.extract_from_easergy(pdf_path)
    
    print(f"✅ Total extraído: {len(df)} parâmetros")
    valores_vazios = df['Value'].isna().sum() + (df['Value'] == '').sum()
    print(f"⚠️  Valores vazios: {valores_vazios} ({valores_vazios/len(df)*100:.1f}%)")
    print()
    
    if len(df) > 0:
        print("📌 Primeiros 20 parâmetros extraídos:")
        print("-" * 80)
        for idx, row in df.head(20).iterrows():
            code = str(row['Code']).ljust(6)
            desc = str(row['Description'])[:40].ljust(40)
            value = str(row['Value'])[:30]
            print(f"  {code} | {desc} | {value}")
    else:
        print("❌ NENHUM parâmetro extraído!")
        print("   Possíveis causas:")
        print("   - Detecção de checkbox falhou")
        print("   - Threshold de densidade incorreto")
        print("   - Formato do PDF incompatível")
    
    print()
    print("=" * 80)
    print("📊 ANÁLISE DE QUALIDADE")
    print("=" * 80)
    print(f"Total parâmetros:  {len(df)}")
    print(f"Valores vazios:    {valores_vazios} ({valores_vazios/len(df)*100:.1f}%)")
    print(f"Valores preenchidos: {len(df) - valores_vazios} ({(len(df)-valores_vazios)/len(df)*100:.1f}%)")
    print()
    
    # Salvar CSV para análise visual
    output_dir = base_dir / "outputs/test_results"
    output_dir.mkdir(exist_ok=True)
    
    csv_densidade = output_dir / "p922_densidade_based.csv"
    
    df.to_csv(csv_densidade, index=False, encoding='utf-8')
    
    print(f"💾 CSV salvo em {output_dir}/")
    print(f"   - {csv_densidade.name}")
    print()
    print("=" * 80)
    print("✅ TESTE CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    test_p922_with_checkbox()

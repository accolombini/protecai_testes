#!/usr/bin/env python3
"""
Script de teste para validar extração do P922 52-MF-01BC
Após correção do bug no _extract_all_text_parameters()
"""

import sys
from pathlib import Path

# Adicionar src ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.intelligent_relay_extractor import IntelligentRelayExtractor

def test_p922_extraction():
    """Testa extração do arquivo problemático P922 52-MF-01BC.pdf"""
    
    print("=" * 80)
    print("🧪 TESTE DE EXTRAÇÃO - P922 52-MF-01BC.pdf")
    print("=" * 80)
    
    # Caminho do PDF problemático
    pdf_path = project_root / "inputs" / "pdf" / "P922 52-MF-01BC.pdf"
    
    if not pdf_path.exists():
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    print(f"📄 Arquivo: {pdf_path.name}")
    print(f"📂 Caminho: {pdf_path}")
    
    # Criar extrator (SEM template de checkbox para forçar fallback)
    print("\n🔧 Criando extrator sem template (forçar _extract_all_text_parameters)...")
    extractor = IntelligentRelayExtractor()
    
    # Extrair parâmetros
    print("\n🔍 Extraindo parâmetros...")
    df = extractor.extract_from_easergy(pdf_path)
    
    # Resultados
    print("\n" + "=" * 80)
    print("📊 RESULTADOS DA EXTRAÇÃO")
    print("=" * 80)
    print(f"✅ Total de parâmetros extraídos: {len(df)}")
    print(f"📋 Colunas: {list(df.columns)}")
    
    if len(df) > 0:
        print(f"\n📌 Primeiros 20 parâmetros:")
        print("-" * 80)
        for idx, row in df.head(20).iterrows():
            code = row.get('Code', 'N/A')
            desc = row.get('Description', 'N/A')
            value = row.get('Value', 'N/A')
            print(f"  {code:6s} | {desc:40s} | {value}")
        
        if len(df) > 20:
            print(f"\n  ... e mais {len(df) - 20} parâmetros")
        
        print("\n" + "-" * 80)
        print(f"📌 Últimos 10 parâmetros:")
        print("-" * 80)
        for idx, row in df.tail(10).iterrows():
            code = row.get('Code', 'N/A')
            desc = row.get('Description', 'N/A')
            value = row.get('Value', 'N/A')
            print(f"  {code:6s} | {desc:40s} | {value}")
    
    # Análise
    print("\n" + "=" * 80)
    print("📈 ANÁLISE")
    print("=" * 80)
    
    if len(df) < 10:
        print("❌ FALHA! Menos de 10 parâmetros extraídos de um PDF de 16 páginas!")
        print("   Esperado: Pelo menos 50-100 parâmetros")
    elif len(df) < 50:
        print("⚠️  PARCIAL! Extraiu parâmetros mas pode estar faltando dados.")
        print(f"   Extraído: {len(df)} parâmetros")
        print("   Esperado: 50-100+ parâmetros")
    else:
        print(f"✅ SUCESSO! Extraiu {len(df)} parâmetros (quantidade razoável)")
        print("   Verificar qualidade dos dados nos CSVs gerados.")
    
    # Verificar códigos únicos
    unique_codes = df['Code'].nunique() if 'Code' in df.columns else 0
    print(f"\n📊 Códigos únicos: {unique_codes}")
    
    # Verificar valores vazios
    if 'Value' in df.columns:
        empty_values = df['Value'].isna().sum() + (df['Value'] == '').sum()
        print(f"⚠️  Valores vazios: {empty_values} ({empty_values/len(df)*100:.1f}%)")
    
    print("\n" + "=" * 80)
    print("✅ TESTE CONCLUÍDO")
    print("=" * 80)
    
    return df

if __name__ == "__main__":
    test_p922_extraction()

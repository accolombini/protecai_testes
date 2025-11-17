#!/usr/bin/env python3
"""Teste COMPLETO da pipeline - checkboxes + parâmetros + correlação"""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

from precise_parameter_extractor import PreciseParameterExtractor
import pandas as pd

print("🎯 TESTE COMPLETO DA PIPELINE CORRIGIDA")
print("="*60)

# Testar no P122 página 1
pdf_path = Path('inputs/pdf/P122_204-PN-06_LADO_A_2014-08-01.pdf')
extractor = PreciseParameterExtractor()

print(f"\n📄 Processando: {pdf_path.name}")
print("-"*60)

# Extrair tudo
df = extractor.extract_from_pdf(str(pdf_path))

print(f"\n📊 RESULTADOS:")
print(f"  Total de parâmetros extraídos: {len(df)}")
print(f"  Parâmetros com checkbox marcado: {df['is_active'].sum()}")
print(f"  Parâmetros com valor: {df['Value'].notna().sum()}")

print(f"\n🔍 PRIMEIROS 20 PARÂMETROS:")
print("-"*60)
for idx, row in df.head(20).iterrows():
    status = "☑" if row['is_active'] else "☐"
    value = row['Value'] if pd.notna(row['Value']) else "(vazio)"
    code = row['Code'] if pd.notna(row['Code']) else "????"
    desc = row['Description'] if pd.notna(row['Description']) else ""
    print(f"{status} {code:6s} | {desc[:30]:30s} | {value}")

# Focar em LED 5 (0150)
print(f"\n🎯 FOCO: LED 5 (código 0150 e variantes)")
print("-"*60)
led5_codes = ['0150', '0151', '0154', '0155']
led5_df = df[df['Code'].isin(led5_codes)]

if len(led5_df) > 0:
    print(f"Total de parâmetros LED 5: {len(led5_df)}")
    print()
    for idx, row in led5_df.iterrows():
        status = "☑" if row['is_active'] else "☐"
        value = row['Value'] if pd.notna(row['Value']) else "(vazio)"
        code = row['Code']
        desc = row['Description'] if pd.notna(row['Description']) else ""
        print(f"{status} {code:6s} | {desc[:30]:30s} | {value}")
else:
    print("❌ Nenhum parâmetro LED 5 encontrado!")

# Estatísticas por código
print(f"\n📈 ESTATÍSTICAS POR CÓDIGO:")
print("-"*60)
stats = df.groupby('Code').agg({
    'Code': 'count',
    'is_active': 'sum',
    'Value': lambda x: x.notna().sum()
}).rename(columns={'Code': 'total', 'is_active': 'marcados', 'Value': 'com_valor'})

for code, row in stats.iterrows():
    print(f"{code}: {row['total']} parâmetros ({row['marcados']} marcados, {row['com_valor']} com valor)")

print("\n" + "="*60)
print("✅ TESTE COMPLETO!")

#!/usr/bin/env python3
import re

def detect_model(filename):
    filename_upper = filename.upper()
    
    # SEPAM: arquivos .S40 ou que começam com 00-MF-
    if filename_upper.endswith('.S40') or filename.startswith('00-MF-'):
        return 'SEPAM'
    
    # P922S deve vir ANTES de P922 para evitar match incorreto
    if 'P922S' in filename_upper:
        return 'P922S'
    
    # Padrões para outros modelos (ordem alfabética)
    patterns = {
        'P122': r'P[\s_]?122',
        'P143': r'P[\s_]?143', 
        'P220': r'P[\s_]?220',
        'P241': r'P[\s_]?241',
        'P922': r'P[\s_]?922(?!S)'  # Negative lookahead para não pegar P922S
    }
    
    for model, pattern in patterns.items():
        if re.search(pattern, filename_upper):
            return model
    
    return None

# Testar arquivos problemáticos
test_files = [
    '00-MF-12_2016-03-31.S40',
    '00-MF-14_2016-03-31.S40',
    '00-MF-24_2024-09-10.S40',
    'P122 52-MF-02A_2021-03-08.pdf',
    'P_122 52-MF-03B1_2021-03-17.pdf',
    'P122_204-MF-2B1_2014-07-28.pdf',
    'P143_204-MF-03B_2014-08-14.pdf',
    'P143 52-MF-03A.pdf',
    'P220 52-MP-01A.pdf',
    'P220_52-MK-02A_2020-07-08.pdf',
    'P241_52-MP-20_2019-08-15.pdf',
    'P241_53-MK-01_2019-08-15.pdf',
    'P922 52-MF-01BC.pdf',
    'P922 52-MF-02AC.pdf',
    'P922S_204-MF-1AC_2014-07-28.pdf'
]

print("TESTE DE DETECÇÃO DE MODELO")
print("=" * 70)
for f in test_files:
    result = detect_model(f)
    status = "✅" if result else "❌"
    print(f'{status} {f:45} -> {result}')

#!/usr/bin/env python3
"""
Testes rápidos para validar funções de normalização
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from normalize_to_3nf import Normalizer3NF

def test_extract_value_and_unit():
    """Testa extração de valor e unidade"""
    print("\n" + "="*80)
    print("🧪 TESTE: extract_value_and_unit()")
    print("="*80)
    
    normalizer = Normalizer3NF()
    
    test_cases = [
        # (input, expected_value, expected_unit)
        ('60Hz', '60', 'Hz'),
        ('13800kV', '13800', 'kV'),
        ('1.5s', '1.5', 's'),
        ('0.10In', '0.10', 'In'),
        ('50 Ω', '50', 'Ω'),
        ('4.20 mA', '4.20', 'mA'),
        ('25°C', '25', '°C'),  # °C é unidade completa!
        ('100%', '100', '%'),
        ('0.90s', '0.90', 's'),
        ('200', '200', ''),  # sem unidade
        ('DMT', 'DMT', ''),  # texto puro
        ('Yes', 'Yes', ''),  # booleano textual
        ('tU<', 'tU<', ''),  # texto especial
        ('-5.2kV', '-5.2', 'kV'),  # negativo
        ('+3.14°', '+3.14', '°'),  # positivo explícito
    ]
    
    passed = 0
    failed = 0
    
    for input_str, expected_value, expected_unit in test_cases:
        value, unit = normalizer.extract_value_and_unit(input_str)
        
        if value == expected_value and unit == expected_unit:
            print(f"✅ '{input_str}' → ('{value}', '{unit}')")
            passed += 1
        else:
            print(f"❌ '{input_str}' → ('{value}', '{unit}') | ESPERADO: ('{expected_value}', '{expected_unit}')")
            failed += 1
    
    print(f"\n📊 Resultado: {passed} passed, {failed} failed")
    return failed == 0


def test_multipart_parsing():
    """Testa parsing de descrições multipart"""
    print("\n" + "="*80)
    print("🧪 TESTE: identify_multipart_groups() patterns")
    print("="*80)
    
    import pandas as pd
    import re
    
    # Padrão usado no identify_multipart_groups
    pattern = r'^(?:\d+:\s*)?(.+?)\s+(?:part|PART)\s+(\d+)(?::\s*(.*))?$|^(?:\d+:\s*)?(.+?)\s+\((\d+)/\d+\)(?:\s*(.*))?$'
    
    test_cases = [
        # (description, expected_base, expected_part, expected_extra)
        ('LED 5 part 1', 'LED 5', 1, ''),
        ('LED 5 PART 1:', 'LED 5', 1, ''),
        ('0150: LED 5 PART 1: tU<', 'LED 5', 1, 'tU<'),
        ('Blocking Logic 1 part 2', 'Blocking Logic 1', 2, ''),
        ('Input 1 (1/4)', 'Input 1', 1, ''),
        ('0240: Input 2 (2/5)', 'Input 2', 2, ''),
        ('LED 8 part 3: DMT', 'LED 8', 3, 'DMT'),
    ]
    
    passed = 0
    failed = 0
    
    for desc, expected_base, expected_part, expected_extra in test_cases:
        match = re.match(pattern, desc, re.IGNORECASE)
        
        if match:
            if match.group(1):  # formato "part"
                base_name = match.group(1).strip()
                part_num = int(match.group(2))
                extra_suffix = match.group(3).strip() if match.group(3) else ''
            else:  # formato "(X/Y)"
                base_name = match.group(4).strip()
                part_num = int(match.group(5))
                extra_suffix = match.group(6).strip() if match.group(6) else ''
            
            # Limpar prefixos numéricos
            base_name = re.sub(r'^\d+:\s*', '', base_name).strip()
            
            if base_name == expected_base and part_num == expected_part and extra_suffix == expected_extra:
                print(f"✅ '{desc}'")
                print(f"   → base='{base_name}', part={part_num}, extra='{extra_suffix}'")
                passed += 1
            else:
                print(f"❌ '{desc}'")
                print(f"   → base='{base_name}', part={part_num}, extra='{extra_suffix}'")
                print(f"   ESPERADO: base='{expected_base}', part={expected_part}, extra='{expected_extra}'")
                failed += 1
        else:
            print(f"❌ '{desc}' → NÃO MATCHED!")
            failed += 1
    
    print(f"\n📊 Resultado: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Executa todos os testes"""
    print("\n" + "="*80)
    print("🚀 TESTES DE NORMALIZAÇÃO 3FN")
    print("="*80)
    
    test1_ok = test_extract_value_and_unit()
    test2_ok = test_multipart_parsing()
    
    print("\n" + "="*80)
    if test1_ok and test2_ok:
        print("✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
    print("="*80 + "\n")
    
    return 0 if (test1_ok and test2_ok) else 1


if __name__ == '__main__':
    sys.exit(main())

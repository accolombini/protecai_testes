"""
TESTE DOS PADRÕES DE EXTRAÇÃO
Valida se os regex estão capturando corretamente cada formato
"""

import re
import sys
from pathlib import Path

# Corrigir path para importar de src/
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

try:
    from universal_format_converter import UniversalFormatConverter
except ImportError as e:
    print(f"❌ Erro ao importar: {e}")
    print(f"   Verificar se {src_path}/universal_format_converter.py existe")
    sys.exit(1)

def test_patterns():
    converter = UniversalFormatConverter()
    
    print("="*80)
    print("🧪 TESTANDO PADRÕES DE EXTRAÇÃO")
    print("="*80)
    
    # EASERGY
    print("\n📌 EASERGY (P122, P220, P922):")
    easergy_lines = [
        "0104: Frequency:60Hz",
        "010A: Reference:2A.1",
        "0120: Line CT primary: 200"
    ]
    
    for line in easergy_lines:
        micom_match = converter.re_micom.match(line)
        easergy_eq = converter.re_easergy_equals.match(line)
        easergy_col = converter.re_easergy_colon.match(line)
        
        print(f"\n  Linha: {line}")
        print(f"    MiCOM:         {'✅' if micom_match else '❌'}")
        print(f"    Easergy (=):   {'✅' if easergy_eq else '❌'}")
        print(f"    Easergy (:):   {'✅' if easergy_col else '❌'} {easergy_col.groups() if easergy_col else ''}")
    
    # MICOM
    print("\n📌 MICOM (P143, P241):")
    micom_lines = [
        "00.01: Language: English",
        "00.06: Model Number: P143312A2A0150C",
        "09.01: Restore Defaults: No Operation"
    ]
    
    for line in micom_lines:
        micom_match = converter.re_micom.match(line)
        easergy_eq = converter.re_easergy_equals.match(line)
        easergy_col = converter.re_easergy_colon.match(line)
        
        print(f"\n  Linha: {line}")
        print(f"    MiCOM:         {'✅' if micom_match else '❌'} {micom_match.groups() if micom_match else ''}")
        print(f"    Easergy (=):   {'✅' if easergy_eq else '❌'}")
        print(f"    Easergy (:):   {'✅' if easergy_col else '❌'}")
    
    # SEPAM
    print("\n📌 SEPAM (.S40):")
    sepam_lines = [
        "frequence_reseau=1",
        "tension_primaire_nominale=13800",
        "repere=00-MF-12 NS08170043"
    ]
    
    # Pattern SEPAM (deveria ser diferente)
    re_sepam = re.compile(r"^([^=\[\]]+)=(.*)$")
    
    for line in sepam_lines:
        sepam_match = re_sepam.match(line)
        
        print(f"\n  Linha: {line}")
        print(f"    SEPAM pattern: {'✅' if sepam_match else '❌'} {sepam_match.groups() if sepam_match else ''}")

if __name__ == "__main__":
    test_patterns()

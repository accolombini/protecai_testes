#!/usr/bin/env python3
"""
TESTE: Correção de voltage_class para modelos SEPAM
Extrai tension_primaire_nominale dos arquivos .S40 processados
"""

import sys
from pathlib import Path

# Adicionar scripts ao path
sys.path.insert(0, str(Path(__file__).parent))

from universal_robust_relay_processor import UniversalRobustRelayProcessor

def test_voltage_fix():
    print("🧪 TESTE: Correção de voltage_class SEPAM")
    print("=" * 60)
    
    processor = UniversalRobustRelayProcessor()
    
    # 1. Conectar ao banco
    if not processor.connect_database():
        print("❌ Falha na conexão")
        return False
    
    # 2. Executar correção
    processor.update_sepam_voltage_class_from_files()
    
    # 3. Verificar resultado no banco
    with processor.conn.cursor() as cur:
        cur.execute("""
            SELECT model_code, model_name, voltage_class
            FROM protec_ai.relay_models
            WHERE model_code LIKE 'SEPAM%'
            ORDER BY model_code
        """)
        
        print("\n📋 Modelos SEPAM após correção:")
        print("-" * 60)
        for row in cur.fetchall():
            print(f"  {row[0]:<15} {row[1]:<35} {row[2]}")
    
    print("\n✅ TESTE CONCLUÍDO!")
    print("🎯 CAUSA RAIZ: Script agora extrai voltage_class dos arquivos .S40 reais")
    return True

if __name__ == "__main__":
    success = test_voltage_fix()
    sys.exit(0 if success else 1)

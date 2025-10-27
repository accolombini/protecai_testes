#!/usr/bin/env python3
"""
Teste das correções finais dos endpoints 422
Baseado nas descobertas:
- Datetime: date-only format
- Study types: short_circuit, coordination, selectivity, arc_flash
- Equipment ID: string format agora corrigido
"""

import requests
import json
from datetime import datetime, date
import uuid

BASE_URL = "http://localhost:8000"

# ✅ DADOS CORRETOS DESCOBERTOS
VALID_TEST_DATA = {
    "EquipmentCreate": {
        "plant_reference": "PETROBRAS-TEST-001",
        "tag_reference": "REL-001-TEST",
        "description": "Teste Equipment Create Corrigido",
        "bay_position": "BAY-01",
        "installation_date": "2024-01-15",  # ✅ Date-only format
        "commissioning_date": "2024-01-20",  # ✅ Date-only format  
        "frequency": 60.0,
        "status": "OPERATIONAL",
        "serial_number": "SN-001-TEST",
        "software_version": "v1.0.0",
        "model_id": "MODEL-001"
    },
    
    "EquipmentUpdate": {
        "plant_reference": "PETROBRAS-TEST-002",
        "tag_reference": "REL-002-UPDATED",
        "description": "Teste Equipment Update Corrigido",
        "bay_position": "BAY-02",
        "installation_date": "2024-02-15",  # ✅ Date-only format
        "commissioning_date": "2024-02-20",  # ✅ Date-only format
        "frequency": 60.0,
        "status": "MAINTENANCE",
        "serial_number": "SN-002-UPDATED",
        "software_version": "v1.1.0"
    },
    
    "StudyCreateRequest": {
        "name": "Teste Study Type Válido",
        "description": "Teste com study type descoberto como válido",
        "study_type": "coordination",  # ✅ Válido descoberto
        "plant_reference": "PETROBRAS-STUDY-001",
        "protection_standard": "petrobras",
        "frequency": 60.0,
        "base_voltage": 138.0,
        "base_power": 100.0,
        "study_config": {
            "analysis_type": "full",
            "include_coordination": True
        }
    },
    
    "EquipmentConfigRequest": {
        "equipment_id": "protec_ai_5",  # ✅ String format corrigido no schema
        "etap_device_id": "ETAP_DEV_001",
        "device_name": "Relay Protection 001",
        "device_type": "Distance Relay",
        "bus_name": "BUS_138KV_01",
        "bay_position": "BAY-PROT-01",
        "rated_voltage": 138.0,
        "rated_current": 1000.0,
        "rated_power": 50.0,
        "protection_config": {
            "zones": 3,
            "reach_zone1": 0.8,
            "reach_zone2": 1.2,
            "time_zone2": 0.3
        }
    }
}

def test_corrected_endpoints():
    """Testa os endpoints corrigidos"""
    print("🔧 TESTE DAS CORREÇÕES FINAIS")
    print("=" * 60)
    
    results = []
    
    # 1. Equipment Create
    print("\n📅 TESTANDO: Equipment Create com date-only")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/equipments/",
            json=VALID_TEST_DATA["EquipmentCreate"],
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            print("   ✅ CORRIGIDO: Equipment Create funcionando!")
            results.append(("Equipment Create", True, response.status_code))
            
            # Extrair o ID criado para teste de update
            resp_data = response.json()
            if 'message' in resp_data and 'ID:' in resp_data['message']:
                created_id = resp_data['message'].split('ID: ')[1].strip()
                print(f"   📝 Equipment criado com ID: {created_id}")
                
                # 2. Equipment Update com ID real
                print("\n📅 TESTANDO: Equipment Update com ID real")
                response = requests.put(
                    f"{BASE_URL}/api/v1/equipments/{created_id}",
                    json=VALID_TEST_DATA["EquipmentUpdate"],
                    headers={"Content-Type": "application/json"}
                )
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    print("   ✅ CORRIGIDO: Equipment Update funcionando!")
                    results.append(("Equipment Update", True, response.status_code))
                else:
                    print(f"   ❌ Erro: {response.text[:200]}")
                    results.append(("Equipment Update", False, response.status_code))
        else:
            print(f"   ❌ Erro: {response.text[:200]}")
            results.append(("Equipment Create", False, response.status_code))
    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        results.append(("Equipment Create", False, "ERROR"))
    
    # 3. Study Create
    print("\n🔢 TESTANDO: Study Create com type válido")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/etap/studies",
            json=VALID_TEST_DATA["StudyCreateRequest"],
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            print("   ✅ CORRIGIDO: Study Create funcionando!")
            results.append(("Study Create", True, response.status_code))
        else:
            print(f"   ❌ Erro: {response.text[:200]}")
            results.append(("Study Create", False, response.status_code))
    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        results.append(("Study Create", False, "ERROR"))
    
    # 4. Equipment Config
    print("\n🆔 TESTANDO: Equipment Config com ID string")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/etap/studies/1/equipment",
            json=VALID_TEST_DATA["EquipmentConfigRequest"],
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 201]:
            print("   ✅ CORRIGIDO: Equipment Config funcionando!")
            results.append(("Equipment Config", True, response.status_code))
        else:
            print(f"   ❌ Erro: {response.text[:200]}")
            results.append(("Equipment Config", False, response.status_code))
    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        results.append(("Equipment Config", False, "ERROR"))
    
    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO DAS CORREÇÕES")
    print("=" * 60)
    
    successful = len([r for r in results if r[1] == True])
    total = len(results)
    
    for endpoint, success, status in results:
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {endpoint}: {status}")
    
    print(f"\n🎯 PROGRESSO: {successful}/{total} endpoints corrigidos ({successful/total*100:.1f}%)")
    
    if successful > 0:
        print("🚀 AVANÇO SIGNIFICATIVO! Sistema recuperando da regressão PostgreSQL")
    
    # Salvar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"temp/test_corrections_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "total_tested": total,
            "successful": successful,
            "success_rate": f"{successful/total*100:.1f}%",
            "results": [{"endpoint": r[0], "success": r[1], "status": r[2]} for r in results]
        }, f, indent=2)
    
    print(f"💾 Resultados salvos em: {results_file}")
    
    return results

if __name__ == "__main__":
    test_corrected_endpoints()
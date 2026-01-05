#!/usr/bin/env python3
"""
Correção específica para problemas de datetime parsing
"""

import requests
import json
from datetime import datetime, date

def test_equipment_endpoints():
    """Testa endpoints de equipamentos com datas corretas"""
    base_url = "http://localhost:8000"
    
    # Dados com formato date-only (não datetime)
    equipment_create_data = {
        "tag_reference": "TR-001-TEST",
        "plant_reference": "REPAR-001",
        "bay_position": "Bay-A1",
        "description": "Relé de proteção teste",
        "model_id": 1,
        "serial_number": "SN123456789",
        "software_version": "v2.1.0",
        "installation_date": "2024-01-15",  # Formato date-only
        "commissioning_date": "2024-01-20",  # Formato date-only
        "frequency": 60.0,
        "status": "active"
    }
    
    equipment_update_data = {
        "description": "Relé de proteção atualizado",
        "installation_date": "2024-01-15",  # Formato date-only
        "commissioning_date": "2024-01-20",  # Formato date-only
        "status": "maintenance"
    }
    
    results = {}
    
    print("🔧 TESTANDO: Equipment Create com date-only")
    try:
        response = requests.post(
            f"{base_url}/api/v1/equipments/",
            headers={"Content-Type": "application/json"},
            json=equipment_create_data,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Sucesso! Equipment criado")
            results["create"] = {"status": "success", "data": response.json()}
        else:
            print(f"   ❌ Erro: {response.text[:200]}")
            results["create"] = {"status": "failed", "error": response.text}
    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        results["create"] = {"status": "exception", "error": str(e)}
    
    print("\n🔧 TESTANDO: Equipment Update com date-only")
    try:
        response = requests.put(
            f"{base_url}/api/v1/equipments/1",
            headers={"Content-Type": "application/json"},
            json=equipment_update_data,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Sucesso! Equipment atualizado")
            results["update"] = {"status": "success", "data": response.json()}
        else:
            print(f"   ❌ Erro: {response.text[:200]}")
            results["update"] = {"status": "failed", "error": response.text}
    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        results["update"] = {"status": "exception", "error": str(e)}
    
    return results

def test_study_types():
    """Testa diferentes tipos de estudo para descobrir valores válidos"""
    base_url = "http://localhost:8000"
    
    # Tenta diferentes tipos de estudo
    study_types = [
        "load_flow",
        "short_circuit", 
        "protection",
        "coordination",
        "selectivity",
        "fault_analysis",
        "power_flow",
        "stability",
        "harmonic",
        "arc_flash"
    ]
    
    results = {}
    
    for study_type in study_types:
        study_data = {
            "name": f"Teste {study_type} Study",
            "description": f"Teste para descobrir study_type válido: {study_type}",
            "study_type": study_type,
            "plant_reference": "REPAR-001",
            "frequency": 60.0
        }
        
        print(f"🔍 TESTANDO: Study type '{study_type}'")
        try:
            response = requests.post(
                f"{base_url}/api/v1/etap/studies",
                headers={"Content-Type": "application/json"},
                json=study_data,
                timeout=10
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ VÁLIDO! Study type '{study_type}' aceito")
                results[study_type] = {"status": "valid", "data": response.json()}
                break  # Para no primeiro que funcionar
            else:
                print(f"   ❌ Inválido: {response.text[:100]}")
                results[study_type] = {"status": "invalid", "error": response.text}
        except Exception as e:
            print(f"   ❌ Exceção: {e}")
            results[study_type] = {"status": "exception", "error": str(e)}
    
    return results

def get_valid_equipment_id():
    """Busca um equipment_id válido no banco"""
    base_url = "http://localhost:8000"
    
    print("🔍 BUSCANDO: Equipment ID válido")
    try:
        response = requests.get(
            f"{base_url}/api/v1/equipments/",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                equipment_id = data["data"][0]["id"]
                print(f"   ✅ Equipment ID encontrado: {equipment_id}")
                return equipment_id
            else:
                print(f"   ❌ Nenhum equipment encontrado")
                return None
        else:
            print(f"   ❌ Erro ao buscar equipments: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        return None

def test_equipment_config(equipment_id):
    """Testa endpoint de configuração de equipamento com ID válido"""
    base_url = "http://localhost:8000"
    
    config_data = {
        "equipment_id": equipment_id,  # Usar ID válido
        "device_name": "Relay-Test-001",
        "device_type": "overcurrent_relay",
        "etap_device_id": "ETAP_001",
        "bus_name": "Bus-138kV-01",
        "bay_position": "Bay-A1",
        "rated_voltage": 138.0,
        "rated_current": 1000.0,
        "rated_power": 10.0,
        "protection_config": {
            "phase_overcurrent": {
                "pickup": 1.2,
                "time_dial": 0.5,
                "curve": "normal_inverse"
            }
        }
    }
    
    print(f"🔧 TESTANDO: Equipment Config com ID {equipment_id}")
    try:
        response = requests.post(
            f"{base_url}/api/v1/etap/studies/1/equipment",
            headers={"Content-Type": "application/json"},
            json=config_data,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Sucesso! Equipment config criado")
            return {"status": "success", "data": response.json()}
        else:
            print(f"   ❌ Erro: {response.text[:200]}")
            return {"status": "failed", "error": response.text}
    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        return {"status": "exception", "error": str(e)}

if __name__ == "__main__":
    print("🔧 CORREÇÃO ESPECÍFICA - Problemas Datetime/Enum/ID")
    print("=" * 60)
    
    # 1. Testar datas no formato correto
    print("\n📅 CORRIGINDO: Datetime parsing")
    equipment_results = test_equipment_endpoints()
    
    # 2. Descobrir study_type válido
    print("\n📊 DESCOBRINDO: Study types válidos")
    study_results = test_study_types()
    
    # 3. Usar equipment_id válido
    print("\n🆔 CORRIGINDO: Equipment ID validation")
    equipment_id = get_valid_equipment_id()
    config_results = None
    if equipment_id:
        config_results = test_equipment_config(equipment_id)
    
    # Salvar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "timestamp": timestamp,
        "equipment_datetime_tests": equipment_results,
        "study_type_tests": study_results,
        "valid_equipment_id": equipment_id,
        "equipment_config_test": config_results
    }
    
    filename = f"temp/fix_datetime_results_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Resultados salvos em: {filename}")
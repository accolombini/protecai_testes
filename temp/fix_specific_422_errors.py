#!/usr/bin/env python3
"""
🔧 CORREÇÃO ESPECÍFICA - Erros 422 Detalhados
============================================================
Corrige os problemas específicos identificados na primeira passada:
- Datetime parsing
- Enum validation  
- Integer parsing
- Missing attributes
"""
import requests
import json
from datetime import datetime, timezone
import uuid

def test_endpoint(method, url, data=None, description=""):
    """Testa um endpoint com dados específicos"""
    try:
        if method.upper() == "POST":
            response = requests.post(f"http://localhost:8000{url}", json=data, timeout=10)
        elif method.upper() == "PUT":
            response = requests.put(f"http://localhost:8000{url}", json=data, timeout=10)
        else:
            response = requests.get(f"http://localhost:8000{url}", timeout=10)
            
        return response.status_code, response.text[:200]
    except Exception as e:
        return 0, str(e)[:200]

def main():
    print("🔧 CORREÇÃO ESPECÍFICA - Erros 422 Detalhados")
    print("="*60)
    
    results = []
    
    # 1. Corrigir datetime parsing (ISO format com timezone)
    print("\n📅 CORRIGINDO: Datetime parsing")
    
    # Equipment Create - datetime correto
    equipment_data = {
        "tag_reference": "REL-001-FIXED",
        "plant_reference": "REDUC-001",
        "description": "Relé de proteção corrigido",
        "model_id": 1,
        "serial_number": "SN001",
        "installation_date": "2024-01-15T10:30:00Z",  # ISO format with Z
        "commissioning_date": "2024-02-01T14:20:00Z",
        "status": "active",
        "bay_position": "Bay 1",
        "frequency": 60.0,
        "software_version": "v2.1.0"
    }
    
    status, response = test_endpoint("POST", "/api/v1/equipments/", equipment_data, "Equipment Create")
    print(f"   {'✅' if status == 200 or status == 201 else '❌'} {status} - Equipment Create: {response}")
    results.append({"endpoint": "POST /api/v1/equipments/", "status": status, "response": response})
    
    # Equipment Update - datetime correto
    equipment_update = {
        "tag_reference": "REL-001-UPDATED",
        "plant_reference": "REDUC-001",
        "description": "Relé de proteção atualizado",
        "serial_number": "SN001-UPD",
        "installation_date": "2024-01-15T10:30:00+00:00",  # ISO format with +00:00
        "commissioning_date": "2024-02-01T14:20:00+00:00",
        "status": "active",
        "bay_position": "Bay 1 Updated",
        "frequency": 60.0,
        "software_version": "v2.2.0"
    }
    
    status, response = test_endpoint("PUT", "/api/v1/equipments/1", equipment_update, "Equipment Update")
    print(f"   {'✅' if status == 200 else '❌'} {status} - Equipment Update: {response}")
    results.append({"endpoint": "PUT /api/v1/equipments/1", "status": status, "response": response})
    
    # 2. Corrigir enum validation
    print("\n🔢 CORRIGINDO: Enum validation")
    
    # Verificar valores válidos de enum primeiro
    status, response = test_endpoint("GET", "/openapi.json")
    if status == 200:
        try:
            openapi = json.loads(response)
            study_type_enum = openapi.get("components", {}).get("schemas", {}).get("StudyType", {}).get("enum", [])
            analysis_type_enum = openapi.get("components", {}).get("schemas", {}).get("MLAnalysisTypeEnum", {}).get("enum", [])
            print(f"   📋 StudyType enum disponível: {study_type_enum}")
            print(f"   📋 MLAnalysisType enum disponível: {analysis_type_enum}")
        except:
            study_type_enum = ["protection", "coordination", "selectivity", "fault_analysis"]
            analysis_type_enum = ["COORDINATION", "SELECTIVITY", "SIMULATION"]
    else:
        # Valores padrão baseados no código
        study_type_enum = ["protection", "coordination", "selectivity", "fault_analysis"]
        analysis_type_enum = ["COORDINATION", "SELECTIVITY", "SIMULATION"]
    
    # Study Create - usar enum válido
    study_data = {
        "name": "Estudo de Proteção REDUC-001",
        "description": "Análise de coordenação e seletividade",
        "study_type": study_type_enum[0] if study_type_enum else "protection",  # Primeiro enum válido
        "plant_reference": "REDUC-001-UNIT-01",
        "protection_standard": "petrobras",
        "frequency": 60.0,
        "base_voltage": 138.0,
        "base_power": 100.0,
        "study_config": {
            "fault_types": ["3phase", "line_to_ground"],
            "analysis_depth": "detailed"
        }
    }
    
    status, response = test_endpoint("POST", "/api/v1/etap/studies", study_data, "Study Create")
    print(f"   {'✅' if status == 200 or status == 201 else '❌'} {status} - Study Create: {response}")
    results.append({"endpoint": "POST /api/v1/etap/studies", "status": status, "response": response})
    
    # 3. Corrigir integer parsing
    print("\n🔢 CORRIGINDO: Integer parsing")
    
    # Equipment Config - usar integers corretos
    equipment_config = {
        "equipment_id": 1,  # Integer, não string
        "etap_device_id": "DEV-001",
        "device_name": "Relé Principal",
        "device_type": "relay",
        "bus_name": "Bus 138kV",
        "bay_position": "Bay 01",
        "rated_voltage": 138.0,
        "rated_current": 1000.0,
        "rated_power": 100.0,
        "protection_config": {
            "overcurrent": {"pickup": 0.8, "time_delay": 0.1},
            "differential": {"pickup": 0.3, "slope": 25.0}
        }
    }
    
    status, response = test_endpoint("POST", "/api/v1/etap/studies/1/equipment", equipment_config, "Equipment Config")
    print(f"   {'✅' if status == 200 or status == 201 else '❌'} {status} - Equipment Config: {response}")
    results.append({"endpoint": "POST /api/v1/etap/studies/1/equipment", "status": status, "response": response})
    
    # 4. Corrigir ML Job com enum válido
    print("\n🤖 CORRIGINDO: ML Job enum")
    
    # ML Job - usar enum válido
    ml_job_data = {
        "job_name": f"Análise_Coordenação_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "name": "Análise de Coordenação ML",
        "analysis_type": analysis_type_enum[0] if analysis_type_enum else "COORDINATION",  # Enum válido
        "type": "coordination_analysis",
        "priority": "NORMAL",
        "source_data_config": {
            "data_source": "etap_studies",
            "include_historical": True,
            "filters": {"study_type": "coordination"}
        },
        "etap_study_id": 1,
        "ml_module_version": "v2.1.0",
        "ml_algorithm": "gradient_boosting",
        "ml_parameters": {
            "max_depth": 10,
            "learning_rate": 0.1,
            "n_estimators": 100
        },
        "requested_by": "system_test"
    }
    
    status, response = test_endpoint("POST", "/api/v1/ml-gateway/jobs", ml_job_data, "ML Job")
    print(f"   {'✅' if status == 200 or status == 201 else '❌'} {status} - ML Job: {response}")
    results.append({"endpoint": "POST /api/v1/ml-gateway/jobs", "status": status, "response": response})
    
    # 5. Salvar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"temp/fix_specific_422_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tested": len(results),
            "results": results,
            "summary": {
                "corrected": len([r for r in results if r["status"] in [200, 201]]),
                "still_failing": len([r for r in results if r["status"] not in [200, 201]])
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 RELATÓRIO ESPECÍFICO:")
    print(f"✅ Endpoints testados: {len(results)}")
    print(f"✅ Corrigidos: {len([r for r in results if r['status'] in [200, 201]])}")
    print(f"❌ Ainda falhando: {len([r for r in results if r['status'] not in [200, 201]])}")
    print(f"💾 Resultados salvos em: {filename}")

if __name__ == "__main__":
    main()
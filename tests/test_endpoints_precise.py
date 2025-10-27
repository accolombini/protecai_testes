#!/usr/bin/env python3
"""
🎯 TESTE PRECISO DOS ENDPOINTS COM PAYLOADS CORRETOS
=================================================

Script de teste que usa payloads específicos e corretos para cada endpoint,
baseado na análise individual que fizemos.
"""

import requests
import json
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

# Payloads específicos para cada endpoint
ENDPOINT_PAYLOADS = {
    # VALIDATION - Usar body correto
    "/api/v1/validation/": {
        "equipment_ids": [1],
        "validation_type": "full"
    },
    "/api/v1/validation/custom": {
        "equipment_ids": [1],
        "custom_rules": {"test_rule": "basic_validation"}
    },
    
    # ETAP-NATIVE - Usar defaults ou body mínimo
    "/api/v1/etap-native/initialize": {},  # Já funciona com {}
    "/api/v1/etap-native/import": {
        "study_data": {"name": "test_study", "type": "test"},
        "prefer_native": True,
        "sync_to_database": True
    },
    "/api/v1/etap-native/batch/import-studies": {
        "study_paths": ["./inputs/test"],
        "prefer_native": True
    },
    
    # ML-GATEWAY - Payloads mais específicos
    "/api/v1/ml-gateway/results/coordination/{job_uuid}": {
        "coordination_data": {
            "job_id": "test_job_123",
            "equipment_data": {"relay_001": {"current": 100, "time": 0.5}}
        }
    },
    "/api/v1/ml-gateway/results/selectivity/{job_uuid}": {
        "selectivity_data": {
            "job_id": "test_job_123", 
            "analysis_results": {"coordination_ok": True}
        }
    },
    "/api/v1/ml-gateway/results/simulation/{job_uuid}": {
        "simulation_results": {
            "job_id": "test_job_123",
            "scenarios": [{"name": "test", "result": "pass"}]
        }
    },
    "/api/v1/ml-gateway/recommendations": {
        "equipment_data": {"relay_001": {"model": "MiCOM P143"}},
        "analysis_type": "coordination"
    },
    
    # ETAP - Casos específicos
    "/api/v1/etap/studies/{study_id}/equipment": {
        "equipment_id": "test_relay_001", 
        "device_type": "protection_relay", 
        "voltage_level": "138kV"
    },
    "/api/v1/etap/import-csv": {},  # Precisa de file upload, vamos testar sem
    
    # ML-GATEWAY Cancel e outros
    "/api/v1/ml-gateway/jobs/{job_uuid}/cancel": {
        "reason": "test_cancellation"
    },
    "/api/v1/ml-gateway/data/extract": {
        "equipment_ids": [1],
        "data_types": ["configuration", "measurements"]
    },
    "/api/v1/ml-gateway/bulk-upload": {
        "files_metadata": [{"name": "test.csv", "type": "configuration"}]
    }
}

def test_endpoint_precise(endpoint, method="POST", payload=None):
    """Testa um endpoint com payload específico"""
    url = f"{BASE_URL}{endpoint}"
    
    # Substituir placeholders
    url = url.replace("{study_id}", "STUDY_001")
    url = url.replace("{import_id}", "123") 
    url = url.replace("{job_uuid}", "test_job_123")
    
    try:
        if method == "POST":
            if endpoint in ["/api/v1/etap/import-csv"]:
                # Endpoints que precisam de file upload - testar sem arquivo por enquanto
                response = requests.post(url, files={}, timeout=TIMEOUT)
            else:
                response = requests.post(url, json=payload, timeout=TIMEOUT)
        elif method == "DELETE":
            response = requests.delete(url, json=payload, timeout=TIMEOUT)
        elif method == "PUT":
            response = requests.put(url, json=payload, timeout=TIMEOUT)
        else:
            response = requests.get(url, timeout=TIMEOUT)
            
        return response.status_code, response.text
        
    except requests.exceptions.Timeout:
        return 408, "Request Timeout"
    except requests.exceptions.ConnectionError:
        return 503, "Connection Error"
    except Exception as e:
        return 500, f"Error: {str(e)}"

def main():
    """Executa teste preciso dos endpoints problemáticos"""
    print("🎯 TESTE PRECISO DOS ENDPOINTS PROBLEMÁTICOS")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Objetivo: Testar com payloads específicos corretos\n")
    
    # Endpoints que falharam no último teste
    failed_endpoints = [
        ("/api/v1/etap/studies/{study_id}/equipment", "POST"),
        ("/api/v1/etap/import-csv", "POST"),
        ("/api/v1/etap-native/initialize", "POST"),
        ("/api/v1/etap-native/import", "POST"),
        ("/api/v1/etap-native/batch/import-studies", "POST"),
        ("/api/v1/validation/", "POST"),
        ("/api/v1/validation/custom", "POST"),
        ("/api/v1/ml-gateway/jobs/{job_uuid}/cancel", "POST"),
        ("/api/v1/ml-gateway/data/extract", "POST"),
        ("/api/v1/ml-gateway/results/coordination/{job_uuid}", "POST"),
        ("/api/v1/ml-gateway/results/selectivity/{job_uuid}", "POST"),
        ("/api/v1/ml-gateway/results/simulation/{job_uuid}", "POST"),
        ("/api/v1/ml-gateway/recommendations", "POST"),
        ("/api/v1/ml-gateway/bulk-upload", "POST"),
    ]
    
    successes = 0
    total = len(failed_endpoints)
    results = []
    
    for i, (endpoint, method) in enumerate(failed_endpoints, 1):
        payload = ENDPOINT_PAYLOADS.get(endpoint, {})
        
        print(f"[{i:2d}/{total}] Testando: {method} {endpoint}")
        print(f"          Payload: {json.dumps(payload) if payload else '{}'}")
        
        status, response = test_endpoint_precise(endpoint, method, payload)
        
        if status in [200, 201]:
            print(f"         ✅ {status} - SUCCESS")
            successes += 1
            results.append({"endpoint": endpoint, "status": status, "success": True})
        else:
            print(f"         ❌ {status} - FAILED")
            print(f"         Resposta: {response[:100]}...")
            results.append({"endpoint": endpoint, "status": status, "success": False, "response": response[:200]})
        
        print()
    
    # Resultado final
    success_rate = (successes / total) * 100
    print("=" * 60)
    print("📊 RESULTADOS FINAIS")
    print("=" * 60)
    print(f"🎯 TOTAL TESTADO: {total} endpoints")
    print(f"✅ SUCESSOS: {successes} ({success_rate:.1f}%)")
    print(f"❌ FALHAS: {total - successes}")
    
    # Salvar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = Path(f"temp/test_results/precise_test_results_{timestamp}.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump({
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "total_endpoints": total,
                "test_type": "precise_endpoint_testing"
            },
            "summary": {
                "total": total,
                "successful": successes,
                "success_rate": success_rate
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Resultados salvos em: {results_file}")
    
    if success_rate > 70:
        print("🎉 EXCELENTE! Maioria dos endpoints funcionando!")
    elif success_rate > 50:
        print("👍 BOM PROGRESSO! Mais da metade funcionando!")
    else:
        print("⚠️ NECESSITA MAIS TRABALHO!")

if __name__ == "__main__":
    main()
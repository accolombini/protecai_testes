#!/usr/bin/env python3
"""
🧪 TESTE INTELIGENTE DOS ENDPOINTS POST/PUT/DELETE
=================================================

Script para testar adequadamente os 27 endpoints POST/PUT/DELETE 
com payloads corretos e dados apropriados.

Petrobras ProtecAI - 27/10/2025
"""

import requests
import json
import tempfile
from datetime import datetime
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 10

def get_smart_payload(endpoint: str, method: str) -> Dict[str, Any]:
    """Retorna payload inteligente baseado no endpoint"""
    
    # 📋 PAYLOADS ESPECÍFICOS POR ENDPOINT
    payloads = {
        "/api/v1/compare/equipment-configurations": {
            "method": "POST",
            "data": ["test_123", "test_456"],
            "content_type": "application/json"
        },
        "/api/v1/imports/reprocess/{import_id}": {
            "method": "POST", 
            "data": {"force_reprocess": True, "validate_data": True},
            "content_type": "application/json"
        },
        "/api/v1/imports/delete/{import_id}": {
            "method": "DELETE",
            "data": None,
            "content_type": "application/json"
        },
        "/api/v1/imports/upload": {
            "method": "POST",
            "data": "FILE_UPLOAD",  # Especial - precisa de arquivo
            "content_type": "multipart/form-data"
        },
        "/api/v1/etap/studies/{study_id}/equipment": {
            "method": "POST",
            "data": {
                "equipment_id": "test_relay_001",
                "device_type": "protection_relay",
                "voltage_level": "138kV"
            },
            "content_type": "application/json"
        },
        "/api/v1/etap/studies/import/csv": {
            "method": "POST",
            "data": "CSV_UPLOAD",  # Especial - precisa de CSV
            "content_type": "multipart/form-data"
        },
        "/api/v1/etap/import-csv": {
            "method": "POST",
            "data": "CSV_UPLOAD",
            "content_type": "multipart/form-data"
        },
        "/api/v1/etap/batch-import": {
            "method": "POST",
            "data": {
                "studies": ["study_001", "study_002"],
                "import_format": "etap_compatible"
            },
            "content_type": "application/json"
        },
        "/api/v1/etap-native/initialize": {
            "method": "POST",
            "data": {
                "connection_type": "api",
                "host": "localhost",
                "port": 8888
            },
            "content_type": "application/json"
        },
        "/api/v1/etap-native/test-capabilities": {
            "method": "POST",
            "data": {"test_type": "connectivity"},
            "content_type": "application/json"
        },
        "/api/v1/etap-native/import": {
            "method": "POST",
            "data": {
                "source_file": "test_study.etap",
                "import_options": {"validate": True}
            },
            "content_type": "application/json"
        },
        "/api/v1/etap-native/export": {
            "method": "POST",
            "data": {
                "study_id": "test_study_123",
                "export_format": "etap_native"
            },
            "content_type": "application/json"
        },
        "/api/v1/etap-native/analyze/coordination": {
            "method": "POST",
            "data": {
                "study_id": "test_study_123",
                "analysis_type": "time_current_coordination"
            },
            "content_type": "application/json"
        },
        "/api/v1/etap-native/analyze/selectivity": {
            "method": "POST",
            "data": {
                "study_id": "test_study_123",
                "selectivity_margin": 0.3
            },
            "content_type": "application/json"
        },
        "/api/v1/etap-native/batch/import-studies": {
            "method": "POST",
            "data": {
                "study_files": ["study1.etap", "study2.etap"],
                "batch_options": {"parallel": True}
            },
            "content_type": "application/json"
        },
        "/api/v1/etap-native/batch/analyze-studies": {
            "method": "POST",
            "data": {
                "study_ids": ["test_study_123", "test_study_456"],
                "analysis_types": ["coordination", "selectivity"]
            },
            "content_type": "application/json"
        },
        "/api/v1/ml/optimize": {
            "method": "POST",
            "data": {
                "equipment_ids": ["test_123", "test_456"],
                "optimization_type": "coordination",
                "constraints": {"max_time": 0.5}
            },
            "content_type": "application/json"
        },
        "/api/v1/ml/feedback": {
            "method": "POST",
            "data": {
                "optimization_id": "opt_123",
                "rating": 4,
                "comments": "Good results"
            },
            "content_type": "application/json"
        },
        "/api/v1/validation/": {
            "method": "POST",
            "data": {
                "equipment_data": {
                    "id": "test_123",
                    "voltage": "138kV",
                    "current": "600A"
                },
                "validation_rules": ["voltage_range", "current_rating"]
            },
            "content_type": "application/json"
        },
        "/api/v1/validation/custom": {
            "method": "POST",
            "data": {
                "custom_rules": [
                    {"parameter": "voltage", "min": 100, "max": 150}
                ],
                "data_to_validate": {"voltage": 138}
            },
            "content_type": "application/json"
        },
        "/api/v1/ml-gateway/jobs/{job_uuid}/cancel": {
            "method": "POST",
            "data": {"reason": "User requested cancellation"},
            "content_type": "application/json"
        },
        "/api/v1/ml-gateway/data/extract": {
            "method": "POST",
            "data": {
                "source_systems": ["etap", "database"],
                "data_types": ["equipment", "studies"]
            },
            "content_type": "application/json"
        },
        "/api/v1/ml-gateway/results/coordination/{job_uuid}": {
            "method": "POST",
            "data": {
                "result_data": {
                    "coordination_margin": 0.3,
                    "recommendations": ["Adjust relay 1", "Review relay 2"]
                }
            },
            "content_type": "application/json"
        },
        "/api/v1/ml-gateway/results/selectivity/{job_uuid}": {
            "method": "POST",
            "data": {
                "selectivity_results": {
                    "analysis_complete": True,
                    "issues_found": 2
                }
            },
            "content_type": "application/json"
        },
        "/api/v1/ml-gateway/results/simulation/{job_uuid}": {
            "method": "POST",
            "data": {
                "simulation_data": {
                    "fault_scenarios": 5,
                    "success_rate": 95.5
                }
            },
            "content_type": "application/json"
        },
        "/api/v1/ml-gateway/recommendations": {
            "method": "POST",
            "data": {
                "equipment_ids": ["test_123"],
                "analysis_type": "optimization",
                "priority": "high"
            },
            "content_type": "application/json"
        },
        "/api/v1/ml-gateway/bulk-upload": {
            "method": "POST",
            "data": "FILE_UPLOAD",
            "content_type": "multipart/form-data"
        }
    }
    
    return payloads.get(endpoint, {
        "method": method,
        "data": {"test": True},
        "content_type": "application/json"
    })

def create_test_file():
    """Cria arquivo temporário para testes de upload"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("equipment_id,type,voltage\n")
        f.write("test_relay_001,protection_relay,138kV\n")
        f.write("test_relay_002,protection_relay,69kV\n")
        return f.name

def test_endpoint_smart(endpoint: str, method: str) -> Dict[str, Any]:
    """Testa endpoint com payload inteligente"""
    
    # Adaptar endpoint para teste
    test_endpoint = endpoint
    test_endpoint = test_endpoint.replace("{import_id}", "test_import_123")
    test_endpoint = test_endpoint.replace("{study_id}", "test_study_123")
    test_endpoint = test_endpoint.replace("{job_uuid}", "test_job_uuid_123")
    
    payload_config = get_smart_payload(endpoint, method)
    
    full_url = f"{BASE_URL}{test_endpoint}"
    
    try:
        if payload_config["content_type"] == "multipart/form-data":
            # Endpoints que precisam de arquivo
            test_file = create_test_file()
            with open(test_file, 'rb') as f:
                files = {'file': ('test_data.csv', f, 'text/csv')}
                response = requests.post(full_url, files=files, timeout=TIMEOUT)
        
        elif method.upper() == "POST":
            response = requests.post(
                full_url, 
                json=payload_config["data"],
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
            )
        elif method.upper() == "DELETE":
            response = requests.delete(full_url, timeout=TIMEOUT)
        else:
            response = requests.request(
                method.upper(),
                full_url,
                json=payload_config["data"],
                timeout=TIMEOUT
            )
        
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response_size": len(response.content),
            "payload_type": "smart_payload"
        }
        
    except Exception as e:
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": f"ERROR: {str(e)}",
            "success": False,
            "response_size": 0,
            "payload_type": "smart_payload"
        }

def main():
    """Executar teste inteligente dos endpoints POST/PUT/DELETE"""
    
    # Endpoints que falharam no teste anterior
    failed_endpoints = [
        ("/api/v1/compare/equipment-configurations", "POST"),
        ("/api/v1/imports/reprocess/{import_id}", "POST"),
        ("/api/v1/imports/delete/{import_id}", "DELETE"),
        ("/api/v1/imports/upload", "POST"),
        ("/api/v1/etap/studies/{study_id}/equipment", "POST"),
        ("/api/v1/etap/studies/import/csv", "POST"),
        ("/api/v1/etap/import-csv", "POST"),
        ("/api/v1/etap/batch-import", "POST"),
        ("/api/v1/etap-native/initialize", "POST"),
        ("/api/v1/etap-native/test-capabilities", "POST"),
        ("/api/v1/etap-native/import", "POST"),
        ("/api/v1/etap-native/export", "POST"),
        ("/api/v1/etap-native/analyze/coordination", "POST"),
        ("/api/v1/etap-native/analyze/selectivity", "POST"),
        ("/api/v1/etap-native/batch/import-studies", "POST"),
        ("/api/v1/etap-native/batch/analyze-studies", "POST"),
        ("/api/v1/ml/optimize", "POST"),
        ("/api/v1/ml/feedback", "POST"),
        ("/api/v1/validation/", "POST"),
        ("/api/v1/validation/custom", "POST"),
        ("/api/v1/ml-gateway/jobs/{job_uuid}/cancel", "POST"),
        ("/api/v1/ml-gateway/data/extract", "POST"),
        ("/api/v1/ml-gateway/results/coordination/{job_uuid}", "POST"),
        ("/api/v1/ml-gateway/results/selectivity/{job_uuid}", "POST"),
        ("/api/v1/ml-gateway/results/simulation/{job_uuid}", "POST"),
        ("/api/v1/ml-gateway/recommendations", "POST"),
        ("/api/v1/ml-gateway/bulk-upload", "POST")
    ]
    
    print("🧪 TESTE INTELIGENTE DOS 27 ENDPOINTS POST/PUT/DELETE")
    print("=" * 65)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Objetivo: Testar com payloads corretos")
    print()
    
    results = []
    success_count = 0
    
    for i, (endpoint, method) in enumerate(failed_endpoints, 1):
        print(f"[{i:2d}/27] Testando: {method} {endpoint}")
        
        result = test_endpoint_smart(endpoint, method)
        results.append(result)
        
        if result["success"]:
            success_count += 1
            print(f"         ✅ {result['status_code']} - SUCCESS")
        else:
            print(f"         ❌ {result['status_code']} - FAILED")
    
    print()
    print("=" * 65)
    print("📊 RESULTADOS FINAIS")
    print("=" * 65)
    print(f"🎯 TOTAL TESTADO: 27 endpoints")
    print(f"✅ SUCESSOS: {success_count} ({success_count/27*100:.1f}%)")
    print(f"❌ FALHAS: {27 - success_count}")
    print()
    
    # Salvar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"smart_post_test_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "total_endpoints": 27,
                "test_type": "smart_post_testing"
            },
            "summary": {
                "total": 27,
                "successful": success_count,
                "success_rate": success_count/27*100
            },
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Resultados salvos em: {filename}")
    
    if success_count >= 20:
        print("🎉 EXCELENTE! Maioria dos endpoints funcionando!")
    elif success_count >= 15:
        print("👍 BOM PROGRESSO! Endpoints respondendo adequadamente!")
    else:
        print("⚠️ NECESSITA INVESTIGAÇÃO: Muitos endpoints ainda falhando")
    
    return success_count

if __name__ == "__main__":
    main()
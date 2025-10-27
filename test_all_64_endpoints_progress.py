#!/usr/bin/env python3
"""
📊 TESTE COMPLETO 64 ENDPOINTS - MEDIÇÃO DE PROGRESSO
====================================================

Script para medir o progresso real dos 3 adaptadores implementados:
- equipment_id adapter (Equipment Service)
- job_uuid adapter (ML Gateway)  
- study_id adapter (ETAP Service)

Petrobras ProtecAI - 27/10/2025
"""

import requests
import json
import time
from datetime import datetime
from urllib.parse import quote

# Configuração do servidor
BASE_URL = "http://localhost:8000"
TIMEOUT = 10

def get_all_endpoints():
    """Obter todos os 64 endpoints do OpenAPI"""
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=TIMEOUT)
        if response.status_code == 200:
            openapi_data = response.json()
            endpoints = list(openapi_data.get('paths', {}).keys())
            print(f"✅ Encontrados {len(endpoints)} endpoints no OpenAPI")
            return endpoints
        else:
            print(f"❌ Erro ao obter OpenAPI: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return []

def test_endpoint_with_params(endpoint, method="GET"):
    """Testar endpoint com parâmetros de teste apropriados"""
    
    # Adaptar endpoint para teste com IDs fictícios
    test_endpoint = endpoint
    
    # 🔧 ADAPTAÇÃO 1: Equipment ID (testar nosso adapter)
    if "{equipment_id}" in endpoint:
        test_endpoint = endpoint.replace("{equipment_id}", "test_123")
    
    # 🔧 ADAPTAÇÃO 2: Job UUID (testar nosso adapter)
    if "{job_uuid}" in endpoint:
        test_endpoint = endpoint.replace("{job_uuid}", "test_job_uuid_123")
    
    # 🔧 ADAPTAÇÃO 3: Study ID (testar nosso adapter)
    if "{study_id}" in endpoint:
        test_endpoint = endpoint.replace("{study_id}", "test_study_123")
    
    # Outros parâmetros comuns
    test_endpoint = test_endpoint.replace("{file_id}", "test_file_123")
    test_endpoint = test_endpoint.replace("{comparison_id}", "test_comparison_123")
    test_endpoint = test_endpoint.replace("{analysis_id}", "test_analysis_123")
    test_endpoint = test_endpoint.replace("{recommendation_id}", "test_rec_123")
    test_endpoint = test_endpoint.replace("{import_id}", "test_import_123")
    test_endpoint = test_endpoint.replace("{validation_id}", "test_validation_123")
    
    full_url = f"{BASE_URL}{test_endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(full_url, timeout=TIMEOUT)
        elif method.upper() == "POST":
            # Para POST, enviar payload mínimo
            response = requests.post(full_url, json={}, timeout=TIMEOUT)
        elif method.upper() == "PUT":
            response = requests.put(full_url, json={}, timeout=TIMEOUT)
        elif method.upper() == "DELETE":
            response = requests.delete(full_url, timeout=TIMEOUT)
        else:
            response = requests.get(full_url, timeout=TIMEOUT)
        
        return {
            "endpoint": endpoint,
            "test_url": test_endpoint,
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response_size": len(response.content),
            "adapter_used": detect_adapter_usage(endpoint, response.status_code)
        }
        
    except requests.exceptions.Timeout:
        return {
            "endpoint": endpoint,
            "test_url": test_endpoint,
            "status_code": "TIMEOUT",
            "success": False,
            "response_size": 0,
            "adapter_used": "none"
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "test_url": test_endpoint,
            "status_code": f"ERROR: {str(e)}",
            "success": False,
            "response_size": 0,
            "adapter_used": "none"
        }

def detect_adapter_usage(endpoint, status_code):
    """Detectar qual adapter foi usado baseado no endpoint"""
    if "{equipment_id}" in endpoint and status_code == 200:
        return "equipment_id_adapter"
    elif "{job_uuid}" in endpoint and status_code == 200:
        return "job_uuid_adapter"
    elif "{study_id}" in endpoint and status_code == 200:
        return "study_id_adapter"
    elif status_code == 200:
        return "native_success"
    else:
        return "none"

def analyze_results(results):
    """Analisar resultados e gerar estatísticas"""
    total = len(results)
    success_count = sum(1 for r in results if r["success"])
    
    # Contar por tipo de adapter
    equipment_adapter = sum(1 for r in results if r["adapter_used"] == "equipment_id_adapter")
    job_uuid_adapter = sum(1 for r in results if r["adapter_used"] == "job_uuid_adapter")
    study_id_adapter = sum(1 for r in results if r["adapter_used"] == "study_id_adapter")
    native_success = sum(1 for r in results if r["adapter_used"] == "native_success")
    
    # Contar por status code
    status_codes = {}
    for r in results:
        code = str(r["status_code"])
        status_codes[code] = status_codes.get(code, 0) + 1
    
    return {
        "total_endpoints": total,
        "successful": success_count,
        "success_rate": (success_count / total * 100) if total > 0 else 0,
        "adapter_usage": {
            "equipment_id_adapter": equipment_adapter,
            "job_uuid_adapter": job_uuid_adapter,
            "study_id_adapter": study_id_adapter,
            "native_success": native_success,
            "total_adapter_fixes": equipment_adapter + job_uuid_adapter + study_id_adapter
        },
        "status_codes": status_codes,
        "failed_endpoints": [r["endpoint"] for r in results if not r["success"]]
    }

def main():
    """Executar teste completo dos 64 endpoints"""
    print("🚀 INICIANDO TESTE COMPLETO DOS 64 ENDPOINTS")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Objetivo: Medir progresso dos adaptadores implementados")
    print()
    
    # Obter todos os endpoints
    endpoints = get_all_endpoints()
    if not endpoints:
        print("❌ Não foi possível obter endpoints. Verifique se o servidor está rodando.")
        return
    
    print(f"📊 Testando {len(endpoints)} endpoints...")
    print()
    
    results = []
    
    # Testar cada endpoint
    for i, endpoint in enumerate(endpoints, 1):
        print(f"[{i:2d}/{len(endpoints)}] Testando: {endpoint}")
        result = test_endpoint_with_params(endpoint)
        results.append(result)
        
        # Status visual
        status_icon = "✅" if result["success"] else "❌"
        adapter_info = f" ({result['adapter_used']})" if result['adapter_used'] != 'none' else ""
        print(f"         {status_icon} {result['status_code']}{adapter_info}")
        
        # Pequena pausa para não sobrecarregar
        time.sleep(0.1)
    
    print()
    print("=" * 60)
    print("📊 ANÁLISE DE RESULTADOS")
    print("=" * 60)
    
    # Analisar resultados
    analysis = analyze_results(results)
    
    print(f"🎯 TOTAL DE ENDPOINTS: {analysis['total_endpoints']}")
    print(f"✅ SUCESSOS: {analysis['successful']} ({analysis['success_rate']:.1f}%)")
    print(f"❌ FALHAS: {analysis['total_endpoints'] - analysis['successful']}")
    print()
    
    print("🔧 IMPACTO DOS ADAPTADORES:")
    adapters = analysis['adapter_usage']
    print(f"   📱 Equipment ID Adapter: {adapters['equipment_id_adapter']} endpoints")
    print(f"   🤖 Job UUID Adapter: {adapters['job_uuid_adapter']} endpoints") 
    print(f"   📋 Study ID Adapter: {adapters['study_id_adapter']} endpoints")
    print(f"   🎯 TOTAL CORRIGIDO POR ADAPTADORES: {adapters['total_adapter_fixes']}")
    print(f"   ✨ Sucesso nativo (sem adapter): {adapters['native_success']}")
    print()
    
    print("📈 STATUS CODES:")
    for code, count in sorted(analysis['status_codes'].items()):
        print(f"   {code}: {count} endpoints")
    print()
    
    # Salvar resultados detalhados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"endpoint_progress_test_{timestamp}.json"
    
    detailed_results = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "total_endpoints": len(endpoints),
            "test_type": "progress_measurement"
        },
        "summary": analysis,
        "detailed_results": results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Resultados detalhados salvos em: {filename}")
    print()
    
    # Conclusão
    print("🎯 CONCLUSÃO:")
    if analysis['success_rate'] >= 80:
        print(f"   🎉 EXCELENTE! {analysis['success_rate']:.1f}% de sucesso")
    elif analysis['success_rate'] >= 60:
        print(f"   👍 BOM PROGRESSO! {analysis['success_rate']:.1f}% de sucesso")
    else:
        print(f"   ⚠️  NECESSITA MAIS TRABALHO! {analysis['success_rate']:.1f}% de sucesso")
    
    print(f"   🔧 Adaptadores corrigiram {adapters['total_adapter_fixes']} endpoints")
    print(f"   📋 Próximo: Corrigir schemas POST (P3)")
    
    return analysis

if __name__ == "__main__":
    main()
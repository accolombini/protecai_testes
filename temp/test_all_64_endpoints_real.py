#!/usr/bin/env python3
"""
ProtecAI - Teste Completo de 64 Endpoints (Status Real)
======================================================
Sistema de Proteção de Relés - PETROBRAS
Data: 26 de outubro de 2025

Objetivo: Verificar FUNCIONAMENTO REAL dos 64 endpoints
Context: Ontem (25/10) tínhamos 58/63 funcionais, faltavam 5
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import defaultdict

BASE_URL = "http://localhost:8000"
TIMEOUT = 10

def test_endpoint_functionality(method: str, path: str, test_data: Any = None) -> Tuple[bool, int, str, float]:
    """
    Testa se um endpoint está REALMENTE FUNCIONAL
    
    Returns:
        (success, status_code, error_message, response_time)
    """
    start_time = time.time()
    url = f"{BASE_URL}{path}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=TIMEOUT)
        elif method.upper() == "POST":
            response = requests.post(url, json=test_data or {}, timeout=TIMEOUT)
        elif method.upper() == "PUT":
            response = requests.put(url, json=test_data or {}, timeout=TIMEOUT)
        elif method.upper() == "DELETE":
            response = requests.delete(url, timeout=TIMEOUT)
        else:
            return False, 0, f"Método {method} não suportado", 0
            
        response_time = time.time() - start_time
        
        # Critérios de SUCESSO REAL:
        # - Status 200-299 (sucesso)
        # - Não é erro 404, 422, 500, 501, 503
        # - Resposta tem conteúdo válido
        
        if response.status_code in [200, 201, 202, 204]:
            # Verificar se há conteúdo válido (não erro interno)
            try:
                if response.text:
                    data = response.json()
                    # Verificar se não é erro disfarçado
                    if isinstance(data, dict) and ("error" in data or "detail" in data):
                        return False, response.status_code, f"Erro interno retornado", response_time
                return True, response.status_code, "OK", response_time
            except:
                # Se não conseguir parse JSON, mas status é bom, considerar sucesso
                return True, response.status_code, "OK (non-JSON)", response_time
        else:
            return False, response.status_code, f"HTTP {response.status_code}", response_time
            
    except requests.exceptions.Timeout:
        return False, 0, "Timeout", time.time() - start_time
    except requests.exceptions.ConnectionError:
        return False, 0, "Connection Error", time.time() - start_time
    except Exception as e:
        return False, 0, f"Exception: {str(e)}", time.time() - start_time

def get_all_endpoints() -> Dict[str, List[Tuple[str, str]]]:
    """Busca todos os endpoints do OpenAPI e organiza por router/tag"""
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=TIMEOUT)
        openapi_data = response.json()
        
        endpoints_by_tag = defaultdict(list)
        
        for path, methods in openapi_data["paths"].items():
            for method, details in methods.items():
                # Pega a primeira tag como categoria
                tag = details.get("tags", ["unknown"])[0].lower()
                endpoints_by_tag[tag].append((method.upper(), path))
        
        return dict(endpoints_by_tag)
        
    except Exception as e:
        print(f"❌ Erro ao buscar endpoints: {e}")
        return {}

def main():
    print("🔧 ProtecAI - Teste Completo de 64 Endpoints (Status REAL)")
    print("Sistema de Proteção de Relés - PETROBRAS")
    print(f"Data: {datetime.now().strftime('%d de %B de %Y')}")
    print()
    
    # Verificar se backend está online
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ Backend ProtecAI online e funcionando")
        else:
            print(f"⚠️  Backend respondeu com status {response.status_code}")
    except:
        print("❌ Backend ProtecAI offline! Verificar se está rodando.")
        return
    
    print("🚀 INICIANDO TESTE REAL DE FUNCIONALIDADE")
    print("=" * 60)
    start_time = datetime.now()
    print(f"⏰ Início: {start_time.strftime('%H:%M:%S')}")
    print("🎯 Critério: Apenas endpoints REALMENTE funcionais")
    print()
    
    # Buscar todos os endpoints
    endpoints_by_tag = get_all_endpoints()
    
    if not endpoints_by_tag:
        print("❌ Não foi possível recuperar endpoints")
        return
    
    total_endpoints = sum(len(endpoints) for endpoints in endpoints_by_tag.values())
    print(f"📊 Total de endpoints encontrados: {total_endpoints}")
    print()
    
    # Resultados
    results = {}
    total_success = 0
    total_tested = 0
    api_status = {}
    
    # Testar cada categoria
    for tag, endpoints in sorted(endpoints_by_tag.items()):
        print(f"📍 {tag.upper()} ENDPOINTS")
        
        category_success = 0
        category_total = len(endpoints)
        category_results = []
        
        for method, path in sorted(endpoints):
            total_tested += 1
            
            # Testar funcionalidade real
            success, status_code, error_msg, response_time = test_endpoint_functionality(method, path)
            
            if success:
                print(f"  ✅ {method} {path} ({response_time:.3f}s)")
                total_success += 1
                category_success += 1
            else:
                print(f"  ❌ {method} {path} - {error_msg}")
            
            category_results.append({
                "method": method,
                "path": path,
                "success": success,
                "status_code": status_code,
                "error": error_msg,
                "response_time": response_time
            })
        
        # Status da API
        success_rate = (category_success / category_total) * 100 if category_total > 0 else 0
        api_status[tag] = {
            "success": category_success,
            "total": category_total,
            "rate": success_rate,
            "status": "🟢" if success_rate == 100 else "🟡" if success_rate >= 70 else "🔴"
        }
        
        print(f"  → {category_success}/{category_total} funcionais ({success_rate:.1f}%)")
        print()
        
        results[tag] = category_results
    
    # Relatório final
    print("=" * 60)
    print("🏆 RELATÓRIO FINAL - TESTE DE FUNCIONALIDADE REAL")
    print("=" * 60)
    
    print("📊 ESTATÍSTICAS GERAIS:")
    print(f"  • Total testado: {total_tested} endpoints")
    print(f"  • Sucessos: {total_success} endpoints")
    print(f"  • Falhas: {total_tested - total_success} endpoints")
    print(f"  • Taxa de sucesso: {(total_success/total_tested)*100:.1f}%")
    print()
    
    print("📋 STATUS POR API:")
    apis_100_percent = []
    for tag, status in sorted(api_status.items()):
        print(f"  • {tag}: {status['success']}/{status['total']} ({status['rate']:.1f}%) {status['status']}")
        if status['rate'] == 100:
            apis_100_percent.append(tag)
    print()
    
    print("🎯 APIS 100% FUNCIONAIS:")
    if apis_100_percent:
        for api in apis_100_percent:
            print(f"  ✅ {api.upper()}")
    else:
        print("  ⚠️  Nenhuma API com 100% de funcionalidade")
    print()
    
    # Comparação com meta
    print("📈 COMPARAÇÃO COM CONTEXTO:")
    print(f"  • Ontem (25/10): 58/63 funcionais (91.3%)")
    print(f"  • Hoje atual: {total_success}/{total_tested} funcionais ({(total_success/total_tested)*100:.1f}%)")
    
    if total_success >= 58:
        print(f"  🎉 MANTIVEMOS OU MELHORAMOS o progresso!")
    else:
        print(f"  ⚠️  REGRESSÃO: perdemos {58 - total_success} endpoints funcionais")
    print()
    
    # Performance
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    avg_response = sum(
        result["response_time"] 
        for category in results.values() 
        for result in category 
        if result["success"]
    ) / max(total_success, 1)
    
    print("⚡ PERFORMANCE:")
    print(f"  • Tempo médio de resposta: {avg_response:.3f}s")
    print(f"  • Duração total do teste: {duration:.1f}s")
    print()
    
    print("🎯 PRÓXIMOS PASSOS:")
    if total_success < total_tested:
        failures = total_tested - total_success
        print(f"  1. Corrigir {failures} endpoints com falha")
        print(f"  2. Focar em APIs com baixa taxa de sucesso")
        print(f"  3. Objetivo: 100% de funcionalidade")
    else:
        print("  🎉 PARABÉNS! Todos os endpoints estão funcionais!")
    print()
    
    print(f"⏰ Teste concluído: {end_time.strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Salvar resultados detalhados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"temp/test_64_endpoints_real_{timestamp}.json"
    
    detailed_results = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tested": total_tested,
            "total_success": total_success,
            "success_rate": (total_success/total_tested)*100,
            "apis_100_percent": apis_100_percent
        },
        "api_status": api_status,
        "detailed_results": results,
        "context": {
            "yesterday": "58/63 funcionais (91.3%)",
            "target": "100% funcionalidade"
        }
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Resultados detalhados salvos em: {results_file}")

if __name__ == "__main__":
    main()
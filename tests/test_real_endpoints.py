#!/usr/bin/env python3
"""
🔧 ProtecAI - Teste Baseado em OpenAPI REAL
============================================
Testa apenas endpoints que REALMENTE existem no sistema.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

class RealEndpointTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.start_time = None
        
    def get_openapi_schema(self) -> Dict[str, Any]:
        """Busca o schema OpenAPI real do sistema."""
        try:
            response = requests.get(f"{self.base_url}/openapi.json", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Erro ao buscar OpenAPI schema: {e}")
            return {}
    
    def extract_real_endpoints(self, schema: Dict[str, Any]) -> List[str]:
        """Extrai apenas endpoints GET que existem no schema."""
        endpoints = []
        
        if "paths" not in schema:
            return endpoints
            
        for path, methods in schema["paths"].items():
            # Apenas endpoints GET para teste de integridade
            if "get" in methods:
                endpoints.append(path)
                
        return sorted(endpoints)
    
    def test_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Testa um endpoint específico."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start = time.time()
            response = requests.get(url, timeout=10)
            duration = time.time() - start
            
            result = {
                "endpoint": endpoint,
                "url": url,
                "status_code": response.status_code,
                "duration": round(duration, 3),
                "success": response.status_code in [200, 201],
                "timestamp": datetime.now().isoformat()
            }
            
            if result["success"]:
                try:
                    # Verificar se retorna JSON válido
                    response.json()
                    result["content_type"] = "json"
                except:
                    result["content_type"] = "other"
            else:
                result["error"] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result = {
                "endpoint": endpoint,
                "url": url,
                "status_code": 0,
                "duration": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
        return result
    
    def run_tests(self):
        """Executa testes em todos os endpoints reais."""
        print("🔧 ProtecAI - Teste de Endpoints REAIS")
        print("Sistema de Proteção de Relés - PETROBRAS")
        print(f"Data: {datetime.now().strftime('%d de %B de %Y')}")
        print()
        
        # Verificar se backend está online
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                print("✅ Backend ProtecAI online e funcionando")
            else:
                print(f"⚠️ Backend responde mas com status {response.status_code}")
        except:
            print("❌ Backend ProtecAI offline!")
            return
            
        # Buscar schema real
        print("📋 Buscando endpoints reais do OpenAPI...")
        schema = self.get_openapi_schema()
        real_endpoints = self.extract_real_endpoints(schema)
        
        if not real_endpoints:
            print("❌ Nenhum endpoint encontrado no schema!")
            return
            
        print(f"📊 Encontrados {len(real_endpoints)} endpoints GET para teste")
        print("🚀 INICIANDO TESTE DE ENDPOINTS REAIS")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # Agrupar por categoria
        endpoint_groups = {}
        for endpoint in real_endpoints:
            parts = endpoint.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "api" and parts[1] == "v1":
                # /api/v1/category/...
                category = parts[2] if len(parts) > 2 else "root"
            else:
                # Endpoints raiz
                category = "root"
                
            if category not in endpoint_groups:
                endpoint_groups[category] = []
            endpoint_groups[category].append(endpoint)
        
        # Testar por categoria
        total_success = 0
        total_tested = 0
        
        for category, endpoints in sorted(endpoint_groups.items()):
            print(f"\\n📍 {category.upper()} ENDPOINTS")
            category_success = 0
            
            for endpoint in endpoints:
                result = self.test_endpoint(endpoint)
                self.results.append(result)
                
                status_icon = "✅" if result["success"] else "❌"
                duration_str = f"({result['duration']}s)" if result["success"] else f"- {result.get('error', 'Error')}"
                
                print(f"  {status_icon} {endpoint} {duration_str}")
                
                if result["success"]:
                    category_success += 1
                    total_success += 1
                total_tested += 1
            
            print(f"  → {category_success}/{len(endpoints)} funcionais")
        
        # Relatório final
        self.generate_final_report(total_success, total_tested)
    
    def generate_final_report(self, total_success: int, total_tested: int):
        """Gera relatório final dos testes."""
        duration = time.time() - self.start_time
        success_rate = (total_success / total_tested * 100) if total_tested > 0 else 0
        
        print("\\n" + "=" * 60)
        print("🏆 RELATÓRIO FINAL - TESTE DE ENDPOINTS REAIS")
        print("=" * 60)
        print(f"📊 ESTATÍSTICAS GERAIS:")
        print(f"  • Total testado: {total_tested} endpoints")
        print(f"  • Sucessos: {total_success} endpoints")
        print(f"  • Falhas: {total_tested - total_success} endpoints")
        print(f"  • Taxa de sucesso: {success_rate:.1f}%")
        
        # Estatísticas por categoria
        category_stats = {}
        for result in self.results:
            endpoint = result["endpoint"]
            parts = endpoint.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "api" and parts[1] == "v1":
                category = parts[2] if len(parts) > 2 else "root"
            else:
                category = "root"
                
            if category not in category_stats:
                category_stats[category] = {"success": 0, "total": 0}
            category_stats[category]["total"] += 1
            if result["success"]:
                category_stats[category]["success"] += 1
        
        print(f"\\n📋 STATUS POR CATEGORIA:")
        for category, stats in sorted(category_stats.items()):
            success_rate_cat = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"  • {category}: {stats['success']}/{stats['total']} ({success_rate_cat:.1f}%)")
        
        # Performance
        if self.results:
            durations = [r["duration"] for r in self.results if r["success"]]
            if durations:
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                print(f"\\n⚡ PERFORMANCE:")
                print(f"  • Tempo médio de resposta: {avg_duration:.3f}s")
                print(f"  • Tempo máximo: {max_duration:.3f}s")
        
        # Conclusão
        print(f"\\n🎯 CONCLUSÃO:")
        if success_rate >= 90:
            print(f"  ✅ EXCELENTE! Sistema com {success_rate:.1f}% de sucesso")
        elif success_rate >= 75:
            print(f"  ✅ BOM! Sistema com {success_rate:.1f}% de sucesso")
        elif success_rate >= 50:
            print(f"  ⚠️  ATENÇÃO! Sistema com {success_rate:.1f}% de sucesso")
        else:
            print(f"  ❌ CRÍTICO! Sistema com {success_rate:.1f}% de sucesso")
        
        print(f"\\n⏰ Teste concluído: {datetime.now().strftime('%H:%M:%S')}")
        print(f"⏱️  Duração total: {duration:.1f}s")
        print("=" * 60)
        
        # Salvar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"temp/real_endpoint_test_results_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_tested": total_tested,
                "total_success": total_success,
                "success_rate": success_rate,
                "duration": duration,
                "results": self.results
            }, f, indent=2)
        
        print(f"💾 Resultados detalhados salvos em: {filename}")

if __name__ == "__main__":
    tester = RealEndpointTester()
    tester.run_tests()
#!/usr/bin/env python3
"""
AUDITORIA COMPLETA DE ENDPOINTS - PERSPECTIVA FRONTEND
======================================================

Varredura sistemática de TODOS os 63 endpoints do ProtecAI
para identificar problemas antes de integrar no frontend.

Evita retrabalho um-a-um. Encontra CAUSA RAIZ.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

class ProtecAIEndpointAuditor:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = []
        self.summary = {
            "total_endpoints": 0,
            "working": 0,
            "broken": 0,
            "by_api": {},
            "common_issues": []
        }
    
    def test_endpoint(self, method: str, endpoint: str, description: str, api_group: str) -> Dict:
        """Testa um endpoint específico"""
        full_url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method.upper() == "GET":
                response = requests.get(full_url, timeout=10)
            elif method.upper() == "POST":
                # POST básico para testar estrutura
                response = requests.post(full_url, json={}, timeout=10)
            else:
                response = requests.request(method, full_url, timeout=10)
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            # Tentar parsear JSON
            try:
                json_data = response.json()
                has_data = bool(json_data)
            except:
                json_data = None
                has_data = False
            
            result = {
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "api_group": api_group,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "working": response.status_code < 400,
                "has_data": has_data,
                "json_response": json_data,
                "headers": dict(response.headers),
                "error": None
            }
            
        except requests.exceptions.ConnectionError:
            result = {
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "api_group": api_group,
                "status_code": None,
                "response_time_ms": None,
                "working": False,
                "has_data": False,
                "json_response": None,
                "headers": {},
                "error": "CONNECTION_REFUSED"
            }
        except requests.exceptions.Timeout:
            result = {
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "api_group": api_group,
                "status_code": None,
                "response_time_ms": None,
                "working": False,
                "has_data": False,
                "json_response": None,
                "headers": {},
                "error": "TIMEOUT"
            }
        except Exception as e:
            result = {
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "api_group": api_group,
                "status_code": None,
                "response_time_ms": None,
                "working": False,
                "has_data": False,
                "json_response": None,
                "headers": {},
                "error": str(e)
            }
        
        return result
    
    def run_audit(self):
        """Executa auditoria completa de todos os endpoints"""
        
        print("🔍 INICIANDO AUDITORIA COMPLETA DE ENDPOINTS")
        print("=" * 60)
        print(f"📅 Timestamp: {datetime.now()}")
        print(f"🎯 Base URL: {self.base_url}")
        print()
        
        # ENDPOINTS MAPEADOS ONTEM (63 total)
        endpoints_to_test = [
            # ROOT API (3 endpoints)
            ("GET", "/", "Root endpoint", "Root"),
            ("GET", "/health", "Health check", "Root"),
            ("GET", "/api/v1/info", "API information", "Root"),
            
            # EQUIPMENT API (11 endpoints)
            ("GET", "/api/v1/equipments/", "List equipments", "Equipment"),
            ("GET", "/api/v1/equipments/statistics/unified", "Equipment statistics", "Equipment"),
            ("GET", "/api/v1/equipments/manufacturers/unified", "Equipment manufacturers", "Equipment"),
            ("POST", "/api/v1/equipments/", "Create equipment", "Equipment"),
            ("PUT", "/api/v1/equipments/protec_ai_5", "Update equipment", "Equipment"),
            ("DELETE", "/api/v1/equipments/protec_ai_5", "Delete equipment", "Equipment"),
            ("GET", "/api/v1/equipments/protec_ai_5/electrical", "Equipment electrical data", "Equipment"),
            ("GET", "/api/v1/equipments/protec_ai_5/protection-functions", "Protection functions", "Equipment"),
            ("GET", "/api/v1/equipments/protec_ai_5/io-configuration", "I/O configuration", "Equipment"),
            ("GET", "/api/v1/equipments/protec_ai_5/summary", "Equipment summary", "Equipment"),
            ("GET", "/api/v1/equipments/protec_ai_5", "Equipment details", "Equipment"),
            
            # IMPORT API (7 endpoints)
            ("GET", "/api/v1/imports/statistics", "Import statistics", "Import"),
            ("GET", "/api/v1/imports/history", "Import history", "Import"),
            ("GET", "/api/v1/imports/details/1", "Import details", "Import"),
            ("POST", "/api/v1/imports/reprocess/1", "Reprocess import", "Import"),
            ("DELETE", "/api/v1/imports/delete/1", "Delete import", "Import"),
            ("POST", "/api/v1/imports/upload", "Upload file", "Import"),
            ("GET", "/api/v1/imports/status", "Import status", "Import"),
            
            # COMPARE API (2 endpoints)
            ("POST", "/api/v1/compare/", "Compare configurations", "Compare"),
            ("GET", "/api/v1/compare/reports/1", "Comparison report", "Compare"),
            
            # ETAP NATIVE API (12 endpoints)
            ("POST", "/api/v1/etap-native/initialize", "Initialize ETAP", "ETAP Native"),
            ("GET", "/api/v1/etap-native/auto-detect", "Auto-detect ETAP", "ETAP Native"),
            ("GET", "/api/v1/etap-native/status", "ETAP status", "ETAP Native"),
            ("POST", "/api/v1/etap-native/test-capabilities", "Test capabilities", "ETAP Native"),
            ("POST", "/api/v1/etap-native/import", "Import ETAP data", "ETAP Native"),
            ("POST", "/api/v1/etap-native/export", "Export to ETAP", "ETAP Native"),
            ("POST", "/api/v1/etap-native/analyze/coordination", "Coordination analysis", "ETAP Native"),
            ("POST", "/api/v1/etap-native/analyze/selectivity", "Selectivity analysis", "ETAP Native"),
            ("POST", "/api/v1/etap-native/batch/import-studies", "Batch import", "ETAP Native"),
            ("POST", "/api/v1/etap-native/batch/analyze-studies", "Batch analysis", "ETAP Native"),
            ("GET", "/api/v1/etap-native/performance/metrics", "Performance metrics", "ETAP Native"),
            ("GET", "/api/v1/etap-native/health", "ETAP health check", "ETAP Native"),
            
            # ML GATEWAY API (14 endpoints)
            ("GET", "/api/v1/ml-gateway/health", "ML Gateway health", "ML Gateway"),
            ("POST", "/api/v1/ml-gateway/jobs", "Create ML job", "ML Gateway"),
            ("GET", "/api/v1/ml-gateway/jobs", "List ML jobs", "ML Gateway"),
            ("GET", "/api/v1/ml-gateway/jobs/test-uuid", "ML job status", "ML Gateway"),
            ("DELETE", "/api/v1/ml-gateway/jobs/test-uuid", "Cancel ML job", "ML Gateway"),
            ("POST", "/api/v1/ml-gateway/data/extract", "Extract ML data", "ML Gateway"),
            ("GET", "/api/v1/ml-gateway/data/studies", "ML studies data", "ML Gateway"),
            ("GET", "/api/v1/ml-gateway/data/equipment", "ML equipment data", "ML Gateway"),
            ("POST", "/api/v1/ml-gateway/results/coordination/test-uuid", "Coordination results", "ML Gateway"),
            ("POST", "/api/v1/ml-gateway/results/selectivity/test-uuid", "Selectivity results", "ML Gateway"),
            ("POST", "/api/v1/ml-gateway/results/simulation/test-uuid", "Simulation results", "ML Gateway"),
            ("POST", "/api/v1/ml-gateway/recommendations", "ML recommendations", "ML Gateway"),
            ("GET", "/api/v1/ml-gateway/export/test-uuid", "Export ML results", "ML Gateway"),
            ("POST", "/api/v1/ml-gateway/bulk-upload", "Bulk upload", "ML Gateway"),
            
            # VALIDATION API (3 endpoints)
            ("POST", "/api/v1/validation/", "Standard validation", "Validation"),
            ("GET", "/api/v1/validation/rules", "Validation rules", "Validation"),
            ("POST", "/api/v1/validation/custom", "Custom validation", "Validation"),
            
            # ETAP INTEGRATION API (11 endpoints)
            ("POST", "/api/v1/etap/studies", "Create ETAP study", "ETAP Integration"),
            ("GET", "/api/v1/etap/studies", "List ETAP studies", "ETAP Integration"),
            ("GET", "/api/v1/etap/studies/1", "ETAP study details", "ETAP Integration"),
            ("POST", "/api/v1/etap/studies/1/equipment", "Add equipment to study", "ETAP Integration"),
            ("POST", "/api/v1/etap/studies/import/csv", "Import CSV to study", "ETAP Integration"),
            ("GET", "/api/v1/etap/studies/1/export/csv", "Export study to CSV", "ETAP Integration"),
            ("GET", "/api/v1/etap/integration/status", "ETAP integration status", "ETAP Integration"),
            ("POST", "/api/v1/etap/import-csv", "Simple CSV import", "ETAP Integration"),
            ("GET", "/api/v1/etap/studies/1/export-csv", "Simple CSV export", "ETAP Integration"),
            ("POST", "/api/v1/etap/batch-import", "Batch import", "ETAP Integration"),
            ("GET", "/api/v1/etap/studies/1/migration-status", "Migration status", "ETAP Integration"),
        ]
        
        self.summary["total_endpoints"] = len(endpoints_to_test)
        
        # Executar testes
        for method, endpoint, description, api_group in endpoints_to_test:
            print(f"🧪 Testando: {method} {endpoint}")
            result = self.test_endpoint(method, endpoint, description, api_group)
            self.results.append(result)
            
            # Atualizar summary
            if api_group not in self.summary["by_api"]:
                self.summary["by_api"][api_group] = {"total": 0, "working": 0, "broken": 0}
            
            self.summary["by_api"][api_group]["total"] += 1
            
            if result["working"]:
                self.summary["working"] += 1
                self.summary["by_api"][api_group]["working"] += 1
                status = "✅ OK"
            else:
                self.summary["broken"] += 1
                self.summary["by_api"][api_group]["broken"] += 1
                status = f"❌ {result['status_code'] or result['error']}"
            
            print(f"   └─ {status}")
        
        self.generate_report()
    
    def generate_report(self):
        """Gera relatório detalhado"""
        
        print("\n" + "=" * 80)
        print("📊 RELATÓRIO DE AUDITORIA COMPLETA")
        print("=" * 80)
        
        # Resumo geral
        success_rate = (self.summary["working"] / self.summary["total_endpoints"]) * 100
        print(f"📈 RESUMO GERAL:")
        print(f"   • Total de endpoints: {self.summary['total_endpoints']}")
        print(f"   • ✅ Funcionando: {self.summary['working']}")
        print(f"   • ❌ Com problemas: {self.summary['broken']}")
        print(f"   • 📊 Taxa de sucesso: {success_rate:.1f}%")
        print()
        
        # Por API
        print(f"📋 DETALHAMENTO POR API:")
        for api_name, stats in self.summary["by_api"].items():
            api_success_rate = (stats["working"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            status_icon = "✅" if api_success_rate == 100 else "⚠️" if api_success_rate >= 50 else "❌"
            print(f"   {status_icon} {api_name:15} | {stats['working']:2}/{stats['total']:2} ({api_success_rate:5.1f}%)")
        print()
        
        # Problemas encontrados
        broken_endpoints = [r for r in self.results if not r["working"]]
        if broken_endpoints:
            print(f"🚨 ENDPOINTS COM PROBLEMAS ({len(broken_endpoints)}):")
            for endpoint in broken_endpoints:
                error_info = endpoint['status_code'] if endpoint['status_code'] else endpoint['error']
                print(f"   ❌ {endpoint['method']:4} {endpoint['endpoint']:40} | {error_info}")
            print()
        
        # Identificar padrões de erro
        error_patterns = {}
        for endpoint in broken_endpoints:
            if endpoint['status_code']:
                error_key = f"HTTP {endpoint['status_code']}"
            else:
                error_key = endpoint['error'] or "UNKNOWN"
            
            if error_key not in error_patterns:
                error_patterns[error_key] = []
            error_patterns[error_key].append(endpoint)
        
        if error_patterns:
            print(f"🔍 PADRÕES DE ERRO IDENTIFICADOS:")
            for error_type, endpoints in error_patterns.items():
                print(f"   🔸 {error_type}: {len(endpoints)} endpoints")
                for ep in endpoints[:3]:  # Mostrar apenas 3 exemplos
                    print(f"      └─ {ep['method']} {ep['endpoint']}")
                if len(endpoints) > 3:
                    print(f"      └─ ... e mais {len(endpoints) - 3} endpoints")
            print()
        
        # Recomendações
        print(f"💡 RECOMENDAÇÕES PARA O FRONTEND:")
        
        if any(ep['status_code'] == 404 for ep in broken_endpoints):
            print("   🔧 Endpoints 404: Verificar prefixos de rotas no FastAPI")
        
        if any(ep['status_code'] == 405 for ep in broken_endpoints):
            print("   🔧 Endpoints 405: Verificar métodos HTTP permitidos")
        
        if any(ep['status_code'] == 422 for ep in broken_endpoints):
            print("   🔧 Endpoints 422: Verificar schemas de validação")
        
        if any(ep.get('error') == 'CONNECTION_REFUSED' for ep in broken_endpoints):
            print("   🔧 Conexão recusada: Verificar se servidor está rodando")
        
        working_endpoints = [r for r in self.results if r["working"]]
        if working_endpoints:
            print(f"   ✅ {len(working_endpoints)} endpoints prontos para integração no frontend")
        
        print()
        print("🎯 PRÓXIMOS PASSOS:")
        print("   1. Corrigir endpoints com 404 (rotas não registradas)")
        print("   2. Ajustar métodos HTTP para endpoints com 405")
        print("   3. Validar schemas para endpoints com 422")
        print("   4. Integrar endpoints funcionais no dashboard")
        print("   5. Criar interfaces específicas para cada API")
        
        # Salvar resultado detalhado
        with open('/Users/accol/Library/Mobile Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes/temp/frontend_audit_results.json', 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": self.summary,
                "detailed_results": self.results
            }, f, indent=2)
        
        print("\n📄 Relatório detalhado salvo em: temp/frontend_audit_results.json")

if __name__ == "__main__":
    auditor = ProtecAIEndpointAuditor()
    auditor.run_audit()
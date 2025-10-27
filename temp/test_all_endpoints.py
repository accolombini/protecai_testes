#!/usr/bin/env python3
"""
🔍 TESTE COMPLETO DOS ENDPOINTS CORRIGIDOS
Verifica se todos os 8 APIs estão funcionando após as correções
"""

import requests
import json
from datetime import datetime

def test_endpoint(name, url, method="GET"):
    """Testa um endpoint específico"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json={}, timeout=5)
        
        status = "✅ ONLINE" if response.status_code in [200, 201, 405] else f"❌ ERROR {response.status_code}"
        
        print(f"{name:20} | {status:15} | {response.status_code:3} | {url}")
        return response.status_code in [200, 201, 405]
    except Exception as e:
        print(f"{name:20} | ❌ OFFLINE    | ERR | {url} ({str(e)[:50]})")
        return False

def main():
    print("🎯 TESTE COMPLETO DOS ENDPOINTS PROTECAI")
    print("=" * 80)
    print(f"📅 Timestamp: {datetime.now()}")
    print()
    
    endpoints = [
        ("Root API", "http://localhost:8000/"),
        ("Equipment List", "http://localhost:8000/api/v1/equipments/"),
        ("Equipment Stats", "http://localhost:8000/api/v1/equipments/statistics/unified"),
        ("Equipment Manufacturers", "http://localhost:8000/api/v1/equipments/manufacturers/unified"),
        ("Import Statistics", "http://localhost:8000/api/v1/imports/statistics"),
        ("Import History", "http://localhost:8000/api/v1/imports/history"),
        ("Compare API", "http://localhost:8000/api/v1/compare/", "POST"),
        ("ETAP Native Status", "http://localhost:8000/api/v1/etap-native/status"),
        ("ETAP Integration", "http://localhost:8000/api/v1/etap/integration/status"),
        ("ML Gateway Health", "http://localhost:8000/api/v1/ml-gateway/health"),
        ("Validation Rules", "http://localhost:8000/api/v1/validation/rules"),
    ]
    
    online_count = 0
    total_count = len(endpoints)
    
    for name, url, *method in endpoints:
        method = method[0] if method else "GET"
        if test_endpoint(name, url, method):
            online_count += 1
    
    print()
    print("=" * 80)
    print(f"📊 RESULTADO: {online_count}/{total_count} endpoints funcionando")
    
    if online_count == total_count:
        print("🎉 TODOS OS ENDPOINTS FUNCIONANDO! SISTEMA 100% OPERACIONAL!")
    elif online_count > total_count * 0.8:
        print("⚠️  MAIORIA DOS ENDPOINTS FUNCIONANDO - Alguns ajustes necessários")
    else:
        print("❌ PROBLEMAS CRÍTICOS DETECTADOS - Revisar configurações")

if __name__ == "__main__":
    main()
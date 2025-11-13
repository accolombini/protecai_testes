#!/usr/bin/env python3
"""
Test Report Endpoints - Validação dos Endpoints de Relatórios
============================================================

Testa os novos endpoints de relatórios:
- Metadados
- Exportação multi-formato
- Filtros dinâmicos
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_metadata():
    """Testa endpoint de metadados"""
    print("\n🔍 Testando /api/v1/reports/metadata...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/metadata")
        if response.status_code == 200:
            data = response.json()
            print("✅ Metadados obtidos com sucesso!")
            print(f"   - Status disponíveis: {len(data['enums']['status'])}")
            print(f"   - Fabricantes: {len(data['dynamic']['manufacturers'])}")
            print(f"   - Modelos: {len(data['dynamic']['models'])}")
            print(f"   - Total equipamentos: {data['dynamic']['total_equipments']}")
            return True
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_manufacturers():
    """Testa endpoint de fabricantes"""
    print("\n🏭 Testando /api/v1/reports/manufacturers...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/manufacturers")
        if response.status_code == 200:
            data = response.json()
            print("✅ Fabricantes obtidos!")
            for mfg in data['manufacturers'][:5]:
                print(f"   - {mfg['name']}: {mfg['count']} equipamentos")
            return True
        else:
            print(f"❌ Erro {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_models():
    """Testa endpoint de modelos"""
    print("\n📱 Testando /api/v1/reports/models...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/models")
        if response.status_code == 200:
            data = response.json()
            print("✅ Modelos obtidos!")
            for model in data['models'][:5]:
                print(f"   - {model['name']} ({model['manufacturer']}): {model['count']}")
            return True
        else:
            print(f"❌ Erro {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_export_csv():
    """Testa exportação CSV"""
    print("\n📥 Testando exportação CSV...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/export/csv?manufacturer=Schneider")
        if response.status_code == 200:
            print("✅ CSV gerado com sucesso!")
            print(f"   - Tamanho: {len(response.content)} bytes")
            # Salvar arquivo de teste
            with open(f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 'wb') as f:
                f.write(response.content)
            print("   - Arquivo salvo para verificação")
            return True
        else:
            print(f"❌ Erro {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_export_xlsx():
    """Testa exportação XLSX"""
    print("\n📊 Testando exportação XLSX...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/export/xlsx")
        if response.status_code == 200:
            print("✅ XLSX gerado com sucesso!")
            print(f"   - Tamanho: {len(response.content)} bytes")
            # Salvar arquivo de teste
            with open(f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", 'wb') as f:
                f.write(response.content)
            print("   - Arquivo salvo para verificação")
            return True
        else:
            print(f"❌ Erro {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_export_pdf():
    """Testa exportação PDF"""
    print("\n📄 Testando exportação PDF...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/export/pdf?status=ACTIVE")
        if response.status_code == 200:
            print("✅ PDF gerado com sucesso!")
            print(f"   - Tamanho: {len(response.content)} bytes")
            # Salvar arquivo de teste
            with open(f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", 'wb') as f:
                f.write(response.content)
            print("   - Arquivo salvo para verificação")
            return True
        else:
            print(f"❌ Erro {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("="*60)
    print("🧪 TESTE DE ENDPOINTS DE RELATÓRIOS")
    print("="*60)
    
    results = {
        "Metadados": test_metadata(),
        "Fabricantes": test_manufacturers(),
        "Modelos": test_models(),
        "Export CSV": test_export_csv(),
        "Export XLSX": test_export_xlsx(),
        "Export PDF": test_export_pdf()
    }
    
    print("\n" + "="*60)
    print("📊 RESULTADO DOS TESTES")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    total_pass = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nTotal: {total_pass}/{total} testes passaram")
    
    if total_pass == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM")

if __name__ == "__main__":
    main()

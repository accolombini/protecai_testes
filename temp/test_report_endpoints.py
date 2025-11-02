#!/usr/bin/env python3
"""
🧪 TESTE DE ENDPOINTS DE RELATÓRIOS
===================================
Valida todos os endpoints criados para o sistema de relatórios.
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_metadata_endpoint():
    """Testa endpoint de metadados"""
    print("\n🔍 Testando GET /api/v1/reports/metadata")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/metadata")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Metadados obtidos com sucesso!")
            print(f"   Fabricantes: {len(data.get('manufacturers', []))}")
            print(f"   Modelos: {len(data.get('models', []))}")
            print(f"   Famílias: {len(data.get('families', []))}")
            print(f"   Barramentos: {len(data.get('bays', []))}")
            print(f"   Subestações: {len(data.get('substations', []))}")
            print(f"   Status: {data.get('status_options', [])}")
            print(f"   Sistemas de Proteção: {len(data.get('protection_systems', []))}")
            return True
        else:
            print(f"❌ Erro: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

def test_manufacturers_endpoint():
    """Testa endpoint de fabricantes"""
    print("\n🔍 Testando GET /api/v1/reports/manufacturers")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/manufacturers")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Fabricantes obtidos: {len(data.get('manufacturers', []))}")
            for mfg in data.get('manufacturers', [])[:5]:
                print(f"   - {mfg['name']} ({mfg['equipment_count']} equipamentos)")
            return True
        else:
            print(f"❌ Erro: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

def test_models_endpoint():
    """Testa endpoint de modelos"""
    print("\n🔍 Testando GET /api/v1/reports/models")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/models")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Modelos obtidos: {len(data.get('models', []))}")
            for model in data.get('models', [])[:5]:
                print(f"   - {model['model_name']} ({model['equipment_count']} unidades)")
            return True
        else:
            print(f"❌ Erro: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

def test_export_csv():
    """Testa exportação CSV"""
    print("\n📄 Testando POST /api/v1/reports/export (CSV)")
    
    payload = {
        "format": "csv",
        "filters": {
            "manufacturer": "",
            "status": "ACTIVE"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/reports/export",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            output_path = Path("outputs/reports/test_export.csv")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            
            file_size = output_path.stat().st_size
            print(f"✅ CSV exportado com sucesso!")
            print(f"   Arquivo: {output_path}")
            print(f"   Tamanho: {file_size} bytes")
            
            # Contar linhas
            lines = output_path.read_text().strip().split('\n')
            print(f"   Linhas: {len(lines)} (incluindo cabeçalho)")
            return True
        else:
            print(f"❌ Erro: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

def test_export_xlsx():
    """Testa exportação XLSX"""
    print("\n📊 Testando POST /api/v1/reports/export (XLSX)")
    
    payload = {
        "format": "xlsx",
        "filters": {
            "manufacturer": "Schneider"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/reports/export",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            output_path = Path("outputs/reports/test_export.xlsx")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            
            file_size = output_path.stat().st_size
            print(f"✅ XLSX exportado com sucesso!")
            print(f"   Arquivo: {output_path}")
            print(f"   Tamanho: {file_size} bytes")
            return True
        else:
            print(f"❌ Erro: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

def test_export_pdf():
    """Testa exportação PDF"""
    print("\n📕 Testando POST /api/v1/reports/export (PDF)")
    
    payload = {
        "format": "pdf",
        "filters": {
            "status": "ACTIVE"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/reports/export",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            output_path = Path("outputs/reports/test_export.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            
            file_size = output_path.stat().st_size
            print(f"✅ PDF exportado com sucesso!")
            print(f"   Arquivo: {output_path}")
            print(f"   Tamanho: {file_size} bytes")
            return True
        else:
            print(f"❌ Erro: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("=" * 60)
    print("🧪 TESTE DE ENDPOINTS DE RELATÓRIOS")
    print("=" * 60)
    
    results = {
        "metadata": test_metadata_endpoint(),
        "manufacturers": test_manufacturers_endpoint(),
        "models": test_models_endpoint(),
        "export_csv": test_export_csv(),
        "export_xlsx": test_export_xlsx(),
        "export_pdf": test_export_pdf()
    }
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:20s}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    return all(results.values())

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

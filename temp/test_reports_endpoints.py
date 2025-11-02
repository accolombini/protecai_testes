#!/usr/bin/env python3
"""
Test Script - Validação de Endpoints de Relatórios
=================================================

Testa todos os endpoints de relatórios:
- Metadata (enums + dinâmicos)
- Exportação multi-formato (CSV, XLSX, PDF)
- Filtros avançados
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1/reports"

def print_section(title):
    """Helper para printar seções"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_metadata():
    """Testa endpoint de metadados"""
    print_section("TEST 1: Metadados de Relatórios")
    
    try:
        response = requests.get(f"{BASE_URL}/metadata")
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"\n📊 Enums disponíveis:")
        print(f"   - Status: {len(data['enums']['status'])} opções")
        print(f"   - Famílias: {len(data['enums']['families'])} opções")
        print(f"   - Sistemas Proteção: {len(data['enums']['protection_systems'])} opções")
        print(f"   - Níveis Tensão: {len(data['enums']['voltage_levels'])} opções")
        print(f"   - Formatos Export: {len(data['enums']['export_formats'])} opções")
        
        print(f"\n📦 Dados Dinâmicos:")
        print(f"   - Total Equipamentos: {data['dynamic']['total_equipments']}")
        print(f"   - Fabricantes: {len(data['dynamic']['manufacturers'])}")
        print(f"   - Modelos: {len(data['dynamic']['models'])}")
        print(f"   - Barramentos: {len(data['dynamic']['busbars'])}")
        
        print(f"\n✨ Top 3 Fabricantes:")
        for mfg in data['dynamic']['manufacturers'][:3]:
            print(f"   - {mfg['name']}: {mfg['count']} equipamentos")
        
        print(f"\n✨ Top 3 Modelos:")
        for model in data['dynamic']['models'][:3]:
            print(f"   - {model['name']} ({model['manufacturer']}): {model['count']} unidades")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_manufacturers():
    """Testa endpoint de fabricantes"""
    print_section("TEST 2: Lista de Fabricantes")
    
    try:
        response = requests.get(f"{BASE_URL}/manufacturers")
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"📋 Total de fabricantes: {data['total']}\n")
        
        for mfg in data['manufacturers'][:5]:
            print(f"   - {mfg['name']}: {mfg['count']} equipamentos")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_models():
    """Testa endpoint de modelos"""
    print_section("TEST 3: Lista de Modelos")
    
    try:
        response = requests.get(f"{BASE_URL}/models")
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"📋 Total de modelos: {data['total']}\n")
        
        for model in data['models'][:5]:
            print(f"   - {model['name']} ({model['manufacturer']}): {model['count']} unidades")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_families():
    """Testa endpoint de famílias"""
    print_section("TEST 4: Famílias de Relés")
    
    try:
        response = requests.get(f"{BASE_URL}/families")
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"📋 Total de famílias: {data['total']}\n")
        
        for family in data['families']:
            print(f"   - {family['family']}: {family['count']} equipamentos")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_export_csv():
    """Testa exportação CSV"""
    print_section("TEST 5: Exportação CSV")
    
    try:
        # Export com filtro de status
        response = requests.get(
            f"{BASE_URL}/export/csv",
            params={"status": "ACTIVE"}
        )
        response.raise_for_status()
        
        print(f"✅ Status: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('content-type')}")
        
        # Salvar arquivo
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(f"/tmp/{filename}", "wb") as f:
            f.write(response.content)
        
        print(f"💾 Arquivo salvo: /tmp/{filename}")
        print(f"📊 Tamanho: {len(response.content)} bytes")
        
        # Mostrar primeiras linhas
        lines = response.content.decode('utf-8').split('\n')[:5]
        print(f"\n📝 Primeiras linhas:")
        for line in lines:
            print(f"   {line[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_export_xlsx():
    """Testa exportação XLSX"""
    print_section("TEST 6: Exportação XLSX")
    
    try:
        response = requests.get(
            f"{BASE_URL}/export/xlsx",
            params={"status": "ACTIVE"}
        )
        response.raise_for_status()
        
        print(f"✅ Status: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('content-type')}")
        
        # Salvar arquivo
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        with open(f"/tmp/{filename}", "wb") as f:
            f.write(response.content)
        
        print(f"💾 Arquivo salvo: /tmp/{filename}")
        print(f"📊 Tamanho: {len(response.content)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_export_pdf():
    """Testa exportação PDF"""
    print_section("TEST 7: Exportação PDF")
    
    try:
        response = requests.get(
            f"{BASE_URL}/export/pdf",
            params={"status": "ACTIVE"}
        )
        response.raise_for_status()
        
        print(f"✅ Status: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('content-type')}")
        
        # Salvar arquivo
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        with open(f"/tmp/{filename}", "wb") as f:
            f.write(response.content)
        
        print(f"💾 Arquivo salvo: /tmp/{filename}")
        print(f"📊 Tamanho: {len(response.content)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_preview():
    """Testa preview de relatório"""
    print_section("TEST 8: Preview de Relatório")
    
    try:
        filters = {
            "status": "ACTIVE"
        }
        
        response = requests.post(
            f"{BASE_URL}/preview",
            json=filters,
            params={"page": 1, "size": 10}
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"\n📊 Paginação:")
        print(f"   - Página: {data['pagination']['page']}")
        print(f"   - Tamanho: {data['pagination']['size']}")
        print(f"   - Total: {data['pagination']['total']}")
        print(f"   - Total Páginas: {data['pagination']['total_pages']}")
        
        print(f"\n🔍 Filtros Aplicados:")
        for key, value in data['filters_applied'].items():
            print(f"   - {key}: {value}")
        
        print(f"\n📋 Primeiros equipamentos:")
        for eq in data['data'][:3]:
            print(f"   - {eq['equipment_tag']} ({eq['model_name']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "🚀 "*35)
    print("  TESTE DE ENDPOINTS DE RELATÓRIOS - PROTECAI")
    print("🚀 "*35)
    
    tests = [
        ("Metadata", test_metadata),
        ("Manufacturers", test_manufacturers),
        ("Models", test_models),
        ("Families", test_families),
        ("Export CSV", test_export_csv),
        ("Export XLSX", test_export_xlsx),
        ("Export PDF", test_export_pdf),
        ("Preview", test_preview)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Erro fatal em {name}: {e}")
            results.append((name, False))
    
    # Sumário
    print_section("SUMÁRIO DOS TESTES")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"✅ Passou: {passed}/{total}")
    print(f"❌ Falhou: {total - passed}/{total}")
    print(f"📊 Taxa de Sucesso: {(passed/total)*100:.1f}%\n")
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {name}")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()

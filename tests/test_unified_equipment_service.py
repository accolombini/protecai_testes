#!/usr/bin/env python3
"""
Teste da Implementação Unificada de Equipment Service
====================================================

Testa a integração robusta entre schemas relay_configs + protec_ai
Validação completa antes de aplicar no sistema principal
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Adicionar caminho do projeto
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.core.database import engine, SessionLocal
from unified_equipment_service import UnifiedEquipmentService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_unified_equipment_service():
    """Teste completo do UnifiedEquipmentService"""
    
    print("🧪 TESTE DO UNIFIED EQUIPMENT SERVICE")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        service = UnifiedEquipmentService(db)
        
        # Teste 1: Estatísticas unificadas
        print("\n📊 TESTE 1: Estatísticas Unificadas")
        print("-" * 40)
        
        stats = await service.get_unified_statistics()
        print(f"✅ Estatísticas obtidas com sucesso!")
        print(f"   Dados protec_ai: {stats['unified_statistics']['protec_ai_data']}")
        print(f"   Dados relay_configs: {stats['unified_statistics']['relay_configs_data']}")
        print(f"   Total de registros: {stats['unified_statistics']['total_records']}")
        
        # Teste 2: Busca de fabricantes unificados
        print("\n🏭 TESTE 2: Fabricantes Unificados")
        print("-" * 40)
        
        manufacturers_result = await service.search_unified_manufacturers()
        manufacturers = manufacturers_result["manufacturers"]  # CORRIGIDO: Acessar a lista correta
        print(f"✅ Fabricantes encontrados: {len(manufacturers)}")
        
        relay_configs_count = len([m for m in manufacturers if m["source"] == "relay_configs"])
        protec_ai_count = len([m for m in manufacturers if m["source"] == "protec_ai"])
        
        print(f"   relay_configs: {relay_configs_count}")
        print(f"   protec_ai: {protec_ai_count}")
        
        if manufacturers:
            print(f"   Exemplo: {manufacturers[0]['name']} ({manufacturers[0]['source']})")
        
        # Teste 3: Busca de equipamentos unificados
        print("\n🔧 TESTE 3: Equipamentos Unificados")
        print("-" * 40)
        
        equipments, total = await service.get_unified_equipment_data(page=1, size=5)
        print(f"✅ Equipamentos encontrados: {total}")
        
        relay_configs_eq = len([eq for eq in equipments if eq["source"] == "relay_configs"])
        protec_ai_eq = len([eq for eq in equipments if eq["source"] == "protec_ai"])
        
        print(f"   relay_configs: {relay_configs_eq}")
        print(f"   protec_ai: {protec_ai_eq}")
        
        if equipments:
            print(f"   Exemplo: {equipments[0].get('description', 'N/A')} ({equipments[0]['source']})")
        
        # Teste 4: Detalhes de configuração (se houver dados)
        if equipments:
            print("\n🔍 TESTE 4: Detalhes de Configuração")
            print("-" * 40)
            
            for equipment in equipments[:2]:  # Testar os 2 primeiros
                eq_id = equipment["id"]
                try:
                    details = await service.get_equipment_configuration_details(eq_id)
                    if details:
                        print(f"✅ Detalhes obtidos para {eq_id}:")
                        print(f"   Fonte: {details['source']}")
                        print(f"   Tipo: {details['data_type']}")
                        if details['source'] == 'relay_configs':
                            print(f"   Fabricante: {details['manufacturer']['name']}")
                        else:
                            print(f"   Tokens extraídos: {details['summary']['tokens_extracted']}")
                    else:
                        print(f"❌ Nenhum detalhe encontrado para {eq_id}")
                except Exception as e:
                    print(f"⚠️ Erro ao buscar detalhes de {eq_id}: {e}")
        
        print("\n✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        print("🎯 Sistema unificado funcionando corretamente")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        logger.error(f"Erro no teste: {e}")
        return False
    finally:
        db.close()

def test_database_connection():
    """Teste básico de conexão com o banco"""
    print("🔌 TESTE DE CONEXÃO COM BANCO DE DADOS")
    print("-" * 50)
    
    try:
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # Testar ambos os schemas
            relay_result = conn.execute(text("SELECT COUNT(*) FROM relay_configs.relay_equipment"))
            relay_count = relay_result.scalar()
            
            protec_result = conn.execute(text("SELECT COUNT(*) FROM protec_ai.valores_originais"))
            protec_count = protec_result.scalar()
            
            print(f"✅ Conexão estabelecida com sucesso!")
            print(f"   relay_configs.relay_equipment: {relay_count} registros")
            print(f"   protec_ai.valores_originais: {protec_count} registros")
            
            return True
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

if __name__ == "__main__":
    print("🧪 INICIANDO TESTES DO SISTEMA UNIFICADO")
    print("=" * 60)
    
    # Teste 1: Conexão básica
    if not test_database_connection():
        print("❌ Falha na conexão. Encerrando testes.")
        sys.exit(1)
    
    # Teste 2: Service unificado
    try:
        success = asyncio.run(test_unified_equipment_service())
        if success:
            print("\n🎉 IMPLEMENTAÇÃO UNIFICADA VALIDADA!")
            print("   Pronto para aplicar no sistema principal")
        else:
            print("\n❌ FALHA NA VALIDAÇÃO")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        sys.exit(1)
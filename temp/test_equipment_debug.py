#!/usr/bin/env python3
"""
Teste de debug direto para Equipment Service
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from api.core.database import get_db
from api.services.unified_equipment_service import UnifiedEquipmentService

async def test_equipment_debug():
    """Testa diretamente o Equipment Service"""
    try:
        # Obter sessão do banco
        db_gen = get_db()
        db = next(db_gen)
        
        print("✅ Sessão do banco obtida")
        
        # Criar instância do serviço unificado
        service = UnifiedEquipmentService(db)
        print("✅ UnifiedEquipmentService criado")
        
        # Testar método get_unified_equipment_data
        print("\n🔍 Testando get_unified_equipment_data...")
        result, total = await service.get_unified_equipment_data(page=1, size=10)
        
        print(f"✅ Resultado: {len(result)} equipamentos de {total} total")
        if result:
            print(f"Primeiro item: {result[0]}")
        else:
            print("Nenhum resultado encontrado")
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            db.close()
            print("✅ Sessão fechada")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_equipment_debug())
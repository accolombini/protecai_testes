#!/usr/bin/env python3
"""
TESTE: VALIDAÇÃO DA NORMALIZAÇÃO 3FN
Sistema ProtecAI - PETROBRAS
Data: 31 de outubro de 2025

Valida a estrutura 3FN antes de reprocessar todos os arquivos
"""

import psycopg2
from psycopg2.extras import RealDictCursor

def test_3nf_structure():
    """Testar estrutura 3FN do banco de dados"""
    
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'protecai_db',
        'user': 'protecai',
        'password': 'protecai'
    }
    
    print("🧪 TESTE: VALIDAÇÃO NORMALIZAÇÃO 3FN")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Verificar tabela substations
            print("\n📊 1. TABELA: protec_ai.substations")
            print("-" * 60)
            
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'protec_ai' 
                AND table_name = 'substations'
                ORDER BY ordinal_position
            """)
            
            for col in cur.fetchall():
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"   ✓ {col['column_name']:20} {col['data_type']:20} {nullable}")
            
            cur.execute("SELECT COUNT(*) as total FROM protec_ai.substations")
            total = cur.fetchone()['total']
            print(f"\n   📈 Total de subestações: {total}")
            
            # 2. Verificar tabela bays
            print("\n📊 2. TABELA: protec_ai.bays")
            print("-" * 60)
            
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'protec_ai' 
                AND table_name = 'bays'
                ORDER BY ordinal_position
            """)
            
            for col in cur.fetchall():
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"   ✓ {col['column_name']:20} {col['data_type']:20} {nullable}")
            
            cur.execute("SELECT COUNT(*) as total FROM protec_ai.bays")
            total = cur.fetchone()['total']
            print(f"\n   📈 Total de bays: {total}")
            
            # 3. Verificar relay_equipment (modificado)
            print("\n📊 3. TABELA: protec_ai.relay_equipment (MODIFICADA)")
            print("-" * 60)
            
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'protec_ai' 
                AND table_name = 'relay_equipment'
                ORDER BY ordinal_position
            """)
            
            for col in cur.fetchall():
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                emoji = "🔗" if col['column_name'] == 'bay_id' else "✓"
                print(f"   {emoji} {col['column_name']:20} {col['data_type']:20} {nullable}")
            
            cur.execute("SELECT COUNT(*) as total FROM protec_ai.relay_equipment")
            total = cur.fetchone()['total']
            print(f"\n   📈 Total de equipamentos: {total}")
            
            # 4. Testar funções helper
            print("\n🔧 4. TESTANDO FUNÇÕES HELPER")
            print("-" * 60)
            
            # Testar get_or_create_substation
            cur.execute("""
                SELECT protec_ai.get_or_create_substation('SE-TEST', 'Subestação Teste', 'Brasil') as id
            """)
            result = cur.fetchone()
            test_substation_id = result['id']
            print(f"   ✅ get_or_create_substation → ID: {test_substation_id}")
            
            # Testar get_or_create_bay (3 parâmetros: bay_code, substation_id, voltage)
            cur.execute("""
                SELECT protec_ai.get_or_create_bay('TEST-BAY-01', %s, '13.8kV') as id
            """, (test_substation_id,))
            result = cur.fetchone()
            test_bay_id = result['id']
            print(f"   ✅ get_or_create_bay → ID: {test_bay_id}")
            
            # Limpar dados de teste
            cur.execute("DELETE FROM protec_ai.bays WHERE bay_code = 'TEST-BAY-01'")
            cur.execute("DELETE FROM protec_ai.substations WHERE substation_code = 'SE-TEST'")
            print(f"   🧹 Dados de teste removidos")
            
            # 5. Testar VIEW equipment_full_details
            print("\n📊 5. VIEW: protec_ai.equipment_full_details")
            print("-" * 60)
            
            cur.execute("""
                SELECT COUNT(*) as total 
                FROM protec_ai.equipment_full_details
            """)
            total = cur.fetchone()['total']
            print(f"   📈 Total de registros na view: {total}")
            
            if total > 0:
                cur.execute("""
                    SELECT 
                        equipment_tag,
                        substation_name,
                        bay_name,
                        bay_voltage,
                        substation_voltage,
                        manufacturer_name,
                        model_name,
                        equipment_status,
                        bay_status,
                        substation_status
                    FROM protec_ai.equipment_full_details
                    LIMIT 3
                """)
                rows = cur.fetchall()
                print("\n   📋 Exemplos:")
                for row in rows:
                    print(f"      • {row['equipment_tag']}")
                    print(f"        Subestação: {row['substation_name'] or 'N/A'}")
                    print(f"        Bay: {row['bay_name'] or 'N/A'}")
                    print(f"        Tensão Bay: {row['bay_voltage'] or 'N/A'}")
                    print(f"        Tensão SE: {row['substation_voltage'] or 'N/A'}")
                    print(f"        Fabricante: {row['manufacturer_name'] or 'N/A'}")
                    print(f"        Modelo: {row['model_name'] or 'N/A'}")
                    print(f"        Status: {row['equipment_status'] or 'N/A'}")
                    print()
            
            # 6. Verificar integridade referencial
            print("\n🔗 6. INTEGRIDADE REFERENCIAL")
            print("-" * 60)
            
            # Equipamentos sem bay
            cur.execute("""
                SELECT COUNT(*) as total 
                FROM protec_ai.relay_equipment
                WHERE bay_id IS NULL
            """)
            no_bay = cur.fetchone()['total']
            print(f"   ⚠️  Equipamentos SEM bay: {no_bay}")
            
            # Bays sem subestação
            cur.execute("""
                SELECT COUNT(*) as total 
                FROM protec_ai.bays
                WHERE substation_id IS NULL
            """)
            no_substation = cur.fetchone()['total']
            print(f"   ⚠️  Bays SEM subestação: {no_substation}")
            
            # Equipamentos com bay válido
            cur.execute("""
                SELECT COUNT(*) as total 
                FROM protec_ai.relay_equipment
                WHERE bay_id IS NOT NULL
            """)
            with_bay = cur.fetchone()['total']
            print(f"   ✅ Equipamentos COM bay: {with_bay}")
            
            print("\n" + "=" * 60)
            print("✅ VALIDAÇÃO 3FN CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    test_3nf_structure()

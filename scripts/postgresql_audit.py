#!/usr/bin/env python3
"""
AUDITORIA CRÍTICA POSTGRESQL - ProtecAI
========================================

Verifica TODA a estrutura do banco de dados:
- Todos os schemas
- Todas as tabelas
- Todas as colunas com tipos
- Todas as chaves primárias/estrangeiras
- Contagem de registros
- Integridade referencial
"""

import psycopg2
import json
from datetime import datetime
from typing import Dict, List, Any

class PostgreSQLAuditor:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.audit_results = {
            "timestamp": datetime.now().isoformat(),
            "database": "protecai_db",
            "schemas": {},
            "integrity_issues": [],
            "summary": {}
        }
    
    def connect(self):
        """Conectar ao PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="protecai_db",
                user="protecai",
                password="protecai"
            )
            self.cursor = self.conn.cursor()
            print("✅ Conectado ao PostgreSQL")
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            raise
    
    def get_all_schemas(self) -> List[str]:
        """Obter todos os schemas do banco"""
        query = """
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
        ORDER BY schema_name;
        """
        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_tables_in_schema(self, schema_name: str) -> List[Dict]:
        """Obter todas as tabelas de um schema"""
        query = """
        SELECT 
            table_name,
            table_type
        FROM information_schema.tables 
        WHERE table_schema = %s
        ORDER BY table_name;
        """
        self.cursor.execute(query, (schema_name,))
        return [{"name": row[0], "type": row[1]} for row in self.cursor.fetchall()]
    
    def get_table_columns(self, schema_name: str, table_name: str) -> List[Dict]:
        """Obter todas as colunas de uma tabela"""
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
        """
        self.cursor.execute(query, (schema_name, table_name))
        return [
            {
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3],
                "max_length": row[4],
                "precision": row[5],
                "scale": row[6]
            }
            for row in self.cursor.fetchall()
        ]
    
    def get_primary_keys(self, schema_name: str, table_name: str) -> List[str]:
        """Obter chaves primárias"""
        query = """
        SELECT column_name
        FROM information_schema.key_column_usage
        WHERE table_schema = %s 
        AND table_name = %s
        AND constraint_name IN (
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_schema = %s 
            AND table_name = %s
            AND constraint_type = 'PRIMARY KEY'
        )
        ORDER BY ordinal_position;
        """
        self.cursor.execute(query, (schema_name, table_name, schema_name, table_name))
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_foreign_keys(self, schema_name: str, table_name: str) -> List[Dict]:
        """Obter chaves estrangeiras"""
        query = """
        SELECT 
            kcu.column_name,
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = %s
        AND tc.table_name = %s;
        """
        self.cursor.execute(query, (schema_name, table_name))
        return [
            {
                "column": row[0],
                "references_schema": row[1],
                "references_table": row[2],
                "references_column": row[3],
                "constraint_name": row[4]
            }
            for row in self.cursor.fetchall()
        ]
    
    def get_table_row_count(self, schema_name: str, table_name: str) -> int:
        """Contar registros na tabela"""
        try:
            query = f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}";'
            self.cursor.execute(query)
            return self.cursor.fetchone()[0]
        except Exception as e:
            return -1  # Erro ao contar
    
    def check_data_integrity(self, schema_name: str, table_name: str, foreign_keys: List[Dict]) -> List[Dict]:
        """Verificar integridade referencial"""
        issues = []
        for fk in foreign_keys:
            try:
                # Verificar se há registros órfãos
                query = f"""
                SELECT COUNT(*) 
                FROM "{schema_name}"."{table_name}" t
                LEFT JOIN "{fk['references_schema']}"."{fk['references_table']}" r
                ON t."{fk['column']}" = r."{fk['references_column']}"
                WHERE t."{fk['column']}" IS NOT NULL 
                AND r."{fk['references_column']}" IS NULL;
                """
                self.cursor.execute(query)
                orphan_count = self.cursor.fetchone()[0]
                
                if orphan_count > 0:
                    issues.append({
                        "type": "orphan_records",
                        "table": f"{schema_name}.{table_name}",
                        "column": fk['column'],
                        "references": f"{fk['references_schema']}.{fk['references_table']}.{fk['references_column']}",
                        "orphan_count": orphan_count
                    })
            except Exception as e:
                issues.append({
                    "type": "integrity_check_error",
                    "table": f"{schema_name}.{table_name}",
                    "error": str(e)
                })
        
        return issues
    
    def audit_complete_database(self):
        """Executar auditoria completa"""
        print("🔍 INICIANDO AUDITORIA COMPLETA POSTGRESQL")
        print("=" * 60)
        
        # 1. Obter todos os schemas
        schemas = self.get_all_schemas()
        print(f"📊 Schemas encontrados: {len(schemas)}")
        
        total_tables = 0
        total_records = 0
        
        for schema_name in schemas:
            print(f"\n🗂️  SCHEMA: {schema_name}")
            schema_info = {
                "tables": {},
                "total_tables": 0,
                "total_records": 0
            }
            
            # 2. Obter tabelas do schema
            tables = self.get_tables_in_schema(schema_name)
            schema_info["total_tables"] = len(tables)
            
            for table_info in tables:
                table_name = table_info["name"]
                print(f"  📋 Tabela: {table_name}")
                
                # 3. Obter estrutura da tabela
                columns = self.get_table_columns(schema_name, table_name)
                primary_keys = self.get_primary_keys(schema_name, table_name)
                foreign_keys = self.get_foreign_keys(schema_name, table_name)
                row_count = self.get_table_row_count(schema_name, table_name)
                
                # 4. Verificar integridade
                integrity_issues = self.check_data_integrity(schema_name, table_name, foreign_keys)
                if integrity_issues:
                    self.audit_results["integrity_issues"].extend(integrity_issues)
                
                schema_info["tables"][table_name] = {
                    "type": table_info["type"],
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys,
                    "row_count": row_count,
                    "integrity_issues": len(integrity_issues)
                }
                
                schema_info["total_records"] += max(0, row_count)
                print(f"    📊 Registros: {row_count}")
                print(f"    🔑 PKs: {len(primary_keys)}")
                print(f"    🔗 FKs: {len(foreign_keys)}")
                print(f"    ⚠️  Issues: {len(integrity_issues)}")
            
            self.audit_results["schemas"][schema_name] = schema_info
            total_tables += schema_info["total_tables"]
            total_records += schema_info["total_records"]
        
        # 5. Resumo final
        self.audit_results["summary"] = {
            "total_schemas": len(schemas),
            "total_tables": total_tables,
            "total_records": total_records,
            "total_integrity_issues": len(self.audit_results["integrity_issues"])
        }
        
        print("\n" + "=" * 60)
        print("📈 RESUMO DA AUDITORIA:")
        print(f"   • Schemas: {len(schemas)}")
        print(f"   • Tabelas: {total_tables}")
        print(f"   • Registros: {total_records:,}")
        print(f"   • Problemas de integridade: {len(self.audit_results['integrity_issues'])}")
        
        return self.audit_results
    
    def save_results(self, filename: str = "postgresql_audit_results.json"):
        """Salvar resultados da auditoria"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.audit_results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Resultados salvos em: {filename}")
    
    def close(self):
        """Fechar conexão"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

def main():
    auditor = PostgreSQLAuditor()
    
    try:
        auditor.connect()
        results = auditor.audit_complete_database()
        auditor.save_results("temp/postgresql_audit_critical.json")
        
        # Mostrar problemas críticos
        if results["integrity_issues"]:
            print("\n🚨 PROBLEMAS CRÍTICOS ENCONTRADOS:")
            for issue in results["integrity_issues"][:10]:  # Mostrar primeiros 10
                print(f"   ❌ {issue['type']}: {issue.get('table', 'N/A')}")
        
    except Exception as e:
        print(f"💥 Erro na auditoria: {e}")
    finally:
        auditor.close()

if __name__ == "__main__":
    main()
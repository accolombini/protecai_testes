"""
Database Schema Router
Endpoint para visualização da estrutura do banco de dados PostgreSQL
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.engine import Connection
from typing import List, Dict, Any
from datetime import datetime
from api.core.database import get_db
import logging

router = APIRouter(prefix="/database", tags=["Database"])
logger = logging.getLogger(__name__)


@router.get("/statistics")
async def get_database_statistics(db: Session = Depends(get_db)):
    """
    📊 **Estatísticas Reais do Banco de Dados**
    
    Retorna contagens reais de todas as tabelas principais.
    100% REAL - Dados direto do PostgreSQL.
    """
    try:
        # Buscar contagens reais de cada tabela
        stats = {}
        
        # Schema relay_configs
        relay_equipment_query = text("SELECT COUNT(*) FROM protec_ai.relay_equipment")
        protection_functions_query = text("SELECT COUNT(*) FROM protec_ai.protection_functions")
        io_config_query = text("SELECT COUNT(*) FROM protec_ai.io_configuration")
        
        # Schema public
        active_functions_query = text("SELECT COUNT(*) FROM active_protection_functions")
        
        # Executar queries
        stats["relay_equipment"] = db.execute(relay_equipment_query).scalar() or 0
        stats["protection_functions"] = db.execute(protection_functions_query).scalar() or 0
        stats["io_configuration"] = db.execute(io_config_query).scalar() or 0
        stats["active_protection_functions"] = db.execute(active_functions_query).scalar() or 0
        
        # Calcular totais
        total_records = sum(stats.values())
        
        # Buscar relés únicos com funções ativas
        unique_relays_query = text("SELECT COUNT(DISTINCT relay_file) FROM active_protection_functions")
        unique_relays = db.execute(unique_relays_query).scalar() or 0
        
        # Query para dados reais do protec_ai schema
        equipments_query = text("SELECT COUNT(*) FROM protec_ai.relay_equipment")
        settings_query = text("SELECT COUNT(*) FROM protec_ai.relay_settings")
        active_settings_query = text("SELECT COUNT(*) FROM protec_ai.relay_settings WHERE is_active = true")
        
        stats["total_equipments"] = db.execute(equipments_query).scalar() or 0
        stats["total_settings"] = db.execute(settings_query).scalar() or 0
        stats["active_settings"] = db.execute(active_settings_query).scalar() or 0
        
        return {
            "database": "protecai_db",
            "timestamp": datetime.now().isoformat(),
            "tables": stats,
            "summary": {
                "total_records": total_records,
                "relay_equipment_count": stats["relay_equipment"],
                "protection_functions_count": stats["protection_functions"],
                "io_configurations_count": stats["io_configuration"],
                "active_functions_count": stats["active_protection_functions"],
                "unique_relays_with_functions": unique_relays,
                "total_equipments": stats["total_equipments"],
                "total_settings": stats["total_settings"],
                "active_settings": stats["active_settings"]
            },
            "data_source": "postgresql_real",
            "note": "100% dados reais do protec_ai schema - zero mocks"
        }
        
    except Exception as e:
        logger.error(f"Error getting database statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving database statistics: {str(e)}"
        )

@router.get("/schema")
async def get_database_schema(db: Connection = Depends(get_db)) -> Dict[str, Any]:
    """
    Retorna a estrutura completa do banco de dados:
    - Nome do banco
    - Schemas
    - Tabelas de cada schema
    - Colunas de cada tabela (com tipos, constraints, etc)
    """
    try:
        # Get database name
        db_name_query = text("SELECT current_database()")
        db_name = db.execute(db_name_query).scalar()

        # Get all schemas (excluding system schemas)
        schemas_query = text("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name
        """)
        schemas_result = db.execute(schemas_query).fetchall()
        
        schemas_data = []
        
        for schema_row in schemas_result:
            schema_name = schema_row[0]
            
            # Get all tables in this schema
            tables_query = text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = :schema_name
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables_result = db.execute(tables_query, {"schema_name": schema_name}).fetchall()
            
            tables_data = []
            
            for table_row in tables_result:
                table_name = table_row[0]
                
                # Get row count for this table
                try:
                    count_query = text(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"')
                    row_count = db.execute(count_query).scalar() or 0
                except Exception:
                    row_count = 0
                
                # Get all columns for this table
                columns_query = text("""
                    SELECT 
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key,
                        CASE WHEN fk.column_name IS NOT NULL THEN true ELSE false END as is_foreign_key
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT ku.column_name, ku.table_name, ku.table_schema
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku
                            ON tc.constraint_name = ku.constraint_name
                            AND tc.table_schema = ku.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                    ) pk ON c.column_name = pk.column_name 
                        AND c.table_name = pk.table_name
                        AND c.table_schema = pk.table_schema
                    LEFT JOIN (
                        SELECT ku.column_name, ku.table_name, ku.table_schema
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku
                            ON tc.constraint_name = ku.constraint_name
                            AND tc.table_schema = ku.table_schema
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                    ) fk ON c.column_name = fk.column_name 
                        AND c.table_name = fk.table_name
                        AND c.table_schema = fk.table_schema
                    WHERE c.table_schema = :schema_name
                    AND c.table_name = :table_name
                    ORDER BY c.ordinal_position
                """)
                columns_result = db.execute(
                    columns_query, 
                    {"schema_name": schema_name, "table_name": table_name}
                ).fetchall()
                
                columns = [
                    {
                        "column_name": col[0],
                        "data_type": col[1],
                        "is_nullable": col[2],
                        "column_default": col[3],
                        "is_primary_key": col[4],
                        "is_foreign_key": col[5]
                    }
                    for col in columns_result
                ]
                
                tables_data.append({
                    "table_name": table_name,
                    "row_count": row_count,
                    "columns": columns
                })
            
            schemas_data.append({
                "schema_name": schema_name,
                "tables": tables_data
            })
        
        return {
            "database_name": db_name,
            "schemas": schemas_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar estrutura do banco: {str(e)}"
        )


@router.get("/stats")
async def get_database_stats(db: Connection = Depends(get_db)) -> Dict[str, Any]:
    """
    Retorna estatísticas gerais do banco de dados
    """
    try:
        stats_query = text("""
            SELECT 
                (SELECT COUNT(*) FROM information_schema.schemata 
                 WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')) as total_schemas,
                (SELECT COUNT(*) FROM information_schema.tables 
                 WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                 AND table_type = 'BASE TABLE') as total_tables,
                pg_database_size(current_database()) as database_size
        """)
        result = db.execute(stats_query).fetchone()
        
        return {
            "total_schemas": result[0],
            "total_tables": result[1],
            "database_size_bytes": result[2],
            "database_size_mb": round(result[2] / (1024 * 1024), 2)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar estatísticas: {str(e)}"
        )

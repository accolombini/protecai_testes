"""
Router de Funções Ativas - Consulta de Funções de Proteção
==========================================================

Endpoints para consultar funções de proteção ativas detectadas nos relés.
100% REAL - Dados direto do PostgreSQL.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import logging

from api.core.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/relays/{relay_id}/active-functions")
async def get_relay_active_functions(
    relay_id: str,
    db: Session = Depends(get_db)
):
    """
    🔍 **Funções Ativas de um Relé Específico**
    
    Retorna todas as funções de proteção ativas detectadas para um relé.
    Dados reais do PostgreSQL (tabela active_protection_functions).
    
    - **relay_id**: ID ou nome do arquivo do relé (ex: "00-MF-12", "Tela 05.pdf")
    """
    try:
        # Buscar funções ativas no banco
        query = text("""
            SELECT 
                id,
                relay_file,
                relay_model,
                function_code,
                function_description,
                detection_method,
                source_file,
                detection_timestamp
            FROM protec_ai.active_protection_functions
            WHERE relay_file ILIKE :relay_pattern
            ORDER BY function_code
        """)
        
        result = db.execute(query, {"relay_pattern": f"%{relay_id}%"})
        functions = result.fetchall()
        
        if not functions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhuma função ativa encontrada para relé '{relay_id}'"
            )
        
        # Formatar resposta
        functions_list = []
        for func in functions:
            functions_list.append({
                "id": func[0],
                "relay_file": func[1],
                "relay_model": func[2],
                "function_code": func[3],
                "function_description": func[4],
                "detection_method": func[5],
                "source_file": func[6],
                "detection_timestamp": func[7].isoformat() if func[7] else None
            })
        
        # Estatísticas
        stats = {
            "total_functions": len(functions_list),
            "relay_model": functions_list[0]["relay_model"] if functions_list else None,
            "detection_methods": list(set(f["detection_method"] for f in functions_list)),
            "function_codes": [f["function_code"] for f in functions_list]
        }
        
        logger.info(f"✅ {len(functions_list)} funções encontradas para {relay_id}")
        
        return {
            "relay_id": relay_id,
            "relay_file": functions_list[0]["relay_file"] if functions_list else relay_id,
            "relay_model": stats["relay_model"],
            "functions": functions_list,
            "statistics": stats,
            "data_source": "postgresql_real"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar funções ativas para {relay_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar funções ativas: {str(e)}"
        )

@router.get("/active-functions/summary")
async def get_active_functions_summary(db: Session = Depends(get_db)):
    """
    📊 **Resumo Geral de Funções Ativas**
    
    Retorna estatísticas consolidadas de todas as funções ativas detectadas.
    """
    try:
        # Estatísticas gerais
        stats_query = text("""
            SELECT 
                COUNT(*) as total_functions,
                COUNT(DISTINCT relay_file) as total_relays,
                COUNT(DISTINCT relay_model) as total_models,
                COUNT(DISTINCT function_code) as unique_functions
            FROM protec_ai.active_protection_functions
        """)
        
        stats_result = db.execute(stats_query).fetchone()
        
        # Funções mais comuns
        functions_query = text("""
            SELECT 
                function_code,
                function_description,
                COUNT(*) as relay_count
            FROM protec_ai.active_protection_functions
            GROUP BY function_code, function_description
            ORDER BY relay_count DESC
        """)
        
        functions_result = db.execute(functions_query).fetchall()
        
        # Modelos mais comuns
        models_query = text("""
            SELECT 
                relay_model,
                COUNT(*) as function_count
            FROM protec_ai.active_protection_functions
            GROUP BY relay_model
            ORDER BY function_count DESC
        """)
        
        models_result = db.execute(models_query).fetchall()
        
        return {
            "summary": {
                "total_functions": stats_result[0] if stats_result else 0,
                "total_relays": stats_result[1] if stats_result else 0,
                "total_models": stats_result[2] if stats_result else 0,
                "unique_function_codes": stats_result[3] if stats_result else 0
            },
            "functions_by_code": [
                {
                    "code": row[0],
                    "description": row[1],
                    "relay_count": row[2],
                    "percentage": round((row[2] / stats_result[1] * 100), 1) if stats_result and stats_result[1] > 0 else 0
                }
                for row in functions_result
            ],
            "functions_by_model": [
                {
                    "model": row[0],
                    "function_count": row[1]
                }
                for row in models_result
            ],
            "data_source": "postgresql_real"
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar resumo de funções ativas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar resumo: {str(e)}"
        )

@router.get("/active-functions/search")
async def search_active_functions(
    function_code: Optional[str] = None,
    relay_model: Optional[str] = None,
    detection_method: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    🔎 **Busca Avançada de Funções Ativas**
    
    Busca funções ativas com filtros múltiplos.
    
    - **function_code**: Código ANSI da função (ex: "50/51", "27")
    - **relay_model**: Modelo do relé (ex: "MICON_P220", "SEPAM_S40")
    - **detection_method**: Método de detecção (ex: "checkbox", "function_field")
    """
    try:
        # Construir query dinamicamente
        conditions = []
        params = {}
        
        if function_code:
            conditions.append("function_code = :function_code")
            params["function_code"] = function_code
        
        if relay_model:
            conditions.append("relay_model ILIKE :relay_model")
            params["relay_model"] = f"%{relay_model}%"
        
        if detection_method:
            conditions.append("detection_method = :detection_method")
            params["detection_method"] = detection_method
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = text(f"""
            SELECT 
                relay_file,
                relay_model,
                function_code,
                function_description,
                detection_method,
                detection_timestamp
            FROM protec_ai.active_protection_functions
            WHERE {where_clause}
            ORDER BY relay_file, function_code
        """)
        
        result = db.execute(query, params)
        records = result.fetchall()
        
        return {
            "filters": {
                "function_code": function_code,
                "relay_model": relay_model,
                "detection_method": detection_method
            },
            "total_results": len(records),
            "results": [
                {
                    "relay_file": row[0],
                    "relay_model": row[1],
                    "function_code": row[2],
                    "function_description": row[3],
                    "detection_method": row[4],
                    "detection_timestamp": row[5].isoformat() if row[5] else None
                }
                for row in records
            ],
            "data_source": "postgresql_real"
        }
        
    except Exception as e:
        logger.error(f"Erro na busca de funções ativas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na busca: {str(e)}"
        )

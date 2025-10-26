"""
Router de Comparação - Core da Aplicação ProtecAI
=================================================

Endpoints para comparação inteligente de configurações de relés.
Integra com o relay_configuration_comparator.py existente.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
import uuid
from datetime import datetime

from api.core.database import get_db
from api.schemas import (
    ComparisonRequest,
    ComparisonResponse,
    BaseResponse
)
from api.services.comparison_service import ComparisonService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/equipment-configurations", response_model=dict)
async def compare_equipment_configurations(
    equipment_ids: List[str],
    db: Session = Depends(get_db)
):
    """
    🔬 **Comparar Configurações de Equipamentos**
    
    Realiza comparação inteligente entre configurações de equipamentos.
    """
    try:
        if len(equipment_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 equipment IDs are required for comparison"
            )
        
        service = ComparisonService(db)
        
        # Verificar se os equipamentos existem
        equipments = []
        for eq_id in equipment_ids[:2]:  # Compare first 2 equipments
            equipment = await service.get_equipment(eq_id)
            if not equipment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Equipment with ID {eq_id} not found"
                )
            equipments.append(equipment)
        
        # Realizar comparação
        comparison_result = await service.compare_equipments(
            equipment_1_id=equipment_ids[0],
            equipment_2_id=equipment_ids[1],
            comparison_type="full",
            include_details=True
        )
        
        # Gerar ID do relatório
        comparison_id = f"comp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await service.save_comparison_report(comparison_id, comparison_result)
        
        logger.info(f"Comparison completed between equipment {equipment_ids[0]} and {equipment_ids[1]}")
        
        return {
            "success": True,
            "comparison_id": comparison_id,
            "equipment_1": equipments[0],
            "equipment_2": equipments[1],
            "summary": comparison_result["summary"],
            "differences": comparison_result["differences"],
            "message": f"Comparison completed successfully - {comparison_result['summary']['total_comparisons']} parameters analyzed",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing equipment comparison"
        )

@router.get("/recommendations/{comparison_id}", response_model=dict)
async def get_comparison_recommendations(
    comparison_id: str,
    db: Session = Depends(get_db)
):
    """
    📄 **Obter Recomendações de Comparação**
    
    Recupera recomendações baseadas em uma comparação previamente executada.
    """
    try:
        service = ComparisonService(db)
        
        # Get recommendations using the service method (doesn't require saved report)
        recommendations_result = await service.get_recommendations(comparison_id)
        
        return recommendations_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recommendations for comparison {comparison_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving comparison recommendations"
        )
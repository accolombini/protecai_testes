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

@router.post("/", response_model=ComparisonResponse)
async def compare_equipments(
    comparison_request: ComparisonRequest,
    db: Session = Depends(get_db)
):
    """
    🔬 **Comparar Equipamentos**
    
    Realiza comparação inteligente entre dois equipamentos de proteção.
    
    **Funcionalidades:**
    - Comparação de configurações elétricas (TC/TP, tensões)
    - Análise de funções de proteção (habilitadas/desabilitadas)
    - Verificação de configurações I/O
    - Classificação por criticidade (🚨 crítico, ⚠️ aviso, ℹ️ informativo)
    - Geração de relatório detalhado
    
    **Tipos de Comparação:**
    - `full`: Comparação completa (padrão)
    - `electrical`: Apenas configurações elétricas
    - `protection`: Apenas funções de proteção
    - `io`: Apenas configurações I/O
    """
    try:
        # Validar se os equipamentos existem
        if comparison_request.equipment_1_id == comparison_request.equipment_2_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot compare equipment with itself"
            )
        
        service = ComparisonService(db)
        
        # Verificar se os equipamentos existem
        equipment_1 = await service.get_equipment(comparison_request.equipment_1_id)
        equipment_2 = await service.get_equipment(comparison_request.equipment_2_id)
        
        if not equipment_1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment with ID {comparison_request.equipment_1_id} not found"
            )
        
        if not equipment_2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment with ID {comparison_request.equipment_2_id} not found"
            )
        
        # Realizar comparação
        comparison_result = await service.compare_equipments(
            equipment_1_id=comparison_request.equipment_1_id,
            equipment_2_id=comparison_request.equipment_2_id,
            comparison_type=comparison_request.comparison_type,
            include_details=comparison_request.include_details
        )
        
        # Gerar ID do relatório se solicitado
        report_id = None
        if comparison_request.include_details:
            report_id = str(uuid.uuid4())
            await service.save_comparison_report(report_id, comparison_result)
        
        logger.info(f"Comparison completed between equipment {comparison_request.equipment_1_id} and {comparison_request.equipment_2_id}")
        
        return ComparisonResponse(
            equipment_1=equipment_1,
            equipment_2=equipment_2,
            summary=comparison_result["summary"],
            differences=comparison_result["differences"],
            comparison_type=comparison_request.comparison_type,
            report_id=report_id,
            message=f"Comparison completed successfully - {comparison_result['summary']['total_comparisons']} parameters analyzed"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing equipment comparison"
        )

@router.get("/reports/{report_id}", response_model=dict)
async def get_comparison_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    📄 **Obter Relatório de Comparação**
    
    Recupera relatório detalhado de uma comparação previamente executada.
    
    - **report_id**: ID único do relatório gerado
    """
    try:
        service = ComparisonService(db)
        report = await service.get_comparison_report(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comparison report with ID {report_id} not found"
            )
        
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving comparison report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving comparison report"
        )

@router.get("/history/{equipment_id}", response_model=List[dict])
async def get_comparison_history(
    equipment_id: int,
    limit: Optional[int] = 10,
    db: Session = Depends(get_db)
):
    """
    📚 **Histórico de Comparações**
    
    Retorna histórico de comparações envolvendo um equipamento específico.
    
    - **equipment_id**: ID do equipamento
    - **limit**: Número máximo de comparações a retornar (padrão: 10)
    """
    try:
        service = ComparisonService(db)
        history = await service.get_comparison_history(equipment_id, limit)
        
        return history
    except Exception as e:
        logger.error(f"Error retrieving comparison history for equipment {equipment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving comparison history"
        )

@router.post("/batch", response_model=List[ComparisonResponse])
async def compare_equipment_batch(
    equipment_pairs: List[ComparisonRequest],
    db: Session = Depends(get_db)
):
    """
    📊 **Comparação em Lote**
    
    Realiza múltiplas comparações em uma única requisição.
    
    - **equipment_pairs**: Lista de pares de equipamentos para comparar
    
    **Limitações:**
    - Máximo de 10 comparações por requisição
    - Timeout de 30 segundos por comparação
    """
    try:
        if len(equipment_pairs) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 comparisons allowed per batch request"
            )
        
        service = ComparisonService(db)
        results = []
        
        for pair in equipment_pairs:
            try:
                # Realizar comparação individual
                equipment_1 = await service.get_equipment(pair.equipment_1_id)
                equipment_2 = await service.get_equipment(pair.equipment_2_id)
                
                if not equipment_1 or not equipment_2:
                    continue  # Pular comparações com equipamentos não encontrados
                
                comparison_result = await service.compare_equipments(
                    equipment_1_id=pair.equipment_1_id,
                    equipment_2_id=pair.equipment_2_id,
                    comparison_type=pair.comparison_type,
                    include_details=pair.include_details
                )
                
                results.append(ComparisonResponse(
                    equipment_1=equipment_1,
                    equipment_2=equipment_2,
                    summary=comparison_result["summary"],
                    differences=comparison_result["differences"],
                    comparison_type=pair.comparison_type,
                    message="Batch comparison completed successfully"
                ))
                
            except Exception as e:
                logger.warning(f"Failed comparison in batch: {pair.equipment_1_id} vs {pair.equipment_2_id}: {e}")
                continue
        
        logger.info(f"Batch comparison completed: {len(results)} successful comparisons")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing batch comparison"
        )

@router.get("/statistics", response_model=dict)
async def get_comparison_statistics(
    db: Session = Depends(get_db)
):
    """
    📈 **Estatísticas de Comparações**
    
    Retorna estatísticas gerais sobre comparações realizadas no sistema.
    """
    try:
        service = ComparisonService(db)
        stats = await service.get_comparison_statistics()
        
        return {
            "success": True,
            "message": "Comparison statistics retrieved successfully",
            "timestamp": datetime.now().isoformat(),
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error retrieving comparison statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving comparison statistics"
        )
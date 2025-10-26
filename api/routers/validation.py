"""
Router de Validação - Verificação de Conformidade
=================================================

Endpoints para validação de configurações e seletividade.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from api.core.database import get_db
from api.schemas.main_schemas import ValidationRequest, ValidationResponse, BaseResponse
from api.services.validation_service import ValidationService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ValidationResponse)
async def validate_configuration(
    validation_request: ValidationRequest,
    db: Session = Depends(get_db)
):
    """
    ✅ **Validar Configuração**
    
    Valida configurações de equipamentos segundo normas e boas práticas.
    
    **Tipos de Validação:**
    - `full`: Validação completa (configuração elétrica + proteção + I/O)
    - `electrical`: Apenas configuração elétrica
    - `protection`: Apenas funções de proteção
    - `io`: Apenas configurações I/O
    - `selectivity`: Validação de seletividade
    
    **Verificações Realizadas:**
    - Conformidade com normas técnicas
    - Consistência de parametrização
    - Adequação de ajustes
    - Coordenação entre funções
    """
    try:
        logger.info(f"🔍 VALIDATION DEBUG: Starting validation for {validation_request.equipment_ids}")
        
        service = ValidationService(db)
        logger.info(f"🔍 VALIDATION DEBUG: ValidationService created successfully")
        
        validation_result = await service.validate_equipments(
            equipment_ids=validation_request.equipment_ids,
            validation_type=validation_request.validation_type
        )
        logger.info(f"🔍 VALIDATION DEBUG: validate_equipments returned: {type(validation_result)}")
        
        return validation_result
    except Exception as e:
        logger.error(f"🚨 VALIDATION ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"🚨 VALIDATION TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing configuration validation"
        )

@router.get("/rules", response_model=dict)
async def get_validation_rules():
    """
    📋 **Regras de Validação**
    
    Retorna todas as regras de validação utilizadas pelo sistema.
    """
    try:
        service = ValidationService(None)  # Não precisa de DB para regras estáticas
        rules = await service.get_validation_templates()
        
        return {
            "success": True,
            "message": "Validation rules retrieved successfully",
            "rules": rules
        }
    except Exception as e:
        logger.error(f"Error retrieving validation rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving validation rules"
        )

@router.post("/custom", response_model=ValidationResponse)
async def custom_validation(
    equipment_ids: List[int],
    custom_rules: dict,
    db: Session = Depends(get_db)
):
    """
    🔧 **Validação Customizada**
    
    Executa validação com regras personalizadas.
    """
    try:
        service = ValidationService(db)
        validation_result = await service.custom_validation(
            equipment_ids=equipment_ids,
            custom_rules=custom_rules
        )
        
        return validation_result
    except Exception as e:
        logger.error(f"Error during custom validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing custom validation"
        )
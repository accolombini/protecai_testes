"""
Router de Equipamentos - CRUD Completo com Sistema Unificado
============================================================

Endpoints para gerenciamento de equipamentos de proteção com
integração transparente entre schemas protec_ai e relay_configs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from api.core.database import get_db
from api.schemas import (
    EquipmentResponse, 
    EquipmentCreate, 
    EquipmentUpdate, 
    EquipmentListResponse,
    BaseResponse,
    PaginationParams
)
from api.services.unified_equipment_service import UnifiedEquipmentService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=Dict[str, Any])
async def list_equipments(
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(10, ge=1, le=100, description="Itens por página"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por status"),
    manufacturer: Optional[str] = Query(None, description="Filtrar por fabricante"),
    db: Session = Depends(get_db)
):
    """
    📋 **Listar Equipamentos Unificados**
    
    Retorna lista paginada de equipamentos de ambos os schemas (protec_ai + relay_configs).
    
    - **page**: Número da página (padrão: 1)
    - **size**: Itens por página (padrão: 10, máximo: 100)
    - **status**: Filtrar por status (active, inactive, maintenance, decommissioned)
    - **manufacturer**: Filtrar por nome do fabricante
    """
    try:
        # Usar o service unificado validado
        service = UnifiedEquipmentService(db)
        
        equipments_data, total = await service.get_unified_equipment_data(
            page=page,
            size=size,
            manufacturer_filter=manufacturer or ""
        )
        
        return {
            "data": equipments_data,
            "total": total,
            "page": page,
            "size": size,
            "message": f"Found {len(equipments_data)} unified equipments",
            "protec_ai_count": len([eq for eq in equipments_data if eq.get("source_schema") == "protec_ai"]),
            "relay_configs_count": len([eq for eq in equipments_data if eq.get("source_schema") == "relay_configs"])
        }
    except Exception as e:
        logger.error(f"Error listing unified equipments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving equipments"
        )

@router.get("/{equipment_id}", response_model=Dict[str, Any])
async def get_equipment(
    equipment_id: str,
    db: Session = Depends(get_db)
):
    """
    🔍 **Obter Equipamento por ID Unificado**
    
    Retorna detalhes completos de um equipamento de qualquer schema.
    
    - **equipment_id**: ID único do equipamento (formato: schema_id)
    """
    try:
        service = UnifiedEquipmentService(db)
        equipment = await service.get_unified_equipment_details(equipment_id)
        
        if not equipment or not equipment.get("equipment"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment with ID {equipment_id} not found"
            )
        
        return equipment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting equipment {equipment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving equipment"
        )

@router.get("/statistics/unified")
async def get_unified_statistics(db: Session = Depends(get_db)):
    """Obter estatísticas unificadas do sistema de equipamentos"""
    try:
        logger.info("Retrieving unified equipment statistics")
        service = UnifiedEquipmentService(db)
        stats = await service.get_unified_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting unified statistics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")

@router.get("/manufacturers/unified", response_model=Dict[str, Any])
async def get_unified_manufacturers(
    query: str = Query("", description="Filtro de busca por nome"),
    db: Session = Depends(get_db)
):
    """
    🏭 **Fabricantes Unificados**
    
    Retorna lista consolidada de fabricantes de ambos os schemas.
    """
    try:
        service = UnifiedEquipmentService(db)
        manufacturers = await service.search_unified_manufacturers(query)
        return manufacturers
    except Exception as e:
        logger.error(f"Error getting unified manufacturers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving manufacturers"
        )

@router.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    equipment: EquipmentCreate,
    db: Session = Depends(get_db)
):
    """
    ➕ **Criar Novo Equipamento**
    
    AVISO: Funcionalidade em desenvolvimento para sistema unificado.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Create functionality being implemented for unified system"
    )

@router.put("/{equipment_id}", response_model=BaseResponse)
async def update_equipment(
    equipment_id: str,
    equipment_update: EquipmentUpdate,
    db: Session = Depends(get_db)
):
    """
    📝 **Atualizar Equipamento**
    
    AVISO: Funcionalidade em desenvolvimento para sistema unificado.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Update functionality being implemented for unified system"
    )

@router.delete("/{equipment_id}", response_model=BaseResponse)
async def delete_equipment(
    equipment_id: str,
    db: Session = Depends(get_db)
):
    """
    🗑️ **Excluir Equipamento**
    
    AVISO: Funcionalidade em desenvolvimento para sistema unificado.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete functionality being implemented for unified system"
    )

@router.get("/{equipment_id}/electrical", response_model=dict)
async def get_equipment_electrical_config(
    equipment_id: str,
    db: Session = Depends(get_db)
):
    """
    ⚡ **Obter Configuração Elétrica**
    
    AVISO: Funcionalidade em desenvolvimento para sistema unificado.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Electrical configuration functionality being implemented for unified system"
    )

@router.get("/{equipment_id}/protection-functions", response_model=List[dict])
async def get_equipment_protection_functions(
    equipment_id: str,
    db: Session = Depends(get_db)
):
    """
    🛡️ **Obter Funções de Proteção**
    
    AVISO: Funcionalidade em desenvolvimento para sistema unificado.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Protection functions functionality being implemented for unified system"
    )

@router.get("/{equipment_id}/io-configuration", response_model=List[dict])
async def get_equipment_io_configuration(
    equipment_id: str,
    db: Session = Depends(get_db)
):
    """
    🔌 **Obter Configuração I/O**
    
    AVISO: Funcionalidade em desenvolvimento para sistema unificado.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="I/O configuration functionality being implemented for unified system"
    )

@router.get("/{equipment_id}/summary", response_model=dict)
async def get_equipment_summary(
    equipment_id: str,
    db: Session = Depends(get_db)
):
    """
    📊 **Obter Resumo Completo**
    
    AVISO: Funcionalidade em desenvolvimento para sistema unificado.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Summary functionality being implemented for unified system"
    )
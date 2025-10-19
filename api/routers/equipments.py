"""
Router de Equipamentos - CRUD Completo
======================================

Endpoints para gerenciamento de equipamentos de proteção.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status
from sqlalchemy.orm import Session
from typing import List, Optional
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
from api.services.equipment_service import EquipmentService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=EquipmentListResponse)
async def list_equipments(
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(10, ge=1, le=100, description="Itens por página"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por status"),
    manufacturer: Optional[str] = Query(None, description="Filtrar por fabricante"),
    db: Session = Depends(get_db)
):
    """
    📋 **Listar Equipamentos**
    
    Retorna lista paginada de equipamentos com filtros opcionais.
    
    - **page**: Número da página (padrão: 1)
    - **size**: Itens por página (padrão: 10, máximo: 100)
    - **status**: Filtrar por status (active, inactive, maintenance, decommissioned)
    - **manufacturer**: Filtrar por nome do fabricante
    """
    try:
        # Buscar equipamentos usando service com DB real
        service = EquipmentService(db)
        equipments_data, total = await service.get_equipments(
            page=page, 
            size=size, 
            status_filter=status_filter,
            manufacturer_filter=manufacturer
        )
        
        return EquipmentListResponse(
            data=equipments_data,
            total=total,
            page=page,
            size=size,
            message=f"Found {total} equipments"
        )
    except Exception as e:
        logger.error(f"Error listing equipments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving equipments"
        )

@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    """
    🔍 **Obter Equipamento por ID**
    
    Retorna detalhes completos de um equipamento específico.
    
    - **equipment_id**: ID único do equipamento
    """
    try:
        service = EquipmentService()
        equipment = await service.get_equipment_by_id(equipment_id)
        
        if not equipment:
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

@router.post("/", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    equipment: EquipmentCreate,
    db: Session = Depends(get_db)
):
    """
    ➕ **Criar Novo Equipamento**
    
    Cria um novo equipamento no sistema.
    
    - **equipment**: Dados do equipamento a ser criado
    """
    try:
        service = EquipmentService()
        new_equipment = await service.create_equipment(equipment)
        
        logger.info(f"Equipment created with ID: {new_equipment.id}")
        return new_equipment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating equipment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating equipment"
        )

@router.put("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    equipment_update: EquipmentUpdate,
    db: Session = Depends(get_db)
):
    """
    📝 **Atualizar Equipamento**
    
    Atualiza dados de um equipamento existente.
    
    - **equipment_id**: ID do equipamento a ser atualizado
    - **equipment_update**: Dados a serem atualizados
    """
    try:
        service = EquipmentService()
        updated_equipment = await service.update_equipment(equipment_id, equipment_update)
        
        if not updated_equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment with ID {equipment_id} not found"
            )
        
        logger.info(f"Equipment {equipment_id} updated successfully")
        return updated_equipment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating equipment {equipment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating equipment"
        )

@router.delete("/{equipment_id}", response_model=BaseResponse)
async def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    """
    🗑️ **Excluir Equipamento**
    
    Remove um equipamento do sistema (soft delete - marca como descomissionado).
    
    - **equipment_id**: ID do equipamento a ser excluído
    """
    try:
        service = EquipmentService()
        success = await service.delete_equipment(equipment_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment with ID {equipment_id} not found"
            )
        
        logger.info(f"Equipment {equipment_id} deleted successfully")
        return BaseResponse(
            message=f"Equipment {equipment_id} deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting equipment {equipment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting equipment"
        )

@router.get("/{equipment_id}/electrical", response_model=dict)
async def get_equipment_electrical_config(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    """
    ⚡ **Obter Configuração Elétrica**
    
    Retorna configuração elétrica completa de um equipamento.
    
    - **equipment_id**: ID do equipamento
    """
    try:
        service = EquipmentService()
        electrical_config = await service.get_electrical_configuration(equipment_id)
        
        if not electrical_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Electrical configuration not found for equipment {equipment_id}"
            )
        
        return electrical_config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting electrical config for equipment {equipment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving electrical configuration"
        )

@router.get("/{equipment_id}/protection-functions", response_model=List[dict])
async def get_equipment_protection_functions(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    """
    🛡️ **Obter Funções de Proteção**
    
    Retorna todas as funções de proteção de um equipamento.
    
    - **equipment_id**: ID do equipamento
    """
    try:
        service = EquipmentService()
        protection_functions = await service.get_protection_functions(equipment_id)
        
        return protection_functions
    except Exception as e:
        logger.error(f"Error getting protection functions for equipment {equipment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving protection functions"
        )

@router.get("/{equipment_id}/io-configuration", response_model=List[dict])
async def get_equipment_io_configuration(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    """
    🔌 **Obter Configuração I/O**
    
    Retorna configuração de I/O completa de um equipamento.
    
    - **equipment_id**: ID do equipamento
    """
    try:
        service = EquipmentService()
        io_config = await service.get_io_configuration(equipment_id)
        
        return io_config
    except Exception as e:
        logger.error(f"Error getting I/O configuration for equipment {equipment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving I/O configuration"
        )

@router.get("/{equipment_id}/summary", response_model=dict)
async def get_equipment_summary(
    equipment_id: int,
    db: Session = Depends(get_db)
):
    """
    📊 **Obter Resumo Completo**
    
    Retorna resumo completo do equipamento com todas as configurações.
    
    - **equipment_id**: ID do equipamento
    """
    try:
        service = EquipmentService()
        summary = await service.get_equipment_summary(equipment_id)
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment with ID {equipment_id} not found"
            )
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting equipment summary {equipment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving equipment summary"
        )
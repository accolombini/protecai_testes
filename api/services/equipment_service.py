"""
Equipment Service - Robusta com SQLAlchemy ORM
===============================================

Service layer REAL para operacoes CRUD de equipamentos.
Queries diretas no PostgreSQL usando SQLAlchemy ORM.
Arquitetura escalavel para producao.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import SQLAlchemyError

from api.models.equipment_models import (
    RelayEquipment, 
    RelayModel, 
    Manufacturer,
    ElectricalConfiguration,
    ProtectionFunction,
    IOConfiguration
)

logger = logging.getLogger(__name__)

class EquipmentService:
    """Service para gerenciamento REAL de equipamentos com SQLAlchemy ORM"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_equipments(
        self,
        page: int = 1,
        size: int = 10,
        status_filter: Optional[str] = None,
        manufacturer_filter: Optional[str] = None
    ) -> Tuple[List[Dict], int]:
        """
        Busca equipamentos com paginacao e filtros usando SQLAlchemy ORM
        
        Returns:
            Tuple[List[Dict], int]: (equipments_data, total_count)
        """
        try:
            # Query base com joins otimizados
            query = self.db.query(RelayEquipment)\
                           .join(RelayModel)\
                           .join(Manufacturer)\
                           .options(
                               selectinload(RelayEquipment.model)
                               .selectinload(RelayModel.manufacturer)
                           )
            
            # Aplicar filtros
            if status_filter:
                query = query.filter(RelayEquipment.status == status_filter)
            
            if manufacturer_filter:
                query = query.filter(Manufacturer.name.ilike(f"%{manufacturer_filter}%"))
            
            # Contar total antes da paginacao
            total = query.count()
            
            # Aplicar paginacao
            offset = (page - 1) * size
            equipments = query.offset(offset).limit(size).all()
            
            # Converter para formato de resposta
            equipments_data = []
            for equipment in equipments:
                equipment_dict = {
                    "id": equipment.id,
                    "tag_reference": equipment.tag_reference,
                    "serial_number": equipment.serial_number,
                    "plant_reference": equipment.plant_reference,
                    "bay_position": equipment.bay_position,
                    "software_version": equipment.software_version,
                    "frequency": float(equipment.frequency) if equipment.frequency else None,
                    "description": equipment.description,
                    "installation_date": equipment.installation_date,
                    "commissioning_date": equipment.commissioning_date,
                    "status": equipment.status,
                    "model_id": equipment.model_id,
                    "created_at": equipment.created_at.isoformat() if equipment.created_at else None,
                    "updated_at": equipment.updated_at.isoformat() if equipment.updated_at else None,
                    "model": {
                        "id": equipment.model.id,
                        "name": equipment.model.name,
                        "model_type": equipment.model.model_type,
                        "family": equipment.model.family,
                        "application_type": equipment.model.application_type,
                        "voltage_class": equipment.model.voltage_class,
                        "current_class": equipment.model.current_class,
                        "manufacturer_id": equipment.model.manufacturer_id,
                        "manufacturer": {
                            "id": equipment.model.manufacturer.id,
                            "name": equipment.model.manufacturer.name,
                            "country": equipment.model.manufacturer.country,
                            "website": equipment.model.manufacturer.website,
                            "support_contact": equipment.model.manufacturer.support_contact
                        }
                    }
                }
                equipments_data.append(equipment_dict)
            
            logger.info(f"Retrieved {len(equipments_data)} equipments from database")
            return equipments_data, total
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting equipments: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting equipments: {e}")
            raise
    
    async def get_equipment_by_id(self, equipment_id: int) -> Optional[Dict]:
        """
        Busca equipamento por ID com todas as relacoes carregadas
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Optional[Dict]: Dados completos do equipamento ou None
        """
        try:
            equipment = self.db.query(RelayEquipment)\
                              .options(
                                  selectinload(RelayEquipment.model)
                                  .selectinload(RelayModel.manufacturer)
                              )\
                              .filter(RelayEquipment.id == equipment_id)\
                              .first()
            
            if not equipment:
                return None
            
            equipment_dict = {
                "id": equipment.id,
                "tag_reference": equipment.tag_reference,
                "serial_number": equipment.serial_number,
                "plant_reference": equipment.plant_reference,
                "bay_position": equipment.bay_position,
                "software_version": equipment.software_version,
                "frequency": float(equipment.frequency) if equipment.frequency else None,
                "description": equipment.description,
                "installation_date": equipment.installation_date,
                "commissioning_date": equipment.commissioning_date,
                "status": equipment.status,
                "model_id": equipment.model_id,
                "created_at": equipment.created_at.isoformat() if equipment.created_at else None,
                "updated_at": equipment.updated_at.isoformat() if equipment.updated_at else None,
                "model": {
                    "id": equipment.model.id,
                    "name": equipment.model.name,
                    "model_type": equipment.model.model_type,
                    "family": equipment.model.family,
                    "application_type": equipment.model.application_type,
                    "voltage_class": equipment.model.voltage_class,
                    "current_class": equipment.model.current_class,
                    "manufacturer_id": equipment.model.manufacturer_id,
                    "manufacturer": {
                        "id": equipment.model.manufacturer.id,
                        "name": equipment.model.manufacturer.name,
                        "country": equipment.model.manufacturer.country,
                        "website": equipment.model.manufacturer.website,
                        "support_contact": equipment.model.manufacturer.support_contact
                    }
                }
            }
            
            logger.info(f"Retrieved equipment {equipment_id} from database")
            return equipment_dict
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting equipment {equipment_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting equipment {equipment_id}: {e}")
            raise
    
    async def get_electrical_configuration(self, equipment_id: int) -> Optional[Dict]:
        """Busca configuracao eletrica do equipamento"""
        try:
            config = self.db.query(ElectricalConfiguration)\
                           .filter(ElectricalConfiguration.equipment_id == equipment_id)\
                           .first()
            
            if not config:
                return None
            
            return {
                "id": config.id,
                "equipment_id": config.equipment_id,
                "phase_ct_primary": config.phase_ct_primary,
                "phase_ct_secondary": config.phase_ct_secondary,
                "neutral_ct_primary": config.neutral_ct_primary,
                "neutral_ct_secondary": config.neutral_ct_secondary,
                "vt_primary": config.vt_primary,
                "vt_secondary": config.vt_secondary,
                "nominal_voltage": config.nominal_voltage,
                "frequency": config.frequency
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting electrical config for equipment {equipment_id}: {e}")
            raise
    
    async def get_protection_functions(self, equipment_id: int) -> List[Dict]:
        """Busca funcoes de protecao do equipamento"""
        try:
            functions = self.db.query(ProtectionFunction)\
                             .filter(ProtectionFunction.equipment_id == equipment_id)\
                             .order_by(ProtectionFunction.function_code)\
                             .all()
            
            functions_data = []
            for func in functions:
                function_dict = {
                    "id": func.id,
                    "equipment_id": func.equipment_id,
                    "function_code": func.function_code,
                    "function_name": func.function_name,
                    "enabled": func.enabled,
                    "pickup_value": func.pickup_value,
                    "time_delay": func.time_delay,
                    "curve_type": func.curve_type,
                    "settings": func.settings
                }
                functions_data.append(function_dict)
            
            return functions_data
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting protection functions for equipment {equipment_id}: {e}")
            return []
    
    async def get_io_configuration(self, equipment_id: int) -> List[Dict]:
        """Busca configuracao I/O do equipamento"""
        try:
            io_configs = self.db.query(IOConfiguration)\
                               .filter(IOConfiguration.equipment_id == equipment_id)\
                               .order_by(IOConfiguration.channel_number)\
                               .all()
            
            io_data = []
            for io in io_configs:
                io_dict = {
                    "id": io.id,
                    "equipment_id": io.equipment_id,
                    "channel_number": io.channel_number,
                    "channel_type": io.channel_type,
                    "signal_type": io.signal_type,
                    "description": io.description,
                    "enabled": io.enabled,
                    "configuration": io.configuration
                }
                io_data.append(io_dict)
            
            return io_data
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting I/O configuration for equipment {equipment_id}: {e}")
            return []
    
    async def get_equipment_summary(self, equipment_id: int) -> Optional[Dict]:
        """Busca resumo completo do equipamento"""
        try:
            equipment = await self.get_equipment_by_id(equipment_id)
            if not equipment:
                return None
            
            electrical_config = await self.get_electrical_configuration(equipment_id)
            protection_functions = await self.get_protection_functions(equipment_id)
            io_configuration = await self.get_io_configuration(equipment_id)
            
            return {
                "equipment": equipment,
                "electrical_configuration": electrical_config,
                "protection_functions": protection_functions,
                "io_configuration": io_configuration,
                "summary_stats": {
                    "total_protection_functions": len(protection_functions),
                    "enabled_protection_functions": len([f for f in protection_functions if f.get("enabled", False)]),
                    "total_io_channels": len(io_configuration),
                    "enabled_io_channels": len([io for io in io_configuration if io.get("enabled", False)])
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating equipment summary for {equipment_id}: {e}")
            raise
    
    async def create_equipment(self, equipment_data) -> Dict:
        """
        Cria novo equipamento no banco de dados
        
        Args:
            equipment_data: Dados do equipamento a ser criado
            
        Returns:
            Dict: Dados do equipamento criado
        """
        try:
            # Verificar se o model_id existe
            model_exists = self.db.query(RelayModel)\
                                .filter(RelayModel.id == equipment_data.model_id)\
                                .first()
            
            if not model_exists:
                raise ValueError(f"Model with ID {equipment_data.model_id} not found")
            
            # Criar novo equipamento
            new_equipment = RelayEquipment(
                tag_reference=equipment_data.tag_reference,
                serial_number=equipment_data.serial_number,
                plant_reference=equipment_data.plant_reference,
                bay_position=getattr(equipment_data, 'bay_position', None),
                software_version=getattr(equipment_data, 'software_version', None),
                frequency=getattr(equipment_data, 'frequency', None),
                description=equipment_data.description,
                installation_date=getattr(equipment_data, 'installation_date', None),
                commissioning_date=getattr(equipment_data, 'commissioning_date', None),
                status=equipment_data.status,
                model_id=equipment_data.model_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(new_equipment)
            self.db.commit()
            self.db.refresh(new_equipment)
            
            logger.info(f"Created new equipment with ID: {new_equipment.id}")
            
            # Retornar dados completos do equipamento criado
            return await self.get_equipment_by_id(new_equipment.id)
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating equipment: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error creating equipment: {e}")
            raise
    
    async def update_equipment(self, equipment_id: int, equipment_data) -> Optional[Dict]:
        """
        Atualiza equipamento existente
        
        Args:
            equipment_id: ID do equipamento
            equipment_data: Dados a serem atualizados
            
        Returns:
            Optional[Dict]: Dados do equipamento atualizado ou None
        """
        try:
            equipment = self.db.query(RelayEquipment)\
                              .filter(RelayEquipment.id == equipment_id)\
                              .first()
            
            if not equipment:
                return None
            
            # Atualizar campos fornecidos
            update_data = equipment_data.dict(exclude_unset=True)
            
            if 'model_id' in update_data:
                model_exists = self.db.query(RelayModel)\
                                    .filter(RelayModel.id == update_data['model_id'])\
                                    .first()
                if not model_exists:
                    raise ValueError(f"Model with ID {update_data['model_id']} not found")
            
            for field, value in update_data.items():
                setattr(equipment, field, value)
            
            equipment.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(equipment)
            
            logger.info(f"Updated equipment with ID: {equipment_id}")
            
            # Retornar dados completos do equipamento atualizado
            return await self.get_equipment_by_id(equipment_id)
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating equipment {equipment_id}: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error updating equipment {equipment_id}: {e}")
            raise
    
    async def delete_equipment(self, equipment_id: int) -> bool:
        """
        Exclui equipamento (soft delete - marca como descomissionado)
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            bool: True se excluído com sucesso, False se não encontrado
        """
        try:
            equipment = self.db.query(RelayEquipment)\
                              .filter(RelayEquipment.id == equipment_id)\
                              .first()
            
            if not equipment:
                return False
            
            # Soft delete - marcar como descomissionado
            equipment.status = 'decommissioned'
            equipment.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Soft deleted equipment with ID: {equipment_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting equipment {equipment_id}: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error deleting equipment {equipment_id}: {e}")
            raise

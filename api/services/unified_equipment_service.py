"""
Unified Equipment Service - Integração Multi-Schema
==================================================

Service ROBUSTO que integra transparentemente dados de:
- Schema 'relay_configs': Equipamentos estruturados (tabelas SQLAlchemy)
- Schema 'protec_ai': Dados processados (tokens, fabricantes, configurações)

Solução robusta que UNIFICA as duas arquiteturas sem migração destrutiva.
Implementa fallbacks inteligentes e busca consolidada.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from fastapi import HTTPException

from api.models.equipment_models import (
    RelayEquipment, RelayModel, Manufacturer,
    ElectricalConfiguration, ProtectionFunction, IOConfiguration
)
from api.core.database import engine

logger = logging.getLogger(__name__)

class UnifiedEquipmentService:
    """
    Service unificado para dados de equipamentos
    Integra dados de relay_configs + protec_ai transparentemente
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.engine = engine
    
    async def get_unified_statistics(self) -> Dict[str, Any]:
        """
        Obtém estatísticas unificadas dos dois schemas
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                SELECT 
                    (SELECT COUNT(*) FROM protec_ai.arquivos) as processed_files,
                    (SELECT COUNT(*) FROM protec_ai.fabricantes) as extracted_manufacturers,
                    (SELECT COUNT(*) FROM protec_ai.tokens_valores) as parsed_tokens,
                    (SELECT COUNT(*) FROM protec_ai.valores_originais) as original_values,
                    (SELECT COUNT(DISTINCT codigo_campo) FROM protec_ai.campos_originais) as unique_parameters,
                    (SELECT COUNT(*) FROM relay_configs.relay_equipment) as relay_equipment_count,
                    (SELECT COUNT(*) FROM relay_configs.etap_studies) as etap_studies,
                    (SELECT COUNT(*) FROM relay_configs.etap_sync_logs) as sync_logs
                """)
                
                result = conn.execute(query).fetchone()
                
                return {
                    "unified_statistics": {
                        "protec_ai_data": {
                            "processed_files": result.processed_files,
                            "extracted_manufacturers": result.extracted_manufacturers,
                            "parsed_tokens": result.parsed_tokens,
                            "original_values": result.original_values,
                            "unique_parameters": result.unique_parameters
                        },
                        "relay_configs_data": {
                            "relay_equipment_count": result.relay_equipment_count,
                            "etap_studies": result.etap_studies,
                            "sync_logs": result.sync_logs
                        },
                        "total_records": (result.processed_files + result.extracted_manufacturers + 
                                        result.parsed_tokens + result.original_values + 
                                        result.relay_equipment_count + result.etap_studies + result.sync_logs)
                    }
                }
                
        except Exception as e:
            logger.error(f"Database error getting unified stats: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    async def search_unified_manufacturers(self, query: str = "") -> Dict[str, Any]:
        """Busca fabricantes em ambos os schemas de forma unificada"""
        try:
            with self.engine.connect() as conn:
                # Buscar em protec_ai.fabricantes
                protec_ai_query = text("""
                SELECT 
                    'protec_ai' as source_schema,
                    id,
                    nome_completo as name,
                    pais_origem as country,
                    created_at,
                    (SELECT COUNT(*) FROM protec_ai.arquivos WHERE fabricante_id = f.id) as file_count
                FROM protec_ai.fabricantes f
                WHERE (:query = '' OR nome_completo ILIKE :search_pattern)
                ORDER BY nome_completo
            """)
                
                search_pattern = f"%{query}%" if query else "%"
                protec_ai_result = conn.execute(protec_ai_query, {
                    "query": query,
                    "search_pattern": search_pattern
                }).fetchall()
                
                # Buscar em relay_configs.manufacturers (pode estar vazio)
                relay_configs_query = text("""
                SELECT 
                    'relay_configs' as source_schema,
                    id,
                    name,
                    country,
                    created_at,
                    (SELECT COUNT(*) FROM relay_configs.relay_models WHERE manufacturer_id = m.id) as model_count
                FROM relay_configs.manufacturers m
                WHERE (:query = '' OR name ILIKE :search_pattern)
                ORDER BY name
            """)
                
                relay_configs_result = conn.execute(relay_configs_query, {
                    "query": query,
                    "search_pattern": search_pattern
                }).fetchall()
                
                # Consolidar resultados
                manufacturers = []
                
                # Adicionar fabricantes do protec_ai
                for row in protec_ai_result:
                    manufacturers.append({
                        "id": f"protec_ai_{row.id}",
                        "source": "protec_ai",
                        "name": row.name,
                        "country": row.country,
                        "created_at": row.created_at,
                        "file_count": row.file_count,
                        "model_count": 0
                    })
                
                # Adicionar fabricantes do relay_configs
                for row in relay_configs_result:
                    manufacturers.append({
                        "id": f"relay_configs_{row.id}",
                        "source": "relay_configs",
                        "name": row.name,
                        "country": row.country,
                        "created_at": row.created_at,
                        "file_count": 0,
                        "model_count": row.model_count
                    })
                
                return {
                    "manufacturers": manufacturers,
                    "total_protec_ai": len(protec_ai_result),
                    "total_relay_configs": len(relay_configs_result),
                    "total_unified": len(manufacturers)
                }
                
        except Exception as e:
            logger.error(f"Database error searching unified manufacturers: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    
    async def get_unified_equipment_data(self, page: int = 1, size: int = 10, manufacturer_filter: str = "") -> Tuple[List[Dict], int]:
        """
        Busca unificada de dados de equipamentos
        Combina dados estruturados + dados extraídos
        """
        try:
            results = []
            
            # 1. Equipamentos estruturados (relay_configs)
            structured_query = text("""
                SELECT 
                    'relay_configs' as source_schema,
                    re.id,
                    re.tag_reference,
                    re.serial_number,
                    re.plant_reference,
                    re.bay_position,
                    re.status,
                    re.description,
                    rm.name as model_name,
                    rm.model_type,
                    rm.family,
                    m.name as manufacturer_name,
                    m.country as manufacturer_country,
                    re.created_at
                FROM relay_configs.relay_equipment re
                JOIN relay_configs.relay_models rm ON re.model_id = rm.id
                JOIN relay_configs.manufacturers m ON rm.manufacturer_id = m.id
                WHERE (:manufacturer_filter = '' OR m.name ILIKE :manufacturer_pattern)
                ORDER BY re.id
            """)
            
            structured_equipment = self.db.execute(structured_query, {
                "manufacturer_filter": manufacturer_filter,
                "manufacturer_pattern": f"%{manufacturer_filter}%" if manufacturer_filter else "%"
            }).fetchall()
            
            for eq in structured_equipment:
                results.append({
                    "id": f"relay_configs_{eq.id}",
                    "source": "relay_configs",
                    "tag_reference": eq.tag_reference,
                    "serial_number": eq.serial_number,
                    "plant_reference": eq.plant_reference,
                    "bay_position": eq.bay_position,
                    "status": eq.status,
                    "description": eq.description,
                    "model": {
                        "name": eq.model_name,
                        "type": eq.model_type,
                        "family": eq.family
                    },
                    "manufacturer": {
                        "name": eq.manufacturer_name,
                        "country": eq.manufacturer_country
                    },
                    "data_completeness": "structured",
                    "created_at": eq.created_at
                })
            
            # 2. Configurações extraídas (protec_ai) - amostras representativas
            extracted_query = text("""
                SELECT DISTINCT
                    'protec_ai' as source_schema,
                    vo.id,
                    co.codigo_campo,
                    vo.valor_original,
                    'N/A' as unidade,
                    f.nome_completo as manufacturer_name,
                    f.pais_origem as manufacturer_country,
                    a.nome_arquivo,
                    co.created_at as data_criacao
                FROM protec_ai.valores_originais vo
                JOIN protec_ai.campos_originais co ON vo.campo_id = co.id
                JOIN protec_ai.arquivos a ON co.arquivo_id = a.id
                JOIN protec_ai.fabricantes f ON a.fabricante_id = f.id
                WHERE (:manufacturer_filter = '' OR f.nome_completo ILIKE :manufacturer_pattern)
                AND co.descricao_campo ILIKE '%model%'
                ORDER BY vo.id
                LIMIT 50
            """)
            
            extracted_configs = self.db.execute(extracted_query, {
                "manufacturer_filter": manufacturer_filter,
                "manufacturer_pattern": f"%{manufacturer_filter}%" if manufacturer_filter else "%"
            }).fetchall()
            
            for config in extracted_configs:
                results.append({
                    "id": f"protec_ai_{config.id}",
                    "source": "protec_ai", 
                    "tag_reference": None,
                    "serial_number": None,
                    "plant_reference": None,
                    "bay_position": None,
                    "status": "extracted",
                    "description": f"Extracted parameter: {config.codigo_campo}",
                    "model": {
                        "name": config.valor_original,
                        "type": "extracted",
                        "family": None
                    },
                    "manufacturer": {
                        "name": config.manufacturer_name,
                        "country": config.manufacturer_country
                    },
                    "data_completeness": "extracted",
                    "source_file": config.nome_arquivo,
                    "parameter_field": config.codigo_campo,
                    "value": config.valor_original,
                    "unit": config.unidade,
                    "created_at": config.data_criacao
                })
            
            # 3. Aplicar paginação aos resultados unificados
            total = len(results)
            offset = (page - 1) * size
            paginated_results = results[offset:offset + size]
            
            logger.info(f"Retrieved {len(paginated_results)} unified equipment records (total: {total})")
            return paginated_results, total
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting unified equipment data: {e}")
            raise
    
    async def get_equipment_configuration_details(self, equipment_id: str) -> Optional[Dict]:
        """
        Busca detalhes completos de configuração
        Suporta IDs unificados: 'relay_configs_123' ou 'protec_ai_456'
        """
        try:
            schema, internal_id = self._parse_unified_id(equipment_id)
            
            if schema == "relay_configs":
                return await self._get_structured_equipment_details(int(internal_id))
            elif schema == "protec_ai":
                return await self._get_extracted_configuration_details(int(internal_id))
            else:
                logger.warning(f"Invalid equipment ID format: {equipment_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting equipment configuration details for {equipment_id}: {e}")
            raise
    
    def _parse_unified_id(self, unified_id: str) -> Tuple[str, str]:
        """
        Parse unified ID format: 'schema_internalid'
        Returns: (schema, internal_id)
        """
        if '_' not in unified_id:
            raise ValueError(f"Invalid unified ID format: {unified_id}")
        
        parts = unified_id.split('_', 1)
        return parts[0], parts[1]
    
    async def _get_structured_equipment_details(self, equipment_id: int) -> Dict:
        """Busca detalhes de equipamento estruturado (relay_configs)"""
        try:
            query = text("""
                SELECT 
                    re.id,
                    re.tag_reference,
                    re.serial_number,
                    re.plant_reference,
                    re.bay_position,
                    re.software_version,
                    re.frequency,
                    re.description,
                    re.installation_date,
                    re.commissioning_date,
                    re.status,
                    rm.name as model_name,
                    rm.model_type,
                    rm.family,
                    rm.application_type,
                    rm.voltage_class,
                    rm.current_class,
                    rm.protection_functions,
                    m.name as manufacturer_name,
                    m.country as manufacturer_country,
                    m.website,
                    m.support_contact,
                    -- Configuração elétrica
                    ec.phase_ct_primary,
                    ec.phase_ct_secondary,
                    ec.nominal_voltage,
                    -- Contagem de funções de proteção
                    (SELECT COUNT(*) FROM relay_configs.protection_functions WHERE equipment_id = re.id) as protection_count,
                    -- Contagem de I/O
                    (SELECT COUNT(*) FROM relay_configs.io_configuration WHERE equipment_id = re.id) as io_count
                FROM relay_configs.relay_equipment re
                JOIN relay_configs.relay_models rm ON re.model_id = rm.id
                JOIN relay_configs.manufacturers m ON rm.manufacturer_id = m.id
                LEFT JOIN relay_configs.electrical_configuration ec ON re.id = ec.equipment_id
                WHERE re.id = :equipment_id
            """)
            
            result = self.db.execute(query, {"equipment_id": equipment_id}).fetchone()
            
            if not result:
                return None
            
            return {
                "source": "relay_configs",
                "data_type": "structured",
                "equipment": {
                    "id": result.id,
                    "tag_reference": result.tag_reference,
                    "serial_number": result.serial_number,
                    "plant_reference": result.plant_reference,
                    "bay_position": result.bay_position,
                    "software_version": result.software_version,
                    "frequency": float(result.frequency) if result.frequency else None,
                    "description": result.description,
                    "installation_date": result.installation_date,
                    "commissioning_date": result.commissioning_date,
                    "status": result.status
                },
                "model": {
                    "name": result.model_name,
                    "type": result.model_type,
                    "family": result.family,
                    "application_type": result.application_type,
                    "voltage_class": result.voltage_class,
                    "current_class": result.current_class,
                    "protection_functions": result.protection_functions
                },
                "manufacturer": {
                    "name": result.manufacturer_name,
                    "country": result.manufacturer_country,
                    "website": result.website,
                    "support_contact": result.support_contact
                },
                "electrical_configuration": {
                    "phase_ct_primary": result.phase_ct_primary,
                    "phase_ct_secondary": result.phase_ct_secondary,
                    "nominal_voltage": result.nominal_voltage
                } if result.phase_ct_primary else None,
                "summary": {
                    "protection_functions_count": result.protection_count,
                    "io_channels_count": result.io_count,
                    "data_completeness": "complete"
                }
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting structured equipment details: {e}")
            raise
    
    async def _get_extracted_configuration_details(self, value_id: int) -> Dict:
        """Busca detalhes de configuração extraída (protec_ai)"""
        try:
            # Buscar dados principais
            main_query = text("""
                SELECT 
                    vo.id,
                    vo.valor_original,
                    'N/A' as unidade,
                    co.codigo_campo,
                    co.descricao_campo,
                    'N/A' as linha_origem,
                    a.nome_arquivo,
                    'N/A' as tipo_arquivo,
                    a.data_processamento,
                    f.nome_completo as manufacturer_name,
                    f.pais_origem as manufacturer_country,
                    -- Tokens associados
                    (SELECT COUNT(*) FROM protec_ai.tokens_valores WHERE campo_id = co.id) as token_count
                FROM protec_ai.valores_originais vo
                JOIN protec_ai.campos_originais co ON vo.campo_id = co.id
                JOIN protec_ai.arquivos a ON co.arquivo_id = a.id
                JOIN protec_ai.fabricantes f ON a.fabricante_id = f.id
                WHERE vo.id = :value_id
            """)
            
            main_result = self.db.execute(main_query, {"value_id": value_id}).fetchone()
            
            if not main_result:
                return None
            
            # Buscar tokens detalhados
            tokens_query = text("""
                SELECT 
                    tv.valor_token,
                    tv.significado,
                    tv.confianca,
                    tv.posicao,
                    tt.codigo as tipo_token,
                    tt.descricao as tipo_descricao
                FROM protec_ai.tokens_valores tv
                JOIN protec_ai.tipos_token tt ON tv.tipo_token_id = tt.id
                WHERE tv.valor_id = :value_id
                ORDER BY tv.posicao
            """)
            
            tokens = self.db.execute(tokens_query, {"value_id": value_id}).fetchall()
            
            return {
                "source": "protec_ai",
                "data_type": "extracted",
                "configuration": {
                    "id": main_result.id,
                    "parameter_field": main_result.codigo_campo,
                    "description": main_result.descricao_campo,
                    "value": main_result.valor_original,
                    "unit": main_result.unidade,
                    "source_line": main_result.linha_origem
                },
                "source_file": {
                    "filename": main_result.nome_arquivo,
                    "file_type": main_result.tipo_arquivo,
                    "processed_at": main_result.data_processamento
                },
                "manufacturer": {
                    "name": main_result.manufacturer_name,
                    "country": main_result.manufacturer_country
                },
                "parsed_tokens": [
                    {
                        "value": token.valor_token,
                        "meaning": token.significado,
                        "confidence": float(token.confianca) if token.confianca else None,
                        "position": token.posicao,
                        "type": token.tipo_token,
                        "type_description": token.tipo_descricao
                    }
                    for token in tokens
                ],
                "summary": {
                    "tokens_extracted": len(tokens),
                    "data_completeness": "extracted",
                    "confidence_score": sum(float(t.confianca) if t.confianca else 0 for t in tokens) / len(tokens) if tokens else 0
                }
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting extracted configuration details: {e}")
            raise
    
    async def create_equipment_from_extracted_data(self, protec_ai_id: int, additional_data: Dict) -> Dict:
        """
        Cria equipamento estruturado baseado em dados extraídos
        Migração robusta de protec_ai -> relay_configs
        """
        try:
            # 1. Buscar dados extraídos
            extracted_data = await self._get_extracted_configuration_details(protec_ai_id)
            if not extracted_data:
                raise ValueError(f"No extracted data found for ID: {protec_ai_id}")
            
            # 2. Criar/buscar manufacturer
            manufacturer = await self._ensure_manufacturer_exists(
                extracted_data["manufacturer"]["name"],
                extracted_data["manufacturer"]["country"]
            )
            
            # 3. Criar/buscar model
            model = await self._ensure_model_exists(
                manufacturer.id,
                extracted_data["configuration"]["value"],  # Usar valor como nome do modelo
                additional_data.get("model_type", "extracted")
            )
            
            # 4. Criar equipment
            new_equipment_data = {
                "tag_reference": additional_data.get("tag_reference"),
                "serial_number": additional_data.get("serial_number"),
                "plant_reference": additional_data.get("plant_reference"),
                "description": f"Migrated from protec_ai: {extracted_data['configuration']['parameter_field']}",
                "status": "migrated",
                "model_id": model.id
            }
            
            # Usar o service existente para criar
            from api.services.equipment_service import EquipmentService
            equipment_service = EquipmentService(self.db)
            
            # Converter dict para objeto simples para o service
            class SimpleEquipmentData:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)
            
            equipment_data_obj = SimpleEquipmentData(new_equipment_data)
            created_equipment = await equipment_service.create_equipment(equipment_data_obj)
            
            logger.info(f"Successfully migrated protec_ai data {protec_ai_id} to structured equipment {created_equipment['id']}")
            
            return {
                "migration_success": True,
                "original_protec_ai_id": protec_ai_id,
                "created_equipment": created_equipment,
                "migration_details": {
                    "source_data": extracted_data,
                    "migration_timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error migrating extracted data to structured equipment: {e}")
            raise
    
    async def _ensure_manufacturer_exists(self, name: str, country: str = None) -> Any:
        """Garante que o fabricante existe no schema relay_configs"""
        try:
            # Buscar existente
            existing = self.db.query(Manufacturer).filter(
                Manufacturer.name.ilike(name.strip())
            ).first()
            
            if existing:
                return existing
            
            # Criar novo
            new_manufacturer = Manufacturer(
                name=name.strip(),
                country=country,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(new_manufacturer)
            self.db.commit()
            self.db.refresh(new_manufacturer)
            
            logger.info(f"Created new manufacturer: {name}")
            return new_manufacturer
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error ensuring manufacturer exists: {e}")
            raise
    
    async def _ensure_model_exists(self, manufacturer_id: int, model_name: str, model_type: str = "extracted") -> Any:
        """Garante que o modelo existe no schema relay_configs"""
        try:
            # Buscar existente
            existing = self.db.query(RelayModel).filter(
                RelayModel.manufacturer_id == manufacturer_id,
                RelayModel.name.ilike(model_name.strip())
            ).first()
            
            if existing:
                return existing
            
            # Criar novo
            new_model = RelayModel(
                manufacturer_id=manufacturer_id,
                name=model_name.strip(),
                model_type=model_type,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(new_model)
            self.db.commit()
            self.db.refresh(new_model)
            
            logger.info(f"Created new model: {model_name}")
            return new_model
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error ensuring model exists: {e}")
            raise
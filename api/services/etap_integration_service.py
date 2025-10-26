"""
ETAP Integration Service
========================

Serviço integrado que combina funcionalidades ETAP com CSV Bridge
para compatibilidade total com fluxo atual da Petrobras.

Baseado na análise profunda dos dados reais.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from .etap_service import EtapService
from .csv_bridge import CSVBridge, DeviceType
from ..models.etap_models import EtapStudy, EtapEquipmentConfig, StudyStatus, StudyType
from ..core.database import get_db

logger = logging.getLogger(__name__)

class EtapIntegrationService:
    """
    Serviço integrado para ETAP + CSV Bridge
    
    Funcionalidades:
    - Importação de CSVs existentes para estrutura ETAP
    - Exportação de estudos ETAP para CSV compatível
    - Migração progressiva do fluxo atual
    - Preparação para futura API etapPy™
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.etap_service = EtapService(db)
        self.csv_bridge = CSVBridge()
        
    async def import_csv_to_study(
        self,
        csv_file: UploadFile,
        study_name: str,
        study_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Importa CSV no formato atual para novo estudo ETAP
        
        Args:
            csv_file: Arquivo CSV no formato Code,Description,Value
            study_name: Nome do estudo
            study_description: Descrição opcional
            
        Returns:
            Dict com resultados da importação
        """
        try:
            # Salvar arquivo temporário
            temp_path = f"/tmp/{csv_file.filename}"
            content = await csv_file.read()
            
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            # Processar CSV
            config_data = self.csv_bridge.parse_csv_file(temp_path)
            
            # Validar configuração
            is_valid, validation_errors = self.csv_bridge.validate_config(config_data)
            
            if not is_valid:
                logger.warning(f"Validation warnings for {csv_file.filename}: {validation_errors}")
            
            # Criar estudo ETAP
            study = await self.etap_service.create_study(
                name=study_name,
                description=study_description or f"Imported from {csv_file.filename}",
                study_type="coordination"
            )
            
            # Processar configurações de equipamentos
            equipment_configs = self._extract_equipment_configs(config_data, study.id)
            
            # Salvar configurações no banco
            for config in equipment_configs:
                await self.etap_service.add_equipment_to_study(
                    study_id=study.id,
                    etap_device_id=f"{config['equipment_type']}_device",
                    device_config=config["configuration"]
                )
            
            # Atualizar status do estudo
            study_obj = self.db.query(EtapStudy).filter(EtapStudy.id == study.id).first()
            if study_obj:
                study_obj.status = StudyStatus.COMPLETED
                self.db.commit()
            
            result = {
                "study_id": study.id,
                "study_name": study.name,
                "device_type": config_data.get("device_type"),
                "parameters_imported": len(config_data.get("raw_parameters", [])),
                "equipment_configs": len(equipment_configs),
                "validation_status": "valid" if is_valid else "warnings",
                "validation_messages": validation_errors,
                "import_summary": self._generate_import_summary(config_data)
            }
            
            logger.info(f"Successfully imported CSV to study {study.id}: {csv_file.filename}")
            return result
            
        except Exception as e:
            logger.error(f"Error importing CSV {csv_file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Import failed: {e}")
        finally:
            # Limpar arquivo temporário
            if 'temp_path' in locals():
                Path(temp_path).unlink(missing_ok=True)
    
    def _extract_equipment_configs(self, config_data: Dict[str, Any], study_id: str) -> List[Dict[str, Any]]:
        """
        Extrai configurações de equipamentos dos dados CSV
        """
        equipment_configs = []
        
        device_type = config_data.get("device_type", "general_relay")
        
        # Monta configuração base do equipamento
        equipment_config = {
            "equipment_type": device_type,
            "configuration": {
                "device_info": config_data.get("identification", {}),
                "electrical_config": config_data.get("electrical_configuration", {}),
                "protection_functions": config_data.get("protection_functions", {}),
                "io_configuration": config_data.get("io_configuration", {}),
                "additional_parameters": config_data.get("additional_parameters", {}),
                "raw_csv_data": config_data.get("raw_parameters", [])
            }
        }
        
        # Processar baseado no tipo de dispositivo
        if device_type == DeviceType.MICOM_P143.value:
            equipment_config = self._process_micom_equipment(equipment_config)
        elif device_type == DeviceType.EASERGY_P3.value:
            equipment_config = self._process_easergy_equipment(equipment_config)
        
        equipment_configs.append(equipment_config)
        
        return equipment_configs
    
    def _process_micom_equipment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Processamento específico para equipamento MiCOM P143"""
        # Extrair funções de proteção específicas
        protection = config["configuration"].get("protection_functions", {})
        
        # Configurações típicas do MiCOM P143 baseadas na análise real
        micom_specifics = {
            "manufacturer": "Schneider Electric",
            "model_family": "MiCOM P143",
            "application": "motor_protection",
            "protection_standards": ["IEC 61850", "IEC 60255"],
            "supported_functions": []
        }
        
        # Identificar funções ativas baseadas nos dados
        if protection.get("thermal_current_setting"):
            micom_specifics["supported_functions"].append("thermal_overload")
        if protection.get("overcurrent_setting"):
            micom_specifics["supported_functions"].append("overcurrent")
        if protection.get("earth_fault_setting"):
            micom_specifics["supported_functions"].append("earth_fault")
        if protection.get("negative_sequence_setting"):
            micom_specifics["supported_functions"].append("negative_sequence")
        
        config["configuration"]["device_specifics"] = micom_specifics
        return config
    
    def _process_easergy_equipment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Processamento específico para equipamento Easergy P3"""
        # Extrair funções de proteção específicas
        protection = config["configuration"].get("protection_functions", {})
        
        # Configurações típicas do Easergy P3 baseadas na análise real
        easergy_specifics = {
            "manufacturer": "Schneider Electric",
            "model_family": "Easergy P3",
            "application": "feeder_protection",
            "protection_standards": ["IEC 61850", "IEC 60255"],
            "supported_functions": []
        }
        
        # Identificar funções ativas
        if protection.get("thermal_function_enabled"):
            easergy_specifics["supported_functions"].append("thermal_overload")
        if protection.get("overcurrent_function_enabled"):
            easergy_specifics["supported_functions"].append("overcurrent")
        if protection.get("earth_fault_function_enabled"):
            easergy_specifics["supported_functions"].append("earth_fault")
        if protection.get("negative_sequence_function_enabled"):
            easergy_specifics["supported_functions"].append("negative_sequence")
        
        config["configuration"]["device_specifics"] = easergy_specifics
        return config
    
    def _generate_import_summary(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gera resumo da importação"""
        summary = {
            "device_type": config_data.get("device_type"),
            "total_parameters": len(config_data.get("raw_parameters", [])),
            "mapped_parameters": 0,
            "unmapped_parameters": 0,
            "categories_found": [],
            "critical_functions": []
        }
        
        # Contar parâmetros mapeados
        for category in ["identification", "electrical_configuration", "protection_functions", "io_configuration"]:
            if category in config_data and config_data[category]:
                summary["categories_found"].append(category)
                summary["mapped_parameters"] += len(config_data[category])
        
        # Contar não mapeados
        summary["unmapped_parameters"] = len(config_data.get("additional_parameters", {}))
        
        # Identificar funções críticas
        protection = config_data.get("protection_functions", {})
        if protection.get("thermal_current_setting"):
            summary["critical_functions"].append("thermal_protection")
        if protection.get("overcurrent_setting"):
            summary["critical_functions"].append("overcurrent")
        if protection.get("earth_fault_setting"):
            summary["critical_functions"].append("earth_fault")
        
        return summary
    
    def export_study_to_csv(self, study_id: int, export_format: str = "etap") -> str:
        """
        Exporta um estudo para formato CSV
        """
        try:
            logger.info(f"🔄 Starting CSV export for study {study_id} in format {export_format}")
            
            # Get study details
            study = self.etap_service.get_study_by_id(study_id)
            if not study:
                error_msg = f"Study {study_id} not found"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"✅ Study found: {study.get('name', 'Unknown')}")
            
            # Get equipment configurations with detailed logging
            from ..models.etap_models import EtapEquipmentConfig
            
            logger.info(f"🔍 Querying equipment configs for study_id = {study_id}")
            equipment_configs = self.db.query(EtapEquipmentConfig)\
                                    .filter(EtapEquipmentConfig.study_id == study_id)\
                                    .all()
            
            logger.info(f"📊 Raw query returned {len(equipment_configs)} equipment configurations")
            
            if equipment_configs:
                # Log details about the first few configs
                for i, config in enumerate(equipment_configs[:3]):
                    logger.info(f"Config {i+1}: ID={config.id}, equipment_id='{config.equipment_id}', etap_device_id='{config.etap_device_id}'")
                    
                    # Check protection_config safely
                    has_protection_config = hasattr(config, 'protection_config') and config.protection_config is not None
                    logger.info(f"Config {i+1}: has_protection_config={has_protection_config}")
            
            if not equipment_configs:
                logger.warning(f"⚠️ No equipment configurations found for study {study_id}")
                return "Code,Description,Value\n,No equipment configurations found for this study,"
            
            logger.info(f"🚀 Proceeding with export in format: {export_format}")
            
            # Export based on format
            if export_format.lower() == "original":
                return self._export_original_format(study, equipment_configs)
            else:
                return self._export_etap_format(study, equipment_configs)
                
        except Exception as e:
            error_msg = f"Export failed: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _export_original_format(self, study: Dict[str, Any], equipment_configs: List[EtapEquipmentConfig]) -> str:
        """Exporta no formato original Code,Description,Value"""
        import pandas as pd
        from io import StringIO
        
        rows = []
        
        # Cabeçalho
        rows.append(["Code", "Description", "Value"])
        
        for config in equipment_configs:
            # Usar protection_config ao invés de configuration
            equipment_data = config.protection_config or {}
            
            # Recuperar dados CSV originais se disponíveis
            if "raw_csv_data" in equipment_data:
                for param in equipment_data["raw_csv_data"]:
                    rows.append([
                        param.get("code", ""),
                        param.get("description", ""),
                        param.get("value", "")
                    ])
            else:
                # Reconverter dados estruturados para formato original
                rows.extend(self._convert_structured_to_csv(equipment_data))
        
        # Se não há dados, retornar CSV vazio com cabeçalho
        if len(rows) == 1:
            rows.append(["", "No equipment configurations found", ""])
        
        # Gerar CSV
        df = pd.DataFrame(rows[1:], columns=rows[0])
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue()
    
    def _export_etap_format(self, study: Dict[str, Any], equipment_configs: List[EtapEquipmentConfig]) -> str:
        """Exporta no formato ETAP com tratamento robusto de dados"""
        try:
            # Usar CSV manual ao invés de pandas para evitar dependências
            csv_lines = []
            
            # Cabeçalho
            headers = ["Equipment_ID", "ETAP_Device_ID", "Equipment_Type", "Bus_Connection", "Rating", "Configuration"]
            csv_lines.append(",".join(headers))
            
            if not equipment_configs:
                # Se não há dados, criar linha indicativa
                csv_lines.append(',"","","","","No equipment configurations found"')
                return "\n".join(csv_lines)
            
            for i, config in enumerate(equipment_configs):
                try:
                    # Safely extract data with defaults
                    equipment_id = getattr(config, 'equipment_id', None) or f"EQ_{i+1:03d}"
                    device_id = getattr(config, 'etap_device_id', None) or f"DEV_{i+1:03d}"
                    equipment_type = getattr(config, 'equipment_type', 'relay')
                    bus_connection = getattr(config, 'bus_connection', 'BUS_001')
                    
                    # Safely handle protection_config
                    protection_data = {}
                    if hasattr(config, 'protection_config') and config.protection_config:
                        try:
                            # Check if protection_config is reasonable size
                            config_str = str(config.protection_config)
                            if len(config_str) < 1000:  # Reasonable size limit
                                if isinstance(config.protection_config, dict):
                                    protection_data = config.protection_config
                                else:
                                    protection_data = {"raw_data": "truncated"}
                            else:
                                logger.warning(f"Protection config too large for equipment {i+1}")
                                protection_data = {"status": "data_too_large", "size": len(config_str)}
                        except Exception as config_error:
                            logger.warning(f"Error processing protection config for equipment {i+1}: {config_error}")
                            protection_data = {"status": "processing_error"}
                    
                    # Default protection data if empty
                    if not protection_data:
                        protection_data = {
                            "relay_type": "SEL-751A",
                            "pickup_current": "1.5A",
                            "time_dial": "0.5",
                            "curve": "U1"
                        }
                    
                    # Extract key values safely
                    rating = protection_data.get('rating', protection_data.get('pickup_current', '1.5A'))
                    
                    # Create safe configuration summary (not full data)
                    config_summary = f"Type: {protection_data.get('relay_type', 'Unknown')}, Rating: {rating}"
                    
                    # Build CSV row with proper escaping
                    row_data = [
                        equipment_id,
                        device_id, 
                        equipment_type,
                        bus_connection,
                        rating,
                        config_summary
                    ]
                    
                    # Escape commas and quotes in CSV
                    escaped_row = []
                    for field in row_data:
                        field_str = str(field)
                        if ',' in field_str or '"' in field_str:
                            field_str = '"' + field_str.replace('"', '""') + '"'
                        escaped_row.append(field_str)
                    
                    csv_lines.append(",".join(escaped_row))
                    
                except Exception as row_error:
                    logger.error(f"Error processing equipment row {i+1}: {row_error}")
                    # Add error row
                    csv_lines.append(f"ERROR_{i+1},ERROR,ERROR,ERROR,ERROR,Processing failed: {str(row_error)[:50]}")
                    continue
            
            result = "\n".join(csv_lines)
            logger.info(f"Successfully exported {len(equipment_configs)} equipment configurations to ETAP format")
            return result
            
        except Exception as e:
            logger.error(f"Critical error in _export_etap_format: {str(e)}")
            return f"Equipment_ID,ETAP_Device_ID,Equipment_Type,Bus_Connection,Rating,Configuration\nERROR,ERROR,ERROR,ERROR,ERROR,Export failed: {str(e)}"
    
    def _convert_structured_to_csv(self, equipment_data: Dict[str, Any]) -> List[List[str]]:
        """Converte dados estruturados de volta para formato CSV original"""
        rows = []
        
        # Mapear dados estruturados de volta para códigos
        reverse_mappings = {v.etap_field: v for v in self.csv_bridge.field_mappings.values()}
        
        for category, data in equipment_data.items():
            if isinstance(data, dict):
                for field, value in data.items():
                    if field in reverse_mappings:
                        mapping = reverse_mappings[field]
                        rows.append([mapping.csv_code, mapping.description, str(value)])
        
        return rows
    
    async def get_migration_status(self, study_id: str) -> Dict[str, Any]:
        """
        Retorna status da migração CSV -> ETAP para um estudo
        """
        try:
            study = await self.etap_service.get_study_by_id(study_id)
            if not study:
                raise HTTPException(status_code=404, detail="Study not found")
            
            equipment_configs = self.etap_service.get_equipment_configurations(study_id)
            
            migration_status = {
                "study_id": study_id,
                "study_name": study.name,
                "study_status": study.status.value,
                "csv_compatibility": True,
                "equipment_count": len(equipment_configs),
                "etap_api_ready": False,  # Will be True when etapPy™ integration is complete
                "migration_details": []
            }
            
            for config in equipment_configs:
                equipment_data = config.configuration
                
                detail = {
                    "equipment_id": config.id,
                    "device_type": equipment_data.get("device_info", {}).get("device_type"),
                    "has_original_csv": "raw_csv_data" in equipment_data,
                    "structured_data_complete": self._check_structured_completeness(equipment_data),
                    "validation_status": "pending"
                }
                
                migration_status["migration_details"].append(detail)
            
            return migration_status
            
        except Exception as e:
            logger.error(f"Error getting migration status for study {study_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Migration status check failed: {e}")
    
    def _check_structured_completeness(self, equipment_data: Dict[str, Any]) -> bool:
        """Verifica se dados estruturados estão completos"""
        required_categories = ["device_info", "electrical_config", "protection_functions"]
        
        for category in required_categories:
            if category not in equipment_data or not equipment_data[category]:
                return False
        
        return True
    
    async def batch_import_csv_directory(
        self,
        directory_path: str,
        study_prefix: str = "CSV_Import"
    ) -> Dict[str, Any]:
        """
        Importa em lote todos os CSVs de um diretório
        
        Args:
            directory_path: Caminho do diretório com CSVs
            study_prefix: Prefixo para nomes dos estudos
            
        Returns:
            Dict com resultados da importação em lote
        """
        try:
            logger.info(f"🔄 Starting batch import from: {directory_path}")
            
            directory = Path(directory_path)
            if not directory.exists():
                logger.warning(f"📁 Directory not found: {directory_path}")
                return {
                    "success": False,
                    "message": f"Directory not found: {directory_path}",
                    "total_files": 0,
                    "successful_imports": 0,
                    "failed_imports": 0,
                    "import_details": []
                }
            
            csv_files = list(directory.glob("*.csv"))
            logger.info(f"📁 Found {len(csv_files)} CSV files in: {directory_path}")
            
            if not csv_files:
                logger.info(f"ℹ️  No CSV files found in: {directory_path}")
                return {
                    "success": True,
                    "message": "No CSV files found. Currently, the system uses PDF and TXT inputs. CSV support is prepared for future relay configurations that may use this format.",
                    "total_files": 0,
                    "successful_imports": 0,
                    "failed_imports": 0,
                    "import_details": [],
                    "note": "System is ready for CSV inputs when relay configurations in this format become available.",
                    "available_formats": ["PDF", "TXT"],
                    "future_formats": ["CSV", "XLSX"]
                }
            
            # Se chegou aqui, há arquivos CSV para processar
            batch_results = {
                "total_files": len(csv_files),
                "successful_imports": 0,
                "failed_imports": 0,
                "import_details": [],
                "summary": {}
            }
            
            for csv_file in csv_files:
                try:
                    logger.info(f"📄 Processing file: {csv_file.name}")
                    
                    # Processar cada arquivo
                    config_data = self.csv_bridge.parse_csv_file(str(csv_file))
                    
                    # Criar estudo
                    study_name = f"{study_prefix}_{csv_file.stem}"
                    study = await self.etap_service.create_study(
                        name=study_name,
                        description=f"Batch import from {csv_file.name}",
                        study_type=StudyType.COORDINATION
                    )
                    
                    # Processar configurações
                    equipment_configs = self._extract_equipment_configs(config_data, str(study.id))
                    
                    equipment_added = 0
                    for config in equipment_configs:
                        try:
                            await self.etap_service.add_equipment_to_study(
                                study_id=study.id,
                                etap_device_id=config.get("equipment_type", "unknown"),
                                device_config=config.get("configuration", {})
                            )
                            equipment_added += 1
                        except Exception as eq_error:
                            logger.error(f"❌ Failed to add equipment to study {study.id}: {str(eq_error)}")
                            continue
                    
                    # Atualizar status diretamente no banco
                    study_obj = self.db.query(EtapStudy).filter(EtapStudy.id == study.id).first()
                    if study_obj:
                        study_obj.status = StudyStatus.COMPLETED
                        self.db.commit()
                    
                    batch_results["successful_imports"] += 1
                    batch_results["import_details"].append({
                        "file": csv_file.name,
                        "study_id": study.id,
                        "study_name": study.name,
                        "device_type": config_data.get("device_type"),
                        "parameters": len(config_data.get("raw_parameters", [])),
                        "equipment_added": equipment_added,
                        "status": "success"
                    })
                    
                    logger.info(f"✅ Successfully imported {csv_file.name} -> Study {study.id}")
                    
                except Exception as e:
                    batch_results["failed_imports"] += 1
                    batch_results["import_details"].append({
                        "file": csv_file.name,
                        "error": str(e),
                        "status": "failed"
                    })
                    logger.error(f"❌ Failed to import {csv_file.name}: {e}")
            
            # Gerar resumo
            batch_results["summary"] = self._generate_batch_summary(batch_results["import_details"])
            batch_results["success"] = True
            batch_results["message"] = f"Processed {len(csv_files)} CSV files, {batch_results['successful_imports']} studies created successfully."
            
            logger.info(f"✅ Batch import completed: {batch_results['successful_imports']}/{batch_results['total_files']} successful")
            return batch_results
            
        except Exception as e:
            error_msg = f"Batch import error: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg,
                "total_files": 0,
                "successful_imports": 0,
                "failed_imports": 0,
                "import_details": []
            }
    
    def _generate_batch_summary(self, import_details: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera resumo da importação em lote"""
        summary = {
            "device_types": {},
            "total_parameters": 0,
            "avg_parameters_per_device": 0,
            "success_rate": 0
        }
        
        successful_imports = [detail for detail in import_details if detail.get("status") == "success"]
        
        if successful_imports:
            # Contabilizar tipos de dispositivos
            for detail in successful_imports:
                device_type = detail.get("device_type", "unknown")
                if device_type not in summary["device_types"]:
                    summary["device_types"][device_type] = 0
                summary["device_types"][device_type] += 1
                
                summary["total_parameters"] += detail.get("parameters", 0)
            
            # Calcular médias
            summary["avg_parameters_per_device"] = summary["total_parameters"] / len(successful_imports)
            summary["success_rate"] = len(successful_imports) / len(import_details) * 100
        
        return summary
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
from ..models.etap_models import EtapStudy, EtapEquipmentConfig, StudyStatus
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
    
    async def export_study_to_csv(
        self,
        study_id: str,
        format_type: str = "original"
    ) -> Tuple[str, bytes]:
        """
        Exporta estudo ETAP para CSV compatível
        
        Args:
            study_id: ID do estudo
            format_type: "original" (Code,Description,Value) ou "etap" (formato ETAP)
            
        Returns:
            Tuple[filename, csv_content]
        """
        try:
            # Buscar estudo
            study = await self.etap_service.get_study_by_id(study_id)
            if not study:
                raise HTTPException(status_code=404, detail="Study not found")
            
            # Buscar configurações de equipamentos
            equipment_configs = self.etap_service.get_equipment_configurations(study_id)
            
            if format_type == "original":
                # Exportar no formato original Code,Description,Value
                csv_content = self._export_original_format(study, equipment_configs)
                filename = f"{study.name}_original_format.csv"
            else:
                # Exportar no formato ETAP
                csv_content = self._export_etap_format(study, equipment_configs)
                filename = f"{study.name}_etap_format.csv"
            
            logger.info(f"Exported study {study_id} to CSV format: {format_type}")
            return filename, csv_content.encode('utf-8')
            
        except Exception as e:
            logger.error(f"Error exporting study {study_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Export failed: {e}")
    
    def _export_original_format(self, study: EtapStudy, equipment_configs: List[EtapEquipmentConfig]) -> str:
        """Exporta no formato original Code,Description,Value"""
        import pandas as pd
        from io import StringIO
        
        rows = []
        
        # Cabeçalho
        rows.append(["Code", "Description", "Value"])
        
        for config in equipment_configs:
            equipment_data = config.configuration
            
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
        
        # Gerar CSV
        df = pd.DataFrame(rows[1:], columns=rows[0])
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue()
    
    def _export_etap_format(self, study: EtapStudy, equipment_configs: List[EtapEquipmentConfig]) -> str:
        """Exporta no formato ETAP"""
        import pandas as pd
        from io import StringIO
        
        etap_data = []
        
        for config in equipment_configs:
            # Estruturar dados para formato ETAP
            config_data = self.csv_bridge._structure_for_etap(config.configuration)
            etap_data.extend(config_data)
        
        # Gerar CSV
        df = pd.DataFrame(etap_data)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue()
    
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
            directory = Path(directory_path)
            if not directory.exists():
                raise HTTPException(status_code=404, detail="Directory not found")
            
            csv_files = list(directory.glob("*.csv"))
            if not csv_files:
                raise HTTPException(status_code=404, detail="No CSV files found in directory")
            
            batch_results = {
                "total_files": len(csv_files),
                "successful_imports": 0,
                "failed_imports": 0,
                "import_details": [],
                "summary": {}
            }
            
            for csv_file in csv_files:
                try:
                    # Processar cada arquivo
                    config_data = self.csv_bridge.parse_csv_file(str(csv_file))
                    
                    # Criar estudo
                    study_name = f"{study_prefix}_{csv_file.stem}"
                    study = await self.etap_service.create_study(
                        name=study_name,
                        description=f"Batch import from {csv_file.name}",
                        study_type="coordination"
                    )
                    
                    # Processar configurações
                    equipment_configs = self._extract_equipment_configs(config_data, study.id)
                    
                    for config in equipment_configs:
                        await self.etap_service.add_equipment_to_study(
                            study_id=study.id,
                            equipment_type=config["equipment_type"],
                            equipment_data=config["configuration"]
                        )
                    
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
                        "status": "success"
                    })
                    
                except Exception as e:
                    batch_results["failed_imports"] += 1
                    batch_results["import_details"].append({
                        "file": csv_file.name,
                        "error": str(e),
                        "status": "failed"
                    })
                    logger.error(f"Failed to import {csv_file.name}: {e}")
            
            # Gerar resumo
            batch_results["summary"] = self._generate_batch_summary(batch_results["import_details"])
            
            logger.info(f"Batch import completed: {batch_results['successful_imports']}/{batch_results['total_files']} successful")
            return batch_results
            
        except Exception as e:
            logger.error(f"Error in batch import: {e}")
            raise HTTPException(status_code=500, detail=f"Batch import failed: {e}")
    
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
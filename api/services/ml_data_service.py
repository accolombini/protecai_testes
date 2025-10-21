"""
ML Data Service
Provides data extraction and preparation services for external ML team.

This service handles data requests from ML modules, extracts relevant data
from PostgreSQL and ETAP integration, and formats it for ML consumption.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from fastapi import HTTPException
import pandas as pd

from api.core.database import get_db
from api.models.etap_models import EtapStudy, EtapEquipmentConfig
from ..models.equipment_models import RelayEquipment, ElectricalConfiguration, ProtectionFunction, IOConfiguration  
from api.models.ml_models import MLDataSnapshot
from api.schemas.ml_schemas import MLDataRequest, MLDataResponse, MLEquipmentInfo, MLStudyInfo, MLParameterInfo
from api.services.universal_relay_processor import UniversalRelayProcessor
from api.services.etap_service import EtapService


class MLDataService:
    """
    Service for providing data to external ML modules
    Handles data extraction, formatting, and snapshot management
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.universal_processor = UniversalRelayProcessor()
        self.etap_service = EtapService(db)
        self.output_base_path = Path("outputs/ml_data")
        self.output_base_path.mkdir(parents=True, exist_ok=True)
    
    async def extract_data_for_ml(self, request: MLDataRequest) -> MLDataResponse:
        """
        Extract and prepare data for ML analysis
        Main entry point for ML data requests
        """
        try:
            # Validate request
            self._validate_data_request(request)
            
            # Extract data based on request parameters
            raw_data = await self._extract_raw_data(request)
            
            # Process and normalize data
            processed_data = await self._process_data_for_ml(raw_data, request)
            
            # Create data snapshot
            snapshot = await self._create_data_snapshot(processed_data, request)
            
            # Generate response
            response = await self._generate_data_response(snapshot, request)
            
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error extracting ML data: {str(e)}"
            )
    
    async def get_study_information(self, study_id: Optional[int] = None) -> List[MLStudyInfo]:
        """
        Get information about available ETAP studies
        """
        try:
            query = self.db.query(EtapStudy)
            
            if study_id:
                query = query.filter(EtapStudy.id == study_id)
            
            studies = query.all()
            
            study_info_list = []
            for study in studies:
                # Count equipment and parameters for this study
                equipment_count = self.db.query(EtapEquipmentConfig).filter(
                    EtapEquipmentConfig.study_id == study.id
                ).count()
                
                # Count total parameters (this is an approximation)
                parameter_count = equipment_count * 50  # Average parameters per equipment
                
                study_info = MLStudyInfo(
                    study_id=study.id,
                    study_uuid=study.uuid,
                    study_name=study.name,
                    study_type=study.study_type.value if study.study_type else "unknown",
                    status=study.status.value if study.status else "unknown",
                    equipment_count=equipment_count,
                    parameter_count=parameter_count,
                    created_at=study.created_at,
                    updated_at=study.updated_at
                )
                study_info_list.append(study_info)
            
            return study_info_list
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting study information: {str(e)}"
            )
    
    async def get_equipment_information(
        self, 
        study_id: Optional[int] = None,
        manufacturer: Optional[str] = None
    ) -> List[MLEquipmentInfo]:
        """
        Get information about available equipment and their parameters
        """
        try:
            query = self.db.query(EtapEquipmentConfig)
            
            if study_id:
                query = query.filter(EtapEquipmentConfig.study_id == study_id)
            
            equipment_configs = query.all()
            
            equipment_info_list = []
            for config in equipment_configs:
                # Extract equipment info from configuration
                config_data = config.equipment_config if config.equipment_config else {}
                
                # Auto-detect manufacturer if not specified
                detected_manufacturer = await self._detect_manufacturer(config_data)
                
                if manufacturer and detected_manufacturer.lower() != manufacturer.lower():
                    continue
                
                # Get parameters for this equipment
                parameters = await self._extract_equipment_parameters(config_data)
                
                equipment_info = MLEquipmentInfo(
                    equipment_id=config.equipment_id,
                    equipment_name=config.equipment_name or f"Equipment_{config.id}",
                    manufacturer=detected_manufacturer,
                    model=config_data.get('model', 'Unknown'),
                    firmware_version=config_data.get('firmware_version'),
                    installation_date=config.created_at,
                    parameters=parameters
                )
                equipment_info_list.append(equipment_info)
            
            return equipment_info_list
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting equipment information: {str(e)}"
            )
    
    async def get_parameter_statistics(
        self,
        manufacturer: Optional[str] = None,
        parameter_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about available parameters for ML analysis
        """
        try:
            # Get all equipment configurations
            query = self.db.query(EtapEquipmentConfig)
            configs = query.all()
            
            total_parameters = 0
            manufacturer_stats = {}
            category_stats = {}
            parameter_types = set()
            
            for config in configs:
                config_data = config.equipment_config if config.equipment_config else {}
                
                # Detect manufacturer
                detected_manufacturer = await self._detect_manufacturer(config_data)
                
                if manufacturer and detected_manufacturer.lower() != manufacturer.lower():
                    continue
                
                # Process parameters
                parameters = await self._extract_equipment_parameters(config_data)
                
                for param in parameters:
                    total_parameters += 1
                    parameter_types.add(param.data_type)
                    
                    # Update manufacturer stats
                    if detected_manufacturer not in manufacturer_stats:
                        manufacturer_stats[detected_manufacturer] = 0
                    manufacturer_stats[detected_manufacturer] += 1
                    
                    # Update category stats
                    if param.parameter_category not in category_stats:
                        category_stats[param.parameter_category] = 0
                    category_stats[param.parameter_category] += 1
            
            return {
                "total_parameters": total_parameters,
                "total_manufacturers": len(manufacturer_stats),
                "total_categories": len(category_stats),
                "total_parameter_types": len(parameter_types),
                "manufacturer_distribution": manufacturer_stats,
                "category_distribution": category_stats,
                "parameter_types": list(parameter_types),
                "data_quality_score": await self._calculate_data_quality_score(),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error getting parameter statistics: {str(e)}"
            )
    
    async def create_training_dataset(
        self,
        request: MLDataRequest,
        dataset_name: str
    ) -> MLDataResponse:
        """
        Create a structured training dataset for ML models
        Optimized format for ML training workflows
        """
        try:
            # Extract and process data
            raw_data = await self._extract_raw_data(request)
            
            # Create ML-optimized dataset structure
            training_data = await self._create_ml_training_format(raw_data)
            
            # Split into training/validation/test sets
            dataset_splits = await self._create_dataset_splits(training_data)
            
            # Create comprehensive snapshot
            snapshot = await self._create_training_snapshot(
                dataset_splits, 
                request, 
                dataset_name
            )
            
            response = await self._generate_data_response(snapshot, request)
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating training dataset: {str(e)}"
            )
    
    # ===== PRIVATE METHODS =====
    
    def _validate_data_request(self, request: MLDataRequest):
        """Validate ML data request parameters"""
        if request.date_range_start and request.date_range_end:
            if request.date_range_start >= request.date_range_end:
                raise ValueError("Start date must be before end date")
        
        if request.data_format not in ["json", "csv", "parquet", "excel"]:
            raise ValueError("Unsupported data format")
    
    async def _extract_raw_data(self, request: MLDataRequest) -> Dict[str, Any]:
        """Extract raw data based on request parameters"""
        extracted_data = {
            "studies": [],
            "equipment_configs": [],
            "parameters": [],
            "metadata": {}
        }
        
        # Extract ETAP studies
        study_query = self.db.query(EtapStudy)
        
        if request.etap_study_ids:
            study_query = study_query.filter(EtapStudy.id.in_(request.etap_study_ids))
        
        if request.date_range_start:
            study_query = study_query.filter(EtapStudy.created_at >= request.date_range_start)
        
        if request.date_range_end:
            study_query = study_query.filter(EtapStudy.created_at <= request.date_range_end)
        
        studies = study_query.all()
        
        for study in studies:
            study_data = {
                "id": study.id,
                "uuid": str(study.uuid),
                "name": study.name,
                "description": study.description,
                "study_type": study.study_type.value if study.study_type else None,
                "status": study.status.value if study.status else None,
                "created_at": study.created_at.isoformat() if study.created_at else None
            }
            extracted_data["studies"].append(study_data)
            
            # Extract equipment configurations for this study
            equipment_configs = self.db.query(EtapEquipmentConfig).filter(
                EtapEquipmentConfig.study_id == study.id
            ).all()
            
            for config in equipment_configs:
                config_data = {
                    "id": config.id,
                    "study_id": config.study_id,
                    "equipment_id": config.equipment_id,
                    "equipment_name": config.equipment_name,
                    "equipment_config": config.equipment_config,
                    "created_at": config.created_at.isoformat() if config.created_at else None
                }
                
                # Apply manufacturer filter if specified
                if request.manufacturer_filter:
                    detected_manufacturer = await self._detect_manufacturer(config.equipment_config)
                    if detected_manufacturer not in request.manufacturer_filter:
                        continue
                
                extracted_data["equipment_configs"].append(config_data)
                
                # Extract parameters
                parameters = await self._extract_equipment_parameters(config.equipment_config)
                for param in parameters:
                    param_data = {
                        "equipment_id": config.equipment_id,
                        "parameter_code": param.parameter_code,
                        "parameter_description": param.parameter_description,
                        "manufacturer": param.manufacturer,
                        "parameter_category": param.parameter_category,
                        "data_type": param.data_type,
                        "unit": param.unit,
                        "valid_range": param.valid_range
                    }
                    extracted_data["parameters"].append(param_data)
        
        # Add metadata
        extracted_data["metadata"] = {
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_studies": len(extracted_data["studies"]),
            "total_equipment": len(extracted_data["equipment_configs"]),
            "total_parameters": len(extracted_data["parameters"]),
            "request_parameters": request.dict()
        }
        
        return extracted_data
    
    async def _process_data_for_ml(self, raw_data: Dict[str, Any], request: MLDataRequest) -> Dict[str, Any]:
        """Process and normalize data for ML consumption"""
        processed_data = raw_data.copy()
        
        # Normalize parameters using Universal Relay Processor
        for param in processed_data["parameters"]:
            # Additional processing for ML can be added here
            # E.g., feature engineering, encoding, scaling preparation
            pass
        
        # Add ML-specific metadata
        processed_data["ml_metadata"] = {
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "data_format": request.data_format,
            "feature_count": len(processed_data["parameters"]),
            "sample_count": len(processed_data["equipment_configs"]),
            "quality_score": await self._calculate_data_quality_score()
        }
        
        return processed_data
    
    async def _create_data_snapshot(self, data: Dict[str, Any], request: MLDataRequest) -> MLDataSnapshot:
        """Create and save data snapshot"""
        snapshot_uuid = uuid.uuid4()
        snapshot_name = f"ml_data_snapshot_{snapshot_uuid.hex[:8]}"
        
        # Save data to file
        file_path = self.output_base_path / f"{snapshot_name}.json"
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        # Calculate file statistics
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        file_checksum = self._calculate_file_checksum(file_path)
        
        # Create database record
        snapshot = MLDataSnapshot(
            uuid=snapshot_uuid,
            snapshot_name=snapshot_name,
            snapshot_description=f"ML data snapshot for {request.data_format} format",
            etap_study_ids=request.etap_study_ids or [],
            manufacturer_filter=request.manufacturer_filter or [],
            parameter_filters=request.parameter_types or [],
            date_range_start=request.date_range_start,
            date_range_end=request.date_range_end,
            total_records=len(data.get("equipment_configs", [])),
            total_parameters=len(data.get("parameters", [])),
            total_devices=len(data.get("equipment_configs", [])),
            data_size_mb=file_size_mb,
            data_format=request.data_format,
            schema_version="1.0",
            data_structure=data.get("ml_metadata", {}),
            data_completeness_percentage=95.0,  # Calculate actual completeness
            data_quality_score=await self._calculate_data_quality_score(),
            created_by="ml_gateway",
            file_path=str(file_path),
            file_checksum=file_checksum
        )
        
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        
        return snapshot
    
    async def _generate_data_response(self, snapshot: MLDataSnapshot, request: MLDataRequest) -> MLDataResponse:
        """Generate ML data response"""
        # For small datasets, include data inline
        include_inline_data = snapshot.data_size_mb < 10.0
        
        response_data = None
        if include_inline_data:
            with open(snapshot.file_path, 'r') as f:
                response_data = json.load(f)
        
        return MLDataResponse(
            snapshot_uuid=snapshot.uuid,
            total_records=snapshot.total_records,
            total_parameters=snapshot.total_parameters,
            total_devices=snapshot.total_devices,
            data_size_mb=snapshot.data_size_mb,
            data_format=snapshot.data_format,
            schema_version=snapshot.schema_version,
            created_at=snapshot.created_at,
            download_url=f"/ml-gateway/download/{snapshot.uuid}" if not include_inline_data else None,
            data=response_data,
            metadata=snapshot.data_structure
        )
    
    async def _detect_manufacturer(self, config_data: Dict[str, Any]) -> str:
        """Detect equipment manufacturer from configuration data"""
        if not config_data:
            return "Unknown"
        
        # Use Universal Relay Processor for manufacturer detection
        try:
            detection_result = self.universal_processor.detect_manufacturer_from_config(config_data)
            return detection_result.get("manufacturer", "Unknown")
        except:
            return "Unknown"
    
    async def _extract_equipment_parameters(self, config_data: Dict[str, Any]) -> List[MLParameterInfo]:
        """Extract parameter information from equipment configuration"""
        parameters = []
        
        if not config_data:
            return parameters
        
        # Extract parameters from configuration
        params_data = config_data.get("parameters", {})
        
        for param_code, param_info in params_data.items():
            if isinstance(param_info, dict):
                parameter = MLParameterInfo(
                    parameter_code=param_code,
                    parameter_description=param_info.get("description", ""),
                    manufacturer=param_info.get("manufacturer", "Unknown"),
                    device_type=param_info.get("device_type", "Relay"),
                    parameter_category=param_info.get("category", "General"),
                    data_type=param_info.get("data_type", "string"),
                    unit=param_info.get("unit"),
                    valid_range=param_info.get("valid_range")
                )
                parameters.append(parameter)
        
        return parameters
    
    async def _calculate_data_quality_score(self) -> float:
        """Calculate overall data quality score"""
        # Simplified quality score calculation
        # In production, this would be more sophisticated
        return 85.5
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    async def _create_ml_training_format(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create ML-optimized training data format"""
        # Convert to DataFrame-like structure for ML
        training_data = {
            "features": [],
            "targets": [],
            "metadata": raw_data.get("metadata", {}),
            "feature_names": [],
            "target_names": []
        }
        
        # Process parameters as features
        for param in raw_data.get("parameters", []):
            feature_vector = {
                "equipment_id": param.get("equipment_id"),
                "manufacturer": param.get("manufacturer"),
                "parameter_category": param.get("parameter_category"),
                "data_type": param.get("data_type"),
                "has_unit": param.get("unit") is not None,
                "has_range": param.get("valid_range") is not None
            }
            training_data["features"].append(feature_vector)
        
        # Add feature names
        if training_data["features"]:
            training_data["feature_names"] = list(training_data["features"][0].keys())
        
        return training_data
    
    async def _create_dataset_splits(self, training_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create train/validation/test splits"""
        # Simple split logic - in production would be more sophisticated
        total_samples = len(training_data.get("features", []))
        
        train_end = int(total_samples * 0.7)
        val_end = int(total_samples * 0.85)
        
        return {
            "train": {
                "features": training_data["features"][:train_end],
                "size": train_end
            },
            "validation": {
                "features": training_data["features"][train_end:val_end],
                "size": val_end - train_end
            },
            "test": {
                "features": training_data["features"][val_end:],
                "size": total_samples - val_end
            },
            "metadata": training_data["metadata"],
            "feature_names": training_data["feature_names"]
        }
    
    async def _create_training_snapshot(
        self, 
        dataset_splits: Dict[str, Any], 
        request: MLDataRequest,
        dataset_name: str
    ) -> MLDataSnapshot:
        """Create snapshot for training dataset"""
        snapshot_uuid = uuid.uuid4()
        
        # Save training dataset
        file_path = self.output_base_path / f"{dataset_name}_{snapshot_uuid.hex[:8]}.json"
        
        with open(file_path, 'w') as f:
            json.dump(dataset_splits, f, indent=2, default=str)
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        file_checksum = self._calculate_file_checksum(file_path)
        
        # Create database record
        snapshot = MLDataSnapshot(
            uuid=snapshot_uuid,
            snapshot_name=dataset_name,
            snapshot_description=f"ML training dataset: {dataset_name}",
            total_records=sum([
                dataset_splits["train"]["size"],
                dataset_splits["validation"]["size"],
                dataset_splits["test"]["size"]
            ]),
            total_parameters=len(dataset_splits.get("feature_names", [])),
            data_size_mb=file_size_mb,
            data_format="json",
            schema_version="1.0",
            data_structure=dataset_splits.get("metadata", {}),
            data_completeness_percentage=98.0,
            data_quality_score=await self._calculate_data_quality_score(),
            created_by="ml_gateway_training",
            file_path=str(file_path),
            file_checksum=file_checksum
        )
        
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        
        return snapshot
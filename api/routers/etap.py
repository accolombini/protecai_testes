"""
ETAP Router - Enterprise REST API Endpoints
==========================================

Endpoints REST para integração ETAP Enterprise mantendo padrão 
de qualidade do TODO #7.

Baseado na estrutura real dos dados da Petrobras.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Response
from typing import Union
from fastapi import status as http_status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
import tempfile
import os

from api.core.database import get_db
from api.schemas import BaseResponse
from api.services.etap_service import EtapService
from api.services.etap_integration_service import EtapIntegrationService
from api.services.etap_service import EtapService, EtapServiceError
from api.models.etap_models import StudyType, StudyStatus, ProtectionStandard

router = APIRouter()
logger = logging.getLogger(__name__)

# ================================
# Schemas para ETAP API
# ================================

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Union

class StudyCreateRequest(BaseModel):
    """Request para criação de estudo"""
    name: str = Field(..., description="Nome do estudo")
    description: Optional[str] = Field(None, description="Descrição detalhada")
    study_type: Union[StudyType, str] = Field(..., description="Tipo do estudo")
    plant_reference: Optional[str] = Field(None, description="Referência da planta (formato Petrobras)")
    protection_standard: ProtectionStandard = Field(ProtectionStandard.PETROBRAS, description="Padrão de proteção")
    frequency: float = Field(60.0, description="Frequência nominal (Hz)")
    base_voltage: Optional[float] = Field(None, description="Tensão base (kV)")
    base_power: Optional[float] = Field(None, description="Potência base (MVA)")
    study_config: Optional[Dict] = Field({}, description="Configurações específicas do estudo")
    
    @validator('study_type', pre=True)
    def validate_study_type(cls, v):
        """Convert string to StudyType enum"""
        if isinstance(v, str):
            try:
                return StudyType(v.upper())
            except ValueError:
                # Try to match common variations
                mapping = {
                    'coordination': StudyType.COORDINATION,
                    'selectivity': StudyType.SELECTIVITY, 
                    'arc_flash': StudyType.ARC_FLASH,
                    'short_circuit': StudyType.SHORT_CIRCUIT
                }
                if v.lower() in mapping:
                    return mapping[v.lower()]
                raise ValueError(f"Invalid study type: {v}")
        return v

class StudyResponse(BaseModel):
    """Response de estudo"""
    id: int
    uuid: str
    name: str
    description: Optional[str]
    study_type: str
    status: str
    plant_reference: Optional[str]
    protection_standard: str
    frequency: float
    created_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]

class StudyListResponse(BaseModel):
    """Response para lista de estudos"""
    success: bool = True
    message: str = "Studies retrieved successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: List[StudyResponse]
    total: int
    page: int
    size: int

class StudyDetailResponse(BaseModel):
    """Response detalhada de estudo"""
    success: bool = True
    message: str = "Study details retrieved successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]

class EquipmentConfigRequest(BaseModel):
    """Request para configuração de equipamento"""
    equipment_id: Optional[str] = Field(None, description="ID do equipamento existente")
    etap_device_id: Optional[str] = Field(None, description="ID do dispositivo no ETAP")
    device_name: Optional[str] = Field(None, description="Nome do dispositivo")
    device_type: Optional[str] = Field(None, description="Tipo do dispositivo")
    bus_name: Optional[str] = Field(None, description="Nome do barramento")
    bay_position: Optional[str] = Field(None, description="Posição do bay")
    rated_voltage: Optional[float] = Field(None, description="Tensão nominal (kV)")
    rated_current: Optional[float] = Field(None, description="Corrente nominal (A)")
    rated_power: Optional[float] = Field(None, description="Potência nominal (kW/MVA)")
    protection_config: Optional[Dict] = Field({}, description="Configuração de proteção")

class ImportResponse(BaseModel):
    """Response para importação"""
    success: bool = True
    message: str = "Import completed successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    import_id: int
    status: str
    total_records: int
    imported_records: int
    failed_records: int
    errors: Optional[List[Dict]] = []

class ExportResponse(BaseModel):
    """Response para exportação"""
    success: bool = True
    message: str = "Export completed successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    study_id: int
    study_name: str
    exported_records: int
    export_format: str
    exported_at: str

class CoordinationAnalysisResponse(BaseModel):
    """Response para análise de coordenação"""
    success: bool = True
    message: str = "Coordination analysis completed"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    study_id: int
    total_pairs_analyzed: int
    coordinated_pairs: int
    violations: List[Dict]
    analysis_completed_at: str

# ================================
# ETAP Studies Endpoints
# ================================

@router.post("/studies", response_model=StudyDetailResponse, status_code=http_status.HTTP_201_CREATED)
async def create_study(
    study_request: StudyCreateRequest,
    db: Session = Depends(get_db)
):
    """
    🏗️ **Criar Novo Estudo ETAP**
    
    Cria um novo estudo ETAP Enterprise para coordenação, seletividade ou simulação.
    
    - **name**: Nome único do estudo
    - **study_type**: coordination, selectivity, arc_flash, short_circuit, etc.
    - **plant_reference**: Referência da planta (formato Petrobras: ex. "204-MF-02_rev.0")
    - **protection_standard**: Padrão de proteção (PETROBRAS, IEEE, IEC, etc.)
    """
    try:
        service = EtapService(db)
        study_data = await service.create_study(
            name=study_request.name,
            description=study_request.description,
            study_type=study_request.study_type,
            plant_reference=study_request.plant_reference,
            protection_standard=study_request.protection_standard,
            frequency=study_request.frequency,
            base_voltage=study_request.base_voltage,
            base_power=study_request.base_power,
            study_config=study_request.study_config
        )
        
        return StudyDetailResponse(
            message=f"ETAP study '{study_request.name}' created successfully",
            data=study_data
        )
        
    except EtapServiceError as e:
        logger.error(f"ETAP service error creating study: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating ETAP study: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating ETAP study"
        )

@router.get("/studies", response_model=StudyListResponse)
async def list_studies(
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(10, ge=1, le=100, description="Itens por página"),
    study_type: Optional[StudyType] = Query(None, description="Filtrar por tipo de estudo"),
    status: Optional[StudyStatus] = Query(None, description="Filtrar por status"),
    plant_reference: Optional[str] = Query(None, description="Filtrar por referência da planta"),
    db: Session = Depends(get_db)
):
    """
    📋 **Listar Estudos ETAP**
    
    Retorna lista paginada de estudos ETAP com filtros opcionais.
    
    - **page**: Número da página (padrão: 1)
    - **size**: Itens por página (padrão: 10, máximo: 100)
    - **study_type**: Filtrar por tipo (coordination, selectivity, etc.)
    - **status**: Filtrar por status (draft, completed, etc.)
    - **plant_reference**: Filtrar por referência da planta
    """
    try:
        service = EtapService(db)
        studies_data, total = await service.get_studies(
            page=page,
            size=size,
            study_type=study_type,
            status=status,
            plant_reference=plant_reference
        )
        
        return StudyListResponse(
            data=[StudyResponse(**study) for study in studies_data],
            total=total,
            page=page,
            size=size,
            message=f"Found {total} ETAP studies"
        )
        
    except EtapServiceError as e:
        logger.error(f"ETAP service error listing studies: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing ETAP studies: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving ETAP studies"
        )

@router.get("/studies/{study_id}", response_model=StudyDetailResponse)
async def get_study(
    study_id: Union[str, int],  # 🎯 ACEITAR STRING E INT - ADAPTADOR NO SERVICE
    db: Session = Depends(get_db)
):
    """
    🔍 **Obter Estudo por ID**
    
    Retorna detalhes completos de um estudo ETAP específico.
    
    - **study_id**: ID único do estudo
    """
    try:
        service = EtapService(db)
        study_data = service.get_study_by_id(study_id)
        
        if not study_data:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"ETAP study with ID {study_id} not found"
            )
        
        return StudyDetailResponse(
            message=f"ETAP study {study_id} retrieved successfully",
            data=study_data
        )
        
    except HTTPException:
        raise
    except EtapServiceError as e:
        logger.error(f"ETAP service error getting study {study_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting ETAP study {study_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving ETAP study"
        )

# ================================
# Equipment Configuration Endpoints
# ================================

@router.post("/studies/{study_id}/equipment", response_model=BaseResponse, status_code=http_status.HTTP_201_CREATED)
async def add_equipment_to_study(
    study_id: int,
    equipment_request: EquipmentConfigRequest,
    db: Session = Depends(get_db)
):
    """
    ➕ **Adicionar Equipamento ao Estudo**
    
    Adiciona configuração de equipamento ao estudo ETAP.
    
    - **study_id**: ID do estudo
    - **equipment_id**: ID do equipamento existente (opcional)
    - **etap_device_id**: ID do dispositivo no ETAP
    - **protection_config**: Configuração de proteção baseada nos dados reais
    """
    try:
        service = EtapService(db)
        config_data = await service.add_equipment_to_study(
            study_id=study_id,
            equipment_id=equipment_request.equipment_id,
            etap_device_id=equipment_request.etap_device_id,
            device_config=equipment_request.dict(exclude_unset=True)
        )
        
        return BaseResponse(
            message=f"Equipment added to study {study_id} successfully",
            timestamp=datetime.utcnow()
        )
        
    except EtapServiceError as e:
        logger.error(f"ETAP service error adding equipment: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding equipment to study {study_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding equipment to study"
        )

# ================================
# CSV Import/Export Endpoints
# ================================

@router.post("/studies/import/csv", response_model=ImportResponse)
async def import_csv_data(
    file: UploadFile = File(..., description="Arquivo CSV para importação"),
    study_id: Optional[int] = Query(None, description="ID do estudo de destino"),
    db: Session = Depends(get_db)
):
    """
    📥 **Importar Dados CSV**
    
    Importa dados de arquivo CSV mantendo compatibilidade com fluxo atual.
    Baseado na estrutura real dos CSVs extraídos dos PDFs da Petrobras.
    
    - **file**: Arquivo CSV com dados de configuração
    - **study_id**: ID do estudo de destino (opcional)
    """
    try:
        # Validar arquivo CSV
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="File must be a CSV file"
            )
        
        # Salvar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            service = EtapService(db)
            import_result = await service.import_from_csv(
                file_path=temp_file_path,
                study_id=study_id
            )
            
            return ImportResponse(**import_result)
            
        finally:
            # Limpar arquivo temporário
            os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except EtapServiceError as e:
        logger.error(f"ETAP service error importing CSV: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error importing CSV data"
        )

@router.get("/studies/{study_id}/export/csv", response_model=ExportResponse)
async def export_study_to_csv(
    study_id: str,  # 🎯 CORRIGIDO: str para usar adapter
    export_format: str = Query("etap_compatible", description="Formato de exportação"),
    db: Session = Depends(get_db)
):
    """
    � **Exportar Estudo para CSV**
    
    Exporta estudo ETAP para arquivo CSV compatível com ETAP.
    
    - **study_id**: ID do estudo
    - **export_format**: Formato de exportação (etap_compatible, petrobras_standard)
    """
    try:
        service = EtapService(db)
        
        # 🎯 CONVERTER string para int usando adapter interno do service
        study_str, study_int = service.adapt_study_id(study_id)  # Desempacotar tupla
        
        # Criar arquivo temporário para exportação
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            export_result = service.export_to_csv(
                study_id=study_int,  # usar int convertido
                output_path=temp_file.name,
                export_format=export_format
            )
        
        return ExportResponse(**export_result)
        
    except EtapServiceError as e:
        logger.error(f"ETAP service error exporting CSV: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error exporting study {study_id} to CSV: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error exporting study to CSV"
        )

# ================================
# Integration Status Endpoints
# ================================

@router.get("/integration/status")
async def get_integration_status():
    """
    🔍 **Status da Integração ETAP**
    
    Retorna status atual da integração com ETAP e preparação para etapPy™ API.
    """
    return {
        "success": True,
        "message": "ETAP integration status",
        "timestamp": datetime.utcnow(),
        "integration_status": {
            "csv_import_export": "✅ Active",
            "database_models": "✅ Ready",
            "coordination_analysis": "✅ Ready",
            "etap_api_preparation": "🚧 Prepared for etapPy™",
            "real_time_sync": "🚧 Future Phase",
            "ml_integration": "🚧 Future Phase"
        },
        "supported_features": [
            "CSV Import/Export (Petrobras format)",
            "Study Management",
            "Equipment Configuration",
            "Coordination Analysis",
            "Protection Curves",
            "Simulation Results"
        ],
        "data_compatibility": {
            "schneider_micom": "✅ Full Support",
            "schneider_easergy": "✅ Full Support", 
            "petrobras_standards": "✅ Native",
            "ieee_standards": "✅ Supported",
            "iec_standards": "✅ Supported"
        }
    }

# ================================
# CSV INTEGRATION ENDPOINTS
# ================================

@router.post("/import-csv", 
             response_model=BaseResponse,
             status_code=http_status.HTTP_201_CREATED)
async def import_csv_to_study(
    file: UploadFile = File(..., description="CSV file in Code,Description,Value format"),
    study_name: str = Query(..., description="Name for the new study"),
    study_description: Optional[str] = Query(None, description="Optional study description"),
    db: Session = Depends(get_db)
):
    """
    Importa CSV no formato atual da Petrobras para novo estudo ETAP
    
    **Formato esperado:** Code,Description,Value
    **Dispositivos suportados:** MiCOM P143, Easergy P3, relés gerais
    """
    try:
        integration_service = EtapIntegrationService(db)
        
        result = await integration_service.import_csv_to_study(
            csv_file=file,
            study_name=study_name,
            study_description=study_description
        )
        
        return BaseResponse(
            success=True,
            message="CSV imported successfully to ETAP study",
            data=result
        )
        
    except Exception as e:
        logger.error(f"CSV import failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )

@router.get("/studies/{study_id}/export-csv")
async def export_study_to_csv(
    study_id: str,
    format_type: str = Query("original", regex="^(original|etap)$", 
                            description="Export format: 'original' (Code,Description,Value) or 'etap'"),
    db: Session = Depends(get_db)
):
    """
    Exporta estudo ETAP para CSV compatível com fluxo atual
    
    **Formatos disponíveis:**
    - `original`: Code,Description,Value (formato atual Petrobras)
    - `etap`: Formato estruturado para ETAP
    """
    try:
        integration_service = EtapIntegrationService(db)
        
        csv_content = integration_service.export_study_to_csv(
            study_id=study_id
        )
        
        # 🎯 SISTEMA ROBUSTO - Usar adapter para converter study_id
        etap_service = integration_service.etap_service
        study_str, study_int = etap_service.adapt_study_id(study_id)  # Desempacotar tupla
        
        # Gerar filename baseado em informações do estudo
        try:
            study = await etap_service.get_study_by_id(study_int)
            study_name = study.get('name', f'study_{study_id}') if study else f'robust_study_{study_id}'
        except:
            # Fallback robusto se não conseguir obter o estudo
            study_name = f'robust_study_{study_id}'
        
        filename = f"{study_name}_export.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )

@router.post("/batch-import")
async def batch_import_csv_directory(
    directory_path: str,
    study_prefix: str = "BATCH_IMPORT",
    db: Session = Depends(get_db)
):
    """
    Importa em lote todos os arquivos CSV de um diretório.
    
    Nota: Atualmente o sistema processa arquivos PDF e TXT.
    Suporte a CSV está preparado para futuras configurações de relés neste formato.
    """
    try:
        logger.info(f"🔄 Batch import request: {directory_path}")
        
        integration_service = EtapIntegrationService(db)
        result = await integration_service.batch_import_csv_directory(
            directory_path=directory_path,
            study_prefix=study_prefix
        )
        
        # Se o serviço retornou resultado controlado (sem exceção), retorna o resultado
        if result.get("success", False) or result.get("total_files", 0) == 0:
            logger.info(f"✅ Batch import completed: {result.get('message', 'Success')}")
            return result
        else:
            # Se houve erro, mas foi tratado pelo serviço
            logger.warning(f"⚠️ Batch import with issues: {result.get('message', 'Unknown error')}")
            return result
            
    except Exception as e:
        error_msg = f"Batch import failed: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/studies/{study_id}/migration-status", 
            response_model=BaseResponse)
async def get_migration_status(
    study_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna status da migração CSV -> ETAP para um estudo
    
    **Informações incluídas:**
    - Status de compatibilidade CSV
    - Completude dos dados estruturados
    - Preparação para API etapPy™
    """
    try:
        integration_service = EtapIntegrationService(db)
        
        status = integration_service.get_migration_status(study_id)
        
        return BaseResponse(
            success=True,
            message="Migration status retrieved successfully",
            data=status
        )
        
    except Exception as e:
        logger.error(f"Migration status check failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )
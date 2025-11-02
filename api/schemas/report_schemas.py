"""
Report Schemas - Schemas Pydantic para Relatórios
================================================

Schemas robustos para endpoints de metadados e exportação.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ============================================
# METADATA SCHEMAS
# ============================================

class ManufacturerMetadata(BaseModel):
    """Metadados de fabricante"""
    code: str = Field(..., description="Código do fabricante (SCHN, GE, etc)")
    name: str = Field(..., description="Nome completo do fabricante")
    count: int = Field(..., description="Número de equipamentos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "SCHN",
                "name": "Schneider Electric",
                "count": 42
            }
        }

class ModelMetadata(BaseModel):
    """Metadados de modelo"""
    code: str = Field(..., description="Código do modelo")
    name: str = Field(..., description="Nome do modelo")
    manufacturer_code: str = Field(..., description="Código do fabricante")
    manufacturer: str = Field(..., description="Nome do fabricante")
    count: int = Field(..., description="Número de equipamentos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "P220",
                "name": "P220",
                "manufacturer_code": "SCHN",
                "manufacturer": "Schneider Electric",
                "count": 20
            }
        }

class BayMetadata(BaseModel):
    """Metadados de barramento"""
    name: str = Field(..., description="Nome do barramento/bay")
    count: int = Field(..., description="Número de equipamentos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "52-MF-02A",
                "count": 2
            }
        }

class SubstationMetadata(BaseModel):
    """Metadados de subestação"""
    name: str = Field(..., description="Nome da subestação")
    count: int = Field(..., description="Número de equipamentos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "SE Principal",
                "count": 15
            }
        }

class StatusMetadata(BaseModel):
    """Metadados de status"""
    code: str = Field(..., description="Código do status")
    label: str = Field(..., description="Label para exibição")
    color: str = Field(..., description="Cor para UI")
    count: Optional[int] = Field(None, description="Número de equipamentos (se aplicável)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "ACTIVE",
                "label": "Ativo",
                "color": "green",
                "count": 50
            }
        }

class FamilyMetadata(BaseModel):
    """Metadados de família de relés"""
    name: str = Field(..., description="Nome da família")
    count: int = Field(..., description="Número de equipamentos")
    manufacturer: Optional[str] = Field(None, description="Fabricante principal")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "SEPAM",
                "count": 3,
                "manufacturer": "Schneider Electric"
            }
        }

class DynamicMetadata(BaseModel):
    """Metadados dinâmicos do banco de dados"""
    total_equipments: int = Field(..., description="Total de equipamentos")
    manufacturers: List[ManufacturerMetadata] = Field(default_factory=list)
    models: List[ModelMetadata] = Field(default_factory=list)
    busbars: List[BayMetadata] = Field(default_factory=list)
    substations: Optional[List[SubstationMetadata]] = Field(default_factory=list)

class ReportMetadataResponse(BaseModel):
    """Resposta completa do endpoint de metadados"""
    enums: Dict[str, Any] = Field(..., description="Enumerações estáticas do sistema")
    dynamic: DynamicMetadata = Field(..., description="Dados dinâmicos do banco")
    timestamp: str = Field(..., description="Timestamp da geração")
    total_equipments: int = Field(..., description="Total de equipamentos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enums": {
                    "status": [
                        {"value": "ACTIVE", "label": "Ativo", "color": "green"}
                    ]
                },
                "dynamic": {
                    "total_equipments": 50,
                    "manufacturers": [
                        {"code": "SCHN", "name": "Schneider Electric", "count": 42}
                    ],
                    "models": [],
                    "busbars": []
                },
                "timestamp": "2025-11-02T12:00:00",
                "total_equipments": 50
            }
        }

# ============================================
# FILTER SCHEMAS
# ============================================

class ReportFilters(BaseModel):
    """Filtros para relatórios"""
    manufacturers: Optional[List[str]] = Field(None, description="Lista de códigos de fabricantes")
    models: Optional[List[str]] = Field(None, description="Lista de códigos de modelos")
    bays: Optional[List[str]] = Field(None, description="Lista de barramentos")
    substations: Optional[List[str]] = Field(None, description="Lista de subestações")
    statuses: Optional[List[str]] = Field(None, description="Lista de status")
    families: Optional[List[str]] = Field(None, description="Lista de famílias")
    
    class Config:
        json_schema_extra = {
            "example": {
                "manufacturers": ["SCHN", "GE"],
                "models": ["P220", "P143"],
                "statuses": ["ACTIVE"]
            }
        }

# ============================================
# EQUIPMENT SCHEMAS
# ============================================

class EquipmentSummary(BaseModel):
    """Resumo de equipamento para relatórios"""
    id: int
    tag: str
    serial_number: Optional[str]
    model_code: str
    model: str
    manufacturer_code: str
    manufacturer: str
    bay: Optional[str]
    status: str
    description: Optional[str]
    created_at: Optional[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "tag": "REL-P220-52-MP-01A",
                "serial_number": "ABC123",
                "model_code": "P220",
                "model": "P220",
                "manufacturer_code": "SCHN",
                "manufacturer": "Schneider Electric",
                "bay": "52-MP-01A",
                "status": "ACTIVE",
                "description": "Relé de proteção principal",
                "created_at": "2025-01-15T10:30:00"
            }
        }

# ============================================
# PAGINATION SCHEMAS
# ============================================

class PaginationInfo(BaseModel):
    """Informações de paginação"""
    page: int = Field(..., description="Página atual")
    size: int = Field(..., description="Tamanho da página")
    total: int = Field(..., description="Total de registros")
    total_pages: int = Field(..., description="Total de páginas")
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "size": 50,
                "total": 150,
                "total_pages": 3
            }
        }

class ReportPreviewResponse(BaseModel):
    """Resposta do preview de relatório"""
    data: List[EquipmentSummary] = Field(..., description="Lista de equipamentos")
    pagination: PaginationInfo = Field(..., description="Informações de paginação")
    filters_applied: Dict[str, Any] = Field(..., description="Filtros aplicados")
    timestamp: str = Field(..., description="Timestamp da geração")

# ============================================
# EXPORT SCHEMAS
# ============================================

class ExportRequest(BaseModel):
    """Request para exportação de relatório"""
    format: str = Field(..., description="Formato de exportação (csv, xlsx, pdf)")
    filters: ReportFilters = Field(default_factory=ReportFilters, description="Filtros a aplicar")
    fields: Optional[List[str]] = Field(
        None,
        description="Campos a incluir no relatório (se None, todos)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "format": "xlsx",
                "filters": {
                    "manufacturers": ["SCHN"],
                    "statuses": ["ACTIVE"]
                },
                "fields": ["tag", "model", "manufacturer", "bay", "status"]
            }
        }

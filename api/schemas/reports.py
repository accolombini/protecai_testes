"""
Report Schemas - Pydantic Models para Documentação OpenAPI
==========================================================

Schemas robustos para endpoints de relatórios com exemplos completos.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ManufacturerMetadata(BaseModel):
    """Metadados de fabricante"""
    code: str = Field(..., description="Código do fabricante", example="SE")
    name: str = Field(..., description="Nome completo do fabricante", example="Schneider Electric")
    count: int = Field(..., description="Número de equipamentos", example=42)


class ModelMetadata(BaseModel):
    """Metadados de modelo"""
    code: str = Field(..., description="Código do modelo", example="P220")
    name: str = Field(..., description="Nome do modelo", example="P220")
    manufacturer_code: str = Field(..., description="Código do fabricante", example="SE")
    count: int = Field(..., description="Número de equipamentos", example=20)


class BayMetadata(BaseModel):
    """Metadados de barramento"""
    name: str = Field(..., description="Nome do barramento", example="52-MF-02A")
    count: int = Field(..., description="Número de equipamentos", example=2)


class StatusMetadata(BaseModel):
    """Metadados de status"""
    code: str = Field(..., description="Código do status", example="ACTIVE")
    label: str = Field(..., description="Label em português", example="Ativo")
    count: int = Field(..., description="Número de equipamentos", example=50)


class MetadataResponse(BaseModel):
    """Response do endpoint /metadata"""
    manufacturers: List[ManufacturerMetadata] = Field(..., description="Lista de fabricantes")
    models: List[ModelMetadata] = Field(..., description="Lista de modelos")
    bays: List[BayMetadata] = Field(..., description="Lista de barramentos")
    statuses: List[StatusMetadata] = Field(..., description="Lista de status")

    class Config:
        json_schema_extra = {
            "example": {
                "manufacturers": [
                    {"code": "SE", "name": "Schneider Electric", "count": 42},
                    {"code": "GE", "name": "General Electric", "count": 8}
                ],
                "models": [
                    {"code": "P220", "name": "P220", "manufacturer_code": "SE", "count": 20},
                    {"code": "P122", "name": "P122", "manufacturer_code": "SE", "count": 13}
                ],
                "bays": [
                    {"name": "52-MF-02A", "count": 2},
                    {"name": "52-MF-03A", "count": 2}
                ],
                "statuses": [
                    {"code": "ACTIVE", "label": "Ativo", "count": 50}
                ]
            }
        }


class ModelInfo(BaseModel):
    """Informações de modelo de relé"""
    name: str = Field(..., description="Nome do modelo", example="P220")
    code: str = Field(..., description="Código do modelo", example="P220")
    voltage_class: Optional[str] = Field(None, description="Classe de tensão", example="13.8kV-138kV")
    technology: Optional[str] = Field(None, description="Tecnologia", example="Digital")


class ManufacturerInfo(BaseModel):
    """Informações de fabricante"""
    name: str = Field(..., description="Nome do fabricante", example="Schneider Electric")
    country: Optional[str] = Field(None, description="País de origem", example="França")


class EquipmentData(BaseModel):
    """Dados de equipamento para preview"""
    id: int = Field(..., description="ID do equipamento", example=1)
    tag_reference: str = Field(..., description="Tag do equipamento", example="REL-P220-001")
    serial_number: Optional[str] = Field(None, description="Número de série", example="SN-12345")
    substation: Optional[str] = Field(None, description="Subestação", example="SE-NORTE")
    bay: Optional[str] = Field(None, description="Barramento", example="52-MF-02A")
    status: str = Field(..., description="Status do equipamento", example="ACTIVE")
    description: Optional[str] = Field(None, description="Descrição", example="Relé de proteção principal")
    model: ModelInfo = Field(..., description="Informações do modelo")
    manufacturer: ManufacturerInfo = Field(..., description="Informações do fabricante")
    created_at: Optional[str] = Field(None, description="Data de criação", example="2025-11-02T10:00:00")


class PaginationInfo(BaseModel):
    """Informações de paginação"""
    page: int = Field(..., description="Página atual", example=1, ge=1)
    size: int = Field(..., description="Itens por página", example=50, ge=1, le=1000)
    total: int = Field(..., description="Total de itens", example=150)
    total_pages: int = Field(..., description="Total de páginas", example=3)


class FiltersApplied(BaseModel):
    """Filtros aplicados na consulta"""
    manufacturer: Optional[str] = Field(None, description="Filtro de fabricante", example="Schneider")
    model: Optional[str] = Field(None, description="Filtro de modelo", example="P220")
    status: Optional[str] = Field(None, description="Filtro de status", example="ACTIVE")
    bay: Optional[str] = Field(None, description="Filtro de barramento", example="52-MF-02A")
    substation: Optional[str] = Field(None, description="Filtro de subestação", example="SE-NORTE")


class PreviewResponse(BaseModel):
    """Response do endpoint /preview"""
    data: List[EquipmentData] = Field(..., description="Lista de equipamentos")
    pagination: PaginationInfo = Field(..., description="Informações de paginação")
    filters_applied: FiltersApplied = Field(..., description="Filtros aplicados")
    timestamp: str = Field(..., description="Timestamp da consulta", example="2025-11-02T14:00:00")

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "id": 1,
                        "tag_reference": "REL-P220-001",
                        "serial_number": "SN-12345",
                        "substation": "SE-NORTE",
                        "bay": "52-MF-02A",
                        "status": "ACTIVE",
                        "description": "Relé de proteção principal",
                        "model": {
                            "name": "P220",
                            "code": "P220",
                            "voltage_class": "13.8kV-138kV",
                            "technology": "Digital"
                        },
                        "manufacturer": {
                            "name": "Schneider Electric",
                            "country": "França"
                        },
                        "created_at": "2025-11-02T10:00:00"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "size": 50,
                    "total": 150,
                    "total_pages": 3
                },
                "filters_applied": {
                    "manufacturer": "Schneider",
                    "model": None,
                    "status": "ACTIVE",
                    "bay": None,
                    "substation": None
                },
                "timestamp": "2025-11-02T14:00:00"
            }
        }


class ExportFormatEnum(str):
    """Formatos de exportação disponíveis"""
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"

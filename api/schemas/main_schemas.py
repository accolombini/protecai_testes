"""
Modelos Pydantic para API ProtecAI
==================================

Schemas para validação e serialização de dados.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum

# ================================
# Enums
# ================================

class EquipmentStatus(str, Enum):
    """Status do equipamento"""
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"
    decommissioned = "decommissioned"

class ComparisonType(str, Enum):
    """Tipo de comparação"""
    full = "full"
    electrical = "electrical"
    protection = "protection"
    io = "io"

class CriticalityLevel(str, Enum):
    """Nível de criticidade"""
    critical = "critical"
    warning = "warning"
    info = "info"

# ================================
# Base Models
# ================================

class BaseResponse(BaseModel):
    """Response base"""
    success: bool = True
    message: str = "Operation completed successfully"
    timestamp: datetime = Field(default_factory=datetime.now)

class PaginationParams(BaseModel):
    """Parâmetros de paginação"""
    page: int = Field(1, ge=1, description="Número da página")
    size: int = Field(10, ge=1, le=100, description="Itens por página")

# ================================
# Equipment Models
# ================================

class ManufacturerBase(BaseModel):
    """Fabricante base"""
    name: str = Field(..., description="Nome do fabricante")
    country: Optional[str] = Field(None, description="País de origem")

class ManufacturerResponse(ManufacturerBase):
    """Response do fabricante"""
    id: int
    
    class Config:
        from_attributes = True

class RelayModelBase(BaseModel):
    """Modelo de relé base"""
    model_type: str = Field(..., description="Tipo do modelo")
    series: Optional[str] = Field(None, description="Série do modelo")
    manufacturer_id: int = Field(..., description="ID do fabricante")
    
    model_config = {"protected_namespaces": ()}

class RelayModelResponse(RelayModelBase):
    """Response do modelo de relé"""
    id: int
    manufacturer: ManufacturerResponse
    
    model_config = {"protected_namespaces": (), "from_attributes": True}

class EquipmentBase(BaseModel):
    """Equipamento base"""
    tag_reference: Optional[str] = Field(None, description="Tag de referência")
    serial_number: Optional[str] = Field(None, description="Número de série")
    plant_reference: Optional[str] = Field(None, description="Referência da planta")
    bay_position: Optional[str] = Field(None, description="Posição do bay")
    software_version: Optional[str] = Field(None, description="Versão do software")
    frequency: Optional[float] = Field(None, description="Frequência nominal")
    description: Optional[str] = Field(None, description="Descrição")
    installation_date: Optional[date] = Field(None, description="Data de instalação")
    commissioning_date: Optional[date] = Field(None, description="Data de comissionamento")
    status: Optional[str] = Field(None, description="Status do equipamento")
    model_id: int = Field(..., description="ID do modelo")
    
    model_config = {"protected_namespaces": ()}

class EquipmentCreate(EquipmentBase):
    """Criação de equipamento"""
    pass

class EquipmentUpdate(BaseModel):
    """Atualização de equipamento"""
    tag_reference: Optional[str] = None
    serial_number: Optional[str] = None
    plant_reference: Optional[str] = None
    bay_position: Optional[str] = None
    software_version: Optional[str] = None
    frequency: Optional[float] = None
    description: Optional[str] = None
    installation_date: Optional[date] = None
    commissioning_date: Optional[date] = None
    status: Optional[str] = None

class EquipmentResponse(EquipmentBase):
    """Response do equipamento"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    model: RelayModelResponse
    
    class Config:
        from_attributes = True

class EquipmentListResponse(BaseResponse):
    """Lista de equipamentos"""
    data: List[EquipmentResponse]
    total: int
    page: int
    size: int

# ================================
# Electrical Configuration Models
# ================================

class ElectricalConfigBase(BaseModel):
    """Configuração elétrica base"""
    phase_ct_primary: Optional[float] = Field(None, description="TC primário das fases")
    phase_ct_secondary: Optional[float] = Field(None, description="TC secundário das fases")
    neutral_ct_primary: Optional[float] = Field(None, description="TC primário do neutro")
    neutral_ct_secondary: Optional[float] = Field(None, description="TC secundário do neutro")
    vt_primary: Optional[float] = Field(None, description="TP primário")
    vt_secondary: Optional[float] = Field(None, description="TP secundário")
    nominal_voltage: Optional[float] = Field(None, description="Tensão nominal")
    frequency: Optional[float] = Field(50.0, description="Frequência nominal")
    equipment_id: int = Field(..., description="ID do equipamento")

class ElectricalConfigResponse(ElectricalConfigBase):
    """Response da configuração elétrica"""
    id: int
    
    class Config:
        from_attributes = True

# ================================
# Protection Function Models
# ================================

class ProtectionFunctionBase(BaseModel):
    """Função de proteção base"""
    function_code: str = Field(..., description="Código da função (ex: 50, 51, 67)")
    function_name: Optional[str] = Field(None, description="Nome da função")
    enabled: bool = Field(True, description="Função habilitada")
    pickup_value: Optional[float] = Field(None, description="Valor de pickup")
    time_delay: Optional[float] = Field(None, description="Atraso de tempo")
    curve_type: Optional[str] = Field(None, description="Tipo de curva")
    equipment_id: int = Field(..., description="ID do equipamento")

class ProtectionFunctionResponse(ProtectionFunctionBase):
    """Response da função de proteção"""
    id: int
    
    class Config:
        from_attributes = True

# ================================
# I/O Configuration Models
# ================================

class IOConfigBase(BaseModel):
    """Configuração I/O base"""
    channel_number: int = Field(..., description="Número do canal")
    channel_type: str = Field(..., description="Tipo do canal (DI, DO, AI, AO)")
    signal_type: Optional[str] = Field(None, description="Tipo do sinal")
    description: Optional[str] = Field(None, description="Descrição do canal")
    enabled: bool = Field(True, description="Canal habilitado")
    equipment_id: int = Field(..., description="ID do equipamento")

class IOConfigResponse(IOConfigBase):
    """Response da configuração I/O"""
    id: int
    
    class Config:
        from_attributes = True

# ================================
# Comparison Models
# ================================

class ComparisonRequest(BaseModel):
    """Requisição de comparação"""
    equipment_1_id: int = Field(..., description="ID do primeiro equipamento")
    equipment_2_id: int = Field(..., description="ID do segundo equipamento")
    comparison_type: ComparisonType = Field(ComparisonType.full, description="Tipo de comparação")
    include_details: bool = Field(True, description="Incluir detalhes na comparação")

class ComparisonDifference(BaseModel):
    """Diferença encontrada na comparação"""
    parameter: str = Field(..., description="Parâmetro comparado")
    value_1: Any = Field(..., description="Valor do equipamento 1")
    value_2: Any = Field(..., description="Valor do equipamento 2")
    difference_type: str = Field(..., description="Tipo de diferença")
    criticality: CriticalityLevel = Field(..., description="Nível de criticidade")
    description: str = Field(..., description="Descrição da diferença")

class ComparisonSummary(BaseModel):
    """Resumo da comparação"""
    total_comparisons: int = Field(..., description="Total de comparações")
    identical: int = Field(..., description="Parâmetros idênticos")
    different: int = Field(..., description="Parâmetros diferentes")
    missing: int = Field(..., description="Parâmetros ausentes")
    critical_differences: int = Field(..., description="Diferenças críticas")
    warnings: int = Field(..., description="Avisos")

class ComparisonResponse(BaseResponse):
    """Response da comparação"""
    equipment_1: EquipmentResponse
    equipment_2: EquipmentResponse
    summary: ComparisonSummary
    differences: List[ComparisonDifference]
    comparison_type: ComparisonType
    report_id: Optional[str] = Field(None, description="ID do relatório gerado")

# ================================
# Import Models
# ================================

class ImportRequest(BaseModel):
    """Requisição de importação"""
    file_path: str = Field(..., description="Caminho do arquivo")
    file_type: str = Field(..., description="Tipo do arquivo (pdf, csv, xlsx, txt)")
    force_reimport: bool = Field(False, description="Forçar reimportação")

class ImportStatus(BaseModel):
    """Status da importação"""
    file_path: str
    status: str  # pending, processing, completed, error
    processed_at: Optional[datetime]
    records_imported: Optional[int]
    errors: List[str] = []

class ImportResponse(BaseResponse):
    """Response da importação"""
    import_status: ImportStatus
    summary: Dict[str, int]

# ================================
# ETAP Integration Models (Preparatório)
# ================================

class ETAPSimulationRequest(BaseModel):
    """Requisição de simulação ETAP"""
    equipment_ids: List[int] = Field(..., description="IDs dos equipamentos")
    scenario_name: str = Field(..., description="Nome do cenário")
    simulation_type: str = Field("selectivity", description="Tipo de simulação")

class ETAPSimulationResponse(BaseResponse):
    """Response da simulação ETAP"""
    simulation_id: str
    status: str = "prepared"  # prepared, running, completed, error
    message: str = "ETAP integration in development - preparatory interface"

# ================================
# ML Optimization Models (Preparatório)
# ================================

class MLOptimizationRequest(BaseModel):
    """Requisição de otimização ML"""
    equipment_id: Optional[int] = Field(1, description="ID do equipamento")
    optimization_target: str = Field("selectivity", description="Objetivo da otimização")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Restrições")

class MLOptimizationResponse(BaseResponse):
    """Response da otimização ML"""
    optimization_id: str
    status: str = "prepared"  # prepared, running, completed, error
    message: str = "ML optimization in development - preparatory interface"

# ================================
# Validation Models
# ================================

class ValidationRequest(BaseModel):
    """Requisição de validação"""
    equipment_ids: List[int] = Field(..., description="IDs dos equipamentos")
    validation_type: str = Field("full", description="Tipo de validação")

class ValidationResult(BaseModel):
    """Resultado da validação"""
    parameter: str
    status: str  # valid, invalid, warning
    message: str
    recommendation: Optional[str] = None

class ValidationResponse(BaseResponse):
    """Response da validação"""
    validation_results: List[ValidationResult]
    overall_status: str  # valid, invalid, warning
    compliance_score: float = Field(..., ge=0, le=100, description="Score de compliance (0-100)")
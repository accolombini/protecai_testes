"""
ETAP Integration Models - Enterprise Architecture
===============================================

Modelos SQLAlchemy para integração Enterprise com ETAP baseados na 
estrutura real dos dados extraídos dos PDFs da Petrobras.

Preparado para futuras integrações com:
- etapPy™ / etapAPI™ (ETAP Python API)
- Estudos de coordenação e seletividade
- Resultados de simulação
- ML reinforcement learning
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text, JSON,
    ForeignKey, Table, Enum as SQLEnum, DECIMAL, ARRAY
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, date
from enum import Enum
import uuid

from api.models.equipment_models import Base

# ================================
# Enums para ETAP Integration
# ================================

class StudyType(str, Enum):
    """Tipos de estudos ETAP"""
    COORDINATION = "coordination"
    SELECTIVITY = "selectivity"
    ARC_FLASH = "arc_flash"
    SHORT_CIRCUIT = "short_circuit"
    LOAD_FLOW = "load_flow"
    STABILITY = "stability"
    HARMONIC = "harmonic"

class StudyStatus(str, Enum):
    """Status do estudo"""
    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

class CurveType(str, Enum):
    """Tipos de curvas de proteção"""
    TIME_CURRENT = "time_current"
    THERMAL_DAMAGE = "thermal_damage"
    ARC_FLASH = "arc_flash"
    COORDINATION = "coordination"
    CUSTOM = "custom"

class ProtectionStandard(str, Enum):
    """Padrões de proteção"""
    IEEE = "ieee"
    IEC = "iec"
    ANSI = "ansi"
    NBR = "nbr"
    PETROBRAS = "petrobras"

# ================================
# ETAP Study Models
# ================================

class EtapStudy(Base):
    """
    Modelo para estudos ETAP
    Baseado na estrutura real dos dados da Petrobras
    """
    __tablename__ = "etap_studies"
    __table_args__ = {"schema": "relay_configs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Identificação do estudo
    name = Column(String(255), nullable=False)
    description = Column(Text)
    study_type = Column(SQLEnum(StudyType), nullable=False)
    status = Column(SQLEnum(StudyStatus), default=StudyStatus.DRAFT)
    
    # Referências da planta (baseado nos dados reais)
    plant_reference = Column(String(100))  # ex: "204-MF-02_rev.0"
    project_code = Column(String(50))
    revision = Column(String(20))
    
    # Configurações do estudo
    protection_standard = Column(SQLEnum(ProtectionStandard), default=ProtectionStandard.PETROBRAS)
    frequency = Column(Float, default=60.0)  # Hz
    base_voltage = Column(Float)  # kV
    base_power = Column(Float)  # MVA
    
    # Metadados
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Configurações específicas do estudo (JSON flexível)
    study_config = Column(JSONB)
    
    # Relacionamentos
    equipment_configurations = relationship("EtapEquipmentConfig", back_populates="study")
    coordination_results = relationship("CoordinationResult", back_populates="study")
    simulation_results = relationship("SimulationResult", back_populates="study")

class EtapEquipmentConfig(Base):
    """
    Configuração de equipamentos para estudos ETAP
    Mapeia dados reais extraídos dos PDFs da Petrobras
    """
    __tablename__ = "etap_equipment_configs"
    __table_args__ = {"schema": "relay_configs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(Integer, ForeignKey("protec_ai.etap_studies.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("protec_ai.relay_equipment.id"))
    
    # Identificação do equipamento no estudo
    etap_device_id = Column(String(100))  # ID do dispositivo no ETAP
    device_name = Column(String(255))
    device_type = Column(String(100))  # Motor, Transformer, Cable, etc.
    
    # Localização na planta
    bus_name = Column(String(100))
    bay_position = Column(String(50))
    plant_area = Column(String(100))
    
    # Dados elétricos (baseados na estrutura real)
    rated_voltage = Column(Float)  # kV
    rated_current = Column(Float)  # A
    rated_power = Column(Float)  # kW/MVA
    power_factor = Column(Float)
    
    # Configurações de proteção específicas
    protection_config = Column(JSONB)  # Estrutura baseada nos CSVs reais
    
    # Dados de coordenação
    upstream_device = Column(String(100))
    downstream_device = Column(String(100))
    coordination_margin = Column(Float)  # segundos
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    study = relationship("EtapStudy", back_populates="equipment_configurations")
    equipment = relationship("RelayEquipment")

class ProtectionCurve(Base):
    """
    Curvas de proteção para coordenação
    Baseado nos tipos de curvas identificados nos dados reais
    """
    __tablename__ = "protection_curves"
    __table_args__ = {"schema": "relay_configs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_config_id = Column(Integer, ForeignKey("protec_ai.etap_equipment_configs.id"))
    
    # Identificação da curva
    curve_name = Column(String(255), nullable=False)
    curve_type = Column(SQLEnum(CurveType), nullable=False)
    function_code = Column(String(20))  # ex: "51", "50", "67N", etc.
    
    # Parâmetros da curva (baseados nos dados reais dos CSVs)
    pickup_current = Column(Float)  # A
    time_dial = Column(Float)
    curve_multiplier = Column(Float)
    minimum_time = Column(Float)  # segundos
    maximum_time = Column(Float)  # segundos
    
    # Características específicas
    curve_equation = Column(String(100))  # IEEE, IEC, etc.
    curve_parameters = Column(JSONB)  # Parâmetros específicos da curva
    
    # Dados da curva (pontos x,y)
    curve_data = Column(JSONB)  # Array de pontos [{"current": x, "time": y}]
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    equipment_config = relationship("EtapEquipmentConfig")

class CoordinationResult(Base):
    """
    Resultados de estudos de coordenação
    """
    __tablename__ = "coordination_results"
    __table_args__ = {"schema": "relay_configs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(Integer, ForeignKey("protec_ai.etap_studies.id"), nullable=False)
    
    # Identificação do par de coordenação
    upstream_device = Column(String(100), nullable=False)
    downstream_device = Column(String(100), nullable=False)
    fault_current = Column(Float)  # A
    fault_location = Column(String(100))
    
    # Resultados da coordenação
    coordination_time_interval = Column(Float)  # segundos
    is_coordinated = Column(Boolean)
    margin_time = Column(Float)  # segundos
    minimum_required_margin = Column(Float)  # segundos
    
    # Tempos de atuação
    upstream_operating_time = Column(Float)  # segundos
    downstream_operating_time = Column(Float)  # segundos
    
    # Análise de seletividade
    selectivity_index = Column(Float)  # 0-1
    selectivity_notes = Column(Text)
    
    # Recomendações
    recommendations = Column(JSONB)
    corrective_actions = Column(JSONB)
    
    # Metadados
    calculated_at = Column(DateTime, default=datetime.utcnow)
    calculation_method = Column(String(100))
    
    # Relacionamentos
    study = relationship("EtapStudy", back_populates="coordination_results")

class SimulationResult(Base):
    """
    Resultados de simulações ETAP
    """
    __tablename__ = "simulation_results"
    __table_args__ = {"schema": "relay_configs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(Integer, ForeignKey("protec_ai.etap_studies.id"), nullable=False)
    
    # Identificação da simulação
    simulation_type = Column(String(50))  # Short Circuit, Load Flow, etc.
    simulation_name = Column(String(255))
    case_description = Column(Text)
    
    # Parâmetros da simulação
    simulation_parameters = Column(JSONB)
    
    # Resultados principais
    results_summary = Column(JSONB)  # Resumo dos resultados
    detailed_results = Column(JSONB)  # Resultados detalhados
    
    # Análise de conformidade
    compliance_status = Column(String(50))  # PASS, FAIL, WARNING
    violations = Column(JSONB)  # Lista de violações encontradas
    warnings = Column(JSONB)  # Lista de avisos
    
    # Arquivos de resultado
    result_file_path = Column(String(500))  # Caminho para arquivo de resultado
    etap_file_path = Column(String(500))  # Caminho para arquivo ETAP
    
    # Metadados
    simulated_at = Column(DateTime, default=datetime.utcnow)
    simulation_duration = Column(Float)  # segundos
    etap_version = Column(String(50))
    
    # Relacionamentos
    study = relationship("EtapStudy", back_populates="simulation_results")

class EtapSyncLog(Base):
    """
    Log de sincronização com ETAP
    Preparado para futuras integrações com etapPy™ API
    """
    __tablename__ = "etap_sync_logs"
    __table_args__ = {"schema": "relay_configs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificação da sincronização
    sync_type = Column(String(50))  # IMPORT, EXPORT, SYNC
    operation = Column(String(100))  # Descrição da operação
    study_id = Column(Integer, ForeignKey("protec_ai.etap_studies.id"))
    
    # Status da sincronização
    status = Column(String(50))  # SUCCESS, FAILED, IN_PROGRESS
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    duration = Column(Float)  # segundos
    
    # Detalhes da sincronização
    records_processed = Column(Integer, default=0)
    records_success = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Logs e erros
    log_details = Column(JSONB)
    error_details = Column(JSONB)
    warnings = Column(JSONB)
    
    # Referências de arquivo
    source_file = Column(String(500))
    target_file = Column(String(500))
    
    # Preparado para futura integração API
    api_endpoint = Column(String(200))
    api_version = Column(String(20))
    etap_session_id = Column(String(100))
    
    # Relacionamentos
    study = relationship("EtapStudy")

# ================================
# Configuration and Mapping Tables
# ================================

class EtapFieldMapping(Base):
    """
    Mapeamento de campos entre estrutura interna e ETAP
    Baseado na análise dos CSVs reais da Petrobras
    """
    __tablename__ = "etap_field_mappings"
    __table_args__ = {"schema": "relay_configs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificação do mapeamento
    mapping_name = Column(String(255), nullable=False)
    device_type = Column(String(100))  # Motor, Relay, Transformer, etc.
    manufacturer = Column(String(100))  # Schneider, ABB, etc.
    
    # Mapeamento de campos
    internal_field = Column(String(100), nullable=False)  # Campo interno
    etap_field = Column(String(100), nullable=False)  # Campo ETAP correspondente
    csv_code = Column(String(20))  # Código do CSV (ex: "00.04", "09.0B")
    
    # Transformações
    data_type = Column(String(50))  # string, float, boolean, json
    unit_conversion = Column(String(100))  # A_to_kA, V_to_kV, etc.
    value_transformation = Column(String(200))  # Expressão de transformação
    
    # Validações
    validation_rules = Column(JSONB)  # Regras de validação
    default_value = Column(String(100))
    is_required = Column(Boolean, default=False)
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# ================================
# Import/Export History
# ================================

class EtapImportHistory(Base):
    """
    Histórico de importações de dados ETAP
    """
    __tablename__ = "etap_import_history"
    __table_args__ = {"schema": "relay_configs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificação da importação
    import_type = Column(String(50))  # CSV, ETAP_FILE, API
    file_name = Column(String(255))
    file_path = Column(String(500))
    file_size = Column(Integer)  # bytes
    file_hash = Column(String(64))  # SHA256
    
    # Status da importação
    status = Column(String(50))  # SUCCESS, FAILED, PARTIAL
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Estatísticas
    total_records = Column(Integer, default=0)
    imported_records = Column(Integer, default=0)
    updated_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    
    # Detalhes e logs
    import_summary = Column(JSONB)
    error_log = Column(JSONB)
    validation_warnings = Column(JSONB)
    
    # Usuário e origem
    imported_by = Column(String(100))
    import_source = Column(String(100))  # WEB_UI, API, BATCH
    
    # Relacionamentos opcionais
    study_id = Column(Integer, ForeignKey("protec_ai.etap_studies.id"))
    study = relationship("EtapStudy")
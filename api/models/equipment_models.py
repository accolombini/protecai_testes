"""
SQLAlchemy Models para Sistema ProtecAI
=======================================

Modelos ORM mapeando exatamente o schema relay_configs do PostgreSQL.
Arquitetura robusta e escalável para produção.
"""

from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, Float, ForeignKey, Text, Numeric, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Manufacturer(Base):
    """Fabricante de equipamentos de proteção"""
    __tablename__ = 'manufacturers'
    __table_args__ = {'schema': 'protec_ai'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100))
    website = Column(String(255))
    support_contact = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    models = relationship("RelayModel", back_populates="manufacturer")

class RelayModel(Base):
    """Modelo de relé de proteção"""
    __tablename__ = 'relay_models'
    __table_args__ = {'schema': 'protec_ai'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id = Column(Integer, ForeignKey('protec_ai.manufacturers.id'), nullable=False)
    name = Column(String(255), nullable=False)
    model_type = Column(String(100))
    family = Column(String(100))
    application_type = Column(String(100))
    voltage_class = Column(String(50))
    current_class = Column(String(50))
    protection_functions = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    manufacturer = relationship("Manufacturer", back_populates="models")
    equipments = relationship("RelayEquipment", back_populates="model")

class RelayEquipment(Base):
    """Equipamento de relé instalado"""
    __tablename__ = 'relay_equipment'
    __table_args__ = {'schema': 'protec_ai'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey('protec_ai.relay_models.id'), nullable=False)
    serial_number = Column(String(100))
    tag_reference = Column(String(50))
    plant_reference = Column(String(100))
    bay_position = Column(String(50))
    software_version = Column(String(50))
    frequency = Column(Numeric)
    description = Column(Text)
    installation_date = Column(Date)
    commissioning_date = Column(Date)
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    model = relationship("RelayModel", back_populates="equipments")
    electrical_config = relationship("ElectricalConfiguration", back_populates="equipment", uselist=False)
    protection_functions = relationship("ProtectionFunction", back_populates="equipment")
    io_configurations = relationship("IOConfiguration", back_populates="equipment")

class ElectricalConfiguration(Base):
    """Configuração elétrica do equipamento"""
    __tablename__ = 'electrical_configuration'
    __table_args__ = {'schema': 'protec_ai'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, ForeignKey('protec_ai.relay_equipment.id'), nullable=False)
    phase_ct_primary = Column(Float)
    phase_ct_secondary = Column(Float)
    neutral_ct_primary = Column(Float)
    neutral_ct_secondary = Column(Float)
    vt_primary = Column(Float)
    vt_secondary = Column(Float)
    nominal_voltage = Column(Float)
    frequency = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    equipment = relationship("RelayEquipment", back_populates="electrical_config")

class ProtectionFunction(Base):
    """Funções de proteção configuradas"""
    __tablename__ = 'protection_functions'
    __table_args__ = {'schema': 'protec_ai'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, ForeignKey('protec_ai.relay_equipment.id'), nullable=False)
    function_code = Column(String(10), nullable=False)
    function_name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    pickup_value = Column(Float)
    time_delay = Column(Float)
    curve_type = Column(String(50))
    settings = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    equipment = relationship("RelayEquipment", back_populates="protection_functions")

class IOConfiguration(Base):
    """Configuração de entradas e saídas"""
    __tablename__ = 'io_configuration'
    __table_args__ = {'schema': 'protec_ai'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, ForeignKey('protec_ai.relay_equipment.id'), nullable=False)
    channel_number = Column(Integer, nullable=False)
    channel_type = Column(String(20), nullable=False)  # 'digital_input', 'digital_output', 'analog_input'
    signal_type = Column(String(50))
    description = Column(String(200))
    enabled = Column(Boolean, default=True)
    configuration = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    equipment = relationship("RelayEquipment", back_populates="io_configurations")

class ComparisonReport(Base):
    """Relatórios de comparação entre equipamentos"""
    __tablename__ = 'comparison_reports'
    __table_args__ = {'schema': 'protec_ai'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment1_id = Column(Integer, ForeignKey('protec_ai.relay_equipment.id'), nullable=False)
    equipment2_id = Column(Integer, ForeignKey('protec_ai.relay_equipment.id'), nullable=False)
    comparison_type = Column(String(50), default='full')
    similarity_score = Column(Float)
    differences_count = Column(Integer)
    report_data = Column(Text)  # JSON com detalhes da comparação
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    equipment1 = relationship("RelayEquipment", foreign_keys=[equipment1_id])
    equipment2 = relationship("RelayEquipment", foreign_keys=[equipment2_id])

class ImportHistory(Base):
    """Histórico de importações de dados"""
    __tablename__ = 'import_history'
    __table_args__ = {'schema': 'protec_ai'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_format = Column(String(20), nullable=False)
    import_status = Column(String(20), default='completed')
    records_imported = Column(Integer)
    records_failed = Column(Integer)
    success_rate = Column(Float)
    processing_time = Column(Float)
    error_details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
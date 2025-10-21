"""
ML Models for Machine Learning Integration Gateway
Handles ML analysis jobs, results, and recommendations from external ML team.

This module provides the data layer for integration with external ML/RL modules
responsible for coordination, selectivity analysis, and simulations.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from datetime import datetime

from api.core.database import Base


class MLJobStatus(enum.Enum):
    """Status of ML analysis jobs"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MLAnalysisType(enum.Enum):
    """Types of ML analysis supported"""
    COORDINATION = "coordination"
    SELECTIVITY = "selectivity"
    SIMULATION = "simulation"
    OPTIMIZATION = "optimization"
    PREDICTION = "prediction"


class MLPriority(enum.Enum):
    """Priority levels for ML jobs"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MLRecommendationType(enum.Enum):
    """Types of ML recommendations"""
    SETTINGS_OPTIMIZATION = "settings_optimization"
    COORDINATION_IMPROVEMENT = "coordination_improvement"
    EQUIPMENT_UPGRADE = "equipment_upgrade"
    CONFIGURATION_CHANGE = "configuration_change"
    MAINTENANCE_RECOMMENDATION = "maintenance_recommendation"
    PROTECTION_ENHANCEMENT = "protection_enhancement"


class MLAnalysisJob(Base):
    """
    ML Analysis Job tracking table
    Manages ML analysis requests from external ML team
    """
    __tablename__ = "ml_analysis_jobs"
    __table_args__ = {'schema': 'ml_gateway'}

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Job identification
    job_name = Column(String(255), nullable=False)
    analysis_type = Column(SQLEnum(MLAnalysisType), nullable=False)
    priority = Column(SQLEnum(MLPriority), default=MLPriority.NORMAL)
    
    # Status tracking
    status = Column(SQLEnum(MLJobStatus), default=MLJobStatus.PENDING)
    progress_percentage = Column(Float, default=0.0)
    
    # Source data references
    etap_study_id = Column(Integer, nullable=True)  # Reference to ETAP study (FK removed temporarily)
    source_data_config = Column(JSONB)  # Configuration for data extraction
    
    # ML module information
    ml_module_version = Column(String(50))
    ml_algorithm = Column(String(100))
    ml_parameters = Column(JSONB)  # ML-specific parameters
    
    # Execution tracking
    requested_by = Column(String(100), nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Error handling
    error_message = Column(Text)
    error_details = Column(JSONB)
    
    # Performance metrics
    execution_time_seconds = Column(Float)
    data_size_processed_mb = Column(Float)
    
    # Results reference
    results_summary = Column(JSONB)
    output_file_path = Column(String(500))
    
    # Relationships
    # etap_study = relationship("EtapStudy", back_populates="ml_jobs")  # Comentado temporariamente
    coordination_results = relationship("MLCoordinationResult", back_populates="analysis_job")
    selectivity_results = relationship("MLSelectivityResult", back_populates="analysis_job")
    simulation_results = relationship("MLSimulationResult", back_populates="analysis_job")
    recommendations = relationship("MLRecommendation", back_populates="analysis_job")


class MLCoordinationResult(Base):
    """
    Coordination analysis results from ML module
    Stores results of coordination analysis performed by external ML team
    """
    __tablename__ = "ml_coordination_results"
    __table_args__ = {'schema': 'ml_gateway'}

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Job reference
    analysis_job_id = Column(Integer, ForeignKey('ml_gateway.ml_analysis_jobs.id'), nullable=False)
    
    # Coordination analysis results
    coordination_status = Column(String(50))  # "coordinated", "miscoordinated", "marginal"
    overall_confidence = Column(Float)  # 0.0 to 1.0
    
    # Device pairs analysis
    device_pairs_analyzed = Column(Integer)
    coordinated_pairs = Column(Integer)
    miscoordinated_pairs = Column(Integer)
    marginal_pairs = Column(Integer)
    
    # Detailed results
    pair_analysis_details = Column(JSONB)  # Detailed analysis per pair
    time_margins = Column(JSONB)  # Time margins analysis
    current_margins = Column(JSONB)  # Current margins analysis
    
    # ML model information
    model_version = Column(String(50))
    model_confidence = Column(Float)
    feature_importance = Column(JSONB)
    
    # Performance metrics
    analysis_duration_ms = Column(Float)
    data_points_analyzed = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    analysis_job = relationship("MLAnalysisJob", back_populates="coordination_results")


class MLSelectivityResult(Base):
    """
    Selectivity analysis results from ML module
    Stores results of selectivity analysis performed by external ML team
    """
    __tablename__ = "ml_selectivity_results"
    __table_args__ = {'schema': 'ml_gateway'}

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Job reference
    analysis_job_id = Column(Integer, ForeignKey('ml_gateway.ml_analysis_jobs.id'), nullable=False)
    
    # Selectivity analysis results
    selectivity_status = Column(String(50))  # "selective", "non_selective", "conditional"
    overall_confidence = Column(Float)  # 0.0 to 1.0
    
    # Protection zones analysis
    protection_zones_analyzed = Column(Integer)
    properly_selective_zones = Column(Integer)
    non_selective_zones = Column(Integer)
    
    # Zone coverage analysis
    zone_coverage_percentage = Column(Float)
    backup_protection_adequacy = Column(String(50))
    overlap_analysis = Column(JSONB)
    
    # Detailed results
    zone_analysis_details = Column(JSONB)  # Detailed analysis per zone
    fault_clearing_times = Column(JSONB)  # Fault clearing time analysis
    sensitivity_analysis = Column(JSONB)  # Sensitivity settings analysis
    
    # ML model information
    model_version = Column(String(50))
    model_confidence = Column(Float)
    feature_importance = Column(JSONB)
    
    # Performance metrics
    analysis_duration_ms = Column(Float)
    scenarios_analyzed = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    analysis_job = relationship("MLAnalysisJob", back_populates="selectivity_results")


class MLSimulationResult(Base):
    """
    Simulation results from ML module
    Stores results of protection system simulations performed by external ML team
    """
    __tablename__ = "ml_simulation_results"
    __table_args__ = {'schema': 'ml_gateway'}

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Job reference
    analysis_job_id = Column(Integer, ForeignKey('ml_gateway.ml_analysis_jobs.id'), nullable=False)
    
    # Simulation configuration
    simulation_type = Column(String(100))  # "fault_analysis", "load_flow", "transient", etc.
    simulation_parameters = Column(JSONB)
    
    # Simulation results
    simulation_status = Column(String(50))  # "successful", "failed", "partial"
    convergence_achieved = Column(Boolean)
    iterations_count = Column(Integer)
    
    # Performance metrics
    simulation_time_seconds = Column(Float)
    memory_usage_mb = Column(Float)
    cpu_usage_percentage = Column(Float)
    
    # Results data
    simulation_data = Column(JSONB)  # Raw simulation results
    fault_currents = Column(JSONB)  # Fault current analysis
    voltage_profiles = Column(JSONB)  # Voltage profile results
    protection_operations = Column(JSONB)  # Protection device operations
    
    # ML analysis of results
    ml_insights = Column(JSONB)  # ML-generated insights from simulation
    anomalies_detected = Column(JSONB)  # Detected anomalies
    risk_assessment = Column(JSONB)  # Risk assessment results
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    analysis_job = relationship("MLAnalysisJob", back_populates="simulation_results")


class MLRecommendation(Base):
    """
    ML-generated recommendations
    Stores recommendations generated by external ML team for system improvements
    """
    __tablename__ = "ml_recommendations"
    __table_args__ = {'schema': 'ml_gateway'}

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Job reference
    analysis_job_id = Column(Integer, ForeignKey('ml_gateway.ml_analysis_jobs.id'), nullable=False)
    
    # Recommendation details
    recommendation_type = Column(String(100))  # "parameter_adjustment", "equipment_addition", etc.
    priority = Column(SQLEnum(MLPriority), default=MLPriority.NORMAL)
    
    # Target information
    target_equipment_id = Column(String(100))
    target_parameter = Column(String(100))
    
    # Recommendation content
    current_value = Column(String(200))
    recommended_value = Column(String(200))
    recommendation_rationale = Column(Text)
    
    # Impact analysis
    expected_improvement = Column(JSONB)  # Expected improvements
    implementation_complexity = Column(String(50))  # "low", "medium", "high"
    estimated_cost = Column(Float)
    risk_level = Column(String(50))  # "low", "medium", "high"
    
    # ML confidence
    confidence_score = Column(Float)  # 0.0 to 1.0
    supporting_evidence = Column(JSONB)  # Supporting evidence from ML analysis
    
    # Implementation tracking
    implementation_status = Column(String(50))  # "pending", "approved", "implemented", "rejected"
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime(timezone=True))
    implementation_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    analysis_job = relationship("MLAnalysisJob", back_populates="recommendations")


class MLDataSnapshot(Base):
    """
    Data snapshots provided to ML module
    Tracks what data was provided to ML team for analysis
    """
    __tablename__ = "ml_data_snapshots"
    __table_args__ = {'schema': 'ml_gateway'}

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Snapshot identification
    snapshot_name = Column(String(255), nullable=False)
    snapshot_description = Column(Text)
    
    # Data scope
    etap_study_ids = Column(JSONB)  # List of ETAP study IDs included
    manufacturer_filter = Column(JSONB)  # Manufacturer filters applied
    parameter_filters = Column(JSONB)  # Parameter filters applied
    date_range_start = Column(DateTime(timezone=True))
    date_range_end = Column(DateTime(timezone=True))
    
    # Data statistics
    total_records = Column(Integer)
    total_parameters = Column(Integer)
    total_devices = Column(Integer)
    data_size_mb = Column(Float)
    
    # Data format and structure
    data_format = Column(String(50))  # "json", "csv", "parquet", etc.
    schema_version = Column(String(20))
    data_structure = Column(JSONB)  # Description of data structure
    
    # Quality metrics
    data_completeness_percentage = Column(Float)
    data_quality_score = Column(Float)
    missing_values_count = Column(Integer)
    anomalies_detected = Column(Integer)
    
    # Access tracking
    created_by = Column(String(100), nullable=False)
    accessed_by = Column(JSONB)  # Track who accessed this snapshot
    download_count = Column(Integer, default=0)
    
    # File information
    file_path = Column(String(500))
    file_checksum = Column(String(100))
    expiration_date = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True))
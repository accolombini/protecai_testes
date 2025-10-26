"""
ML Gateway Pydantic Schemas
Defines request/response schemas for ML API Gateway integration.

These schemas ensure type safety and validation for communication
with external ML/RL modules.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
import uuid


class MLJobStatusEnum(str, Enum):
    """Status of ML analysis jobs - SYNCHRONIZED WITH POSTGRESQL"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MLAnalysisTypeEnum(str, Enum):
    """Types of ML analysis supported - SYNCHRONIZED WITH POSTGRESQL"""
    COORDINATION = "COORDINATION"
    SELECTIVITY = "SELECTIVITY"
    SIMULATION = "SIMULATION"
    OPTIMIZATION = "OPTIMIZATION"
    PREDICTION = "PREDICTION"


class MLPriorityEnum(str, Enum):
    """Priority levels for ML jobs - SYNCHRONIZED WITH POSTGRESQL"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ===== REQUEST SCHEMAS =====

class MLDataRequest(BaseModel):
    """Request schema for ML data extraction"""
    etap_study_ids: Optional[List[int]] = Field(None, description="Specific ETAP study IDs to include")
    manufacturer_filter: Optional[List[str]] = Field(None, description="Filter by manufacturer")
    parameter_types: Optional[List[str]] = Field(None, description="Specific parameter types to include")
    include_historical: bool = Field(False, description="Include historical data")
    date_range_start: Optional[datetime] = Field(None, description="Start date for data range")
    date_range_end: Optional[datetime] = Field(None, description="End date for data range")
    data_format: str = Field("json", description="Preferred data format")
    include_metadata: bool = Field(True, description="Include metadata in response")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class MLJobRequest(BaseModel):
    """Request schema for creating ML analysis jobs"""
    # Primary fields (flexible naming for compatibility)
    job_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Unique job name")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Job name (alternative)")
    
    analysis_type: Optional[MLAnalysisTypeEnum] = Field(None, description="Type of analysis to perform")
    type: Optional[str] = Field(None, description="Analysis type (alternative)")
    
    priority: MLPriorityEnum = Field(MLPriorityEnum.NORMAL, description="Job priority level")
    
    # Data scope (optional with defaults)
    source_data_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for data extraction")
    etap_study_id: Optional[int] = Field(None, description="Specific ETAP study to analyze")
    
    # ML configuration
    ml_module_version: Optional[str] = Field(None, max_length=50, description="ML module version")
    ml_algorithm: Optional[str] = Field(None, max_length=100, description="ML algorithm to use")
    ml_parameters: Optional[Dict[str, Any]] = Field(None, description="ML-specific parameters")
    
    # Requester information (optional with default)
    requested_by: Optional[str] = Field(None, min_length=1, max_length=100, description="Who requested the analysis")
    
    @validator('job_name', pre=True, always=True)
    def validate_job_name(cls, v, values):
        # Use job_name if provided, otherwise use name field
        if v:
            return v.strip() if isinstance(v, str) else str(v)
        if 'name' in values and values['name']:
            return str(values['name']).strip()
        # Generate default if neither provided
        import uuid
        return f"ml_job_{str(uuid.uuid4())[:8]}"
    
    @validator('analysis_type', pre=True, always=True)
    def validate_analysis_type(cls, v, values):
        # Use analysis_type if provided, otherwise use type field
        if v:
            return MLAnalysisTypeEnum(v) if isinstance(v, str) else v
        if 'type' in values and values['type']:
            type_value = str(values['type']).lower()
            # Map common variations
            type_mapping = {
                'coordination': MLAnalysisTypeEnum.COORDINATION,
                'selectivity': MLAnalysisTypeEnum.SELECTIVITY,
                'simulation': MLAnalysisTypeEnum.SIMULATION,
                'optimization': MLAnalysisTypeEnum.OPTIMIZATION,
                'prediction': MLAnalysisTypeEnum.PREDICTION
            }
            return type_mapping.get(type_value, MLAnalysisTypeEnum.COORDINATION)
        # Default to coordination
        return MLAnalysisTypeEnum.COORDINATION
    
    @validator('source_data_config', pre=True, always=True)
    def validate_source_data_config(cls, v):
        # Provide default configuration if not specified
        if v:
            return v
        return {
            "include_all_studies": True,
            "include_equipment_configs": True,
            "include_protection_settings": True,
            "data_format": "json"
        }
    
    @validator('requested_by', pre=True, always=True)
    def validate_requested_by(cls, v):
        # Provide default requester if not specified
        if v:
            return str(v).strip()
        return "system_user"


class MLCoordinationResultRequest(BaseModel):
    """Request schema for submitting coordination analysis results"""
    analysis_job_uuid: uuid.UUID = Field(..., description="UUID of the analysis job")
    
    # Coordination results
    coordination_status: str = Field(..., description="Overall coordination status")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")
    
    # Device pairs analysis
    device_pairs_analyzed: int = Field(..., ge=0, description="Number of device pairs analyzed")
    coordinated_pairs: int = Field(..., ge=0, description="Number of coordinated pairs")
    miscoordinated_pairs: int = Field(..., ge=0, description="Number of miscoordinated pairs")
    marginal_pairs: int = Field(..., ge=0, description="Number of marginal pairs")
    
    # Detailed results
    pair_analysis_details: Dict[str, Any] = Field(..., description="Detailed analysis per pair")
    time_margins: Optional[Dict[str, Any]] = Field(None, description="Time margins analysis")
    current_margins: Optional[Dict[str, Any]] = Field(None, description="Current margins analysis")
    
    # ML model information
    ml_model_version: Optional[str] = Field(None, max_length=50, description="ML model version used")
    ml_model_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="ML model confidence")
    feature_importance: Optional[Dict[str, Any]] = Field(None, description="Feature importance analysis")
    
    # Performance metrics
    analysis_duration_ms: Optional[float] = Field(None, ge=0, description="Analysis duration in milliseconds")
    data_points_analyzed: Optional[int] = Field(None, ge=0, description="Number of data points analyzed")


class MLSelectivityResultRequest(BaseModel):
    """Request schema for submitting selectivity analysis results"""
    analysis_job_uuid: uuid.UUID = Field(..., description="UUID of the analysis job")
    
    # Selectivity results
    selectivity_status: str = Field(..., description="Overall selectivity status")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")
    
    # Protection zones analysis
    protection_zones_analyzed: int = Field(..., ge=0, description="Number of zones analyzed")
    properly_selective_zones: int = Field(..., ge=0, description="Number of properly selective zones")
    non_selective_zones: int = Field(..., ge=0, description="Number of non-selective zones")
    
    # Zone coverage
    zone_coverage_percentage: float = Field(..., ge=0.0, le=100.0, description="Zone coverage percentage")
    backup_protection_adequacy: str = Field(..., description="Backup protection adequacy assessment")
    overlap_analysis: Optional[Dict[str, Any]] = Field(None, description="Zone overlap analysis")
    
    # Detailed results
    zone_analysis_details: Dict[str, Any] = Field(..., description="Detailed analysis per zone")
    fault_clearing_times: Optional[Dict[str, Any]] = Field(None, description="Fault clearing time analysis")
    sensitivity_analysis: Optional[Dict[str, Any]] = Field(None, description="Sensitivity settings analysis")
    
    # ML model information
    ml_model_version: Optional[str] = Field(None, max_length=50, description="ML model version used")
    ml_model_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="ML model confidence")
    feature_importance: Optional[Dict[str, Any]] = Field(None, description="Feature importance analysis")
    
    # Performance metrics
    analysis_duration_ms: Optional[float] = Field(None, ge=0, description="Analysis duration in milliseconds")
    scenarios_analyzed: Optional[int] = Field(None, ge=0, description="Number of scenarios analyzed")


class MLSimulationResultRequest(BaseModel):
    """Request schema for submitting simulation results"""
    analysis_job_uuid: uuid.UUID = Field(..., description="UUID of the analysis job")
    
    # Simulation configuration
    simulation_type: str = Field(..., max_length=100, description="Type of simulation performed")
    simulation_parameters: Dict[str, Any] = Field(..., description="Simulation parameters used")
    
    # Simulation results
    simulation_status: str = Field(..., description="Simulation completion status")
    convergence_achieved: bool = Field(..., description="Whether convergence was achieved")
    iterations_count: Optional[int] = Field(None, ge=0, description="Number of iterations performed")
    
    # Performance metrics
    simulation_time_seconds: Optional[float] = Field(None, ge=0, description="Simulation execution time")
    memory_usage_mb: Optional[float] = Field(None, ge=0, description="Memory usage in MB")
    cpu_usage_percentage: Optional[float] = Field(None, ge=0, le=100, description="CPU usage percentage")
    
    # Results data
    simulation_data: Dict[str, Any] = Field(..., description="Raw simulation results")
    fault_currents: Optional[Dict[str, Any]] = Field(None, description="Fault current analysis")
    voltage_profiles: Optional[Dict[str, Any]] = Field(None, description="Voltage profile results")
    protection_operations: Optional[Dict[str, Any]] = Field(None, description="Protection device operations")
    
    # ML analysis
    ml_insights: Optional[Dict[str, Any]] = Field(None, description="ML-generated insights")
    anomalies_detected: Optional[Dict[str, Any]] = Field(None, description="Detected anomalies")
    risk_assessment: Optional[Dict[str, Any]] = Field(None, description="Risk assessment results")


class MLRecommendationRequest(BaseModel):
    """Request schema for submitting ML recommendations"""
    analysis_job_uuid: uuid.UUID = Field(..., description="UUID of the analysis job")
    
    # Recommendation details
    recommendation_type: str = Field(..., max_length=100, description="Type of recommendation")
    priority: MLPriorityEnum = Field(MLPriorityEnum.NORMAL, description="Recommendation priority")
    
    # Target information
    target_equipment_id: Optional[str] = Field(None, max_length=100, description="Target equipment ID")
    target_parameter: Optional[str] = Field(None, max_length=100, description="Target parameter")
    
    # Recommendation content
    current_value: Optional[str] = Field(None, max_length=200, description="Current value")
    recommended_value: Optional[str] = Field(None, max_length=200, description="Recommended value")
    recommendation_rationale: str = Field(..., description="Rationale for the recommendation")
    
    # Impact analysis
    expected_improvement: Optional[Dict[str, Any]] = Field(None, description="Expected improvements")
    implementation_complexity: Optional[str] = Field(None, description="Implementation complexity level")
    estimated_cost: Optional[float] = Field(None, ge=0, description="Estimated implementation cost")
    risk_level: Optional[str] = Field(None, description="Risk level assessment")
    
    # ML confidence
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    supporting_evidence: Optional[Dict[str, Any]] = Field(None, description="Supporting evidence")


class MLJobStatusUpdate(BaseModel):
    """Schema for ML job status updates"""
    analysis_job_uuid: uuid.UUID = Field(..., description="UUID of the analysis job")
    status: MLJobStatusEnum = Field(..., description="New job status")
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Progress percentage")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")


# ===== RESPONSE SCHEMAS =====

class MLJobResponse(BaseModel):
    """Response schema for ML job operations"""
    id: int
    uuid: uuid.UUID
    job_name: str
    analysis_type: str
    status: str
    priority: str
    progress_percentage: float
    requested_by: str
    requested_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    execution_time_seconds: Optional[float]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v)
        }


class MLDataResponse(BaseModel):
    """Response schema for ML data requests"""
    snapshot_uuid: uuid.UUID = Field(..., description="UUID of the data snapshot")
    total_records: int = Field(..., description="Total number of records")
    total_parameters: int = Field(..., description="Total number of parameters")
    total_devices: int = Field(..., description="Total number of devices")
    data_size_mb: float = Field(..., description="Data size in MB")
    data_format: str = Field(..., description="Data format")
    schema_version: str = Field(..., description="Schema version")
    created_at: datetime = Field(..., description="Creation timestamp")
    download_url: Optional[str] = Field(None, description="Download URL for large datasets")
    data: Optional[Dict[str, Any]] = Field(None, description="Inline data for small datasets")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Dataset metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v)
        }


class MLAnalysisHistoryResponse(BaseModel):
    """Response schema for analysis history"""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_execution_time: Optional[float]
    jobs: List[MLJobResponse]
    
    class Config:
        from_attributes = True


class MLHealthResponse(BaseModel):
    """Response schema for ML Gateway health check"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    database_connected: bool = Field(..., description="Database connection status")
    etap_integration_status: bool = Field(..., description="ETAP integration status")
    active_jobs: int = Field(..., description="Number of active ML jobs")
    total_data_snapshots: int = Field(..., description="Total data snapshots available")
    last_successful_analysis: Optional[datetime] = Field(None, description="Last successful analysis")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class MLErrorResponse(BaseModel):
    """Standardized error response schema"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ===== UTILITY SCHEMAS =====

class MLParameterInfo(BaseModel):
    """Schema for parameter information"""
    parameter_code: str
    parameter_description: str
    manufacturer: str
    device_type: str
    parameter_category: str
    data_type: str
    unit: Optional[str]
    valid_range: Optional[Dict[str, Any]]


class MLEquipmentInfo(BaseModel):
    """Schema for equipment information"""
    equipment_id: str
    equipment_name: str
    manufacturer: str
    model: str
    firmware_version: Optional[str]
    installation_date: Optional[datetime]
    parameters: List[MLParameterInfo]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class MLStudyInfo(BaseModel):
    """Schema for ETAP study information"""
    study_id: int
    study_uuid: uuid.UUID
    study_name: str
    study_type: str
    status: str
    equipment_count: int
    parameter_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v)
        }


class PaginationParams(BaseModel):
    """Schema for pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(50, ge=1, le=1000, description="Page size")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel):
    """Generic paginated response schema"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool


# ===== MISSING SCHEMAS FOR ROUTER =====

class MLAnalysisRequest(BaseModel):
    """Generic ML analysis request schema"""
    analysis_type: str = Field(..., description="Type of analysis requested")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Analysis parameters")
    priority: str = Field("medium", description="Request priority")
    

class MLJobStatusResponse(BaseModel):
    """Response schema for job status"""
    job_uuid: uuid.UUID
    status: str
    progress_percentage: float
    estimated_completion: Optional[datetime]
    updated_at: datetime
    message: Optional[str] = None
    processing_logs: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v)
        }


class MLJobSummaryResponse(BaseModel):
    """Response schema for job summary in lists"""
    job_uuid: uuid.UUID
    job_name: str
    analysis_type: str
    status: str
    priority: str
    requested_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    equipment_count: Optional[int]
    parameter_count: Optional[int]
    result_count: int = 0
    progress_percentage: float = 0.0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v)
        }


class MLResultResponse(BaseModel):
    """Response schema for ML analysis results"""
    result_uuid: uuid.UUID
    job_uuid: uuid.UUID
    status: str
    result_type: str
    confidence_score: float
    created_at: datetime
    processing_time_seconds: Optional[float]
    recommendations_count: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v)
        }


class MLRecommendationResponse(BaseModel):
    """Response schema for ML recommendations"""
    recommendation_uuid: uuid.UUID
    result_uuid: uuid.UUID
    recommendation_type: str
    title: str
    priority: str
    confidence_score: float
    status: str
    created_at: datetime
    affected_equipment_count: int = 0
    parameter_changes_count: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v)
        }
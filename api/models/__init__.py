"""
Models package for ProtecAI API
==============================

SQLAlchemy ORM models for relay protection equipment and ETAP integration.
"""

from .equipment_models import (
    Base,
    Manufacturer,
    RelayModel, 
    RelayEquipment,
    ElectricalConfiguration,
    ProtectionFunction,
    IOConfiguration,
    ComparisonReport,
    ImportHistory
)

from .etap_models import (
    StudyType,
    StudyStatus,
    CurveType,
    ProtectionStandard,
    EtapStudy,
    EtapEquipmentConfig,
    ProtectionCurve,
    CoordinationResult,
    SimulationResult,
    EtapSyncLog,
    EtapFieldMapping,
    EtapImportHistory
)

__all__ = [
    # Equipment Models
    "Base",
    "Manufacturer",
    "RelayModel", 
    "RelayEquipment",
    "ElectricalConfiguration",
    "ProtectionFunction", 
    "IOConfiguration",
    "ComparisonReport",
    "ImportHistory",
    
    # ETAP Models
    "StudyType",
    "StudyStatus", 
    "CurveType",
    "ProtectionStandard",
    "EtapStudy",
    "EtapEquipmentConfig",
    "ProtectionCurve",
    "CoordinationResult",
    "SimulationResult",
    "EtapSyncLog",
    "EtapFieldMapping",
    "EtapImportHistory"
]
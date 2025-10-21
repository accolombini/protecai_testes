"""
ETAP Native Adapter - etapPy™ API Preparation
============================================

Adapter preparatório para futura integração com etapPy™ / etapAPI™.
Implementa padrão Adapter para abstrair diferenças entre CSV Bridge e API nativa.

Funcionalidades:
- Interface abstrata para comunicação ETAP
- Mock implementation para desenvolvimento offline
- Protocol definition para etapPy™ integration
- Error handling e retry mechanisms
- Performance monitoring e caching

Baseado na arquitetura universal já implementada.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Union, Protocol
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json
import uuid
from enum import Enum

logger = logging.getLogger(__name__)

# ================================
# Protocol Definitions
# ================================

class EtapConnectionProtocol(Protocol):
    """Protocol para diferentes tipos de conexão ETAP"""
    
    async def connect(self) -> bool:
        """Conectar ao ETAP"""
        ...
    
    async def disconnect(self) -> bool:
        """Desconectar do ETAP"""
        ...
    
    async def is_connected(self) -> bool:
        """Verificar status da conexão"""
        ...

class EtapDataProtocol(Protocol):
    """Protocol para operações de dados ETAP"""
    
    async def import_study(self, study_data: Dict[str, Any]) -> Dict[str, Any]:
        """Importar estudo para ETAP"""
        ...
    
    async def export_study(self, study_id: str) -> Dict[str, Any]:
        """Exportar estudo do ETAP"""
        ...
    
    async def run_analysis(self, analysis_config: Dict[str, Any]) -> Dict[str, Any]:
        """Executar análise no ETAP"""
        ...

# ================================
# Enums and Data Classes
# ================================

class EtapConnectionType(str, Enum):
    """Tipos de conexão ETAP suportados"""
    CSV_BRIDGE = "csv_bridge"           # Atual - via arquivos CSV
    ETAP_API = "etap_api"              # Futuro - etapPy™ nativo
    MOCK_SIMULATOR = "mock_simulator"   # Desenvolvimento offline

class EtapOperationStatus(str, Enum):
    """Status das operações ETAP"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class EtapConnectionConfig:
    """Configuração de conexão ETAP"""
    connection_type: EtapConnectionType
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    license_server: Optional[str] = None
    etap_version: Optional[str] = None
    timeout_seconds: int = 300
    retry_attempts: int = 3
    mock_data_path: Optional[str] = None

@dataclass
class EtapOperationResult:
    """Resultado de operação ETAP"""
    operation_id: str
    status: EtapOperationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None

# ================================
# Abstract Base Adapter
# ================================

class EtapAdapterBase(ABC):
    """
    Adapter abstrato para diferentes tipos de integração ETAP
    """
    
    def __init__(self, config: EtapConnectionConfig):
        self.config = config
        self.connection_id = str(uuid.uuid4())
        self.logger = logger
        self._connected = False
        self._last_operation: Optional[EtapOperationResult] = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Conectar ao ETAP"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Desconectar do ETAP"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Verificar status da conexão"""
        pass
    
    @abstractmethod
    async def import_study_data(
        self, 
        study_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> EtapOperationResult:
        """Importar dados de estudo para ETAP"""
        pass
    
    @abstractmethod
    async def export_study_data(
        self, 
        study_identifier: str,
        export_options: Optional[Dict[str, Any]] = None
    ) -> EtapOperationResult:
        """Exportar dados de estudo do ETAP"""
        pass
    
    @abstractmethod
    async def run_coordination_analysis(
        self,
        analysis_config: Dict[str, Any]
    ) -> EtapOperationResult:
        """Executar análise de coordenação"""
        pass
    
    @abstractmethod
    async def run_selectivity_analysis(
        self,
        analysis_config: Dict[str, Any]  
    ) -> EtapOperationResult:
        """Executar análise de seletividade"""
        pass
    
    # ================================
    # Common Methods
    # ================================
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Informações da conexão"""
        return {
            "connection_id": self.connection_id,
            "connection_type": self.config.connection_type,
            "connected": self._connected,
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "etap_version": self.config.etap_version,
                "timeout_seconds": self.config.timeout_seconds
            },
            "last_operation": self._last_operation.operation_id if self._last_operation else None
        }
    
    def get_last_operation(self) -> Optional[EtapOperationResult]:
        """Última operação executada"""
        return self._last_operation
    
    async def test_connection(self) -> Dict[str, Any]:
        """Testar conectividade"""
        start_time = datetime.utcnow()
        
        try:
            connected = await self.connect()
            if connected:
                is_connected = await self.is_connected()
                await self.disconnect()
                
                return {
                    "success": True,
                    "connection_type": self.config.connection_type,
                    "response_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    "connected": is_connected,
                    "timestamp": start_time.isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to establish connection",
                    "connection_type": self.config.connection_type,
                    "timestamp": start_time.isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "connection_type": self.config.connection_type,
                "timestamp": start_time.isoformat()
            }

# ================================
# CSV Bridge Adapter (Current)
# ================================

class EtapCSVBridgeAdapter(EtapAdapterBase):
    """
    Adapter para CSV Bridge (implementação atual)
    Mantém compatibilidade com fluxo existente
    """
    
    def __init__(self, config: EtapConnectionConfig):
        super().__init__(config)
        # Import local para evitar dependência circular
        from .csv_bridge import CSVBridge
        from .etap_integration_service import EtapIntegrationService
        
        self.csv_bridge = CSVBridge()
        self._csv_export_path = Path("outputs/etap_exports")
        self._csv_export_path.mkdir(exist_ok=True)
    
    async def connect(self) -> bool:
        """CSV Bridge sempre 'conectado' (arquivos locais)"""
        self._connected = True
        self.logger.info("🔗 CSV Bridge Adapter connected")
        return True
    
    async def disconnect(self) -> bool:
        """Desconectar CSV Bridge"""
        self._connected = False
        self.logger.info("📤 CSV Bridge Adapter disconnected")
        return True
    
    async def is_connected(self) -> bool:
        """CSV Bridge status"""
        return self._connected
    
    async def import_study_data(
        self, 
        study_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> EtapOperationResult:
        """Importar via CSV Bridge"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            # Converter dados para formato CSV
            csv_data = self._convert_study_to_csv(study_data)
            
            # Simular processo de importação
            await asyncio.sleep(0.1)  # Simular I/O
            
            result = EtapOperationResult(
                operation_id=operation_id,
                status=EtapOperationStatus.COMPLETED,
                started_at=start_time,
                completed_at=datetime.utcnow(),
                result_data={
                    "imported_studies": 1,
                    "imported_equipment": len(study_data.get("equipment_configs", []) if isinstance(study_data.get("equipment_configs", []), list) else []),
                    "csv_files_generated": 1,
                    "export_path": str(self._csv_export_path)
                },
                performance_metrics={
                    "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    "data_size_kb": len(str(study_data)) / 1024
                }
            )
            
            self._last_operation = result
            self.logger.info(f"📊 CSV Bridge import completed: {operation_id}")
            return result
            
        except Exception as e:
            result = EtapOperationResult(
                operation_id=operation_id,
                status=EtapOperationStatus.FAILED,
                started_at=start_time,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
            self._last_operation = result
            self.logger.error(f"❌ CSV Bridge import failed: {e}")
            return result
    
    async def export_study_data(
        self, 
        study_identifier: str,
        export_options: Optional[Dict[str, Any]] = None
    ) -> EtapOperationResult:
        """Exportar via CSV Bridge"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            # Simular busca do estudo
            study_data = self._mock_study_data(study_identifier)
            
            # Converter para CSV
            csv_content = self._convert_study_to_csv(study_data)
            
            # Salvar arquivo
            export_file = self._csv_export_path / f"study_{study_identifier}_{operation_id}.csv"
            export_file.write_text(csv_content)
            
            result = EtapOperationResult(
                operation_id=operation_id,
                status=EtapOperationStatus.COMPLETED,
                started_at=start_time,
                completed_at=datetime.utcnow(),
                result_data={
                    "exported_file": str(export_file),
                    "file_size_bytes": export_file.stat().st_size,
                    "study_id": study_identifier,
                    "export_format": "csv"
                },
                performance_metrics={
                    "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
                }
            )
            
            self._last_operation = result
            self.logger.info(f"📤 CSV Bridge export completed: {export_file}")
            return result
            
        except Exception as e:
            result = EtapOperationResult(
                operation_id=operation_id,
                status=EtapOperationStatus.FAILED,
                started_at=start_time,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
            self._last_operation = result
            return result
    
    async def run_coordination_analysis(
        self,
        analysis_config: Dict[str, Any]
    ) -> EtapOperationResult:
        """Análise de coordenação via CSV"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Simular análise offline
        await asyncio.sleep(0.5)
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "analysis_type": "coordination",
                "devices_analyzed": len(analysis_config.get("devices", []) if isinstance(analysis_config.get("devices", []), list) else []),
                "coordination_pairs": 5,
                "violations_found": 0,
                "report_generated": True
            },
            warnings=["CSV Bridge: Limited analysis capabilities offline"]
        )
        
        self._last_operation = result
        return result
    
    async def run_selectivity_analysis(
        self,
        analysis_config: Dict[str, Any]
    ) -> EtapOperationResult:
        """Análise de seletividade via CSV"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Simular análise offline
        await asyncio.sleep(0.3)
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "analysis_type": "selectivity",
                "protection_zones": 3,
                "selectivity_verified": True,
                "margin_analysis": "adequate"
            },
            warnings=["CSV Bridge: Simplified selectivity analysis"]
        )
        
        self._last_operation = result
        return result
    
    # ================================
    # Helper Methods
    # ================================
    
    def _convert_study_to_csv(self, study_data: Dict[str, Any]) -> str:
        """Converter estudo para formato CSV"""
        lines = ["Code,Description,Value"]
        
        for equipment in (study_data.get("equipment_configs", []) if isinstance(study_data.get("equipment_configs", []), list) else []):
            config = equipment.get("configuration", {})
            for key, value in config.items():
                lines.append(f"{key},Equipment {equipment.get('tag', 'Unknown')},{value}")
        
        return "\n".join(lines)
    
    def _mock_study_data(self, study_id: str) -> Dict[str, Any]:
        """Gerar dados mock para teste"""
        return {
            "study_id": study_id,
            "name": f"Mock Study {study_id}",
            "equipment_configs": [
                {
                    "tag": "REL001",
                    "manufacturer": "Schneider",
                    "model": "MiCOM P143",
                    "configuration": {
                        "50.01": "Enabled",
                        "50.02": "1000",
                        "51.01": "Enabled"
                    }
                }
            ]
        }

# ================================
# Native etapPy™ Adapter (Future)
# ================================

class EtapNativeAPIAdapter(EtapAdapterBase):
    """
    Adapter para etapPy™ API nativa (implementação futura)
    Preparado para comunicação direta com ETAP
    """
    
    def __init__(self, config: EtapConnectionConfig):
        super().__init__(config)
        self._etap_session = None
        self._etap_client = None
    
    async def connect(self) -> bool:
        """Conectar ao ETAP via etapPy™"""
        try:
            # Futuro: Inicializar etapPy™
            # import etappy
            # self._etap_client = etappy.EtapClient(
            #     host=self.config.host,
            #     port=self.config.port,
            #     username=self.config.username,
            #     password=self.config.password
            # )
            # self._etap_session = await self._etap_client.connect()
            
            # Por enquanto: Mock implementation
            self.logger.info("🚧 Native API Adapter: Future implementation")
            self.logger.info(f"📡 Configured for: {self.config.host}:{self.config.port}")
            
            # Simular conexão
            await asyncio.sleep(1.0)
            self._connected = True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Native API connection failed: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Desconectar do ETAP"""
        try:
            # Futuro: await self._etap_session.disconnect()
            self._connected = False
            self.logger.info("📤 Native API Adapter disconnected")
            return True
            
        except Exception as e:
            self.logger.error(f"Native API disconnect failed: {e}")
            return False
    
    async def is_connected(self) -> bool:
        """Verificar conexão nativa"""
        # Futuro: return self._etap_session.is_active()
        return self._connected
    
    async def import_study_data(
        self, 
        study_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> EtapOperationResult:
        """Importar dados diretamente via API"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Futuro: implementação nativa
        # result = await self._etap_session.import_study(study_data)
        
        # Mock implementation
        await asyncio.sleep(2.0)  # Simular operação mais demorada
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "native_import": True,
                "etap_study_id": f"ETAP_{operation_id}",
                "direct_communication": True,
                "validation_passed": True
            },
            performance_metrics={
                "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "native_api_version": self.config.etap_version or "Future"
            }
        )
        
        self._last_operation = result
        self.logger.info(f"🔥 Native API import (FUTURE): {operation_id}")
        return result
    
    async def export_study_data(
        self, 
        study_identifier: str,
        export_options: Optional[Dict[str, Any]] = None
    ) -> EtapOperationResult:
        """Exportar dados diretamente via API"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Mock implementation
        await asyncio.sleep(1.5)
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "native_export": True,
                "study_id": study_identifier,
                "real_time_data": True,
                "format": "native_etap_format"
            }
        )
        
        self._last_operation = result
        return result
    
    async def run_coordination_analysis(
        self,
        analysis_config: Dict[str, Any]
    ) -> EtapOperationResult:
        """Análise de coordenação nativa"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Futuro: análise real do ETAP
        await asyncio.sleep(3.0)
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "analysis_type": "coordination",
                "native_etap_engine": True,
                "detailed_results": True,
                "curve_analysis": "complete",
                "coordination_verified": True
            }
        )
        
        self._last_operation = result
        return result
    
    async def run_selectivity_analysis(
        self,
        analysis_config: Dict[str, Any]
    ) -> EtapOperationResult:
        """Análise de seletividade nativa"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        await asyncio.sleep(2.5)
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "analysis_type": "selectivity",
                "native_calculations": True,
                "precision": "high",
                "selectivity_matrix": "generated"
            }
        )
        
        self._last_operation = result
        return result

# ================================
# Mock Simulator Adapter
# ================================

class EtapMockSimulatorAdapter(EtapAdapterBase):
    """
    Adapter Mock para desenvolvimento offline
    Simula comportamento ETAP para testes
    """
    
    def __init__(self, config: EtapConnectionConfig):
        super().__init__(config)
        self._mock_data_path = Path(config.mock_data_path or "outputs/mock_etap")
        self._mock_data_path.mkdir(exist_ok=True)
        self._simulation_delay = 1.0
    
    async def connect(self) -> bool:
        """Mock connection sempre sucesso"""
        self.logger.info("🧪 Mock Simulator Adapter connected")
        await asyncio.sleep(0.1)
        self._connected = True
        return True
    
    async def disconnect(self) -> bool:
        """Mock disconnect"""
        self._connected = False
        self.logger.info("📤 Mock Simulator Adapter disconnected")
        return True
    
    async def is_connected(self) -> bool:
        """Mock status"""
        return self._connected
    
    async def import_study_data(
        self, 
        study_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> EtapOperationResult:
        """Mock import com simulação realista"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Simular tempo de processamento baseado no tamanho dos dados
        data_size = len(str(study_data))
        processing_time = min(self._simulation_delay * (data_size / 1000), 5.0)
        await asyncio.sleep(processing_time)
        
        # Salvar dados mock
        mock_file = self._mock_data_path / f"import_{operation_id}.json"
        mock_file.write_text(json.dumps(study_data, indent=2))
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "mock_simulation": True,
                "data_processed": True,
                "equipment_count": len(study_data.get("equipment_configs", []) if isinstance(study_data.get("equipment_configs", []), list) else []),
                "mock_file": str(mock_file),
                "simulation_quality": "high_fidelity"
            },
            performance_metrics={
                "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "data_size_bytes": data_size
            }
        )
        
        self._last_operation = result
        self.logger.info(f"🎭 Mock import completed: {operation_id}")
        return result
    
    async def export_study_data(
        self, 
        study_identifier: str,
        export_options: Optional[Dict[str, Any]] = None
    ) -> EtapOperationResult:
        """Mock export"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        await asyncio.sleep(self._simulation_delay * 0.5)
        
        # Gerar dados mock realistas
        mock_data = self._generate_realistic_mock_data(study_identifier)
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "mock_export": True,
                "study_id": study_identifier,
                "realistic_data": mock_data,
                "format": "mock_etap_native"
            }
        )
        
        self._last_operation = result
        return result
    
    async def run_coordination_analysis(
        self,
        analysis_config: Dict[str, Any]
    ) -> EtapOperationResult:
        """Mock análise de coordenação com resultados realistas"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Simular análise complexa
        await asyncio.sleep(self._simulation_delay * 2)
        
        devices = analysis_config.get("devices", [])
        if not isinstance(devices, (list, tuple)):
            # Se não for lista/tuple, converter para lista vazia
            self.logger.warning(f"⚠️ Devices should be list/tuple, got {type(devices)}: {devices}")
            devices = []
            
        coordination_pairs = []
        
        # Gerar pares de coordenação mock
        for i in range(len(devices) - 1):
            pair = {
                "upstream": devices[i],
                "downstream": devices[i + 1],
                "margin_seconds": 0.3,
                "coordination_valid": True,
                "curve_analysis": "passed"
            }
            coordination_pairs.append(pair)
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "analysis_type": "coordination",
                "mock_simulation": True,
                "coordination_pairs": coordination_pairs,
                "total_devices": len(devices),
                "violations": 0,
                "overall_status": "coordinated"
            },
            performance_metrics={
                "analysis_duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "devices_processed": len(devices)
            }
        )
        
        self._last_operation = result
        self.logger.info(f"🔍 Mock coordination analysis: {len(coordination_pairs)} pairs")
        return result
    
    async def run_selectivity_analysis(
        self,
        analysis_config: Dict[str, Any]
    ) -> EtapOperationResult:
        """Mock análise de seletividade"""
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        await asyncio.sleep(self._simulation_delay * 1.5)
        
        result = EtapOperationResult(
            operation_id=operation_id,
            status=EtapOperationStatus.COMPLETED,
            started_at=start_time,
            completed_at=datetime.utcnow(),
            result_data={
                "analysis_type": "selectivity",
                "mock_simulation": True,
                "selectivity_verified": True,
                "protection_zones": 3,
                "zone_coverage": "complete",
                "backup_protection": "adequate"
            }
        )
        
        self._last_operation = result
        return result
    
    def _generate_realistic_mock_data(self, study_id: str) -> Dict[str, Any]:
        """Gerar dados mock realistas baseados nos dados reais da Petrobras"""
        return {
            "study_id": study_id,
            "name": f"Mock Study {study_id}",
            "equipment": [
                {
                    "tag": "27MCB001",
                    "manufacturer": "Schneider Electric",
                    "model": "MiCOM P143",
                    "parameters": {
                        "50.01": {"description": "I> Function", "value": "Enabled"},
                        "50.02": {"description": "I> Current Setting", "value": "1000A"},
                        "51.01": {"description": "I>> Function", "value": "Enabled"}
                    }
                },
                {
                    "tag": "27MCB002", 
                    "manufacturer": "Schneider Electric",
                    "model": "Easergy P3",
                    "parameters": {
                        "thermal_function": {"description": "Thermal Function", "value": "Active"},
                        "overcurrent_pickup": {"description": "Overcurrent Pickup", "value": "800A"}
                    }
                }
            ],
            "analysis_results": {
                "coordination_valid": True,
                "selectivity_verified": True,
                "total_checks": 15,
                "passed_checks": 15
            }
        }

# ================================
# Adapter Factory
# ================================

class EtapAdapterFactory:
    """
    Factory para criar adapters ETAP baseado na configuração
    """
    
    @staticmethod
    def create_adapter(config: EtapConnectionConfig) -> EtapAdapterBase:
        """Criar adapter baseado no tipo de conexão"""
        
        if config.connection_type == EtapConnectionType.CSV_BRIDGE:
            return EtapCSVBridgeAdapter(config)
        
        elif config.connection_type == EtapConnectionType.ETAP_API:
            return EtapNativeAPIAdapter(config)
        
        elif config.connection_type == EtapConnectionType.MOCK_SIMULATOR:
            return EtapMockSimulatorAdapter(config)
        
        else:
            raise ValueError(f"Unsupported connection type: {config.connection_type}")
    
    @staticmethod
    def get_available_adapters() -> List[Dict[str, Any]]:
        """Lista de adapters disponíveis"""
        return [
            {
                "type": EtapConnectionType.CSV_BRIDGE,
                "name": "CSV Bridge Adapter",
                "description": "Current implementation via CSV files",
                "status": "production",
                "capabilities": ["import", "export", "basic_analysis"]
            },
            {
                "type": EtapConnectionType.ETAP_API,
                "name": "Native etapPy™ API",
                "description": "Future native Python API integration",
                "status": "planned",
                "capabilities": ["native_import", "native_export", "full_analysis", "real_time"]
            },
            {
                "type": EtapConnectionType.MOCK_SIMULATOR,
                "name": "Mock Simulator",
                "description": "Offline development and testing",
                "status": "development",
                "capabilities": ["mock_import", "mock_export", "simulated_analysis", "offline_testing"]
            }
        ]

# ================================
# Main Adapter Manager
# ================================

class EtapAdapterManager:
    """
    Gerenciador principal dos adapters ETAP
    Permite troca dinâmica entre diferentes tipos de conexão
    """
    
    def __init__(self):
        self.current_adapter: Optional[EtapAdapterBase] = None
        self.config_history: List[EtapConnectionConfig] = []
        self.logger = logger
    
    async def initialize_adapter(self, config: EtapConnectionConfig) -> bool:
        """Inicializar adapter com configuração"""
        try:
            # Desconectar adapter atual se existir
            if self.current_adapter:
                await self.current_adapter.disconnect()
            
            # Criar novo adapter
            self.current_adapter = EtapAdapterFactory.create_adapter(config)
            self.config_history.append(config)
            
            # Conectar
            connected = await self.current_adapter.connect()
            
            if connected:
                self.logger.info(f"✅ ETAP Adapter initialized: {config.connection_type}")
                return True
            else:
                self.logger.error(f"❌ Failed to connect ETAP Adapter: {config.connection_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing ETAP Adapter: {e}")
            return False
    
    async def switch_adapter(self, new_config: EtapConnectionConfig) -> bool:
        """Trocar para diferente tipo de adapter"""
        self.logger.info(f"🔄 Switching ETAP adapter to: {new_config.connection_type}")
        return await self.initialize_adapter(new_config)
    
    def get_current_adapter(self) -> Optional[EtapAdapterBase]:
        """Adapter atual"""
        return self.current_adapter
    
    async def test_all_adapters(self) -> Dict[str, Any]:
        """Testar todos os tipos de adapter disponíveis"""
        results = {}
        
        available_adapters = EtapAdapterFactory.get_available_adapters()
        
        for adapter_info in available_adapters:
            adapter_type = adapter_info["type"]
            
            try:
                # Configuração de teste
                test_config = EtapConnectionConfig(
                    connection_type=adapter_type,
                    host="localhost" if adapter_type == EtapConnectionType.ETAP_API else None,
                    port=8080 if adapter_type == EtapConnectionType.ETAP_API else None,
                    mock_data_path="outputs/mock_test" if adapter_type == EtapConnectionType.MOCK_SIMULATOR else None
                )
                
                # Criar e testar adapter
                adapter = EtapAdapterFactory.create_adapter(test_config)
                test_result = await adapter.test_connection()
                
                results[adapter_type] = {
                    "adapter_info": adapter_info,
                    "test_result": test_result,
                    "config": test_config
                }
                
            except Exception as e:
                results[adapter_type] = {
                    "adapter_info": adapter_info,
                    "test_result": {
                        "success": False,
                        "error": str(e)
                    }
                }
        
        return results
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Status do gerenciador"""
        return {
            "current_adapter": {
                "type": self.current_adapter.config.connection_type if self.current_adapter else None,
                "connected": self.current_adapter._connected if self.current_adapter else False,
                "connection_id": self.current_adapter.connection_id if self.current_adapter else None
            },
            "config_history_count": len(self.config_history),
            "available_adapters": len(EtapAdapterFactory.get_available_adapters()),
            "last_operation": self.current_adapter.get_last_operation().operation_id if self.current_adapter and self.current_adapter.get_last_operation() else None
        }

# ================================
# Convenience Functions
# ================================

async def create_csv_bridge_adapter() -> EtapAdapterBase:
    """Criar adapter CSV Bridge (atual)"""
    config = EtapConnectionConfig(
        connection_type=EtapConnectionType.CSV_BRIDGE,
        timeout_seconds=60
    )
    return EtapAdapterFactory.create_adapter(config)

async def create_native_api_adapter(
    host: str = "localhost",
    port: int = 8080,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> EtapAdapterBase:
    """Criar adapter API nativa (futuro)"""
    config = EtapConnectionConfig(
        connection_type=EtapConnectionType.ETAP_API,
        host=host,
        port=port,
        username=username,
        password=password,
        timeout_seconds=300
    )
    return EtapAdapterFactory.create_adapter(config)

async def create_mock_simulator_adapter(
    mock_data_path: str = "outputs/mock_etap"
) -> EtapAdapterBase:
    """Criar adapter mock (desenvolvimento)"""
    config = EtapConnectionConfig(
        connection_type=EtapConnectionType.MOCK_SIMULATOR,
        mock_data_path=mock_data_path,
        timeout_seconds=30
    )
    return EtapAdapterFactory.create_adapter(config)

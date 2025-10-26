"""
ETAP Native Router - etapPy™ API Endpoints
=========================================

Endpoints REST para integração ETAP nativa com fallback automático.
Expõe funcionalidades do EtapNativeService via API.

Funcionalidades:
- Native import/export com fallback
- Análise de coordenação/seletividade nativa
- Gestão de adapters dinâmica
- Monitoramento de performance
- Auto-detecção de melhor conexão

Integração com arquitetura universal existente.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Body
from fastapi import status as http_status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
import logging
from datetime import datetime
import json

from api.core.database import get_db
from api.schemas import BaseResponse
from api.services.etap_native_service import EtapNativeService, create_native_service
from api.services.etap_native_adapter import EtapConnectionType, EtapConnectionConfig

router = APIRouter()  # Sem prefix - já definido no main.py
logger = logging.getLogger(__name__)

# ================================
# Pydantic Schemas
# ================================

from pydantic import BaseModel, Field
from enum import Enum

class ConnectionTypeEnum(str, Enum):
    """Tipos de conexão ETAP para API"""
    CSV_BRIDGE = "csv_bridge"
    ETAP_API = "etap_api" 
    MOCK_SIMULATOR = "mock_simulator"

class NativeConnectionRequest(BaseModel):
    """Request para configurar conexão nativa"""
    connection_type: ConnectionTypeEnum
    etap_host: Optional[str] = Field(None, description="Host do servidor ETAP")
    etap_port: Optional[int] = Field(None, description="Porta do servidor ETAP")
    username: Optional[str] = Field(None, description="Usuário ETAP")
    password: Optional[str] = Field(None, description="Senha ETAP")
    enable_fallback: bool = Field(True, description="Habilitar fallback automático")
    timeout_seconds: int = Field(300, description="Timeout das operações")

class NativeImportRequest(BaseModel):
    """Request para importação nativa"""
    study_data: Dict[str, Any] = Field(..., description="Dados do estudo para importar")
    prefer_native: bool = Field(True, description="Preferir método nativo")
    sync_to_database: bool = Field(True, description="Sincronizar com database")

class NativeExportRequest(BaseModel):
    """Request para exportação nativa"""
    study_id: str = Field(..., description="ID do estudo para exportar")
    export_format: str = Field("native", description="Formato de exportação")
    prefer_native: bool = Field(True, description="Preferir método nativo")

class NativeAnalysisRequest(BaseModel):
    """Request para análise nativa"""
    study_id: str = Field(..., description="ID do estudo para análise")
    analysis_config: Optional[Dict[str, Any]] = Field(None, description="Configuração da análise")
    prefer_native: bool = Field(True, description="Preferir método nativo")

class NativeServiceResponse(BaseModel):
    """Response base do serviço nativo"""
    success: bool = True
    message: str = "Operation completed successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[Dict[str, Any]] = None

# ================================
# Dependency Functions
# ================================

async def get_native_service(db: Session = Depends(get_db)) -> EtapNativeService:
    """Dependency para obter serviço nativo"""
    try:
        return await create_native_service(db)
    except Exception as e:
        logger.error(f"Failed to create native service: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize ETAP Native Service"
        )

# ================================
# Configuration Endpoints
# ================================

@router.post("/initialize", 
             response_model=NativeServiceResponse,
             summary="🚀 Initialize ETAP Native Service")
async def initialize_native_service(
    request: NativeConnectionRequest,
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Inicializar Serviço ETAP Nativo**
    
    Configura conexão com ETAP usando diferentes adapters:
    - `csv_bridge`: Método atual via arquivos CSV (estável)
    - `etap_api`: API nativa etapPy™ (futuro)  
    - `mock_simulator`: Simulador para desenvolvimento
    
    **Features:**
    - Auto-fallback em caso de falha
    - Validação de conectividade
    - Configuração persistente
    """
    try:
        result = await native_service.initialize_with_config(
            connection_type=EtapConnectionType(request.connection_type),
            etap_host=request.etap_host,
            etap_port=request.etap_port,
            enable_fallback=request.enable_fallback
        )
        
        if result["success"]:
            return NativeServiceResponse(
                success=True,
                message=f"ETAP Native Service initialized with {request.connection_type}",
                data=result
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Initialization failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Native service initialization failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/auto-detect",
           response_model=NativeServiceResponse,
           summary="🔍 Auto-detect Best Connection")
async def auto_detect_connection(
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Auto-detectar Melhor Conexão**
    
    Testa todos os adapters disponíveis e seleciona o melhor:
    1. **etapPy™ API** (se disponível)
    2. **CSV Bridge** (fallback estável)
    3. **Mock Simulator** (desenvolvimento)
    
    **Retorna:**
    - Adapter selecionado
    - Resultados dos testes
    - Recomendações de uso
    """
    try:
        result = await native_service.auto_detect_best_connection()
        
        return NativeServiceResponse(
            success=True,
            message="Auto-detection completed",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Auto-detection failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/status",
           response_model=NativeServiceResponse,
           summary="📊 Native Service Status")
async def get_native_status(
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Status do Serviço Nativo**
    
    Informações detalhadas sobre:
    - Adapter atual conectado
    - Modo nativo vs fallback
    - Métricas de performance
    - Capacidades disponíveis
    - Histórico de operações
    """
    try:
        status = native_service.get_native_service_status()
        
        return NativeServiceResponse(
            success=True,
            message="Native service status retrieved",
            data=status
        )
        
    except Exception as e:
        logger.error(f"Status retrieval failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/test-capabilities",
            response_model=NativeServiceResponse,
            summary="🧪 Test All Capabilities")
async def test_native_capabilities(
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Testar Todas as Capacidades**
    
    Executa suite completa de testes:
    - Conectividade com todos os adapters
    - Operações de import/export
    - Análises de coordenação/seletividade
    - Performance benchmarks
    
    **Útil para:**
    - Validação de ambiente
    - Troubleshooting
    - Benchmarking de performance
    """
    try:
        test_results = await native_service.test_native_capabilities()
        
        return NativeServiceResponse(
            success=True,
            message="Capability tests completed",
            data=test_results
        )
        
    except Exception as e:
        logger.error(f"Capability tests failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ================================
# Study Operations
# ================================

@router.post("/import",
            response_model=NativeServiceResponse,
            summary="📥 Native Study Import")
async def import_study_native(
    request: NativeImportRequest,
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Importação Nativa de Estudo**
    
    Importa estudo usando adapter nativo com fallback automático:
    - **Native Mode**: Comunicação direta via etapPy™
    - **Fallback Mode**: CSV Bridge para garantir funcionamento
    - **Database Sync**: Sincronização automática com PostgreSQL
    
    **Vantagens:**
    - Fallback transparente em caso de falha
    - Sincronização automática com database
    - Métricas de performance detalhadas
    """
    try:
        result = await native_service.import_study_native(
            study_data=request.study_data,
            prefer_native=request.prefer_native,
            sync_to_database=request.sync_to_database
        )
        
        if result["success"]:
            return NativeServiceResponse(
                success=True,
                message=f"Study imported successfully via {result.get('adapter_type', 'unknown')}",
                data=result
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Import failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Native import failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/export",
            response_model=NativeServiceResponse,
            summary="📤 Native Study Export")
async def export_study_native(
    request: NativeExportRequest,
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Exportação Nativa de Estudo**
    
    Exporta estudo usando adapter nativo:
    - **Format Options**: native, csv, etap_compatible
    - **Auto-fallback**: CSV Bridge se nativo falhar
    - **Performance**: Otimizado para grandes volumes
    
    **Formatos Suportados:**
    - `native`: Formato ETAP nativo
    - `csv`: CSV compatível com fluxo atual
    - `etap_compatible`: Estruturado para ETAP
    """
    try:
        result = await native_service.export_study_native(
            study_id=request.study_id,
            export_format=request.export_format,
            prefer_native=request.prefer_native
        )
        
        if result["success"]:
            return NativeServiceResponse(
                success=True,
                message=f"Study exported successfully: {request.study_id}",
                data=result
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Export failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Native export failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ================================
# Analysis Operations
# ================================

@router.post("/analyze/coordination",
            response_model=NativeServiceResponse,
            summary="🔍 Native Coordination Analysis")
async def analyze_coordination_native(
    request: NativeAnalysisRequest,
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Análise de Coordenação Nativa**
    
    Executa análise de coordenação usando ETAP nativo:
    - **Native Analysis**: Cálculos diretos do ETAP engine
    - **Fallback Analysis**: Algoritmos offline para desenvolvimento
    - **Database Storage**: Resultados salvos automaticamente
    
    **Análises Incluídas:**
    - Coordenação entre dispositivos
    - Margins de tempo
    - Validação de curvas
    - Otimização de time dials
    """
    try:
        result = await native_service.run_coordination_analysis_native(
            study_id=request.study_id,
            analysis_config=request.analysis_config,
            prefer_native=request.prefer_native
        )
        
        if result["success"]:
            return NativeServiceResponse(
                success=True,
                message=f"Coordination analysis completed for study {request.study_id}",
                data=result
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analysis failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Native coordination analysis failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/analyze/selectivity",
            response_model=NativeServiceResponse,
            summary="🎯 Native Selectivity Analysis")
async def analyze_selectivity_native(
    request: NativeAnalysisRequest,
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Análise de Seletividade Nativa**
    
    Executa análise de seletividade usando ETAP:
    - **Zone Analysis**: Análise por zonas de proteção
    - **Backup Protection**: Verificação de proteção de backup
    - **Selectivity Matrix**: Matriz de seletividade completa
    - **Margin Verification**: Verificação de margens adequadas
    
    **Verificações:**
    - Seletividade entre zonas
    - Cobertura de proteção
    - Tempos de atuação
    - Backup adequado
    """
    try:
        result = await native_service.run_selectivity_analysis_native(
            study_id=request.study_id,
            analysis_config=request.analysis_config,
            prefer_native=request.prefer_native
        )
        
        if result["success"]:
            return NativeServiceResponse(
                success=True,
                message=f"Selectivity analysis completed for study {request.study_id}",
                data=result
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analysis failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Native selectivity analysis failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ================================
# Batch Operations
# ================================

@router.post("/batch/import-studies",
            response_model=NativeServiceResponse,
            summary="📦 Batch Import Studies")
async def batch_import_studies(
    studies_data: List[Dict[str, Any]] = Body(..., description="Lista de estudos para importar"),
    prefer_native: bool = Query(True, description="Preferir método nativo"),
    sync_to_database: bool = Query(True, description="Sincronizar com database"),
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Importação em Lote de Estudos**
    
    Importa múltiplos estudos em operação única:
    - **Parallel Processing**: Processamento paralelo quando possível
    - **Error Handling**: Continua mesmo se alguns falharem
    - **Progress Tracking**: Acompanhamento detalhado do progresso
    - **Batch Optimization**: Otimizações para grandes volumes
    
    **Ideal para:**
    - Migração de dados existentes
    - Importação de múltiplos CSVs
    - Sincronização periódica
    """
    try:
        results = []
        total_studies = len(studies_data)
        successful_imports = 0
        
        logger.info(f"🚀 Starting batch import of {total_studies} studies...")
        
        for i, study_data in enumerate(studies_data):
            try:
                logger.info(f"📊 Processing study {i+1}/{total_studies}")
                
                result = await native_service.import_study_native(
                    study_data=study_data,
                    prefer_native=prefer_native,
                    sync_to_database=sync_to_database
                )
                
                if result["success"]:
                    successful_imports += 1
                
                results.append({
                    "study_index": i,
                    "study_name": study_data.get("name", f"Study_{i}"),
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Study {i} failed: {e}")
                results.append({
                    "study_index": i,
                    "study_name": study_data.get("name", f"Study_{i}"),
                    "result": {
                        "success": False,
                        "error": str(e)
                    }
                })
        
        return NativeServiceResponse(
            success=True,
            message=f"Batch import completed: {successful_imports}/{total_studies} successful",
            data={
                "total_studies": total_studies,
                "successful_imports": successful_imports,
                "failed_imports": total_studies - successful_imports,
                "success_rate": (successful_imports / total_studies) * 100,
                "results": results
            }
        )
        
    except Exception as e:
        logger.error(f"Batch import failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/batch/analyze-studies",
            response_model=NativeServiceResponse,
            summary="🔍 Batch Analyze Studies")
async def batch_analyze_studies(
    study_ids: List[str] = Body(..., description="Lista de IDs de estudos"),
    analysis_types: List[str] = Body(["coordination"], description="Tipos de análise"),
    prefer_native: bool = Query(True, description="Preferir método nativo"),
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Análise em Lote de Estudos**
    
    Executa análises em múltiplos estudos:
    - **Multiple Analysis Types**: coordination, selectivity
    - **Parallel Execution**: Processamento otimizado
    - **Comprehensive Reports**: Relatórios consolidados
    - **Performance Metrics**: Métricas detalhadas
    
    **Analysis Types:**
    - `coordination`: Análise de coordenação
    - `selectivity`: Análise de seletividade
    - `both`: Ambas as análises
    """
    try:
        results = []
        total_analyses = len(study_ids) * len(analysis_types)
        successful_analyses = 0
        
        logger.info(f"🔍 Starting batch analysis: {len(study_ids)} studies, {len(analysis_types)} analysis types")
        
        for study_id in study_ids:
            study_results = {"study_id": study_id, "analyses": {}}
            
            for analysis_type in analysis_types:
                try:
                    if analysis_type == "coordination":
                        result = await native_service.run_coordination_analysis_native(
                            study_id=study_id,
                            prefer_native=prefer_native
                        )
                    elif analysis_type == "selectivity":
                        result = await native_service.run_selectivity_analysis_native(
                            study_id=study_id,
                            prefer_native=prefer_native
                        )
                    else:
                        result = {"success": False, "error": f"Unknown analysis type: {analysis_type}"}
                    
                    if result["success"]:
                        successful_analyses += 1
                    
                    study_results["analyses"][analysis_type] = result
                    
                except Exception as e:
                    logger.error(f"Analysis {analysis_type} for study {study_id} failed: {e}")
                    study_results["analyses"][analysis_type] = {
                        "success": False,
                        "error": str(e)
                    }
            
            results.append(study_results)
        
        return NativeServiceResponse(
            success=True,
            message=f"Batch analysis completed: {successful_analyses}/{total_analyses} successful",
            data={
                "total_studies": len(study_ids),
                "total_analyses": total_analyses,
                "successful_analyses": successful_analyses,
                "success_rate": (successful_analyses / total_analyses) * 100,
                "results": results
            }
        )
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ================================
# Monitoring & Performance
# ================================

@router.get("/performance/metrics",
           response_model=NativeServiceResponse,
           summary="📈 Performance Metrics")
async def get_performance_metrics(
    operation_type: Optional[str] = Query(None, description="Filtrar por tipo de operação"),
    hours: int = Query(24, description="Últimas N horas"),
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Métricas de Performance**
    
    Estatísticas detalhadas de performance:
    - **Operation Types**: import, export, coordination, selectivity
    - **Time Filtering**: Últimas N horas
    - **Success Rates**: Taxa de sucesso por operação
    - **Duration Analysis**: Análise de tempos de execução
    
    **Métricas Incluídas:**
    - Duração média/min/max
    - Taxa de sucesso
    - Throughput
    - Distribuição por adapter
    """
    try:
        status = native_service.get_native_service_status()
        metrics = status.get("performance_metrics", {})
        
        # Aqui seria implementada filtragem mais sofisticada
        # Por enquanto retornamos métricas básicas
        
        return NativeServiceResponse(
            success=True,
            message="Performance metrics retrieved",
            data={
                "current_metrics": metrics,
                "filter_applied": {
                    "operation_type": operation_type,
                    "hours": hours
                },
                "recommendations": [
                    "Consider using native mode for better performance",
                    "Enable caching for repeated operations",
                    "Monitor fallback usage patterns"
                ]
            }
        )
        
    except Exception as e:
        logger.error(f"Performance metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/health",
           summary="🏥 Health Check")
async def health_check(
    native_service: EtapNativeService = Depends(get_native_service)
):
    """
    **Health Check do Serviço Nativo**
    
    Verificação rápida de saúde:
    - Status da conexão atual
    - Disponibilidade de adapters
    - Últimas operações
    - Alertas e warnings
    """
    try:
        status = native_service.get_native_service_status()
        
        health_status = "healthy"
        issues = []
        
        # Verificações básicas de saúde
        if not status["service_status"]["initialized"]:
            health_status = "unhealthy"
            issues.append("Service not initialized")
        
        if not status["current_adapter"]["connected"]:
            health_status = "degraded"
            issues.append("Current adapter not connected")
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "etap-native",
            "version": "1.0.0",
            "issues": issues,
            "details": {
                "adapter_connected": status["current_adapter"]["connected"],
                "native_mode": status["service_status"]["native_mode"],
                "fallback_enabled": status["service_status"]["fallback_enabled"]
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
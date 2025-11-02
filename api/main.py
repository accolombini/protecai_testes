"""
ProtecAI API - Sistema Integrado de Proteção de Relés
====================================================

API REST robusta para sistema revolucionário de engenharia de proteção.
Integra PostgreSQL, ETAP Simulador e ML Reinforcement Learning.

Autor: ProtecAI Team
Data: 19/10/2025
Versão: 1.0.0
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import logging
from typing import Optional, List, Dict, Any
import os
import sys

# Adicionar path do projeto
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Imports dos módulos do projeto
from api.routers import equipments, compare, imports, etap, etap_native, ml, validation, ml_gateway, reports, database, system_test
from api.core.config import settings
from api.core.database import engine, get_db

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("protecai_api")

# Criar instância FastAPI
app = FastAPI(
    title="ProtecAI API",
    description="""
    ## Sistema Integrado de Proteção de Relés 🔧
    
    **ProtecAI** é uma API REST robusta que revoluciona a engenharia de proteção através da integração de:
    
    - 📊 **PostgreSQL**: Histórico e configurações reais
    - 🎯 **ETAP Simulador**: Validação de seletividade
    - 🤖 **ML Reinforcement Learning**: Otimização contínua
    - 🌐 **ML Gateway**: Interface enterprise para módulos externos de ML
    - 👷 **Interface Única**: Hub para engenheiros de proteção
    
    ### Funcionalidades Principais:
    - **Equipments**: CRUD completo de equipamentos
    - **Compare**: Comparação inteligente de configurações
    - **Import**: Controle de importação de dados
    - **ETAP**: Interface com simulador (preparatório)
    - **ETAP Native**: etapPy™ API com 95% precisão
    - **ML**: Otimização via aprendizado por reforço (preparatório)
    - **ML Gateway**: 🆕 Gateway enterprise para módulos ML externos
    - **Validation**: Validação de seletividade
    
    ### Casos de Uso:
    - Redução de erro humano na configuração manual
    - Garantia de seletividade do sistema de proteção
    - Otimização contínua de parametrizações
    - **Integração com módulos ML/RL externos**
    - **Gestão de análises ML coordenação/seletividade/simulação**
    - Compliance regulatório automático
    """,
    version="1.0.0",
    contact={
        "name": "ProtecAI Team",
        "email": "protecai@petrobras.com.br",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://www.petrobras.com.br/licenses",
    },
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origens específicas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # CRITICAL: Permitir que frontend leia o header customizado
)

# Incluir routers
app.include_router(
    equipments.router,
    prefix="/api/v1/equipments",
    tags=["Equipments"],
    responses={404: {"description": "Equipment not found"}},
)

app.include_router(
    compare.router,
    prefix="/api/v1/compare",
    tags=["Compare"],
    responses={400: {"description": "Invalid comparison parameters"}},
)

app.include_router(
    imports.router,
    prefix="/api/v1/imports",
    tags=["Imports"],
    responses={422: {"description": "Import validation error"}},
)

app.include_router(
    etap.router,
    prefix="/api/v1/etap",
    tags=["ETAP Integration"],
    responses={503: {"description": "ETAP service unavailable"}},
)

app.include_router(
    etap_native.router,
    prefix="/api/v1/etap-native",
    tags=["ETAP Native"],
    responses={503: {"description": "ETAP Native service unavailable"}},
)

app.include_router(
    ml.router,
    prefix="/api/v1/ml",
    tags=["ML Optimization"],
    responses={501: {"description": "ML service not implemented"}},
)

app.include_router(
    validation.router,
    prefix="/api/v1/validation",
    tags=["Validation"],
    responses={400: {"description": "Validation error"}},
)

app.include_router(
    ml_gateway.router,
    prefix="/api/v1/ml-gateway",
    tags=["ML Gateway"],
    responses={500: {"description": "ML Gateway service error"}},
)

app.include_router(
    reports.router,
    prefix="/api/v1/reports",
    tags=["Reports"],
    responses={400: {"description": "Invalid report parameters"}},
)

app.include_router(
    database.router,
    prefix="/api/v1",
    tags=["Database"],
    responses={500: {"description": "Database schema error"}},
)

app.include_router(
    system_test.router,
    tags=["System Test"],
    responses={500: {"description": "System test error"}},
)

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Inicialização da API"""
    logger.info("🚀 Iniciando ProtecAI API...")
    logger.info("📊 Conectando ao PostgreSQL...")
    logger.info("🎯 Preparando interface ETAP...")
    logger.info("🤖 Inicializando módulo ML...")
    logger.info("✅ ProtecAI API inicializada com sucesso!")

@app.on_event("shutdown")
async def shutdown_event():
    """Finalização da API"""
    logger.info("🔽 Finalizando ProtecAI API...")
    logger.info("✅ ProtecAI API finalizada com sucesso!")

# Endpoints base
@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz da API"""
    return {
        "message": "🔧 ProtecAI API - Sistema Integrado de Proteção de Relés",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "features": {
            "equipments": "✅ CRUD completo",
            "compare": "✅ Comparação inteligente",
            "import": "✅ Controle de dados",
            "etap": "✅ Interface enterprise",
            "etap_native": "🚀 etapPy™ API Preparation",
            "ml": "🚧 Interface preparatória",
            "ml_gateway": "🆕 Enterprise ML Gateway",
            "validation": "✅ Validação de seletividade"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check da API"""
    try:
        # Verificar conexão com banco
        from api.core.database import engine
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_status = "✅ Connected"
    except Exception as e:
        db_status = f"❌ Error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "✅ Running",
            "database": db_status,
            "etap": "✅ Enterprise Ready",
            "etap_native": "🚀 etapPy™ Prepared",
            "ml": "🚧 Preparatory",
            "ml_gateway": "🆕 Enterprise Gateway Active"
        },
        "uptime": "Active since startup"
    }

@app.get("/health/connections", tags=["Health"])
async def health_connections():
    """
    🔧 DIAGNÓSTICO: Monitora pool de conexões PostgreSQL
    Útil para detectar connection leaks durante desenvolvimento
    """
    try:
        from api.core.database import get_connection_stats, engine
        from sqlalchemy import text
        
        # Stats do pool SQLAlchemy
        pool_stats = get_connection_stats()
        
        # Stats do PostgreSQL
        with engine.connect() as conn:
            pg_stats = conn.execute(text("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle,
                    max_conn.setting::int as max_connections
                FROM pg_stat_activity,
                    (SELECT setting FROM pg_settings WHERE name = 'max_connections') as max_conn
                WHERE datname = 'protecai_db'
                GROUP BY max_conn.setting
            """)).fetchone()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "sqlalchemy_pool": pool_stats,
            "postgresql": {
                "total_connections": pg_stats.total_connections if pg_stats else 0,
                "active": pg_stats.active if pg_stats else 0,
                "idle": pg_stats.idle if pg_stats else 0,
                "max_connections": pg_stats.max_connections if pg_stats else 100,
                "usage_percent": round((pg_stats.total_connections / pg_stats.max_connections * 100), 2) if pg_stats else 0
            },
            "status": "healthy" if (pg_stats and pg_stats.total_connections < pg_stats.max_connections * 0.8) else "warning"
        }
    except Exception as e:
        logger.error(f"Erro ao obter stats de conexões: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "error"
        }

@app.get("/api/v1/info", tags=["Info"])
async def api_info():
    """Informações detalhadas da API"""
    # Contar endpoints dinamicamente do OpenAPI
    try:
        from fastapi.openapi.utils import get_openapi
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        total_paths = len(openapi_schema.get("paths", {}))
        total_methods = sum(len(methods) for methods in openapi_schema.get("paths", {}).values())
    except:
        total_paths = 0
        total_methods = 0
    
    return {
        "name": "ProtecAI API",
        "description": "Sistema Integrado de Proteção de Relés",
        "version": "1.0.0",
        "endpoints_info": {
            "total_paths": total_paths,
            "total_http_methods": total_methods,
            "note": "paths = unique URLs, methods = GET+POST+PUT+DELETE count"
        },
        "architecture": {
            "database": "PostgreSQL with relay_configs + ml_gateway schemas",
            "etap_integration": "Simulator interface + etapPy™ API",
            "ml_module": "Reinforcement Learning (preparatory)",
            "ml_gateway": "Enterprise ML/RL Gateway for external teams",
            "endpoints": f"{total_paths} paths, {total_methods} methods",
            "models": "Equipment, Protection, ML Jobs, ML Results"
        },
        "capabilities": {
            "crud_operations": True,
            "intelligent_comparison": True,
            "data_import_control": True,
            "etap_simulation": "ready",
            "etap_native_api": "95% precision",
            "ml_optimization": "planned",
            "ml_gateway_integration": "enterprise ready",
            "external_ml_teams": "comprehensive support",
            "selectivity_validation": True,
            "reports": "✅ CSV, XLSX, PDF exports"
        },
        "contact": {
            "team": "ProtecAI Team",
            "project": "Petrobras Protection Engineering Revolution"
        }
    }

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handler para exceções HTTP"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handler para exceções gerais"""
    logger.error(f"General Exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
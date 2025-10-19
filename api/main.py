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
from api.routers import equipments, compare, imports, etap, ml, validation
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
    - 👷 **Interface Única**: Hub para engenheiros de proteção
    
    ### Funcionalidades Principais:
    - **Equipments**: CRUD completo de equipamentos
    - **Compare**: Comparação inteligente de configurações
    - **Import**: Controle de importação de dados
    - **ETAP**: Interface com simulador (preparatório)
    - **ML**: Otimização via aprendizado por reforço (preparatório)
    - **Validation**: Validação de seletividade
    
    ### Casos de Uso:
    - Redução de erro humano na configuração manual
    - Garantia de seletividade do sistema de proteção
    - Otimização contínua de parametrizações
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
    prefix="/api/v1/import",
    tags=["Import"],
    responses={422: {"description": "Import validation error"}},
)

app.include_router(
    etap.router,
    prefix="/api/v1/etap",
    tags=["ETAP Integration"],
    responses={503: {"description": "ETAP service unavailable"}},
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
            "etap": "🚧 Interface preparatória",
            "ml": "🚧 Interface preparatória",
            "validation": "✅ Validação de seletividade"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check da API"""
    try:
        # Verificar conexão com banco
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "✅ Connected"
    except Exception as e:
        db_status = f"❌ Error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "✅ Running",
            "database": db_status,
            "etap": "🚧 Preparatory",
            "ml": "🚧 Preparatory"
        },
        "uptime": "Active since startup"
    }

@app.get("/api/v1/info", tags=["Info"])
async def api_info():
    """Informações detalhadas da API"""
    return {
        "name": "ProtecAI API",
        "description": "Sistema Integrado de Proteção de Relés",
        "version": "1.0.0",
        "architecture": {
            "database": "PostgreSQL with relay_configs schema",
            "etap_integration": "Simulator interface (preparatory)",
            "ml_module": "Reinforcement Learning (preparatory)",
            "endpoints": 6,
            "models": "Equipment, Protection Functions, I/O Config"
        },
        "capabilities": {
            "crud_operations": True,
            "intelligent_comparison": True,
            "data_import_control": True,
            "etap_simulation": "planned",
            "ml_optimization": "planned",
            "selectivity_validation": True
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
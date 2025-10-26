"""
Router de Importação - Controle de Dados REAL PostgreSQL
======================================================

Endpoints para controle inteligente de importação de dados.
100% REAL - Zero Mocks - PostgreSQL Integration Complete.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from api.core.database import get_db
from api.services.import_service import ImportService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/statistics")
async def get_import_statistics(db: Session = Depends(get_db)):
    """
    📊 **Estatísticas de Importação REAL**
    
    Retorna estatísticas reais do PostgreSQL + FileRegistry.
    100% dados reais, zero mocks.
    """
    try:
        service = ImportService(db)
        stats = service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting import statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving import statistics: {str(e)}"
        )

@router.get("/history")
async def get_import_history(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db)
):
    """
    📚 **Histórico de Importações REAL**
    
    Retorna histórico real das importações.
    Integra PostgreSQL + FileRegistry para dados completos.
    
    - **page**: Página (começa em 1)
    - **size**: Registros por página (max 100)
    """
    try:
        service = ImportService(db)
        history = await service.get_import_history(page=page, size=size)
        return history
    except Exception as e:
        logger.error(f"Error getting import history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving import history: {str(e)}"
        )

@router.get("/details/{import_id}")
async def get_import_details(
    import_id: str,
    db: Session = Depends(get_db)
):
    """
    🔍 **Detalhes de Importação REAL**
    
    Retorna detalhes completos de uma importação específica.
    Dados reais do PostgreSQL + arquivos + registry.
    """
    try:
        service = ImportService(db)
        details = await service.get_import_details(import_id)
        return details
    except Exception as e:
        logger.error(f"Error getting import details for {import_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving import details: {str(e)}"
        )

@router.post("/reprocess/{import_id}")
async def reprocess_import(
    import_id: str,
    force_reprocess: bool = False,
    db: Session = Depends(get_db)
):
    """
    🔄 **Reprocessar Importação REAL**
    
    Reprocessa uma importação existente com pipeline real.
    Execução real do pipeline, geração de novo import_id.
    """
    try:
        service = ImportService(db)
        options = {"force_reprocess": force_reprocess}
        result = await service.reprocess_import(import_id, options)
        return result
    except Exception as e:
        logger.error(f"Error reprocessing import {import_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reprocessing import: {str(e)}"
        )

@router.delete("/delete/{import_id}")
async def delete_import(
    import_id: str,
    force_delete: bool = False,
    db: Session = Depends(get_db)
):
    """
    🗑️ **Deletar Importação REAL**
    
    Remove importação com limpeza multi-camada real.
    PostgreSQL + arquivos + registry cleanup.
    """
    try:
        service = ImportService(db)
        result = await service.delete_import(import_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting import {import_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting import: {str(e)}"
        )

# Endpoints originais mantidos para compatibilidade
@router.post("/upload")
async def upload_and_import(
    file: UploadFile = File(...),
    force_reimport: bool = False,
    db: Session = Depends(get_db)
):
    """
    📤 **Upload e Importação**
    
    Faz upload de arquivo e importa automaticamente.
    """
    try:
        service = ImportService(db)
        result = await service.upload_and_import(file, force_reimport)
        return result
    except Exception as e:
        logger.error(f"Error uploading and importing file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during file upload and import"
        )

@router.get("/status")
async def get_import_status(db: Session = Depends(get_db)):
    """
    📊 **Status de Importações**
    
    Retorna status de todas as importações recentes.
    """
    try:
        service = ImportService(db)
        status_list = await service.get_import_status()
        return status_list
    except Exception as e:
        logger.error(f"Error getting import status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving import status"
        )

@router.get("/status/{job_id}")
async def get_import_status_by_id(job_id: str, db: Session = Depends(get_db)):
    """
    📊 **Status de Importação Específica**
    
    Retorna status de uma importação específica.
    """
    try:
        service = ImportService(db)
        status_info = await service.get_import_status(job_id)
        return status_info
    except Exception as e:
        logger.error(f"Error getting import status for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving import status for job {job_id}"
        )
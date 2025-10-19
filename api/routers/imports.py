"""
Router de Importação - Controle de Dados
========================================

Endpoints para controle inteligente de importação de dados.
Integra com file_registry_manager.py existente.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from api.core.database import get_db
from api.schemas import ImportRequest, ImportResponse, BaseResponse
from api.services.import_service import ImportService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ImportResponse)
async def import_data(
    import_request: ImportRequest,
    db: Session = Depends(get_db)
):
    """
    📥 **Importar Dados**
    
    Importa dados de configuração de relés de diversos formatos.
    
    **Formatos Suportados:**
    - PDF: Relatórios de configuração
    - CSV: Dados estruturados
    - XLSX: Planilhas Excel
    - TXT: Dados em texto
    
    **Funcionalidades:**
    - Detecção automática de arquivos já processados
    - Controle de duplicação via registry
    - Validação de formato e conteúdo
    - Integração com pipeline existente
    """
    try:
        service = ImportService(db)
        result = await service.import_file(import_request)
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error importing data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during data import"
        )

@router.post("/upload", response_model=ImportResponse)
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

@router.get("/status", response_model=List[dict])
async def get_import_status(
    db: Session = Depends(get_db)
):
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
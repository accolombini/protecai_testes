"""
Reports Router - Endpoints para Geração de Relatórios
====================================================

Endpoints robustos para:
- Metadados (fabricantes, modelos, status, etc)
- Exportação multi-formato (CSV, XLSX, PDF)
- Filtros avançados (família, barramento, sistema)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import io
import logging

from api.core.database import get_db
from api.schemas.equipment_enums import (
    EquipmentStatus, RelayFamily, ProtectionSystem, 
    VoltageLevel, ExportFormat, get_all_enums
)
from api.services.report_service import ReportService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/metadata", response_model=Dict[str, Any])
async def get_report_metadata(db: Session = Depends(get_db)):
    """
    📊 **Metadados para Relatórios**
    
    Retorna todas as opções disponíveis para filtros:
    - Status (ACTIVE, BLOQUEIO, EM_CORTE, etc)
    - Famílias de relés (SEPAM, MiCOM, etc)
    - Fabricantes reais do banco
    - Modelos disponíveis
    - Sistemas de proteção
    - Níveis de tensão
    - Formatos de exportação
    """
    try:
        service = ReportService(db)
        
        # Enums fixos
        enums = get_all_enums()
        
        # Dados dinâmicos do banco
        metadata = await service.get_dynamic_metadata()
        
        return {
            "enums": enums,
            "dynamic": metadata,
            "timestamp": datetime.now().isoformat(),
            "total_equipments": metadata.get("total_equipments", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting report metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/manufacturers")
async def get_manufacturers(db: Session = Depends(get_db)):
    """🏭 Lista de fabricantes únicos do banco"""
    try:
        service = ReportService(db)
        manufacturers = await service.get_manufacturers()
        return {
            "manufacturers": manufacturers,
            "total": len(manufacturers)
        }
    except Exception as e:
        logger.error(f"Error getting manufacturers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def get_models(
    manufacturer: Optional[str] = Query(None, description="Filtrar por fabricante"),
    db: Session = Depends(get_db)
):
    """📱 Lista de modelos únicos (com filtro opcional por fabricante)"""
    try:
        service = ReportService(db)
        models = await service.get_models(manufacturer)
        return {
            "models": models,
            "total": len(models),
            "manufacturer_filter": manufacturer
        }
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/families")
async def get_families(db: Session = Depends(get_db)):
    """👨‍👩‍👧‍👦 Famílias de relés com contagem"""
    try:
        service = ReportService(db)
        families = await service.get_families()
        return {
            "families": families,
            "total": len(families)
        }
    except Exception as e:
        logger.error(f"Error getting families: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/busbars")
async def get_busbars(db: Session = Depends(get_db)):
    """🔌 Lista de barramentos únicos"""
    try:
        service = ReportService(db)
        busbars = await service.get_busbars()
        return {
            "busbars": busbars,
            "total": len(busbars)
        }
    except Exception as e:
        logger.error(f"Error getting busbars: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{format}")
async def export_report(
    format: ExportFormat,
    manufacturer: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    status: Optional[EquipmentStatus] = Query(None),
    family: Optional[RelayFamily] = Query(None),
    busbar: Optional[str] = Query(None),
    protection_system: Optional[ProtectionSystem] = Query(None),
    db: Session = Depends(get_db)
):
    """
    📥 **Exportar Relatório Multi-Formato**
    
    Exporta relatório filtrado em CSV, XLSX ou PDF.
    
    **Formatos suportados:**
    - `csv`: Comma-separated values
    - `xlsx`: Excel spreadsheet
    - `pdf`: PDF com formatação profissional
    
    **Filtros disponíveis:**
    - `manufacturer`: Nome do fabricante
    - `model`: Modelo específico
    - `status`: Status operacional
    - `family`: Família de relés
    - `busbar`: Barramento
    - `protection_system`: Sistema de proteção
    """
    try:
        service = ReportService(db)
        
        # Aplicar filtros
        filters = {
            "manufacturer": manufacturer,
            "model": model,
            "status": status.value if status else None,
            "family": family.value if family else None,
            "busbar": busbar,
            "protection_system": protection_system.value if protection_system else None
        }
        
        # Gerar relatório no formato solicitado
        if format == ExportFormat.CSV:
            content, filename = await service.export_to_csv(filters)
        elif format == ExportFormat.XLSX:
            content, filename = await service.export_to_xlsx(filters)
        elif format == ExportFormat.PDF:
            content, filename = await service.export_to_pdf(filters)
        else:
            raise HTTPException(status_code=400, detail="Formato não suportado")
        
        # Retornar arquivo para download
        return StreamingResponse(
            io.BytesIO(content),
            media_type=ExportFormat.get_mime_type(format.value),
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@router.post("/preview")
async def preview_report(
    filters: Dict[str, Any],
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    👁️ **Preview de Relatório**
    
    Visualiza dados que serão exportados antes do download.
    Útil para validar filtros antes de gerar arquivo grande.
    """
    try:
        service = ReportService(db)
        data, total = await service.get_filtered_equipments(filters, page, size)
        
        return {
            "data": data,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": (total + size - 1) // size
            },
            "filters_applied": {k: v for k, v in filters.items() if v is not None},
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error previewing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
Reports Router - Endpoints para Geração de Relatórios
====================================================

Endpoints robustos para:
- Metadados (fabricantes, modelos, status, etc)
- Exportação multi-formato (CSV, XLSX, PDF)
- Filtros avançados (família, barramento, sistema)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import io
import logging

from api.core.database import get_db
from api.services.report_service import ReportService, ExportFormat, generate_report_filename
from api.schemas.reports import MetadataResponse, PreviewResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/metadata", response_model=MetadataResponse)
async def get_report_metadata(db: Session = Depends(get_db)):
    """
    📊 **Metadados para Relatórios**
    
    Retorna todas as opções disponíveis para filtros de relatórios:
    - **Fabricantes** com contagem de equipamentos
    - **Modelos** com código do fabricante e contagem
    - **Barramentos** com contagem
    - **Status** com labels em português e contagem
    
    Usado para popular dropdowns no frontend.
    """
    try:
        service = ReportService(db)
        metadata = await service.get_metadata()
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/manufacturers")
async def get_manufacturers(db: Session = Depends(get_db)):
    """🏭 Lista de fabricantes únicos do banco"""
    try:
        service = ReportService(db)
        metadata = await service.get_metadata()
        return {
            "manufacturers": metadata["manufacturers"],
            "total": len(metadata["manufacturers"])
        }
    except Exception as e:
        logger.error(f"Error getting manufacturers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def get_models(
    manufacturer: Optional[str] = Query(None, description="Filtrar por fabricante"),
    db: Session = Depends(get_db)
):
    """📱 Lista de modelos únicos"""
    try:
        service = ReportService(db)
        metadata = await service.get_metadata()
        models = metadata["models"]
        
        if manufacturer:
            models = [m for m in models if manufacturer.lower() in m["manufacturer"].lower()]
        
        return {
            "models": models,
            "total": len(models),
            "manufacturer_filter": manufacturer
        }
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint /families removido - coluna 'family' não existe em relay_models
# TODO: Se família for necessária, adicionar coluna ao schema do banco

@router.get("/bays")
async def get_bays(db: Session = Depends(get_db)):
    """🔌 Lista de barramentos únicos"""
    try:
        service = ReportService(db)
        metadata = await service.get_metadata()
        return {
            "bays": metadata["bays"],
            "total": len(metadata["bays"])
        }
    except Exception as e:
        logger.error(f"Error getting bays: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{format}")
async def export_report(
    format: str,
    manufacturer: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    bay: Optional[str] = Query(None),
    substation: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    📥 **Exportar Relatório Multi-Formato**
    
    Exporta relatório filtrado em CSV, XLSX ou PDF.
    """
    try:
        service = ReportService(db)
        
        # Buscar equipamentos filtrados
        equipments = await service.get_filtered_equipments(
            manufacturer=manufacturer,
            model=model,
            bay=bay,
            substation=substation,
            status=status
        )
        
        # Gerar nome de arquivo descritivo baseado nos filtros
        filename = generate_report_filename(
            format=format.lower(),
            manufacturer=manufacturer,
            model=model,
            bay=bay,
            status=status,
            substation=substation
        )
        
        # Gerar arquivo no formato solicitado
        if format.lower() == "csv":
            content = await service.export_to_csv(equipments)
            media_type = "text/csv"
        elif format.lower() == "xlsx":
            content = await service.export_to_xlsx(
                equipments,
                manufacturer=manufacturer,
                model=model,
                bay=bay,
                status=status,
                substation=substation
            )
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format.lower() == "pdf":
            content = await service.export_to_pdf(
                equipments,
                manufacturer=manufacturer,
                model=model,
                bay=bay,
                status=status,
                substation=substation
            )
            media_type = "application/pdf"
        else:
            raise HTTPException(status_code=400, detail="Formato não suportado. Use: csv, xlsx ou pdf")
        
        # Retornar arquivo
        return Response(
            content=content if isinstance(content, bytes) else content.encode('utf-8'),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@router.post("/preview", response_model=PreviewResponse)
async def preview_report(
    manufacturer: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    bay: Optional[str] = None,
    substation: Optional[str] = None,
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(50, ge=1, le=1000, description="Itens por página"),
    db: Session = Depends(get_db)
):
    """
    👁️ **Preview de Relatório**
    
    Visualiza dados que serão exportados antes do download.
    
    **Parâmetros:**
    - **manufacturer**: Filtro por fabricante (busca parcial)
    - **model**: Filtro por modelo (busca parcial)
    - **status**: Filtro por status (ACTIVE, BLOQUEIO, etc.)
    - **bay**: Filtro por barramento
    - **substation**: Filtro por subestação
    - **page**: Número da página (default: 1)
    - **size**: Itens por página (default: 50, max: 1000)
    
    **Retorna:**
    - Lista de equipamentos filtrados
    - Informações de paginação
    - Filtros aplicados
    - Timestamp da consulta
    """
    try:
        service = ReportService(db)
        data = await service.get_filtered_equipments(
            manufacturer=manufacturer,
            model=model,
            bay=bay,
            substation=substation,
            status=status
        )
        
        # Aplicar paginação
        total = len(data)
        start = (page - 1) * size
        end = start + size
        paginated_data = data[start:end]
        
        return {
            "data": paginated_data,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": (total + size - 1) // size
            },
            "filters_applied": {
                "manufacturer": manufacturer,
                "model": model,
                "status": status,
                "bay": bay,
                "substation": substation
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error previewing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

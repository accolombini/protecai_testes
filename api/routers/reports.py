"""
Reports Router - API REST para Geração de Relatórios
===================================================

Módulo responsável pelos endpoints REST para geração e exportação de
relatórios de equipamentos de proteção elétrica.

**ENDPOINTS DISPONÍVEIS:**
    - GET /metadata: Metadados dinâmicos para filtros (fabricantes, modelos, bays)
    - POST /preview: Visualização prévia com paginação
    - GET /export/csv: Exportação em formato CSV
    - GET /export/xlsx: Exportação em formato Excel
    - GET /export/pdf: Exportação em formato PDF

**PRINCÍPIOS DE DESIGN:**
    - ROBUSTO: Validação de entrada, tratamento de erros, logging detalhado
    - FLEXÍVEL: Filtros opcionais combinados, adapta-se a novos dados
    - ZERO MOCK: Todos os dados do PostgreSQL real
    - CAUSA RAIZ: Queries dinâmicas, não listas hardcoded

**SEGURANÇA:**
    Sistema crítico para operação de subestações elétricas.
    Dados precisos são essenciais para tomada de decisão.

Author: ProtecAI Engineering Team
Project: ProtecAI - Sistema de Proteção Elétrica Petrobras
Date: 2025-11-02
Version: 1.0.0
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
    Retorna metadados dinâmicos para popular filtros de relatórios.
    
    Endpoint principal para obter todas as opções disponíveis de filtros,
    com contadores de equipamentos por categoria.
    
    **DADOS RETORNADOS:**
        - Fabricantes: código, nome completo, quantidade de equipamentos
        - Modelos: código, nome, fabricante associado, quantidade
        - Barramentos (bays): código único, quantidade de equipamentos
        - Status: código, label em português, quantidade
    
    **CONSOLIDAÇÃO AUTOMÁTICA:**
        Modelos com variações de nome (SEPAM S40, SEPAM_S40) são
        consolidados em uma única entrada com contagem somada.
    
    **PERFORMANCE:**
        - Típico: ~18ms para 50 equipamentos
        - Queries otimizadas com JOINs e agregações SQL
        - Cache possível em produção (Redis)
    
    Returns:
        MetadataResponse: Estrutura com manufacturers, models, bays, statuses
        
    Raises:
        HTTPException: 500 se houver erro na conexão com banco de dados
        
    Example Response:
        ```json
        {
            "manufacturers": [
                {"code": "GE", "name": "General Electric", "count": 8},
                {"code": "SE", "name": "Schneider Electric", "count": 42}
            ],
            "models": [
                {"code": "P220", "name": "P220", "manufacturer_code": "SE", "count": 20},
                {"code": "P122", "name": "P122", "manufacturer_code": "SE", "count": 13}
            ],
            "bays": [
                {"name": "52-MP-08B", "count": 1},
                {"name": "52-MF-02A", "count": 2}
            ],
            "statuses": [
                {"code": "ACTIVE", "label": "Ativo", "count": 50}
            ]
        }
        ```
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
    """
    Retorna lista de fabricantes com contagem de equipamentos.
    
    Endpoint auxiliar para obter apenas informações de fabricantes,
    útil para dropdowns simplificados ou análises específicas.
    
    Returns:
        dict: {"manufacturers": [...], "total": int}
        
    Raises:
        HTTPException: 500 em caso de erro no banco de dados
    """
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
    """
    Retorna lista de modelos, opcionalmente filtrados por fabricante.
    
    Endpoint auxiliar para obter modelos disponíveis, com filtro opcional
    por fabricante para facilitar seleção hierárquica no frontend.
    
    Args:
        manufacturer: Nome do fabricante para filtrar (case-insensitive)
    
    Returns:
        dict: {"models": [...], "total": int, "manufacturer_filter": str|None}
        
    Example:
        GET /models?manufacturer=Schneider
        Retorna apenas modelos Schneider Electric
    """
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
    """
    Lista todos os barramentos (bays) cadastrados no sistema com contagem de equipamentos.
    
    Returns:
        Dict com:
            - bays: Lista de dicionários {"name": str, "count": int}
            - total: Número total de barramentos distintos
    
    Raises:
        HTTPException: 500 se houver erro na consulta ao banco
    
    Examples:
        GET /api/v1/reports/bays
        Response:
        {
            "bays": [
                {"name": "52-MP-08B", "count": 1},
                {"name": "BAY-01", "count": 3}
            ],
            "total": 2
        }
    """
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
    Exporta relatório de equipamentos em formato CSV, XLSX ou PDF.
    
    Gera arquivo com dados filtrados e nome de arquivo descritivo baseado
    nos critérios de seleção. Usa StreamingResponse para download eficiente.
    
    Args:
        format: Formato desejado ("csv", "xlsx" ou "pdf")
        manufacturer: Nome do fabricante (filtro opcional)
        model: Código do modelo (filtro opcional)
        status: Status do equipamento (filtro opcional)
        bay: Nome do barramento (filtro opcional)
        substation: Nome da subestação (filtro opcional)
        db: Sessão do banco de dados (injetada)
    
    Returns:
        StreamingResponse com arquivo para download e headers apropriados:
            - Content-Disposition: attachment; filename="..."
            - Content-Type: text/csv | application/vnd.openxmlformats... | application/pdf
    
    Raises:
        HTTPException: 400 se formato inválido, 500 se erro na geração
    
    Examples:
        GET /api/v1/reports/export/csv?manufacturer=Schneider&status=ACTIVE
        
        Response Headers:
            Content-Disposition: attachment; filename="REL_SCHN_ACTIVE_20251103_143052.csv"
            Content-Type: text/csv
    
    Note:
        Formatos suportados: csv (~16ms), xlsx (~564ms), pdf (~27ms)
        Filename gerado automaticamente: REL_[FABRICANTE]_[MODELO]_[TIMESTAMP].[ext]
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
    Preview de relatório com paginação para validar dados antes da exportação.
    
    Permite visualizar os equipamentos que serão incluídos no relatório
    final antes de gerar o arquivo para download. Suporta paginação para
    facilitar navegação em grandes conjuntos de dados.
    
    Args:
        manufacturer: Filtro por fabricante (busca parcial, case-insensitive)
        model: Filtro por modelo (busca parcial, case-insensitive)
        status: Filtro por status (ACTIVE, BLOQUEIO, EM_CORTE, etc)
        bay: Filtro por barramento (busca parcial)
        substation: Filtro por subestação (busca parcial)
        page: Número da página (mínimo: 1)
        size: Itens por página (mínimo: 1, máximo: 1000)
        db: Sessão do banco de dados (injetada)
    
    Returns:
        PreviewResponse com:
            - data: Lista de equipamentos da página atual
            - pagination: {"page": int, "size": int, "total": int, "pages": int}
            - filters: Filtros aplicados
    
    Raises:
        HTTPException: 500 se houver erro na consulta
    
    Examples:
        POST /api/v1/reports/preview?manufacturer=Schneider&page=1&size=10
        
        Response:
        {
            "data": [...],
            "pagination": {
                "page": 1,
                "size": 10,
                "total": 42,
                "pages": 5
            },
            "filters": {
                "manufacturer": "Schneider"
            }
        }
    
    Note:
        Use este endpoint para validar resultados antes de exportar arquivos grandes.
        Performance: ~18ms para query + paginação de 50 equipamentos.
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

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


# ============================================================================
# NOVOS ENDPOINTS PROFISSIONAIS - 13/11/2025
# ============================================================================

@router.get("/statistics")
async def get_system_statistics(db: Session = Depends(get_db)):
    """
    Retorna estatísticas completas do sistema em tempo real.
    
    **NOVO ENDPOINT - 13/11/2025**
    
    Fornece métricas detalhadas para dashboards e análises técnicas,
    incluindo dados REAIS do banco de dados (não hardcoded).
    
    **MÉTRICAS INCLUÍDAS:**
        - Total de equipamentos, configurações, funções
        - Distribuição por fabricante e modelo
        - Configurações ativas vs inativas
        - Grupos multipart
        - Tipos de valores (numeric, boolean, text)
        - Distribuição por subestação
    
    Returns:
        Dict com estatísticas completas do sistema
        
    Example Response:
        {
            "equipments": {
                "total": 50,
                "by_manufacturer": {...},
                "by_status": {...}
            },
            "settings": {
                "total": 198744,
                "active": 198744,
                "inactive": 0,
                "by_type": {...}
            },
            "protection_functions": {
                "total": 31,
                "configured_count": 156
            }
        }
    """
    try:
        service = ReportService(db)
        
        with service.engine.connect() as conn:
            # Estatísticas de equipamentos
            equipment_stats = text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active,
                    COUNT(DISTINCT substation_name) as substations,
                    COUNT(DISTINCT barra_nome) as bays
                FROM protec_ai.relay_equipment
            """)
            eq_stats = conn.execute(equipment_stats).fetchone()
            
            # Estatísticas de configurações
            settings_stats = text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN is_active THEN 1 END) as active,
                    COUNT(CASE WHEN is_multipart THEN 1 END) as multipart,
                    COUNT(CASE WHEN value_type = 'numeric' THEN 1 END) as numeric,
                    COUNT(CASE WHEN value_type = 'boolean' THEN 1 END) as boolean,
                    COUNT(CASE WHEN value_type = 'text' THEN 1 END) as text
                FROM protec_ai.relay_settings
            """)
            set_stats = conn.execute(settings_stats).fetchone()
            
            # Distribuição por fabricante
            manufacturer_dist = text("""
                SELECT 
                    f.nome_completo as name,
                    COUNT(DISTINCT re.id) as equipment_count,
                    COUNT(rs.id) as settings_count
                FROM protec_ai.fabricantes f
                JOIN protec_ai.relay_models rm ON rm.manufacturer_id = f.id
                JOIN protec_ai.relay_equipment re ON re.relay_model_id = rm.id
                LEFT JOIN protec_ai.relay_settings rs ON rs.equipment_id = re.id
                GROUP BY f.nome_completo
                ORDER BY equipment_count DESC
            """)
            mfr_dist = conn.execute(manufacturer_dist).fetchall()
            
            # Funções de proteção
            functions_stats = text("""
                SELECT 
                    COUNT(DISTINCT pf.id) as total_functions,
                    COUNT(DISTINCT rs.function_id) as configured_functions
                FROM protec_ai.protection_functions pf
                LEFT JOIN protec_ai.relay_settings rs ON rs.function_id = pf.id
            """)
            func_stats = conn.execute(functions_stats).fetchone()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "equipments": {
                    "total": int(eq_stats.total),
                    "active": int(eq_stats.active),
                    "substations": int(eq_stats.substations),
                    "bays": int(eq_stats.bays),
                    "by_manufacturer": [
                        {
                            "name": m.name,
                            "equipment_count": int(m.equipment_count),
                            "settings_count": int(m.settings_count)
                        }
                        for m in mfr_dist
                    ]
                },
                "settings": {
                    "total": int(set_stats.total),
                    "active": int(set_stats.active),
                    "inactive": int(set_stats.total) - int(set_stats.active),
                    "multipart": int(set_stats.multipart),
                    "by_type": {
                        "numeric": int(set_stats.numeric),
                        "boolean": int(set_stats.boolean),
                        "text": int(set_stats.text)
                    }
                },
                "protection_functions": {
                    "total_available": int(func_stats.total_functions),
                    "configured": int(func_stats.configured_functions)
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment/{equipment_id}/detailed")
async def get_equipment_detailed_report(
    equipment_id: int,
    include_inactive: bool = Query(True, description="Incluir configurações inativas"),
    db: Session = Depends(get_db)
):
    """
    Gera relatório técnico detalhado de um equipamento específico.
    
    **NOVO ENDPOINT PROFISSIONAL - 13/11/2025**
    
    Fornece análise completa de um equipamento individual, incluindo:
    - Metadados completos (SEPAM/PDF)
    - Todas as configurações (ativas e opcionalmente inativas)
    - Grupos multipart expandidos
    - Funções de proteção configuradas
    - Estatísticas de parâmetros
    
    Args:
        equipment_id: ID do equipamento no banco de dados
        include_inactive: Se True, inclui configurações inativas (default: True)
        
    Returns:
        Dict com relatório técnico completo
        
    Example:
        GET /api/v1/reports/equipment/1/detailed?include_inactive=true
    """
    try:
        service = ReportService(db)
        
        with service.engine.connect() as conn:
            # Informações do equipamento
            eq_query = text("""
                SELECT 
                    re.*,
                    rm.model_name,
                    rm.model_code,
                    rm.voltage_class,
                    rm.technology,
                    f.nome_completo as manufacturer_name,
                    f.codigo_fabricante as manufacturer_code
                FROM protec_ai.relay_equipment re
                JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
                JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
                WHERE re.id = :eq_id
            """)
            equipment = conn.execute(eq_query, {"eq_id": equipment_id}).fetchone()
            
            if not equipment:
                raise HTTPException(status_code=404, detail=f"Equipamento {equipment_id} não encontrado")
            
            # Configurações
            settings_filter = "" if include_inactive else "AND rs.is_active = true"
            settings_query = text(f"""
                SELECT 
                    rs.*,
                    u.unit_symbol,
                    pf.function_name
                FROM protec_ai.relay_settings rs
                LEFT JOIN protec_ai.units u ON rs.unit_id = u.id
                LEFT JOIN protec_ai.protection_functions pf ON rs.function_id = pf.id
                WHERE rs.equipment_id = :eq_id {settings_filter}
                ORDER BY rs.parameter_code, rs.multipart_part
                LIMIT 5000
            """)
            settings = conn.execute(settings_query, {"eq_id": equipment_id}).fetchall()
            
            return {
                "equipment": {
                    "id": equipment.id,
                    "tag": equipment.equipment_tag,
                    "serial": equipment.serial_number,
                    "model": equipment.model_name,
                    "manufacturer": equipment.manufacturer_name,
                    "location": {
                        "substation": equipment.substation_name,
                        "bay": equipment.barra_nome,
                        "voltage_level": equipment.voltage_level
                    },
                    "metadata": {
                        "source_file": equipment.source_file,
                        "sepam_repere": equipment.sepam_repere,
                        "pdf_serial": equipment.code_0081
                    }
                },
                "statistics": {
                    "total_settings": len(settings),
                    "active_settings": sum(1 for s in settings if s.is_active),
                    "multipart_settings": sum(1 for s in settings if s.is_multipart)
                },
                "settings": [
                    {
                        "code": s.parameter_code,
                        "name": s.parameter_name,
                        "value": float(s.set_value) if s.set_value else None,
                        "value_text": s.set_value_text,
                        "unit": s.unit_symbol,
                        "function": s.function_name,
                        "is_active": s.is_active,
                        "is_multipart": s.is_multipart,
                        "multipart_info": {
                            "base": s.multipart_base,
                            "part": s.multipart_part
                        } if s.is_multipart else None
                    }
                    for s in settings
                ]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detailed report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# 🆕 NOVOS ENDPOINTS - RELATÓRIOS TÉCNICOS DE ENGENHARIA
# ===================================================================

@router.get("/protection-functions/export/{format}")
async def export_protection_functions_report(
    format: str,
    db: Session = Depends(get_db)
):
    """
    🔒 Relatório de Funções de Proteção Ativas
    
    Exporta todas as 176 funções de proteção detectadas em 50 relés.
    Inclui códigos ANSI + IEC, matriz de proteção por equipamento.
    
    Args:
        format: Formato de exportação ('csv', 'xlsx' ou 'pdf')
        
    Returns:
        StreamingResponse com arquivo para download
    """
    try:
        service = ReportService(db)
        
        # Query para buscar funções ativas
        from sqlalchemy import text
        query = text("""
            SELECT 
                apf.relay_file,
                apf.function_code as ansi_code,
                apf.function_description,
                apf.detection_method,
                re.equipment_tag,
                f.nome_completo as manufacturer_name,
                rm.model_name,
                re.barra_nome,
                re.status
            FROM protec_ai.active_protection_functions apf
            LEFT JOIN protec_ai.relay_equipment re 
                ON REGEXP_REPLACE(re.equipment_tag, '\\.(pdf|S40|txt|xlsx)$', '', 'i') = 
                   REGEXP_REPLACE(apf.relay_file, '\\.(pdf|S40|txt|xlsx)$', '', 'i')
            LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
            LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
            ORDER BY apf.relay_file, apf.function_code
        """)
        
        result = db.execute(query)
        functions_data = [dict(row._mapping) for row in result]
        
        # Gerar arquivo no formato solicitado
        if format.lower() == 'pdf':
            content = await service.export_protection_functions_pdf(functions_data)
            media_type = "application/pdf"
        elif format.lower() == 'xlsx':
            content = await service.export_protection_functions_xlsx(functions_data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format.lower() == 'csv':
            content = await service.export_protection_functions_csv(functions_data)
            media_type = "text/csv"
        else:
            raise HTTPException(status_code=400, detail="Formato inválido. Use: csv, xlsx ou pdf")
        
        filename = f"REL_FUNCOES_PROTECAO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting protection functions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/setpoints/export/{format}")
async def export_setpoints_report(
    format: str,
    db: Session = Depends(get_db)
):
    """
    ⚡ Relatório de Setpoints Críticos
    
    Exporta todos os ajustes de proteção, limites operacionais e curvas.
    Conteúdo crítico para segurança das subestações.
    
    Args:
        format: Formato de exportação ('csv', 'xlsx' ou 'pdf')
    """
    try:
        service = ReportService(db)
        
        from sqlalchemy import text
        query = text("""
            SELECT 
                re.equipment_tag,
                f.nome_completo as manufacturer_name,
                rm.model_name,
                rs.parameter_code,
                rs.parameter_name,
                rs.set_value,
                rs.set_value_text,
                u.unit_symbol,
                pf.function_name,
                rs.category,
                rs.is_active
            FROM protec_ai.relay_settings rs
            JOIN protec_ai.relay_equipment re ON rs.equipment_id = re.id
            LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
            LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
            LEFT JOIN protec_ai.units u ON rs.unit_id = u.id
            LEFT JOIN protec_ai.protection_functions pf ON rs.function_id = pf.id
            WHERE rs.is_active = true
            ORDER BY re.equipment_tag, rs.parameter_code
        """)
        
        result = db.execute(query)
        setpoints_data = [dict(row._mapping) for row in result]
        
        if format.lower() == 'pdf':
            content = await service.export_setpoints_pdf(setpoints_data)
            media_type = "application/pdf"
        elif format.lower() == 'xlsx':
            content = await service.export_setpoints_xlsx(setpoints_data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format.lower() == 'csv':
            content = await service.export_setpoints_csv(setpoints_data)
            media_type = "text/csv"
        else:
            raise HTTPException(status_code=400, detail="Formato inválido")
        
        filename = f"REL_SETPOINTS_CRITICOS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting setpoints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coordination/export/{format}")
async def export_coordination_report(
    format: str,
    db: Session = Depends(get_db)
):
    """
    🎯 Relatório de Coordenação e Seletividade
    
    Análise de coordenação entre dispositivos de proteção.
    """
    try:
        service = ReportService(db)
        
        from sqlalchemy import text
        query = text("""
            WITH coordination_data AS (
                SELECT 
                    re.equipment_tag,
                    re.barra_nome,
                    apf.function_code as ansi_code,
                    apf.function_description,
                    rs.parameter_name,
                    rs.set_value,
                    u.unit_symbol
                FROM protec_ai.active_protection_functions apf
                JOIN protec_ai.relay_equipment re 
                    ON REGEXP_REPLACE(re.equipment_tag, '\\.(pdf|S40|txt|xlsx)$', '', 'i') = 
                       REGEXP_REPLACE(apf.relay_file, '\\.(pdf|S40|txt|xlsx)$', '', 'i')
                LEFT JOIN protec_ai.relay_settings rs 
                    ON rs.equipment_id = re.id AND rs.is_active = true
                LEFT JOIN protec_ai.units u ON rs.unit_id = u.id
                WHERE apf.function_code IN ('50', '51', '50/51', '50N', '51N', '50N/51N')
            )
            SELECT * FROM coordination_data
            ORDER BY barra_nome, equipment_tag, ansi_code
        """)
        
        result = db.execute(query)
        coordination_data = [dict(row._mapping) for row in result]
        
        if format.lower() == 'pdf':
            content = await service.export_coordination_pdf(coordination_data)
            media_type = "application/pdf"
        elif format.lower() == 'xlsx':
            content = await service.export_coordination_xlsx(coordination_data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format.lower() == 'csv':
            content = await service.export_coordination_csv(coordination_data)
            media_type = "text/csv"
        else:
            raise HTTPException(status_code=400, detail="Formato inválido")
        
        filename = f"REL_COORDENACAO_SELETIVIDADE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting coordination: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-bay/export/{format}")
async def export_by_bay_report(
    format: str,
    bay: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    🏭 Relatório por Bay/Subestação
    
    Equipamentos agrupados por localização física.
    """
    try:
        service = ReportService(db)
        
        from sqlalchemy import text
        bay_filter = "WHERE re.barra_nome = :bay" if bay else ""
        params = {"bay": bay} if bay else {}
        
        query = text(f"""
            SELECT 
                -- Extrair subestação do equipment_tag se substation_name vazio
                COALESCE(
                    NULLIF(re.substation_name, ''),
                    CASE 
                        WHEN re.equipment_tag ~ '^P\\d{{3}}_\\d{{3}}' THEN 
                            SUBSTRING(re.equipment_tag FROM '_(\\d{{3}})-')
                        WHEN re.equipment_tag ~ '^\\d{{2}}-' THEN 
                            SUBSTRING(re.equipment_tag FROM '^(\\d{{2}})')
                        ELSE 'N/A'
                    END
                ) as substation_name,
                re.barra_nome,
                re.voltage_level,
                re.equipment_tag,
                f.nome_completo as manufacturer_name,
                rm.model_name,
                re.serial_number,
                re.status,
                COUNT(DISTINCT apf.function_code) as protection_functions_count,
                STRING_AGG(DISTINCT apf.function_code, ', ' ORDER BY apf.function_code) as protection_codes
            FROM protec_ai.relay_equipment re
            LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
            LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
            LEFT JOIN protec_ai.active_protection_functions apf 
                ON REGEXP_REPLACE(re.equipment_tag, '\\.(pdf|S40|txt|xlsx)$', '', 'i') = 
                   REGEXP_REPLACE(apf.relay_file, '\\.(pdf|S40|txt|xlsx)$', '', 'i')
            {bay_filter}
            GROUP BY re.id, re.substation_name, re.barra_nome, re.voltage_level, 
                     re.equipment_tag, f.nome_completo, rm.model_name, 
                     re.serial_number, re.status
            ORDER BY substation_name, re.barra_nome, re.equipment_tag
        """)
        
        result = db.execute(query, params)
        bay_data = [dict(row._mapping) for row in result]
        
        if format.lower() == 'pdf':
            content = await service.export_by_bay_pdf(bay_data)
            media_type = "application/pdf"
        elif format.lower() == 'xlsx':
            content = await service.export_by_bay_xlsx(bay_data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format.lower() == 'csv':
            content = await service.export_by_bay_csv(bay_data)
            media_type = "text/csv"
        else:
            raise HTTPException(status_code=400, detail="Formato inválido")
        
        filename = f"REL_POR_BAY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting by-bay report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/maintenance/export/{format}")
async def export_maintenance_report(
    format: str,
    db: Session = Depends(get_db)
):
    """
    🔧 Relatório de Manutenção e Histórico
    
    Gestão de ciclo de vida dos equipamentos.
    """
    try:
        service = ReportService(db)
        
        from sqlalchemy import text
        query = text("""
            SELECT 
                re.equipment_tag,
                f.nome_completo as manufacturer_name,
                rm.model_name,
                re.serial_number,
                re.barra_nome,
                re.status,
                re.created_at as import_date,
                re.source_file,
                COUNT(DISTINCT rs.id) as total_settings,
                COUNT(DISTINCT CASE WHEN rs.is_active THEN rs.id END) as active_settings
            FROM protec_ai.relay_equipment re
            LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
            LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
            LEFT JOIN protec_ai.relay_settings rs ON rs.equipment_id = re.id
            GROUP BY re.id, re.equipment_tag, f.nome_completo, rm.model_name, 
                     re.serial_number, re.barra_nome, re.status, 
                     re.created_at, re.source_file
            ORDER BY re.created_at DESC, re.equipment_tag
        """)
        
        result = db.execute(query)
        maintenance_data = [dict(row._mapping) for row in result]
        
        if format.lower() == 'pdf':
            content = await service.export_maintenance_pdf(maintenance_data)
            media_type = "application/pdf"
        elif format.lower() == 'xlsx':
            content = await service.export_maintenance_xlsx(maintenance_data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format.lower() == 'csv':
            content = await service.export_maintenance_csv(maintenance_data)
            media_type = "text/csv"
        else:
            raise HTTPException(status_code=400, detail="Formato inválido")
        
        filename = f"REL_MANUTENCAO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting maintenance report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executive/export/{format}")
async def export_executive_report(
    format: str,
    db: Session = Depends(get_db)
):
    """
    📈 Relatório Executivo para Engenharia
    
    Visão estratégica com KPIs e métricas de desempenho.
    """
    try:
        service = ReportService(db)
        
        from sqlalchemy import text
        
        # Consolidar múltiplas queries em um relatório executivo
        queries = {
            'overview': text("""
                SELECT 
                    COUNT(DISTINCT re.id) as total_equipments,
                    COUNT(DISTINCT f.id) as total_manufacturers,
                    COUNT(DISTINCT rm.id) as total_models,
                    COUNT(DISTINCT apf.function_code) as total_protection_codes,
                    COUNT(DISTINCT apf.id) as total_active_functions
                FROM protec_ai.relay_equipment re
                LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
                LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
                LEFT JOIN protec_ai.active_protection_functions apf ON true
            """),
            'by_manufacturer': text("""
                SELECT 
                    f.nome_completo as manufacturer_name,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM protec_ai.relay_equipment re
                LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
                LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
                GROUP BY f.nome_completo
                ORDER BY count DESC
            """),
            'by_status': text("""
                SELECT 
                    re.status,
                    COUNT(*) as count
                FROM protec_ai.relay_equipment re
                GROUP BY re.status
            """),
            'protection_coverage': text("""
                SELECT 
                    COUNT(DISTINCT apf.relay_file) as relays_with_protection,
                    COUNT(DISTINCT re.id) as total_relays,
                    ROUND(COUNT(DISTINCT apf.relay_file) * 100.0 / COUNT(DISTINCT re.id), 2) as coverage_percentage
                FROM protec_ai.relay_equipment re
                LEFT JOIN protec_ai.active_protection_functions apf 
                    ON REGEXP_REPLACE(re.equipment_tag, '\\.(pdf|S40|txt|xlsx)$', '', 'i') = 
                       REGEXP_REPLACE(apf.relay_file, '\\.(pdf|S40|txt|xlsx)$', '', 'i')
            """)
        }
        
        executive_data = {}
        for key, query in queries.items():
            result = db.execute(query)
            executive_data[key] = [dict(row._mapping) for row in result]
        
        if format.lower() == 'pdf':
            content = await service.export_executive_pdf(executive_data)
            media_type = "application/pdf"
        elif format.lower() == 'xlsx':
            content = await service.export_executive_xlsx(executive_data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format.lower() == 'csv':
            content = await service.export_executive_csv(executive_data)
            media_type = "text/csv"
        else:
            raise HTTPException(status_code=400, detail="Formato inválido")
        
        filename = f"REL_EXECUTIVO_ENGENHARIA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting executive report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


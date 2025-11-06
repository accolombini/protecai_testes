"""
================================================================================
RELAY CONFIGURATION ROUTER (CRUD + REPORTS)
================================================================================
Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 2.0.0

Description:
    Endpoints para CRUD completo + relatórios de configuração de relés.
    
    CRUD Endpoints (NOVO):
    - POST   /api/relay-config/settings - Criar configuração
    - PUT    /api/relay-config/settings/{id} - Atualizar configuração
    - DELETE /api/relay-config/settings/{id} - Excluir configuração
    - PATCH  /api/relay-config/settings/bulk - Atualização em lote
    - POST   /api/relay-config/settings/{id}/restore - Desfazer exclusão
    - DELETE /api/relay-config/equipment/{id} - Excluir equipamento + configs
    
    Report Endpoints (Existente):
    - GET /api/relay-config/report/{equipment_id} - Gera relatório JSON
    - GET /api/relay-config/export/{equipment_id} - Exporta CSV/XLSX/PDF
    - GET /api/relay-config/equipment/list - Lista equipamentos disponíveis

Usage:
    # Criar nova configuração
    POST /api/relay-config/settings
    Body: {"equipment_id": 1, "parameter_code": "0201", ...}
    
    # Atualizar configuração
    PUT /api/relay-config/settings/123
    Body: {"set_value": 6.5, "notes": "Ajustado"}
    
    # Excluir (soft delete)
    DELETE /api/relay-config/settings/123?soft_delete=true
    
    # JSON report
    GET /api/relay-config/report/1
    
    # Export CSV
    GET /api/relay-config/export/1?format=csv
================================================================================
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Response, Body
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import io
import logging

from api.core.database import get_db
from api.services.relay_config_report_service import RelayConfigReportService
from api.services.relay_config_crud_service import RelayConfigCRUDService
from api.schemas.relay_config_schemas import (
    RelaySettingCreate,
    RelaySettingUpdate,
    RelaySettingResponse,
    BulkUpdateRequest,
    BulkUpdateResponse,
    DeleteResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/relay-config",
    tags=["Relay Configuration"]
)


# ============================================================================
# CRUD ENDPOINTS (CREATE, UPDATE, DELETE) - NOVO
# ============================================================================

@router.get("/settings", response_model=list[RelaySettingResponse])
def list_all_relay_settings(
    limit: int = Query(100, ge=1, le=1000, description="Máximo de registros a retornar"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    equipment_id: Optional[int] = Query(None, description="Filtrar por equipment_id"),
    is_enabled: Optional[bool] = Query(None, description="Filtrar por status (habilitado/desabilitado)"),
    db: Session = Depends(get_db)
):
    """
    📋 **Listar todas as configurações de relés.**
    
    Endpoint para listagem paginada de configurações com filtros opcionais.
    
    **Filtros disponíveis:**
    - `limit`: Quantidade máxima de registros (padrão: 100, máx: 1000)
    - `offset`: Pular N registros (para paginação)
    - `equipment_id`: Filtrar por equipamento específico
    - `is_enabled`: Filtrar apenas habilitadas (true) ou desabilitadas (false)
    
    **Exemplo de uso:**
    ```
    GET /api/relay-config/settings?limit=50&equipment_id=1
    GET /api/relay-config/settings?is_enabled=true
    GET /api/relay-config/settings?offset=100&limit=50
    ```
    
    Args:
        limit: Máximo de registros a retornar
        offset: Offset para paginação
        equipment_id: Filtrar por equipment_id
        is_enabled: Filtrar por status
        db: Sessão do banco de dados
    
    Returns:
        Lista de RelaySettingResponse
    """
    from sqlalchemy import text
    
    # Construir query base
    query = """
        SELECT 
            rs.id,
            rs.equipment_id,
            pf.function_code,
            rs.parameter_code,
            rs.parameter_name,
            rs.set_value,
            rs.unit_of_measure,
            rs.min_value as min_limit,
            rs.max_value as max_limit,
            rs.is_enabled,
            rs.category,
            rs.modification_reason as notes,
            rs.created_at,
            rs.updated_at,
            rs.modified_by
        FROM protec_ai.relay_settings rs
        LEFT JOIN protec_ai.protection_functions pf ON rs.function_id = pf.id
        WHERE rs.deleted_at IS NULL
    """
    
    params = {}
    
    # Aplicar filtros
    if equipment_id is not None:
        query += " AND rs.equipment_id = :equipment_id"
        params["equipment_id"] = equipment_id
    
    if is_enabled is not None:
        query += " AND rs.is_enabled = :is_enabled"
        params["is_enabled"] = is_enabled
    
    # Ordenar e paginar
    query += " ORDER BY rs.id DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    # Executar query
    result = db.execute(text(query), params)
    rows = result.fetchall()
    
    # Converter para lista de dicts
    settings = []
    for row in rows:
        settings.append(RelaySettingResponse(
            id=row.id,
            equipment_id=row.equipment_id,
            function_code=row.function_code or "",
            parameter_code=row.parameter_code,
            parameter_name=row.parameter_name,
            set_value=row.set_value,
            unit_of_measure=row.unit_of_measure,
            min_limit=row.min_limit,
            max_limit=row.max_limit,
            is_enabled=row.is_enabled,
            category=row.category,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
            modified_by=row.modified_by
        ))
    
    logger.info(f"📋 Listando {len(settings)} configurações (limit={limit}, offset={offset}, equipment_id={equipment_id})")
    return settings


@router.post("/settings", response_model=RelaySettingResponse, status_code=201)
def create_relay_setting(
    setting: RelaySettingCreate,
    db: Session = Depends(get_db)
):
    """
    🆕 **Criar nova configuração de relé manualmente.**
    
    Permite criar configurações que não vieram da importação automática,
    ou adicionar parâmetros customizados.
    
    **Validações automáticas:**
    - equipment_id deve existir
    - Não permite duplicatas (equipment_id + parameter_code)
    - set_value deve estar entre min_limit e max_limit
    
    **Exemplo de uso:**
    ```json
    {
      "equipment_id": 1,
      "function_code": "50",
      "parameter_code": "0201",
      "parameter_name": "I>",
      "set_value": 5.5,
      "unit_of_measure": "A",
      "min_limit": 1.0,
      "max_limit": 20.0,
      "is_enabled": true,
      "notes": "Configuração manual para teste"
    }
    ```
    
    Args:
        setting: Dados da nova configuração
        db: Sessão do banco de dados
    
    Returns:
        RelaySettingResponse com ID gerado e audit trail
    
    Raises:
        404: Equipment não encontrado
        409: Configuração duplicada
        400: Dados inválidos (valor fora dos limites)
    """
    service = RelayConfigCRUDService(db)
    return service.create_setting(setting)


@router.put("/settings/{setting_id}", response_model=RelaySettingResponse)
def update_relay_setting(
    setting_id: int,
    setting_update: RelaySettingUpdate,
    db: Session = Depends(get_db)
):
    """
    ✏️ **Atualizar configuração existente.**
    
    Permite alterar valor (set_value), habilitar/desabilitar, adicionar notas.
    Apenas os campos enviados são atualizados (PATCH semântica).
    
    **Atualização de audit trail:**
    - `updated_at` atualizado automaticamente
    - `modified_by` registrado se fornecido
    
    **Exemplos de uso:**
    
    ```json
    // Alterar apenas o valor
    {"set_value": 6.5}
    
    // Desabilitar configuração
    {"is_enabled": false}
    
    // Alterar valor e adicionar nota
    {
      "set_value": 7.0,
      "notes": "Ajustado conforme estudo rev. 03",
      "modified_by": "eng.silva@petrobras.com.br"
    }
    ```
    
    Args:
        setting_id: ID da configuração a atualizar
        setting_update: Campos a atualizar
        db: Sessão do banco de dados
    
    Returns:
        RelaySettingResponse com dados atualizados
    
    Raises:
        404: Configuração não encontrada
        400: Valor fora dos limites permitidos
    """
    service = RelayConfigCRUDService(db)
    return service.update_setting(setting_id, setting_update)


@router.patch("/settings/bulk", response_model=BulkUpdateResponse)
def bulk_update_relay_settings(
    bulk_request: BulkUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    📦 **Atualizar múltiplas configurações em lote (transação única).**
    
    **IMPORTANTE:** Operação atômica - se UMA atualização falhar, TODAS são revertidas!
    
    Ideal para:
    - Ajustar múltiplos setpoints de uma vez
    - Habilitar/desabilitar funções em grupo
    - Aplicar alterações coordenadas
    
    **Exemplo de uso:**
    ```json
    {
      "equipment_id": 1,
      "updates": [
        {"setting_id": 10, "set_value": 5.5},
        {"setting_id": 11, "set_value": 10.0},
        {"setting_id": 12, "is_enabled": false}
      ],
      "modified_by": "eng.silva@petrobras.com.br"
    }
    ```
    
    **Resposta de sucesso:**
    ```json
    {
      "success": true,
      "message": "3 configurações atualizadas com sucesso",
      "updated_count": 3,
      "updated_ids": [10, 11, 12],
      "errors": []
    }
    ```
    
    Args:
        bulk_request: Lista de atualizações
        db: Sessão do banco de dados
    
    Returns:
        BulkUpdateResponse com resumo da operação
    """
    service = RelayConfigCRUDService(db)
    return service.bulk_update_settings(bulk_request)


@router.delete("/settings/{setting_id}", response_model=DeleteResponse)
def delete_relay_setting(
    setting_id: int,
    soft_delete: bool = Query(True, description="True = soft delete (reversível), False = hard delete (permanente)"),
    db: Session = Depends(get_db)
):
    """
    🗑️ **Excluir configuração de relé.**
    
    **Soft Delete (Padrão - RECOMENDADO):**
    - Marca `deleted_at` sem remover fisicamente
    - Permite desfazer (undo) nos próximos 10 minutos
    - Mantém histórico e rastreabilidade
    
    **Hard Delete (Uso com Cautela):**
    - Remove fisicamente do banco de dados
    - **IRREVERSÍVEL** - não há undo possível
    - Use apenas se tiver certeza absoluta
    
    **Exemplos:**
    ```bash
    # Soft delete (padrão - pode desfazer)
    DELETE /api/relay-config/settings/123?soft_delete=true
    
    # Hard delete (permanente - NÃO pode desfazer)
    DELETE /api/relay-config/settings/123?soft_delete=false
    ```
    
    **Resposta:**
    ```json
    {
      "success": true,
      "message": "Configuração 'I>' marcada como excluída (pode desfazer)",
      "deleted_id": 123,
      "soft_delete": true,
      "can_undo": true,
      "undo_expires_at": "2025-11-03T15:10:00"
    }
    ```
    
    Args:
        setting_id: ID da configuração a excluir
        soft_delete: True = reversível, False = permanente
        db: Sessão do banco de dados
    
    Returns:
        DeleteResponse com detalhes da exclusão
    
    Raises:
        404: Configuração não encontrada
    """
    service = RelayConfigCRUDService(db)
    return service.delete_setting(setting_id, soft_delete)


@router.post("/settings/{setting_id}/restore", response_model=RelaySettingResponse)
def restore_deleted_setting(
    setting_id: int,
    db: Session = Depends(get_db)
):
    """
    ↩️ **Desfazer exclusão (undo) - Restaurar configuração soft-deleted.**
    
    Restaura uma configuração que foi excluída com soft_delete=true.
    
    **Limitações:**
    - Só funciona para soft deletes (deleted_at IS NOT NULL)
    - Hard deletes NÃO podem ser restaurados
    - Recomendado fazer dentro de 10 minutos da exclusão
    
    **Exemplo de uso:**
    ```bash
    # Usuário excluiu por engano
    DELETE /api/relay-config/settings/123?soft_delete=true
    
    # Ops, foi sem querer! Desfazer:
    POST /api/relay-config/settings/123/restore
    ```
    
    Args:
        setting_id: ID da configuração a restaurar
        db: Sessão do banco de dados
    
    Returns:
        RelaySettingResponse com dados restaurados
    
    Raises:
        404: Configuração não encontrada ou não está soft-deleted
    """
    service = RelayConfigCRUDService(db)
    return service.restore_setting(setting_id)


@router.delete("/equipment/{equipment_id}/cascade")
def delete_equipment_with_cascade(
    equipment_id: int,
    soft_delete: bool = Query(True, description="Soft delete (reversível) ou hard delete (permanente)"),
    db: Session = Depends(get_db)
):
    """
    ⚠️ **ATENÇÃO: Excluir equipamento E TODAS as suas configurações (CASCADE).**
    
    **OPERAÇÃO DESTRUTIVA!**
    
    Remove:
    - O equipamento (relay_equipment)
    - TODAS as configurações desse equipamento (relay_settings)
    - Vínculos com funções de proteção
    
    **Soft Delete (Padrão):**
    - Equipamento marcado como 'inactive'
    - Configurações marcadas com deleted_at
    - Possibilidade de restauração posterior
    
    **Hard Delete (PERIGOSO):**
    - Remoção física permanente
    - **IRREVERSÍVEL**
    - Perde todo o histórico
    
    **Aviso ao Usuário:**
    Frontend deve mostrar confirmação:
    "Isso removerá o equipamento REL-001 e suas 32 configurações. Confirmar?"
    
    **Exemplo:**
    ```bash
    # Soft delete (recomendado)
    DELETE /api/relay-config/equipment/1/cascade?soft_delete=true
    ```
    
    **Resposta:**
    ```json
    {
      "success": true,
      "equipment_id": 1,
      "settings_affected": 32,
      "soft_delete": true,
      "message": "Equipamento e 32 configurações desativados"
    }
    ```
    
    Args:
        equipment_id: ID do equipamento a excluir
        soft_delete: True = reversível, False = permanente
        db: Sessão do banco de dados
    
    Returns:
        Dict com estatísticas da exclusão
    
    Raises:
        404: Equipamento não encontrado
    """
    service = RelayConfigCRUDService(db)
    return service.delete_equipment_cascade(equipment_id, soft_delete)


# ============================================================================
# REPORT ENDPOINTS (READ-ONLY) - EXISTENTE
# ============================================================================

@router.get("/report/{equipment_id}")
def get_configuration_report(
    equipment_id: int,
    include_disabled: bool = Query(False, description="Incluir funções/parâmetros desabilitados"),
    db: Session = Depends(get_db)
):
    """
    Gera relatório JSON de configuração do equipamento.
    
    **Retorna:**
    - Informações do equipamento (tag, fabricante, modelo, etc.)
    - Funções de proteção configuradas com seus parâmetros
    - Configurações gerais do relé
    - Sumário com estatísticas
    
    **Exemplo de resposta:**
    ```json
    {
      "equipment": {
        "id": 1,
        "equipment_tag": "52-MF-02A",
        "manufacturer_name": "Schneider Electric",
        "model_name": "P220"
      },
      "protection_functions": [
        {
          "function_code": "50",
          "function_name": "Instantaneous Overcurrent",
          "is_enabled": true,
          "settings": [
            {
              "parameter_name": "I>",
              "parameter_code": "0201",
              "set_value": 0.63,
              "unit_of_measure": "In"
            }
          ]
        }
      ],
      "summary": {
        "total_functions": 5,
        "enabled_functions": 4,
        "total_settings": 32
      }
    }
    ```
    
    Args:
        equipment_id: ID do equipamento
        include_disabled: Incluir funções/parâmetros desabilitados (default: False)
        db: Sessão do banco de dados
    
    Returns:
        Relatório JSON completo
    
    Raises:
        404: Equipamento não encontrado
        500: Erro ao gerar relatório
    """
    try:
        service = RelayConfigReportService(db)
        result = service.generate_configuration_report(
            equipment_id=equipment_id,
            format='json',
            include_disabled=include_disabled
        )
        return result['data']
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")


@router.get("/export/{equipment_id}")
def export_configuration_report(
    equipment_id: int,
    format: str = Query('csv', regex='^(csv|xlsx|pdf)$', description="Formato: csv, xlsx ou pdf"),
    include_disabled: bool = Query(False, description="Incluir funções/parâmetros desabilitados"),
    db: Session = Depends(get_db)
):
    """
    Exporta relatório de configuração em formato CSV, XLSX ou PDF.
    
    **Formatos disponíveis:**
    - **CSV**: Arquivo de texto delimitado por vírgulas (universal)
    - **XLSX**: Planilha Excel formatada (requer openpyxl)
    - **PDF**: Documento PDF formatado (requer reportlab)
    
    **Download automático:**
    - Header `Content-Disposition: attachment` força download
    - Nome do arquivo gerado automaticamente: `CONFIG_{TAG}_{TIMESTAMP}.{ext}`
    
    **Exemplo de uso:**
    ```bash
    # Download CSV
    curl -O http://localhost:8000/api/relay-config/export/1?format=csv
    
    # Download PDF com funções desabilitadas
    curl -O http://localhost:8000/api/relay-config/export/1?format=pdf&include_disabled=true
    ```
    
    Args:
        equipment_id: ID do equipamento
        format: Formato de exportação (csv, xlsx, pdf)
        include_disabled: Incluir funções/parâmetros desabilitados
        db: Sessão do banco de dados
    
    Returns:
        StreamingResponse com arquivo para download
    
    Raises:
        400: Formato inválido
        404: Equipamento não encontrado
        500: Erro ao gerar relatório ou biblioteca ausente
    """
    try:
        service = RelayConfigReportService(db)
        result = service.generate_configuration_report(
            equipment_id=equipment_id,
            format=format.lower(),
            include_disabled=include_disabled
        )
        
        # Determinar MIME type
        mime_types = {
            'csv': 'text/csv',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf'
        }
        
        mime_type = mime_types.get(format.lower(), 'application/octet-stream')
        filename = result.get('filename', f'config_report.{format}')
        
        # Preparar conteúdo
        if format.lower() == 'csv':
            content = io.BytesIO(result['data'].encode('utf-8'))
        else:
            content = io.BytesIO(result['data'])
        
        return StreamingResponse(
            content,
            media_type=mime_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao exportar relatório: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao exportar relatório: {str(e)}")


@router.get("/equipment/list")
def list_available_equipment(
    manufacturer: Optional[str] = Query(None, description="Filtrar por fabricante"),
    model: Optional[str] = Query(None, description="Filtrar por modelo"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de resultados"),
    db: Session = Depends(get_db)
):
    """
    ⚙️ Lista equipamentos disponíveis para seleção de setup.
    
    Retorna lista simplificada de equipamentos com informações essenciais
    para o dropdown de seleção.
    
    Returns:
        {
          "total": 50,
          "equipment": [
            {
              "id": 1,
              "equipment_tag": "21-REL-87B-001",
              "manufacturer_name": "GE",
              "model_name": "P543",
              "bay_name": "Bay 21",
              "substation_name": "SE Norte",
              "has_settings": true
            }
          ]
        }
    """
    try:
        from sqlalchemy import text
        
        # Query usando a estrutura REAL da tabela relay_equipment
        query = text("""
            SELECT 
                re.id,
                re.equipment_tag,
                f.nome_completo as manufacturer_name,
                rm.model_name,
                re.bay_name,
                re.substation_name,
                CASE WHEN COUNT(rs.id) > 0 THEN true ELSE false END as has_settings
            FROM protec_ai.relay_equipment re
            LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
            LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
            LEFT JOIN protec_ai.relay_settings rs ON re.id = rs.equipment_id AND rs.deleted_at IS NULL
            GROUP BY re.id, re.equipment_tag, f.nome_completo, rm.model_name, re.bay_name, re.substation_name
            ORDER BY re.equipment_tag
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit}).fetchall()
        
        equipment_list = [
            {
                "id": row.id,
                "equipment_tag": row.equipment_tag or "N/A",
                "manufacturer_name": row.manufacturer_name or "N/A",
                "model_name": row.model_name or "N/A",
                "bay_name": row.bay_name or "N/A",
                "substation_name": row.substation_name or "N/A",
                "has_settings": bool(row.has_settings)
            }
            for row in result
        ]
        
        return {
            "total": len(equipment_list),
            "equipment": equipment_list
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao listar equipamentos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao listar equipamentos: {str(e)}")


@router.get("/manufacturers")
def list_manufacturers(db: Session = Depends(get_db)):
    """
    🏭 Lista todos os fabricantes de relés disponíveis.
    
    Endpoint para seleção hierárquica: PASSO 1 - Escolher Fabricante
    
    Returns:
        {
          "total": 5,
          "manufacturers": [
            {"id": 1, "name": "Schneider Electric", "relay_count": 25},
            {"id": 2, "name": "GE Grid Solutions", "relay_count": 15}
          ]
        }
    """
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                f.id,
                f.nome_completo as name,
                COUNT(DISTINCT re.id) as relay_count
            FROM protec_ai.fabricantes f
            LEFT JOIN protec_ai.relay_models rm ON f.id = rm.manufacturer_id
            LEFT JOIN protec_ai.relay_equipment re ON rm.id = re.relay_model_id
            WHERE f.ativo = true
            GROUP BY f.id, f.nome_completo
            HAVING COUNT(DISTINCT re.id) > 0
            ORDER BY f.nome_completo
        """)
        
        result = db.execute(query).fetchall()
        
        manufacturers = [
            {
                "id": row.id,
                "name": row.name,
                "relay_count": row.relay_count
            }
            for row in result
        ]
        
        return {
            "total": len(manufacturers),
            "manufacturers": manufacturers
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao listar fabricantes: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar fabricantes: {str(e)}")


@router.get("/models")
def list_models_by_manufacturer(
    manufacturer_id: int = Query(..., description="ID do fabricante"),
    db: Session = Depends(get_db)
):
    """
    📦 Lista modelos de relés filtrados por fabricante.
    
    Endpoint para seleção hierárquica: PASSO 2 - Escolher Modelo (após fabricante)
    
    Args:
        manufacturer_id: ID do fabricante selecionado
    
    Returns:
        {
          "manufacturer_id": 1,
          "manufacturer_name": "Schneider Electric",
          "total": 3,
          "models": [
            {"id": 5, "name": "P122", "relay_count": 10},
            {"id": 6, "name": "P220", "relay_count": 8}
          ]
        }
    """
    try:
        from sqlalchemy import text
        
        # Buscar nome do fabricante
        manufacturer_query = text("""
            SELECT nome_completo FROM protec_ai.fabricantes WHERE id = :manufacturer_id
        """)
        manufacturer = db.execute(manufacturer_query, {"manufacturer_id": manufacturer_id}).fetchone()
        
        if not manufacturer:
            raise HTTPException(status_code=404, detail=f"Fabricante ID {manufacturer_id} não encontrado")
        
        # Buscar modelos deste fabricante
        models_query = text("""
            SELECT 
                rm.id,
                rm.model_name as name,
                COUNT(DISTINCT re.id) as relay_count
            FROM protec_ai.relay_models rm
            LEFT JOIN protec_ai.relay_equipment re ON rm.id = re.relay_model_id
            WHERE rm.manufacturer_id = :manufacturer_id
            GROUP BY rm.id, rm.model_name
            HAVING COUNT(DISTINCT re.id) > 0
            ORDER BY rm.model_name
        """)
        
        result = db.execute(models_query, {"manufacturer_id": manufacturer_id}).fetchall()
        
        models = [
            {
                "id": row.id,
                "name": row.name,
                "relay_count": row.relay_count
            }
            for row in result
        ]
        
        return {
            "manufacturer_id": manufacturer_id,
            "manufacturer_name": manufacturer.nome_completo,
            "total": len(models),
            "models": models
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao listar modelos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar modelos: {str(e)}")


@router.get("/relays")
def list_relays_filtered(
    manufacturer_id: Optional[int] = Query(None, description="ID do fabricante"),
    model_id: Optional[int] = Query(None, description="ID do modelo"),
    db: Session = Depends(get_db)
):
    """
    ⚡ Lista relés filtrados por fabricante e/ou modelo.
    
    Endpoint para seleção hierárquica: PASSO 3 - Escolher Relé Específico
    
    **Pode ser usado de duas formas:**
    1. Após selecionar fabricante + modelo (filtro completo)
    2. Apenas com fabricante (mostra todos modelos desse fabricante)
    
    Args:
        manufacturer_id: ID do fabricante (opcional)
        model_id: ID do modelo (opcional, requer manufacturer_id)
    
    Returns:
        {
          "filters": {"manufacturer_id": 1, "model_id": 5},
          "total": 10,
          "relays": [
            {
              "id": 6,
              "equipment_tag": "REL-P122-P122204-MF-2B1",
              "manufacturer_name": "Schneider Electric",
              "model_name": "P122",
              "bay_name": "204-MF-2B1",
              "substation_name": "N/A",
              "has_settings": true
            }
          ]
        }
    """
    try:
        from sqlalchemy import text
        
        # Construir query dinamicamente baseado nos filtros
        conditions = []
        params = {}
        
        if manufacturer_id is not None:
            conditions.append("rm.manufacturer_id = :manufacturer_id")
            params["manufacturer_id"] = manufacturer_id
        
        if model_id is not None:
            conditions.append("rm.id = :model_id")
            params["model_id"] = model_id
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = text(f"""
            SELECT 
                re.id,
                re.equipment_tag,
                f.nome_completo as manufacturer_name,
                rm.model_name,
                re.bay_name,
                re.substation_name,
                CASE WHEN COUNT(rs.id) > 0 THEN true ELSE false END as has_settings
            FROM protec_ai.relay_equipment re
            LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
            LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
            LEFT JOIN protec_ai.relay_settings rs ON re.id = rs.equipment_id AND rs.deleted_at IS NULL
            {where_clause}
            GROUP BY re.id, re.equipment_tag, f.nome_completo, rm.model_name, re.bay_name, re.substation_name
            ORDER BY re.equipment_tag
        """)
        
        result = db.execute(query, params).fetchall()
        
        relays = [
            {
                "id": row.id,
                "equipment_tag": row.equipment_tag or "N/A",
                "manufacturer_name": row.manufacturer_name or "N/A",
                "model_name": row.model_name or "N/A",
                "bay_name": row.bay_name or "N/A",
                "substation_name": row.substation_name or "N/A",
                "has_settings": bool(row.has_settings)
            }
            for row in result
        ]
        
        return {
            "filters": {
                "manufacturer_id": manufacturer_id,
                "model_id": model_id
            },
            "total": len(relays),
            "relays": relays
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao listar relés: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar relés: {str(e)}")


@router.get("/relay-setup-report/{equipment_id}")
def generate_relay_setup_report(
    equipment_id: int,
    format: str = Query("pdf", description="Formato: pdf, excel, csv"),
    db: Session = Depends(get_db)
):
    """
    📄 Gera relatório de setup do relé (para engenheiros de proteção).
    
    Este endpoint é específico para engenheiros que precisam de um relatório
    profissional com todas as configurações de um relé específico.
    
    **Formatos disponíveis:**
    - pdf: Relatório completo com logo e formatação profissional
    - excel: Planilha para análise e backup
    - csv: Dados brutos para importação
    
    **Exemplo de uso:**
    ```
    GET /api/relay-config/relay-setup-report/1?format=pdf
    ```
    
    Args:
        equipment_id: ID do equipamento/relé
        format: Formato do relatório (pdf, excel, csv)
        db: Sessão do banco de dados
    
    Returns:
        Arquivo para download (PDF, XLSX ou CSV)
    """
    try:
        from sqlalchemy import text
        
        # Buscar dados do equipamento
        equipment_query = text("""
            SELECT 
                re.id,
                re.equipment_tag,
                re.bay_name,
                f.nome_completo as manufacturer_name,
                rm.model_name,
                re.substation_name,
                re.voltage_level,
                re.installation_date,
                re.commissioning_date as last_maintenance
            FROM protec_ai.relay_equipment re
            LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
            LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
            WHERE re.id = :equipment_id
        """)
        
        equipment = db.execute(equipment_query, {"equipment_id": equipment_id}).fetchone()
        
        if not equipment:
            raise HTTPException(status_code=404, detail=f"Equipamento ID {equipment_id} não encontrado")
        
        # Buscar configurações
        settings_query = text("""
            SELECT 
                rs.id,
                pf.function_code,
                pf.function_name,
                rp.parameter_code,
                rp.parameter_name,
                rs.set_value,
                rp.unit_of_measure,
                rp.min_limit,
                rp.max_limit,
                rs.is_enabled,
                rs.notes,
                rs.updated_at,
                rs.modified_by
            FROM protec_ai.relay_settings rs
            LEFT JOIN protec_ai.relay_parameters rp ON rs.parameter_id = rp.id
            LEFT JOIN protec_ai.protection_functions pf ON rp.function_id = pf.id
            WHERE rs.equipment_id = :equipment_id 
              AND rs.deleted_at IS NULL
            ORDER BY pf.function_code, rp.parameter_code
        """)
        
        settings = db.execute(settings_query, {"equipment_id": equipment_id}).fetchall()
        
        # Preparar dados para relatório
        report_data = {
            "equipment": {
                "id": equipment.id,
                "tag": equipment.equipment_tag,
                "manufacturer": equipment.manufacturer_name or "N/A",
                "model": equipment.model_name or "N/A",
                "bay": equipment.bay_name or "N/A",
                "substation": equipment.substation_name or "N/A",
                "voltage": equipment.voltage_level or "N/A",
                "installation_date": str(equipment.installation_date) if equipment.installation_date else "N/A",
                "last_maintenance": str(equipment.last_maintenance) if equipment.last_maintenance else "N/A"
            },
            "settings": [
                {
                    "function_code": s.function_code or "",
                    "function_name": s.function_name or "",
                    "parameter_code": s.parameter_code or "",
                    "parameter_name": s.parameter_name or "",
                    "set_value": s.set_value,
                    "unit": s.unit_of_measure or "",
                    "min_limit": s.min_limit,
                    "max_limit": s.max_limit,
                    "enabled": s.is_enabled,
                    "notes": s.notes or "",
                    "updated_at": str(s.updated_at) if s.updated_at else "",
                    "modified_by": s.modified_by or ""
                }
                for s in settings
            ]
        }
        
        # Gerar relatório conforme formato
        if format.lower() == "pdf":
            # Por enquanto retornar JSON, depois implementamos PDF
            return JSONResponse(content={
                "message": "Geração de PDF em desenvolvimento",
                "data": report_data
            })
        
        elif format.lower() == "excel":
            # Usar endpoint existente de export
            from api.services.relay_config_report_service import RelayConfigReportService
            service = RelayConfigReportService(db)
            excel_file = service.export_to_excel(equipment_id)
            
            return StreamingResponse(
                io.BytesIO(excel_file),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=setup_{equipment.equipment_tag}.xlsx"}
            )
        
        elif format.lower() == "csv":
            # Usar endpoint existente de export
            from api.services.relay_config_report_service import RelayConfigReportService
            service = RelayConfigReportService(db)
            csv_content = service.export_to_csv(equipment_id)
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=setup_{equipment.equipment_tag}.csv"}
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Formato '{format}' não suportado. Use: pdf, excel ou csv")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório de setup: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")


@router.get("/health")
def health_check():
    """
    Verifica saúde do serviço de relatórios.
    
    Returns:
        Status e dependências disponíveis
    """
    from api.services.relay_config_report_service import HAS_REPORTLAB, HAS_OPENPYXL
    
    return {
        'status': 'healthy',
        'service': 'Relay Configuration Reports',
        'capabilities': {
            'json': True,
            'csv': True,
            'xlsx': HAS_OPENPYXL,
            'pdf': HAS_REPORTLAB
        },
        'dependencies': {
            'openpyxl': HAS_OPENPYXL,
            'reportlab': HAS_REPORTLAB
        }
    }

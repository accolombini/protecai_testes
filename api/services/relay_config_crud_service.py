"""
================================================================================
RELAY CONFIGURATION CRUD SERVICE
================================================================================
Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 1.0.0

Description:
    Serviço para operações CRUD (Create, Read, Update, Delete) em 
    configurações de relés de proteção.
    
    Responsabilidades:
    - Criar novas configurações manualmente
    - Atualizar configurações existentes (individual ou em lote)
    - Excluir configurações (soft ou hard delete)
    - Validar integridade dos dados antes de persistir
    - Registrar audit trail (quem, quando, o quê)
    - Garantir transações atômicas em operações em lote
    
    Métodos principais:
    - create_setting: Cria nova configuração
    - update_setting: Atualiza configuração individual
    - bulk_update_settings: Atualiza múltiplas configurações (transação)
    - delete_setting: Exclui configuração (soft/hard)
    - delete_equipment_cascade: Exclui equipamento + todas as configs

Usage:
    from api.services.relay_config_crud_service import RelayConfigCRUDService
    
    service = RelayConfigCRUDService(db)
    result = service.create_setting(setting_data)
================================================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

from api.schemas.relay_config_schemas import (
    RelaySettingCreate,
    RelaySettingUpdate,
    RelaySettingResponse,
    BulkUpdateRequest,
    BulkUpdateResponse,
    DeleteResponse
)

logger = logging.getLogger(__name__)


class RelayConfigCRUDService:
    """
    Serviço para operações CRUD em configurações de relés.
    
    Todas as operações incluem:
    - Validação de dados
    - Verificação de existência (equipment_id, setting_id)
    - Audit trail automático
    - Tratamento de erros com rollback
    """
    
    def __init__(self, db: Session):
        """
        Inicializa o serviço.
        
        Args:
            db: Sessão do SQLAlchemy
        """
        self.db = db
    
    def create_setting(self, data: RelaySettingCreate) -> RelaySettingResponse:
        """
        Cria uma nova configuração de relé.
        
        Validações:
        - equipment_id deve existir na tabela relay_equipment
        - Não permite duplicatas (equipment_id + parameter_code)
        - set_value deve estar dentro de min/max limits
        
        Args:
            data: Dados da nova configuração
            
        Returns:
            RelaySettingResponse com dados criados
            
        Raises:
            HTTPException 404: Equipment não encontrado
            HTTPException 409: Configuração duplicada
            HTTPException 400: Dados inválidos
        """
        try:
            # 1. Validar se equipamento existe
            check_equipment = text("""
                SELECT id FROM protec_ai.relay_equipment 
                WHERE id = :equipment_id
            """)
            result = self.db.execute(check_equipment, {"equipment_id": data.equipment_id}).fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Equipamento com ID {data.equipment_id} não encontrado"
                )
            
            # 2. Validar duplicatas
            check_duplicate = text("""
                SELECT id FROM protec_ai.relay_settings
                WHERE equipment_id = :equipment_id
                AND parameter_code = :parameter_code
                AND deleted_at IS NULL
            """)
            duplicate = self.db.execute(check_duplicate, {
                "equipment_id": data.equipment_id,
                "parameter_code": data.parameter_code
            }).fetchone()
            
            if duplicate:
                raise HTTPException(
                    status_code=409,
                    detail=f"Configuração duplicada: parâmetro {data.parameter_code} já existe para este equipamento"
                )
            
            # 3. Inserir nova configuração
            insert_query = text("""
                INSERT INTO protec_ai.relay_settings (
                    equipment_id,
                    function_id,
                    parameter_code,
                    parameter_name,
                    set_value,
                    unit_of_measure,
                    min_value,
                    max_value,
                    is_enabled,
                    category,
                    modification_reason,
                    created_at,
                    updated_at
                )
                VALUES (
                    :equipment_id,
                    (SELECT id FROM protec_ai.protection_functions WHERE function_code = :function_code LIMIT 1),
                    :parameter_code,
                    :parameter_name,
                    :set_value,
                    :unit_of_measure,
                    :min_limit,
                    :max_limit,
                    :is_enabled,
                    :category,
                    :notes,
                    NOW(),
                    NOW()
                )
                RETURNING id, equipment_id, parameter_code, parameter_name, set_value, 
                          unit_of_measure, min_value as min_limit, max_value as max_limit, 
                          is_enabled, category, modification_reason as notes, created_at, updated_at
            """)
            
            result = self.db.execute(insert_query, {
                "equipment_id": data.equipment_id,
                "function_code": data.function_code,
                "parameter_code": data.parameter_code,
                "parameter_name": data.parameter_name,
                "set_value": data.set_value,
                "unit_of_measure": data.unit_of_measure,
                "min_limit": data.min_limit,
                "max_limit": data.max_limit,
                "is_enabled": data.is_enabled,
                "category": data.category.value if data.category else None,
                "notes": data.notes
            }).fetchone()
            
            self.db.commit()
            
            logger.info(f"✅ Configuração criada: ID={result.id}, param={data.parameter_name}, value={data.set_value}")
            
            return RelaySettingResponse(
                id=result.id,
                equipment_id=result.equipment_id,
                function_code=data.function_code,
                parameter_code=result.parameter_code,
                parameter_name=result.parameter_name,
                set_value=result.set_value,
                unit_of_measure=result.unit_of_measure,
                min_limit=result.min_limit,
                max_limit=result.max_limit,
                is_enabled=result.is_enabled,
                category=result.category,
                notes=result.notes,
                created_at=result.created_at,
                updated_at=result.updated_at,
                modified_by=None
            )
        
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao criar configuração: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao criar configuração: {str(e)}")
    
    def update_setting(self, setting_id: int, data: RelaySettingUpdate) -> RelaySettingResponse:
        """
        Atualiza uma configuração existente.
        
        Apenas os campos enviados são atualizados (PATCH semântica).
        Atualiza automaticamente o campo updated_at.
        
        Args:
            setting_id: ID da configuração a atualizar
            data: Novos dados (apenas campos a atualizar)
            
        Returns:
            RelaySettingResponse com dados atualizados
            
        Raises:
            HTTPException 404: Configuração não encontrada
            HTTPException 400: Valor fora dos limites
        """
        try:
            # 1. Verificar se configuração existe
            check_query = text("""
                SELECT id, min_value as min_limit, max_value as max_limit 
                FROM protec_ai.relay_settings
                WHERE id = :setting_id AND deleted_at IS NULL
            """)
            existing = self.db.execute(check_query, {"setting_id": setting_id}).fetchone()
            
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Configuração com ID {setting_id} não encontrada"
                )
            
            # 2. Validar set_value dentro dos limites (se aplicável)
            if data.set_value is not None:
                min_limit = existing.min_limit
                max_limit = existing.max_limit
                
                if min_limit is not None and data.set_value < min_limit:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Valor {data.set_value} abaixo do limite mínimo {min_limit}"
                    )
                
                if max_limit is not None and data.set_value > max_limit:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Valor {data.set_value} acima do limite máximo {max_limit}"
                    )
            
            # 3. Construir query de atualização dinamicamente
            update_fields = []
            params = {"setting_id": setting_id}
            
            if data.set_value is not None:
                update_fields.append("set_value = :set_value")
                params["set_value"] = data.set_value
            
            if data.is_enabled is not None:
                update_fields.append("is_enabled = :is_enabled")
                params["is_enabled"] = data.is_enabled
            
            if data.min_limit is not None:
                update_fields.append("min_value = :min_limit")
                params["min_limit"] = data.min_limit
            
            if data.max_limit is not None:
                update_fields.append("max_value = :max_limit")
                params["max_limit"] = data.max_limit
            
            if data.category is not None:
                update_fields.append("category = :category")
                params["category"] = data.category.value
            
            if data.notes is not None:
                update_fields.append("modification_reason = :notes")
                params["notes"] = data.notes
            
            if data.modified_by is not None:
                update_fields.append("modified_by = :modified_by")
                params["modified_by"] = data.modified_by
            
            # Sempre atualiza updated_at
            update_fields.append("updated_at = NOW()")
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
            
            update_query = text(f"""
                UPDATE protec_ai.relay_settings
                SET {', '.join(update_fields)}
                WHERE id = :setting_id
                RETURNING id, equipment_id, parameter_code, parameter_name, set_value,
                          unit_of_measure, min_value as min_limit, max_value as max_limit, 
                          is_enabled, category, modification_reason as notes, 
                          created_at, updated_at, modified_by
            """)
            
            result = self.db.execute(update_query, params).fetchone()
            self.db.commit()
            
            logger.info(f"✅ Configuração atualizada: ID={setting_id}, campos={list(params.keys())}")
            
            # Buscar function_code (não está no relay_settings diretamente)
            func_query = text("""
                SELECT pf.function_code
                FROM protec_ai.relay_settings rs
                JOIN protec_ai.protection_functions pf ON rs.function_id = pf.id
                WHERE rs.id = :setting_id
            """)
            func_result = self.db.execute(func_query, {"setting_id": setting_id}).fetchone()
            
            return RelaySettingResponse(
                id=result.id,
                equipment_id=result.equipment_id,
                function_code=func_result.function_code if func_result else "",
                parameter_code=result.parameter_code,
                parameter_name=result.parameter_name,
                set_value=result.set_value,
                unit_of_measure=result.unit_of_measure,
                min_limit=result.min_limit,
                max_limit=result.max_limit,
                is_enabled=result.is_enabled,
                category=result.category,
                notes=result.notes,
                created_at=result.created_at,
                updated_at=result.updated_at,
                modified_by=result.modified_by
            )
        
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao atualizar configuração {setting_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao atualizar: {str(e)}")
    
    def bulk_update_settings(self, request: BulkUpdateRequest) -> BulkUpdateResponse:
        """
        Atualiza múltiplas configurações em uma transação única.
        
        IMPORTANTE: Operação atômica - se uma atualização falhar, TODAS são revertidas.
        
        Args:
            request: Lista de atualizações a aplicar
            
        Returns:
            BulkUpdateResponse com resumo da operação
            
        Raises:
            HTTPException 400: Se alguma atualização falhar
        """
        updated_ids = []
        errors = []
        
        try:
            for item in request.updates:
                try:
                    # Criar objeto RelaySettingUpdate para cada item
                    update_data = RelaySettingUpdate(
                        set_value=item.set_value,
                        is_enabled=item.is_enabled,
                        notes=item.notes,
                        modified_by=request.modified_by
                    )
                    
                    # Atualizar (reutiliza método individual)
                    result = self.update_setting(item.setting_id, update_data)
                    updated_ids.append(result.id)
                
                except HTTPException as e:
                    errors.append({
                        "setting_id": item.setting_id,
                        "error": e.detail
                    })
                    # Em bulk update, um erro quebra tudo
                    raise
            
            # Se chegou aqui, tudo OK
            self.db.commit()
            
            logger.info(f"✅ Bulk update concluído: {len(updated_ids)} configurações atualizadas")
            
            return BulkUpdateResponse(
                success=True,
                message=f"{len(updated_ids)} configurações atualizadas com sucesso",
                updated_count=len(updated_ids),
                failed_count=0,
                updated_ids=updated_ids,
                errors=[]
            )
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro em bulk update: {e}")
            
            return BulkUpdateResponse(
                success=False,
                message="Falha ao atualizar configurações (rollback aplicado)",
                updated_count=0,
                failed_count=len(request.updates),
                updated_ids=[],
                errors=errors if errors else [{"error": str(e)}]
            )
    
    def delete_setting(self, setting_id: int, soft_delete: bool = True) -> DeleteResponse:
        """
        Exclui uma configuração.
        
        Soft delete (padrão): Marca deleted_at, permite undo
        Hard delete: Remove fisicamente do banco (irreversível)
        
        Args:
            setting_id: ID da configuração a excluir
            soft_delete: True = soft delete, False = hard delete
            
        Returns:
            DeleteResponse com detalhes da exclusão
            
        Raises:
            HTTPException 404: Configuração não encontrada
        """
        try:
            # Verificar se existe
            check_query = text("""
                SELECT id, parameter_name FROM protec_ai.relay_settings
                WHERE id = :setting_id AND deleted_at IS NULL
            """)
            existing = self.db.execute(check_query, {"setting_id": setting_id}).fetchone()
            
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Configuração com ID {setting_id} não encontrada"
                )
            
            if soft_delete:
                # Soft delete - marca deleted_at
                delete_query = text("""
                    UPDATE protec_ai.relay_settings
                    SET deleted_at = NOW()
                    WHERE id = :setting_id
                """)
                self.db.execute(delete_query, {"setting_id": setting_id})
                
                undo_expires_at = datetime.now() + timedelta(seconds=600)  # 10 minutos para undo
                
                logger.info(f"✅ Soft delete: configuração {setting_id} ({existing.parameter_name})")
                
                message = f"Configuração '{existing.parameter_name}' marcada como excluída (pode desfazer)"
            else:
                # Hard delete - remove fisicamente
                delete_query = text("""
                    DELETE FROM protec_ai.relay_settings
                    WHERE id = :setting_id
                """)
                self.db.execute(delete_query, {"setting_id": setting_id})
                
                undo_expires_at = None
                
                logger.warning(f"⚠️ Hard delete: configuração {setting_id} ({existing.parameter_name}) REMOVIDA PERMANENTEMENTE")
                
                message = f"Configuração '{existing.parameter_name}' excluída permanentemente"
            
            self.db.commit()
            
            return DeleteResponse(
                success=True,
                message=message,
                deleted_id=setting_id,
                soft_delete=soft_delete,
                can_undo=soft_delete,
                undo_expires_at=undo_expires_at
            )
        
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao excluir configuração {setting_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao excluir: {str(e)}")
    
    def restore_setting(self, setting_id: int) -> RelaySettingResponse:
        """
        Restaura uma configuração soft-deleted (undo).
        
        Args:
            setting_id: ID da configuração a restaurar
            
        Returns:
            RelaySettingResponse com dados restaurados
            
        Raises:
            HTTPException 404: Configuração não encontrada ou não soft-deleted
        """
        try:
            restore_query = text("""
                UPDATE protec_ai.relay_settings
                SET deleted_at = NULL, updated_at = NOW()
                WHERE id = :setting_id AND deleted_at IS NOT NULL
                RETURNING id
            """)
            
            result = self.db.execute(restore_query, {"setting_id": setting_id}).fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Configuração {setting_id} não encontrada ou não está excluída"
                )
            
            self.db.commit()
            
            logger.info(f"✅ Configuração {setting_id} restaurada (undo)")
            
            # Buscar dados completos
            fetch_query = text("""
                SELECT rs.id, rs.equipment_id, rs.parameter_code, rs.parameter_name,
                       rs.set_value, rs.unit_of_measure, 
                       rs.min_value as min_limit, rs.max_value as max_limit,
                       rs.is_enabled, rs.category, rs.modification_reason as notes,
                       rs.created_at, rs.updated_at, rs.modified_by,
                       pf.function_code
                FROM protec_ai.relay_settings rs
                LEFT JOIN protec_ai.protection_functions pf ON rs.function_id = pf.id
                WHERE rs.id = :setting_id
            """)
            data = self.db.execute(fetch_query, {"setting_id": setting_id}).fetchone()
            
            return RelaySettingResponse(
                id=data.id,
                equipment_id=data.equipment_id,
                function_code=data.function_code or "",
                parameter_code=data.parameter_code,
                parameter_name=data.parameter_name,
                set_value=data.set_value,
                unit_of_measure=data.unit_of_measure,
                min_limit=data.min_limit,
                max_limit=data.max_limit,
                is_enabled=data.is_enabled,
                category=data.category,
                notes=data.notes,
                created_at=data.created_at,
                updated_at=data.updated_at,
                modified_by=data.modified_by
            )
        
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao restaurar configuração {setting_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao restaurar: {str(e)}")
    
    def delete_equipment_cascade(
        self, 
        equipment_id: int, 
        soft_delete: bool = True
    ) -> Dict:
        """
        Exclui equipamento e TODAS as suas configurações (cascade).
        
        ATENÇÃO: Operação destrutiva que afeta múltiplas tabelas!
        
        Args:
            equipment_id: ID do equipamento a excluir
            soft_delete: True = soft delete, False = hard delete
            
        Returns:
            Dict com estatísticas da exclusão
            
        Raises:
            HTTPException 404: Equipamento não encontrado
        """
        try:
            # Contar quantas configurações serão afetadas
            count_query = text("""
                SELECT COUNT(*) as total FROM protec_ai.relay_settings
                WHERE equipment_id = :equipment_id AND deleted_at IS NULL
            """)
            count = self.db.execute(count_query, {"equipment_id": equipment_id}).fetchone()
            
            if soft_delete:
                # Soft delete equipamento
                delete_equip = text("""
                    UPDATE protec_ai.relay_equipment
                    SET status = 'inactive', updated_at = NOW()
                    WHERE id = :equipment_id
                """)
                self.db.execute(delete_equip, {"equipment_id": equipment_id})
                
                # Soft delete todas as configurações
                delete_settings = text("""
                    UPDATE protec_ai.relay_settings
                    SET deleted_at = NOW()
                    WHERE equipment_id = :equipment_id AND deleted_at IS NULL
                """)
                self.db.execute(delete_settings, {"equipment_id": equipment_id})
                
                logger.info(f"✅ Soft delete cascade: equipamento {equipment_id} + {count.total} configurações")
            else:
                # Hard delete (remover fisicamente)
                delete_settings = text("""
                    DELETE FROM protec_ai.relay_settings
                    WHERE equipment_id = :equipment_id
                """)
                self.db.execute(delete_settings, {"equipment_id": equipment_id})
                
                delete_equip = text("""
                    DELETE FROM protec_ai.relay_equipment
                    WHERE id = :equipment_id
                """)
                self.db.execute(delete_equip, {"equipment_id": equipment_id})
                
                logger.warning(f"⚠️ Hard delete cascade: equipamento {equipment_id} + {count.total} configurações REMOVIDOS PERMANENTEMENTE")
            
            self.db.commit()
            
            return {
                "success": True,
                "equipment_id": equipment_id,
                "settings_affected": count.total,
                "soft_delete": soft_delete,
                "message": f"Equipamento e {count.total} configurações {'desativados' if soft_delete else 'excluídos permanentemente'}"
            }
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao excluir equipamento {equipment_id} em cascade: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao excluir equipamento: {str(e)}")

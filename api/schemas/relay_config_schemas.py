"""
================================================================================
RELAY CONFIGURATION SCHEMAS
================================================================================
Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 1.0.0

Description:
    Schemas Pydantic para operações CRUD de configurações de relés.
    
    Schemas disponíveis:
    - RelaySettingCreate: Criação de nova configuração
    - RelaySettingUpdate: Atualização de configuração existente
    - RelaySettingResponse: Resposta com dados completos + audit trail
    - BulkUpdateRequest: Atualização em lote (múltiplas configs)
    - DeleteResponse: Resposta de exclusão
    
    Validações implementadas:
    - set_value dentro de min_limit e max_limit
    - Campos obrigatórios vs opcionais
    - Tipos corretos (int, float, str, bool)
    - Limites de tamanho de strings

Usage:
    from api.schemas.relay_config_schemas import RelaySettingCreate
    
    setting = RelaySettingCreate(
        equipment_id=1,
        function_code="50",
        parameter_code="0201",
        parameter_name="I>",
        set_value=5.5,
        unit_of_measure="A",
        min_limit=1.0,
        max_limit=20.0
    )
================================================================================
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SettingCategory(str, Enum):
    """Categorias de configurações"""
    OVERCURRENT_SETTING = "OVERCURRENT_SETTING"
    VOLTAGE_SETTING = "VOLTAGE_SETTING"
    FREQUENCY_SETTING = "FREQUENCY_SETTING"
    TIMING = "TIMING"
    INSTRUMENTATION = "INSTRUMENTATION"
    POWER_SETTING = "POWER_SETTING"
    IMPEDANCE_SETTING = "IMPEDANCE_SETTING"
    OTHER = "OTHER"


class RelaySettingCreate(BaseModel):
    """
    Schema para criação de nova configuração de relé.
    
    Validações:
    - equipment_id deve existir no banco
    - function_code e parameter_code não podem estar vazios
    - set_value deve estar entre min_limit e max_limit (se definidos)
    - parameter_name obrigatório
    
    Exemplo:
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
            "notes": "Ajustado conforme estudo de seletividade"
        }
    """
    equipment_id: int = Field(..., gt=0, description="ID do equipamento (relay_equipment)")
    function_code: str = Field(..., min_length=1, max_length=10, description="Código ANSI da função (ex: 50, 51, 27)")
    parameter_code: str = Field(..., min_length=1, max_length=20, description="Código do parâmetro (ex: 0201, 0202)")
    parameter_name: str = Field(..., min_length=1, max_length=100, description="Nome do parâmetro (ex: I>, V<, t)")
    set_value: float = Field(..., description="Valor configurado (setpoint)")
    unit_of_measure: Optional[str] = Field(None, max_length=20, description="Unidade (A, V, Hz, ms, pu)")
    min_limit: Optional[float] = Field(None, description="Limite mínimo permitido")
    max_limit: Optional[float] = Field(None, description="Limite máximo permitido")
    is_enabled: bool = Field(True, description="Configuração habilitada?")
    category: Optional[SettingCategory] = Field(None, description="Categoria do parâmetro")
    notes: Optional[str] = Field(None, max_length=500, description="Observações")
    
    @field_validator('parameter_code', 'function_code')
    @classmethod
    def validate_codes_not_empty(cls, v: str) -> str:
        """Valida que códigos não estejam vazios e normaliza para uppercase"""
        if not v.strip():
            raise ValueError('Código não pode estar vazio')
        return v.strip().upper()
    
    @model_validator(mode='after')
    def validate_set_value_within_limits(self):
        """
        Valida se setpoint está dentro dos limites definidos.
        
        Raises:
            ValueError: Se valor estiver fora dos limites
        """
        if self.min_limit is not None and self.set_value < self.min_limit:
            raise ValueError(
                f'{self.parameter_name}: valor {self.set_value} abaixo do limite mínimo {self.min_limit}'
            )
        
        if self.max_limit is not None and self.set_value > self.max_limit:
            raise ValueError(
                f'{self.parameter_name}: valor {self.set_value} acima do limite máximo {self.max_limit}'
            )
        
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "equipment_id": 1,
                "function_code": "50",
                "parameter_code": "0201",
                "parameter_name": "I>",
                "set_value": 5.5,
                "unit_of_measure": "A",
                "min_limit": 1.0,
                "max_limit": 20.0,
                "is_enabled": True,
                "category": "OVERCURRENT_SETTING",
                "notes": "Pickup de sobrecorrente instantânea"
            }
        }
    )


class RelaySettingUpdate(BaseModel):
    """
    Schema para atualização de configuração existente.
    
    Todos os campos são opcionais para permitir atualização parcial.
    Apenas os campos enviados serão atualizados.
    
    Exemplo:
        # Alterar apenas o valor
        {"set_value": 6.0}
        
        # Desabilitar configuração
        {"is_enabled": false}
        
        # Alterar valor e adicionar nota
        {
            "set_value": 6.5,
            "notes": "Ajustado após análise de curto-circuito"
        }
    """
    set_value: Optional[float] = Field(None, description="Novo valor configurado")
    is_enabled: Optional[bool] = Field(None, description="Habilitar/desabilitar")
    min_limit: Optional[float] = Field(None, description="Atualizar limite mínimo")
    max_limit: Optional[float] = Field(None, description="Atualizar limite máximo")
    category: Optional[SettingCategory] = Field(None, description="Atualizar categoria")
    notes: Optional[str] = Field(None, max_length=500, description="Atualizar observações")
    modified_by: Optional[str] = Field(None, max_length=100, description="Usuário que fez a modificação")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "set_value": 6.0,
                "is_enabled": True,
                "notes": "Valor ajustado conforme estudo de coordenação rev. 02",
                "modified_by": "eng.silva@petrobras.com.br"
            }
        }
    )


class RelaySettingResponse(BaseModel):
    """
    Schema de resposta com dados completos da configuração.
    
    Inclui audit trail (created_at, updated_at, modified_by).
    """
    id: int = Field(..., description="ID único da configuração")
    equipment_id: int = Field(..., description="ID do equipamento")
    function_code: str = Field(..., description="Código ANSI da função")
    parameter_code: str = Field(..., description="Código do parâmetro")
    parameter_name: str = Field(..., description="Nome do parâmetro")
    set_value: Optional[float] = Field(None, description="Valor configurado (pode ser NULL)")
    unit_of_measure: Optional[str] = Field(None, description="Unidade de medida")
    min_limit: Optional[float] = Field(None, description="Limite mínimo")
    max_limit: Optional[float] = Field(None, description="Limite máximo")
    is_enabled: bool = Field(True, description="Habilitado?")
    category: Optional[str] = Field(None, description="Categoria")
    notes: Optional[str] = Field(None, description="Observações")
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: Optional[datetime] = Field(None, description="Data da última atualização")
    modified_by: Optional[str] = Field(None, description="Última modificação por")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 123,
                "equipment_id": 1,
                "function_code": "50",
                "parameter_code": "0201",
                "parameter_name": "I>",
                "set_value": 5.5,
                "unit_of_measure": "A",
                "min_limit": 1.0,
                "max_limit": 20.0,
                "is_enabled": True,
                "category": "OVERCURRENT_SETTING",
                "notes": "Pickup de sobrecorrente instantânea",
                "created_at": "2025-11-03T10:00:00",
                "updated_at": "2025-11-03T14:30:00",
                "modified_by": "eng.silva@petrobras.com.br"
            }
        }
    )


class BulkUpdateItem(BaseModel):
    """Item individual em uma atualização em lote"""
    setting_id: int = Field(..., gt=0, description="ID da configuração a atualizar")
    set_value: Optional[float] = Field(None, description="Novo valor")
    is_enabled: Optional[bool] = Field(None, description="Habilitar/desabilitar")
    notes: Optional[str] = Field(None, max_length=500, description="Observações")


class BulkUpdateRequest(BaseModel):
    """
    Schema para atualização em lote de múltiplas configurações.
    
    Todas as atualizações são executadas em uma transação única:
    - Se uma falhar, todas são revertidas (rollback)
    - Se todas passarem, todas são confirmadas (commit)
    
    Exemplo:
        {
            "equipment_id": 1,
            "updates": [
                {"setting_id": 10, "set_value": 5.5},
                {"setting_id": 11, "set_value": 10.0},
                {"setting_id": 12, "is_enabled": false}
            ],
            "modified_by": "eng.silva@petrobras.com.br"
        }
    """
    equipment_id: Optional[int] = Field(None, description="ID do equipamento (validação adicional)")
    updates: List[BulkUpdateItem] = Field(..., min_length=1, max_length=100, description="Lista de atualizações")
    modified_by: Optional[str] = Field(None, max_length=100, description="Usuário responsável")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "equipment_id": 1,
                "updates": [
                    {"setting_id": 10, "set_value": 5.5, "notes": "Ajustado"},
                    {"setting_id": 11, "set_value": 10.0},
                    {"setting_id": 12, "is_enabled": False}
                ],
                "modified_by": "eng.silva@petrobras.com.br"
            }
        }
    )


class DeleteResponse(BaseModel):
    """
    Schema de resposta para operações de exclusão.
    """
    success: bool = Field(..., description="Operação bem-sucedida?")
    message: str = Field(..., description="Mensagem descritiva")
    deleted_id: int = Field(..., description="ID do item excluído")
    soft_delete: bool = Field(..., description="Foi soft delete?")
    can_undo: bool = Field(True, description="Pode desfazer?")
    undo_expires_at: Optional[datetime] = Field(None, description="Undo expira em")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Configuração excluída com sucesso",
                "deleted_id": 123,
                "soft_delete": True,
                "can_undo": True,
                "undo_expires_at": "2025-11-03T15:10:00"
            }
        }
    )


class BulkUpdateResponse(BaseModel):
    """
    Schema de resposta para operações de atualização em lote.
    """
    success: bool = Field(..., description="Operação bem-sucedida?")
    message: str = Field(..., description="Mensagem descritiva")
    updated_count: int = Field(..., description="Quantidade atualizada")
    failed_count: int = Field(0, description="Quantidade que falhou")
    updated_ids: List[int] = Field(..., description="IDs atualizados")
    errors: List[dict] = Field(default_factory=list, description="Erros ocorridos")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "3 configurações atualizadas com sucesso",
                "updated_count": 3,
                "failed_count": 0,
                "updated_ids": [10, 11, 12],
                "errors": []
            }
        }
    )

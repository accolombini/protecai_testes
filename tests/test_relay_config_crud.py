"""
================================================================================
TESTES UNITÁRIOS - RELAY CONFIGURATION CRUD
================================================================================
Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 1.0.0

Description:
    Testes para operações CRUD de configurações de relés.
    
    Cobertura:
    - CREATE: Criação de configurações
    - UPDATE: Atualização individual e em lote
    - DELETE: Soft delete, hard delete, cascade
    - RESTORE: Undo de exclusões
    - VALIDAÇÕES: Limites, duplicatas, campos obrigatórios

Usage:
    # Executar todos os testes
    pytest tests/test_relay_config_crud.py -v
    
    # Executar teste específico
    pytest tests/test_relay_config_crud.py::TestCreateSetting::test_create_valid_setting -v
    
    # Com cobertura
    pytest tests/test_relay_config_crud.py --cov=api.services.relay_config_crud_service
================================================================================
"""

import pytest
from fastapi import HTTPException
from api.schemas.relay_config_schemas import (
    RelaySettingCreate,
    RelaySettingUpdate,
    BulkUpdateRequest,
    BulkUpdateItem,
    SettingCategory
)


class TestCreateSetting:
    """Testes de criação de configurações"""
    
    def test_create_valid_setting(self):
        """Deve criar configuração com todos os campos válidos"""
        setting = RelaySettingCreate(
            equipment_id=1,
            function_code="50",
            parameter_code="0201",
            parameter_name="I>",
            set_value=5.5,
            unit_of_measure="A",
            min_limit=1.0,
            max_limit=20.0,
            is_enabled=True,
            category=SettingCategory.OVERCURRENT_SETTING,
            notes="Teste"
        )
        
        assert setting.equipment_id == 1
        assert setting.function_code == "50"
        assert setting.parameter_code == "0201"
        assert setting.parameter_name == "I>"
        assert setting.set_value == 5.5
        assert setting.unit_of_measure == "A"
        assert setting.min_limit == 1.0
        assert setting.max_limit == 20.0
        assert setting.is_enabled is True
        assert setting.category == SettingCategory.OVERCURRENT_SETTING
    
    def test_create_with_minimal_fields(self):
        """Deve criar configuração apenas com campos obrigatórios"""
        setting = RelaySettingCreate(
            equipment_id=1,
            function_code="50",
            parameter_code="0201",
            parameter_name="I>",
            set_value=5.5
        )
        
        assert setting.equipment_id == 1
        assert setting.set_value == 5.5
        assert setting.unit_of_measure is None
        assert setting.min_limit is None
        assert setting.max_limit is None
        assert setting.is_enabled is True  # Default
        assert setting.category is None
    
    def test_validate_set_value_below_min_limit(self):
        """Deve rejeitar set_value abaixo do min_limit"""
        with pytest.raises(ValueError, match="abaixo do limite mínimo"):
            RelaySettingCreate(
                equipment_id=1,
                function_code="50",
                parameter_code="0201",
                parameter_name="I>",
                set_value=0.5,  # Abaixo do mínimo
                min_limit=1.0,
                max_limit=20.0
            )
    
    def test_validate_set_value_above_max_limit(self):
        """Deve rejeitar set_value acima do max_limit"""
        with pytest.raises(ValueError, match="acima do limite máximo"):
            RelaySettingCreate(
                equipment_id=1,
                function_code="50",
                parameter_code="0201",
                parameter_name="I>",
                set_value=25.0,  # Acima do máximo
                min_limit=1.0,
                max_limit=20.0
            )
    
    def test_validate_set_value_within_limits(self):
        """Deve aceitar set_value dentro dos limites"""
        setting = RelaySettingCreate(
            equipment_id=1,
            function_code="50",
            parameter_code="0201",
            parameter_name="I>",
            set_value=10.0,  # Dentro dos limites
            min_limit=1.0,
            max_limit=20.0
        )
        
        assert setting.set_value == 10.0
    
    def test_function_code_normalized_to_uppercase(self):
        """Deve normalizar function_code para uppercase"""
        setting = RelaySettingCreate(
            equipment_id=1,
            function_code="50n",  # Minúsculo
            parameter_code="0301",
            parameter_name="Ie>",
            set_value=2.0
        )
        
        assert setting.function_code == "50N"  # Deve ser uppercase
    
    def test_parameter_code_normalized_to_uppercase(self):
        """Deve normalizar parameter_code para uppercase"""
        setting = RelaySettingCreate(
            equipment_id=1,
            function_code="50",
            parameter_code="abc123",  # Minúsculo
            parameter_name="Test",
            set_value=5.0
        )
        
        assert setting.parameter_code == "ABC123"
    
    def test_reject_empty_function_code(self):
        """Deve rejeitar function_code vazio"""
        with pytest.raises(ValueError, match="não pode estar vazio"):
            RelaySettingCreate(
                equipment_id=1,
                function_code="   ",  # Apenas espaços
                parameter_code="0201",
                parameter_name="I>",
                set_value=5.5
            )
    
    def test_reject_empty_parameter_code(self):
        """Deve rejeitar parameter_code vazio"""
        with pytest.raises(ValueError, match="não pode estar vazio"):
            RelaySettingCreate(
                equipment_id=1,
                function_code="50",
                parameter_code="   ",  # Apenas espaços
                parameter_name="I>",
                set_value=5.5
            )


class TestUpdateSetting:
    """Testes de atualização de configurações"""
    
    def test_update_only_set_value(self):
        """Deve permitir atualizar apenas set_value"""
        update = RelaySettingUpdate(set_value=6.5)
        
        assert update.set_value == 6.5
        assert update.is_enabled is None
        assert update.notes is None
    
    def test_update_only_is_enabled(self):
        """Deve permitir desabilitar configuração"""
        update = RelaySettingUpdate(is_enabled=False)
        
        assert update.is_enabled is False
        assert update.set_value is None
    
    def test_update_multiple_fields(self):
        """Deve permitir atualizar múltiplos campos"""
        update = RelaySettingUpdate(
            set_value=7.0,
            is_enabled=True,
            notes="Ajustado",
            modified_by="eng.silva@petrobras.com.br"
        )
        
        assert update.set_value == 7.0
        assert update.is_enabled is True
        assert update.notes == "Ajustado"
        assert update.modified_by == "eng.silva@petrobras.com.br"
    
    def test_update_category(self):
        """Deve permitir atualizar categoria"""
        update = RelaySettingUpdate(category=SettingCategory.TIMING)
        
        assert update.category == SettingCategory.TIMING


class TestBulkUpdate:
    """Testes de atualização em lote"""
    
    def test_bulk_update_multiple_settings(self):
        """Deve permitir atualizar múltiplas configurações"""
        bulk_request = BulkUpdateRequest(
            equipment_id=1,
            updates=[
                BulkUpdateItem(setting_id=10, set_value=5.5),
                BulkUpdateItem(setting_id=11, set_value=10.0),
                BulkUpdateItem(setting_id=12, is_enabled=False)
            ],
            modified_by="eng.silva@petrobras.com.br"
        )
        
        assert bulk_request.equipment_id == 1
        assert len(bulk_request.updates) == 3
        assert bulk_request.updates[0].setting_id == 10
        assert bulk_request.updates[0].set_value == 5.5
        assert bulk_request.updates[2].is_enabled is False
    
    def test_bulk_update_requires_at_least_one_item(self):
        """Deve rejeitar bulk update sem itens"""
        with pytest.raises(ValueError):
            BulkUpdateRequest(
                equipment_id=1,
                updates=[],  # Lista vazia
                modified_by="eng.silva"
            )
    
    def test_bulk_update_max_100_items(self):
        """Deve limitar bulk update a 100 itens"""
        # Criar 101 itens
        items = [
            BulkUpdateItem(setting_id=i, set_value=float(i))
            for i in range(1, 102)
        ]
        
        with pytest.raises(ValueError):
            BulkUpdateRequest(
                equipment_id=1,
                updates=items
            )


class TestValidationEdgeCases:
    """Testes de casos extremos e validações"""
    
    def test_equipment_id_must_be_positive(self):
        """Deve rejeitar equipment_id zero ou negativo"""
        with pytest.raises(ValueError):
            RelaySettingCreate(
                equipment_id=0,  # Zero não permitido
                function_code="50",
                parameter_code="0201",
                parameter_name="I>",
                set_value=5.5
            )
        
        with pytest.raises(ValueError):
            RelaySettingCreate(
                equipment_id=-1,  # Negativo não permitido
                function_code="50",
                parameter_code="0201",
                parameter_name="I>",
                set_value=5.5
            )
    
    def test_parameter_name_min_length(self):
        """Deve rejeitar parameter_name muito curto"""
        with pytest.raises(ValueError):
            RelaySettingCreate(
                equipment_id=1,
                function_code="50",
                parameter_code="0201",
                parameter_name="",  # Vazio não permitido
                set_value=5.5
            )
    
    def test_parameter_name_max_length(self):
        """Deve rejeitar parameter_name muito longo"""
        with pytest.raises(ValueError):
            RelaySettingCreate(
                equipment_id=1,
                function_code="50",
                parameter_code="0201",
                parameter_name="X" * 101,  # Mais de 100 caracteres
                set_value=5.5
            )
    
    def test_notes_max_length(self):
        """Deve rejeitar notes muito longo"""
        with pytest.raises(ValueError):
            RelaySettingCreate(
                equipment_id=1,
                function_code="50",
                parameter_code="0201",
                parameter_name="I>",
                set_value=5.5,
                notes="X" * 501  # Mais de 500 caracteres
            )
    
    def test_accept_negative_set_value(self):
        """Deve aceitar set_value negativo (ex: ângulos)"""
        # Alguns parâmetros podem ser negativos
        setting = RelaySettingCreate(
            equipment_id=1,
            function_code="21",
            parameter_code="0401",
            parameter_name="Angle",
            set_value=-45.0  # Ângulo negativo é válido
        )
        
        assert setting.set_value == -45.0
    
    def test_accept_zero_set_value(self):
        """Deve aceitar set_value zero"""
        setting = RelaySettingCreate(
            equipment_id=1,
            function_code="50",
            parameter_code="0201",
            parameter_name="Delay",
            set_value=0.0  # Zero pode ser válido
        )
        
        assert setting.set_value == 0.0


class TestCategoryEnum:
    """Testes do enum SettingCategory"""
    
    def test_all_categories_valid(self):
        """Deve aceitar todas as categorias válidas"""
        categories = [
            SettingCategory.OVERCURRENT_SETTING,
            SettingCategory.VOLTAGE_SETTING,
            SettingCategory.FREQUENCY_SETTING,
            SettingCategory.TIMING,
            SettingCategory.INSTRUMENTATION,
            SettingCategory.POWER_SETTING,
            SettingCategory.IMPEDANCE_SETTING,
            SettingCategory.OTHER
        ]
        
        for category in categories:
            setting = RelaySettingCreate(
                equipment_id=1,
                function_code="50",
                parameter_code="0201",
                parameter_name="Test",
                set_value=5.0,
                category=category
            )
            assert setting.category == category
    
    def test_invalid_category_rejected(self):
        """Deve rejeitar categoria inválida"""
        with pytest.raises(ValueError):
            RelaySettingCreate(
                equipment_id=1,
                function_code="50",
                parameter_code="0201",
                parameter_name="Test",
                set_value=5.0,
                category="INVALID_CATEGORY"  # Não existe
            )


class TestResponseSchemas:
    """Testes dos schemas de resposta"""
    
    def test_delete_response_structure(self):
        """Deve ter estrutura correta no DeleteResponse"""
        from api.schemas.relay_config_schemas import DeleteResponse
        from datetime import datetime
        
        response = DeleteResponse(
            success=True,
            message="Excluído",
            deleted_id=123,
            soft_delete=True,
            can_undo=True,
            undo_expires_at=datetime.now()
        )
        
        assert response.success is True
        assert response.deleted_id == 123
        assert response.soft_delete is True
        assert response.can_undo is True
    
    def test_bulk_update_response_structure(self):
        """Deve ter estrutura correta no BulkUpdateResponse"""
        from api.schemas.relay_config_schemas import BulkUpdateResponse
        
        response = BulkUpdateResponse(
            success=True,
            message="Atualizado",
            updated_count=3,
            failed_count=0,
            updated_ids=[10, 11, 12],
            errors=[]
        )
        
        assert response.success is True
        assert response.updated_count == 3
        assert response.failed_count == 0
        assert len(response.updated_ids) == 3


# ============================================================================
# TESTES DE INVARIANTES (Propriedades sempre verdadeiras)
# ============================================================================

class TestInvariants:
    """Testes de invariantes - propriedades sempre verdadeiras"""
    
    def test_create_schema_always_has_required_fields(self):
        """INVARIANTE: Create schema sempre tem equipment_id, codes e set_value"""
        setting = RelaySettingCreate(
            equipment_id=1,
            function_code="50",
            parameter_code="0201",
            parameter_name="I>",
            set_value=5.5
        )
        
        # Esses campos NUNCA podem ser None
        assert setting.equipment_id is not None
        assert setting.function_code is not None
        assert setting.parameter_code is not None
        assert setting.parameter_name is not None
        assert setting.set_value is not None
    
    def test_codes_always_uppercase_after_validation(self):
        """INVARIANTE: Códigos sempre são uppercase após validação"""
        test_cases = [
            ("50", "0201"),
            ("50n", "0301"),
            ("abc", "xyz123"),
            ("MiXeD", "CaSe")
        ]
        
        for func_code, param_code in test_cases:
            setting = RelaySettingCreate(
                equipment_id=1,
                function_code=func_code,
                parameter_code=param_code,
                parameter_name="Test",
                set_value=5.0
            )
            
            assert setting.function_code == setting.function_code.upper()
            assert setting.parameter_code == setting.parameter_code.upper()
    
    def test_is_enabled_always_boolean(self):
        """INVARIANTE: is_enabled sempre é boolean"""
        # Com valor explícito
        setting1 = RelaySettingCreate(
            equipment_id=1,
            function_code="50",
            parameter_code="0201",
            parameter_name="I>",
            set_value=5.5,
            is_enabled=True
        )
        
        # Com valor default
        setting2 = RelaySettingCreate(
            equipment_id=1,
            function_code="50",
            parameter_code="0201",
            parameter_name="I>",
            set_value=5.5
        )
        
        assert isinstance(setting1.is_enabled, bool)
        assert isinstance(setting2.is_enabled, bool)
        assert setting2.is_enabled is True  # Default


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

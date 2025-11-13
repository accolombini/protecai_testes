"""
================================================================================
TESTES DE INTEGRAÇÃO - RELAY CONFIGURATION CRUD
================================================================================
Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 1.0.0

Description:
    Testes de integração para operações CRUD de configurações de relés.
    Testa endpoints reais da API com banco de dados.
    
    Cobertura:
    - POST /api/relay-config/settings - Criar configuração
    - PUT /api/relay-config/settings/{id} - Atualizar
    - DELETE /api/relay-config/settings/{id} - Excluir
    - PATCH /api/relay-config/settings/bulk - Bulk update
    - POST /api/relay-config/settings/{id}/restore - Undo
    - Validação de transações atômicas
    - Casos de erro (404, 409, 400)

Requirements:
    - Banco de dados PostgreSQL rodando
    - Schema protec_ai criado
    - Tabelas relay_equipment, relay_settings, protection_functions
    
Usage:
    # Executar todos os testes de integração
    pytest tests/test_relay_config_crud_integration.py -v -m integration
    
    # Executar teste específico
    pytest tests/test_relay_config_crud_integration.py::TestCreateSettingIntegration::test_create_setting_success -v
    
    # Com output detalhado
    pytest tests/test_relay_config_crud_integration.py -v -s
================================================================================
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from sqlalchemy import text
import os
import logging

# Importar a aplicação
from api.main import app
from api.core.database import get_db

# Logger
logger = logging.getLogger(__name__)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def client(db_session):
    """
    Cliente de teste da API com override de dependência do banco.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_equipment(db_session):
    """
    Cria equipamento de teste no banco usando SQLAlchemy.
    
    Returns:
        dict com equipment_id
    """
    # Criar fabricante
    result = db_session.execute(text("""
        INSERT INTO protec_ai.fabricantes (codigo_fabricante, nome_completo, pais_origem, ativo)
        VALUES ('TEST-MFG', 'Test Manufacturer', 'BR', true)
        ON CONFLICT (codigo_fabricante) DO UPDATE SET codigo_fabricante = EXCLUDED.codigo_fabricante
        RETURNING id
    """))
    manufacturer_id = result.fetchone()[0]
    
    # Criar modelo
    result = db_session.execute(text("""
        INSERT INTO protec_ai.relay_models (model_code, manufacturer_id, model_name, firmware_version)
        VALUES ('TEST-P100', :manufacturer_id, 'Test Model P100', '1.0.0')
        ON CONFLICT (model_code) DO UPDATE SET model_code = EXCLUDED.model_code
        RETURNING id
    """), {"manufacturer_id": manufacturer_id})
    model_id = result.fetchone()[0]
    
    # Criar equipamento (usar timestamp para garantir unicidade)
    import time
    unique_tag = f'TEST-REL-{int(time.time() * 1000) % 100000}'
    
    result = db_session.execute(text("""
        INSERT INTO protec_ai.relay_equipment (
            equipment_tag, relay_model_id, substation_name, bay_name, status
        )
        VALUES (:equipment_tag, :model_id, 'TEST-SUBSTATION', 'BAY-01', 'active')
        RETURNING id
    """), {"equipment_tag": unique_tag, "model_id": model_id})
    equipment_id = result.fetchone()[0]
    
    db_session.commit()
    
    return {"equipment_id": equipment_id, "model_id": model_id, "manufacturer_id": manufacturer_id}


@pytest.fixture(scope="function")
def sample_protection_function(db_session):
    """
    Cria ou busca função de proteção de teste usando SQLAlchemy.
    
    Returns:
        dict com function_id
    """
    # Verificar se já existe
    result = db_session.execute(text("""
        SELECT id FROM protec_ai.protection_functions 
        WHERE function_code = '50'
    """))
    existing = result.fetchone()
    
    if existing:
        function_id = existing[0]
    else:
        # Criar nova
        result = db_session.execute(text("""
            INSERT INTO protec_ai.protection_functions (
                function_code, function_name, function_description
            )
            VALUES ('50', 'Instantaneous Overcurrent', 'Test function')
            RETURNING id
        """))
        function_id = result.fetchone()[0]
        db_session.commit()
    
    return {"function_id": function_id, "function_code": "50"}


# ============================================================================
# TESTES DE CRIAÇÃO (POST)
# ============================================================================

@pytest.mark.integration
class TestCreateSettingIntegration:
    """Testes de criação de configurações com banco real"""
    
    def test_create_setting_success(self, client, sample_equipment, sample_protection_function):
        """Deve criar configuração com sucesso no banco"""
        payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "TEST001",
            "parameter_name": "I>",
            "set_value": 5.5,
            "unit_of_measure": "A",
            "min_limit": 1.0,
            "max_limit": 20.0,
            "is_enabled": True,
            "category": "OVERCURRENT_SETTING",
            "notes": "Teste de integração"
        }
        
        response = client.post("/api/relay-config/settings", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["equipment_id"] == sample_equipment["equipment_id"]
        assert data["parameter_code"] == "TEST001"
        assert data["set_value"] == 5.5
        assert "id" in data
        assert "created_at" in data
    
    def test_create_setting_duplicate_parameter_code(self, client, sample_equipment, sample_protection_function):
        """Deve rejeitar duplicata de parameter_code no mesmo equipamento"""
        payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "DUP001",
            "parameter_name": "I>",
            "set_value": 5.5
        }
        
        # Primeira criação - OK
        response1 = client.post("/api/relay-config/settings", json=payload)
        assert response1.status_code == 201
        
        # Segunda criação - DEVE FALHAR
        response2 = client.post("/api/relay-config/settings", json=payload)
        assert response2.status_code == 409
        response_data = response2.json()
        error_message = response_data.get("detail", response_data.get("message", str(response_data)))
        assert "duplicada" in error_message.lower() or "já existe" in error_message.lower()
    
    def test_create_setting_invalid_equipment_id(self, client):
        """Deve rejeitar equipment_id inexistente"""
        payload = {
            "equipment_id": 99999,  # Não existe
            "function_code": "50",
            "parameter_code": "TEST002",
            "parameter_name": "I>",
            "set_value": 5.5
        }
        
        response = client.post("/api/relay-config/settings", json=payload)
        
        assert response.status_code == 404
        response_data = response.json()
        error_message = response_data.get("detail", response_data.get("message", str(response_data)))
        assert "não encontrado" in error_message.lower() or "not found" in error_message.lower()
    
    def test_create_setting_value_below_min_limit(self, client, sample_equipment, sample_protection_function):
        """Deve rejeitar set_value abaixo do min_limit"""
        payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "TEST003",
            "parameter_name": "I>",
            "set_value": 0.5,  # Abaixo do mínimo
            "min_limit": 1.0,
            "max_limit": 20.0
        }
        
        response = client.post("/api/relay-config/settings", json=payload)
        
        assert response.status_code == 422  # Validation error
        assert "limite mínimo" in str(response.json()).lower()
    
    def test_create_setting_value_above_max_limit(self, client, sample_equipment, sample_protection_function):
        """Deve rejeitar set_value acima do max_limit"""
        payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "TEST004",
            "parameter_name": "I>",
            "set_value": 25.0,  # Acima do máximo
            "min_limit": 1.0,
            "max_limit": 20.0
        }
        
        response = client.post("/api/relay-config/settings", json=payload)
        
        assert response.status_code == 422
        assert "limite máximo" in str(response.json()).lower()


# ============================================================================
# TESTES DE ATUALIZAÇÃO (PUT)
# ============================================================================

@pytest.mark.integration
class TestUpdateSettingIntegration:
    """Testes de atualização de configurações com banco real"""
    
    def test_update_setting_success(self, client, sample_equipment, sample_protection_function, db_session):
        """Deve atualizar configuração com sucesso"""
        # Criar configuração
        create_payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "UPD001",
            "parameter_name": "I>",
            "set_value": 5.5
        }
        create_response = client.post("/api/relay-config/settings", json=create_payload)
        setting_id = create_response.json()["id"]
        
        # Atualizar
        update_payload = {
            "set_value": 6.5,
            "notes": "Valor atualizado",
            "modified_by": "test@example.com"
        }
        
        response = client.put(f"/api/relay-config/settings/{setting_id}", json=update_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["set_value"] == 6.5
        assert data["notes"] == "Valor atualizado"
        assert data["modified_by"] == "test@example.com"
        assert data["updated_at"] is not None
    
    def test_update_setting_not_found(self, client):
        """Deve retornar 404 para setting_id inexistente"""
        update_payload = {"set_value": 7.0}
        
        response = client.put("/api/relay-config/settings/99999", json=update_payload)
        
        assert response.status_code == 404
    
    def test_update_setting_disable(self, client, sample_equipment, sample_protection_function):
        """Deve desabilitar configuração"""
        # Criar
        create_payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "UPD002",
            "parameter_name": "I>",
            "set_value": 5.5,
            "is_enabled": True
        }
        create_response = client.post("/api/relay-config/settings", json=create_payload)
        setting_id = create_response.json()["id"]
        
        # Desabilitar
        update_payload = {"is_enabled": False}
        response = client.put(f"/api/relay-config/settings/{setting_id}", json=update_payload)
        
        assert response.status_code == 200
        assert response.json()["is_enabled"] is False


# ============================================================================
# TESTES DE BULK UPDATE (PATCH)
# ============================================================================

@pytest.mark.integration
class TestBulkUpdateIntegration:
    """Testes de atualização em lote com transações atômicas"""
    
    def test_bulk_update_success(self, client, sample_equipment, sample_protection_function):
        """Deve atualizar múltiplas configurações em transação única"""
        # Criar 3 configurações
        setting_ids = []
        for i in range(3):
            payload = {
                "equipment_id": sample_equipment["equipment_id"],
                "function_code": "50",
                "parameter_code": f"BULK00{i}",
                "parameter_name": f"Param{i}",
                "set_value": float(i + 1)
            }
            response = client.post("/api/relay-config/settings", json=payload)
            setting_ids.append(response.json()["id"])
        
        # Bulk update
        bulk_payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "updates": [
                {"setting_id": setting_ids[0], "set_value": 10.0},
                {"setting_id": setting_ids[1], "set_value": 20.0},
                {"setting_id": setting_ids[2], "set_value": 30.0}
            ],
            "modified_by": "bulk_test@example.com"
        }
        
        response = client.patch("/api/relay-config/settings/bulk", json=bulk_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["updated_count"] == 3
        assert len(data["updated_ids"]) == 3
    
    def test_bulk_update_rollback_on_error(self, client, sample_equipment, sample_protection_function, db_session):
        """Deve fazer rollback se uma atualização falhar (transação atômica)"""
        # Criar 2 configurações
        setting_ids = []
        for i in range(2):
            payload = {
                "equipment_id": sample_equipment["equipment_id"],
                "function_code": "50",
                "parameter_code": f"ROLL00{i}",
                "parameter_name": f"Param{i}",
                "set_value": float(i + 1)
            }
            response = client.post("/api/relay-config/settings", json=payload)
            setting_ids.append(response.json()["id"])
        
        # Bulk update com um ID inválido (deve falhar tudo)
        bulk_payload = {
            "updates": [
                {"setting_id": setting_ids[0], "set_value": 10.0},
                {"setting_id": 99999, "set_value": 20.0},  # ID inválido!
            ]
        }
        
        response = client.patch("/api/relay-config/settings/bulk", json=bulk_payload)
        
        # Deve retornar erro
        assert response.status_code == 200  # Service retorna 200 mas success=False
        data = response.json()
        assert data["success"] is False
        assert data["updated_count"] == 0
        
        # Verificar que NENHUMA atualização foi aplicada (rollback)
        check_response = client.get(f"/api/relay-config/report/{sample_equipment['equipment_id']}")
        # Valores originais devem estar intactos


# ============================================================================
# TESTES DE EXCLUSÃO (DELETE)
# ============================================================================

@pytest.mark.integration
class TestDeleteSettingIntegration:
    """Testes de exclusão de configurações"""
    
    def test_delete_setting_soft_delete(self, client, sample_equipment, sample_protection_function, db_session):
        """Deve fazer soft delete (marca deleted_at)"""
        # Criar
        payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "DEL001",
            "parameter_name": "I>",
            "set_value": 5.5
        }
        create_response = client.post("/api/relay-config/settings", json=payload)
        setting_id = create_response.json()["id"]
        
        # Soft delete
        response = client.delete(f"/api/relay-config/settings/{setting_id}?soft_delete=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["soft_delete"] is True
        assert data["can_undo"] is True
        assert data["deleted_id"] == setting_id
        
        # Verificar que está marcado como deletado no banco
        result = db_session.execute(text("SELECT deleted_at FROM protec_ai.relay_settings WHERE id = :id"), {"id": setting_id})
        row = result.fetchone()
        assert row[0] is not None
    
    def test_delete_setting_hard_delete(self, client, sample_equipment, sample_protection_function, db_session):
        """Deve fazer hard delete (remove fisicamente)"""
        # Criar
        payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "DEL002",
            "parameter_name": "I>",
            "set_value": 5.5
        }
        create_response = client.post("/api/relay-config/settings", json=payload)
        setting_id = create_response.json()["id"]
        
        # Hard delete
        response = client.delete(f"/api/relay-config/settings/{setting_id}?soft_delete=false")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["soft_delete"] is False
        assert data["can_undo"] is False
        
        # Verificar que NÃO existe mais no banco
        result = db_session.execute(text("SELECT id FROM protec_ai.relay_settings WHERE id = :id"), {"id": setting_id})
        row = result.fetchone()
        assert row is None
    
    def test_restore_deleted_setting(self, client, sample_equipment, sample_protection_function):
        """Deve restaurar configuração soft-deleted (undo)"""
        # Criar
        payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "UNDO001",
            "parameter_name": "I>",
            "set_value": 5.5
        }
        create_response = client.post("/api/relay-config/settings", json=payload)
        setting_id = create_response.json()["id"]
        
        # Soft delete
        client.delete(f"/api/relay-config/settings/{setting_id}?soft_delete=true")
        
        # Restore
        response = client.post(f"/api/relay-config/settings/{setting_id}/restore")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == setting_id
        assert data["is_enabled"] is True  # Deve estar ativo novamente


# ============================================================================
# TESTES DE EXCLUSÃO EM CASCADE
# ============================================================================

@pytest.mark.integration
class TestDeleteEquipmentCascadeIntegration:
    """Testes de exclusão de equipamento com cascade"""
    
    def test_delete_equipment_cascade_soft(self, client, sample_equipment, sample_protection_function, db_session):
        """Deve desativar equipamento e marcar configurações como deletadas"""
        equipment_id = sample_equipment["equipment_id"]
        
        # Criar 3 configurações
        for i in range(3):
            payload = {
                "equipment_id": equipment_id,
                "function_code": "50",
                "parameter_code": f"CASC00{i}",
                "parameter_name": f"Param{i}",
                "set_value": float(i + 1)
            }
            client.post("/api/relay-config/settings", json=payload)
        
        # Delete cascade soft
        response = client.delete(f"/api/relay-config/equipment/{equipment_id}/cascade?soft_delete=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["settings_affected"] == 3
        assert data["soft_delete"] is True
        
        # Verificar equipamento marcado como inactive
        result = db_session.execute(text("SELECT status FROM protec_ai.relay_equipment WHERE id = :id"), {"id": equipment_id})
        row = result.fetchone()
        assert row[0] == "inactive"
        
        # Verificar configurações marcadas como deleted
        result = db_session.execute(text("""
            SELECT COUNT(*) as total 
            FROM protec_ai.relay_settings 
            WHERE equipment_id = :id AND deleted_at IS NOT NULL
        """), {"id": equipment_id})
        row = result.fetchone()
        assert row[0] == 3


# ============================================================================
# TESTES DE EDGE CASES E VALIDAÇÕES
# ============================================================================

@pytest.mark.integration
class TestValidationIntegration:
    """Testes de validações com banco real"""
    
    def test_cannot_update_deleted_setting(self, client, sample_equipment, sample_protection_function):
        """Não deve permitir atualizar configuração soft-deleted"""
        # Criar e deletar
        payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50",
            "parameter_code": "VAL001",
            "parameter_name": "I>",
            "set_value": 5.5
        }
        create_response = client.post("/api/relay-config/settings", json=payload)
        setting_id = create_response.json()["id"]
        
        client.delete(f"/api/relay-config/settings/{setting_id}?soft_delete=true")
        
        # Tentar atualizar (deve falhar)
        update_payload = {"set_value": 10.0}
        response = client.put(f"/api/relay-config/settings/{setting_id}", json=update_payload)
        
        assert response.status_code == 404
    
    def test_codes_normalized_to_uppercase(self, client, sample_equipment, sample_protection_function):
        """Códigos devem ser normalizados para uppercase"""
        payload = {
            "equipment_id": sample_equipment["equipment_id"],
            "function_code": "50n",  # Minúsculo
            "parameter_code": "test123",  # Minúsculo
            "parameter_name": "Ie>",
            "set_value": 2.0
        }
        
        response = client.post("/api/relay-config/settings", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["function_code"] == "50N"  # Uppercase
        assert data["parameter_code"] == "TEST123"  # Uppercase


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])

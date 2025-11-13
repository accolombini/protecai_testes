"""
================================================================================
TESTES DE INTEGRAÇÃO - RELAY CONFIGURATION CRUD (COM BANCO DE DADOS)
================================================================================
Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 1.0.0

Description:
    Testes de integração para operações CRUD de configurações de relés.
    REQUER BANCO DE DADOS PostgreSQL rodando!
    
    Cobertura:
    - Conexão com banco de dados real
    - Endpoints POST/PUT/DELETE funcionando
    - Transações atômicas em bulk update
    - Rollback em caso de erro
    - Casos de erro: 404, 409, 400
    - Soft delete vs hard delete
    - Restore (undo)

Pré-requisitos:
    - PostgreSQL rodando (docker ou local)
    - Banco de dados 'protecai_db' criado
    - Schema 'protec_ai' criado
    - Tabelas relay_equipment e relay_settings criadas

Usage:
    # Executar todos os testes de integração
    pytest tests/test_relay_config_integration.py -v -m integration
    
    # Pular testes de integração
    pytest tests/ -m "not integration"
================================================================================
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Marcar todos os testes como integration
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_engine():
    """
    Cria conexão com banco de dados PostgreSQL.
    Usa as mesmas credenciais do docker-compose.
    """
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/protecai_db"
    
    engine = create_engine(DATABASE_URL, echo=False)
    
    # Testar conexão
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        print("✅ Conexão com PostgreSQL estabelecida")
    except Exception as e:
        pytest.skip(f"❌ PostgreSQL não disponível: {e}")
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="module")
def db_session(db_engine):
    """Cria sessão de banco de dados para testes"""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture(scope="module")
def test_client():
    """Cria cliente de teste FastAPI"""
    from api.main import app
    from api.core.database import get_db
    
    # Cliente de teste
    client = TestClient(app)
    
    yield client


@pytest.fixture(scope="function")
def cleanup_test_data(db_session):
    """
    Fixture para limpar dados de teste após cada teste.
    Roda DEPOIS de cada teste.
    """
    yield
    
    # Limpar dados de teste criados
    try:
        db_session.execute(text("""
            DELETE FROM protec_ai.relay_settings 
            WHERE parameter_code LIKE 'TEST_%'
        """))
        db_session.commit()
        print("🧹 Dados de teste limpos")
    except Exception as e:
        db_session.rollback()
        print(f"⚠️ Erro ao limpar dados de teste: {e}")


@pytest.fixture(scope="module")
def setup_test_equipment(db_session):
    """
    Cria equipamento de teste para usar nos testes.
    Roda UMA VEZ no início do módulo.
    """
    # Verificar se já existe equipamento
    result = db_session.execute(text("""
        SELECT id FROM protec_ai.relay_equipment LIMIT 1
    """)).fetchone()
    
    if result:
        equipment_id = result[0]
        print(f"✅ Usando equipamento existente: ID={equipment_id}")
        yield equipment_id
    else:
        # Criar equipamento de teste se não existir
        pytest.skip("❌ Nenhum equipamento encontrado no banco. Execute migrations primeiro.")


# ============================================================================
# TESTES DE CRIAÇÃO (POST /api/relay-config/settings)
# ============================================================================

class TestCreateSettingIntegration:
    """Testes de criação de configurações com banco real"""
    
    def test_create_setting_success(self, test_client, setup_test_equipment, cleanup_test_data):
        """Deve criar configuração no banco de dados"""
        payload = {
            "equipment_id": setup_test_equipment,
            "function_code": "50",
            "parameter_code": "TEST_0001",
            "parameter_name": "I> Test",
            "set_value": 5.5,
            "unit_of_measure": "A",
            "min_limit": 1.0,
            "max_limit": 20.0,
            "is_enabled": True,
            "notes": "Teste de integração"
        }
        
        response = test_client.post("/api/relay-config/settings", json=payload)
        
        assert response.status_code == 201, f"Erro: {response.text}"
        data = response.json()
        
        assert data["equipment_id"] == setup_test_equipment
        assert data["parameter_code"] == "TEST_0001"
        assert data["set_value"] == 5.5
        assert data["is_enabled"] is True
        assert "id" in data
        assert "created_at" in data
        
        print(f"✅ Configuração criada: ID={data['id']}")
    
    def test_create_setting_duplicate_fails(self, test_client, setup_test_equipment, cleanup_test_data):
        """Deve rejeitar configuração duplicada (mesmo parameter_code)"""
        payload = {
            "equipment_id": setup_test_equipment,
            "function_code": "50",
            "parameter_code": "TEST_DUP",
            "parameter_name": "Duplicate Test",
            "set_value": 5.5
        }
        
        # Primeira criação: sucesso
        response1 = test_client.post("/api/relay-config/settings", json=payload)
        assert response1.status_code == 201
        
        # Segunda criação: deve falhar (409 Conflict)
        response2 = test_client.post("/api/relay-config/settings", json=payload)
        assert response2.status_code == 409
        assert "duplicada" in response2.json()["detail"].lower()
        
        print("✅ Duplicata rejeitada corretamente")
    
    def test_create_setting_invalid_equipment_fails(self, test_client, cleanup_test_data):
        """Deve rejeitar equipment_id inexistente (404)"""
        payload = {
            "equipment_id": 999999,  # ID que não existe
            "function_code": "50",
            "parameter_code": "TEST_INVALID",
            "parameter_name": "Invalid Test",
            "set_value": 5.5
        }
        
        response = test_client.post("/api/relay-config/settings", json=payload)
        
        assert response.status_code == 404
        assert "não encontrado" in response.json()["detail"].lower()
        
        print("✅ Equipment inexistente rejeitado")
    
    def test_create_setting_value_out_of_limits_fails(self, test_client, setup_test_equipment):
        """Deve rejeitar valor fora dos limites (400)"""
        payload = {
            "equipment_id": setup_test_equipment,
            "function_code": "50",
            "parameter_code": "TEST_LIMITS",
            "parameter_name": "Limits Test",
            "set_value": 25.0,  # Acima do max_limit
            "min_limit": 1.0,
            "max_limit": 20.0
        }
        
        response = test_client.post("/api/relay-config/settings", json=payload)
        
        assert response.status_code == 422  # Pydantic validation error
        assert "acima do limite máximo" in response.text.lower()
        
        print("✅ Valor fora dos limites rejeitado")


# ============================================================================
# TESTES DE ATUALIZAÇÃO (PUT /api/relay-config/settings/{id})
# ============================================================================

class TestUpdateSettingIntegration:
    """Testes de atualização de configurações com banco real"""
    
    @pytest.fixture
    def created_setting(self, test_client, setup_test_equipment, cleanup_test_data):
        """Cria uma configuração para atualizar nos testes"""
        payload = {
            "equipment_id": setup_test_equipment,
            "function_code": "50",
            "parameter_code": "TEST_UPDATE",
            "parameter_name": "Update Test",
            "set_value": 5.5,
            "min_limit": 1.0,
            "max_limit": 20.0
        }
        
        response = test_client.post("/api/relay-config/settings", json=payload)
        assert response.status_code == 201
        
        return response.json()
    
    def test_update_setting_success(self, test_client, created_setting):
        """Deve atualizar configuração existente"""
        setting_id = created_setting["id"]
        
        update_payload = {
            "set_value": 7.5,
            "notes": "Valor atualizado",
            "modified_by": "test@petrobras.com.br"
        }
        
        response = test_client.put(
            f"/api/relay-config/settings/{setting_id}",
            json=update_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == setting_id
        assert data["set_value"] == 7.5
        assert data["notes"] == "Valor atualizado"
        assert data["modified_by"] == "test@petrobras.com.br"
        assert data["updated_at"] is not None
        
        print(f"✅ Configuração atualizada: ID={setting_id}")
    
    def test_update_setting_not_found(self, test_client):
        """Deve retornar 404 para ID inexistente"""
        update_payload = {"set_value": 10.0}
        
        response = test_client.put(
            "/api/relay-config/settings/999999",
            json=update_payload
        )
        
        assert response.status_code == 404
        assert "não encontrada" in response.json()["detail"].lower()
        
        print("✅ Update de ID inexistente retorna 404")
    
    def test_update_setting_value_out_of_limits(self, test_client, created_setting):
        """Deve rejeitar atualização com valor fora dos limites"""
        setting_id = created_setting["id"]
        
        update_payload = {
            "set_value": 25.0  # Acima do max_limit (20.0)
        }
        
        response = test_client.put(
            f"/api/relay-config/settings/{setting_id}",
            json=update_payload
        )
        
        assert response.status_code == 400
        assert "limite máximo" in response.json()["detail"].lower()
        
        print("✅ Atualização com valor fora dos limites rejeitada")
    
    def test_update_setting_disable(self, test_client, created_setting):
        """Deve permitir desabilitar configuração"""
        setting_id = created_setting["id"]
        
        update_payload = {"is_enabled": False}
        
        response = test_client.put(
            f"/api/relay-config/settings/{setting_id}",
            json=update_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
        
        print(f"✅ Configuração desabilitada: ID={setting_id}")


# ============================================================================
# TESTES DE BULK UPDATE (PATCH /api/relay-config/settings/bulk)
# ============================================================================

class TestBulkUpdateIntegration:
    """Testes de atualização em lote com transações atômicas"""
    
    @pytest.fixture
    def multiple_settings(self, test_client, setup_test_equipment, cleanup_test_data):
        """Cria 3 configurações para bulk update"""
        settings = []
        
        for i in range(1, 4):
            payload = {
                "equipment_id": setup_test_equipment,
                "function_code": "50",
                "parameter_code": f"TEST_BULK_{i:03d}",
                "parameter_name": f"Bulk Test {i}",
                "set_value": float(i * 5),
                "min_limit": 1.0,
                "max_limit": 50.0
            }
            
            response = test_client.post("/api/relay-config/settings", json=payload)
            assert response.status_code == 201
            settings.append(response.json())
        
        return settings
    
    def test_bulk_update_success(self, test_client, multiple_settings):
        """Deve atualizar múltiplas configurações em transação única"""
        bulk_payload = {
            "equipment_id": multiple_settings[0]["equipment_id"],
            "updates": [
                {"setting_id": multiple_settings[0]["id"], "set_value": 6.0},
                {"setting_id": multiple_settings[1]["id"], "set_value": 12.0},
                {"setting_id": multiple_settings[2]["id"], "set_value": 18.0}
            ],
            "modified_by": "bulk_test@petrobras.com.br"
        }
        
        response = test_client.patch("/api/relay-config/settings/bulk", json=bulk_payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["updated_count"] == 3
        assert data["failed_count"] == 0
        assert len(data["updated_ids"]) == 3
        
        print(f"✅ Bulk update bem-sucedido: {data['updated_count']} itens")
    
    def test_bulk_update_rollback_on_error(self, test_client, multiple_settings):
        """Deve fazer rollback se uma atualização falhar"""
        bulk_payload = {
            "equipment_id": multiple_settings[0]["equipment_id"],
            "updates": [
                {"setting_id": multiple_settings[0]["id"], "set_value": 6.0},
                {"setting_id": 999999, "set_value": 12.0},  # ID inexistente -> ERRO
                {"setting_id": multiple_settings[2]["id"], "set_value": 18.0}
            ]
        }
        
        response = test_client.patch("/api/relay-config/settings/bulk", json=bulk_payload)
        
        data = response.json()
        
        assert data["success"] is False
        assert data["updated_count"] == 0  # NENHUM atualizado (rollback)
        assert len(data["errors"]) > 0
        
        print("✅ Rollback funcionou: nenhuma atualização aplicada")


# ============================================================================
# TESTES DE EXCLUSÃO (DELETE)
# ============================================================================

class TestDeleteSettingIntegration:
    """Testes de exclusão (soft/hard delete) com banco real"""
    
    @pytest.fixture
    def created_setting(self, test_client, setup_test_equipment, cleanup_test_data):
        """Cria configuração para excluir"""
        payload = {
            "equipment_id": setup_test_equipment,
            "function_code": "50",
            "parameter_code": "TEST_DELETE",
            "parameter_name": "Delete Test",
            "set_value": 5.5
        }
        
        response = test_client.post("/api/relay-config/settings", json=payload)
        return response.json()
    
    def test_soft_delete_success(self, test_client, created_setting):
        """Deve fazer soft delete (marcando deleted_at)"""
        setting_id = created_setting["id"]
        
        response = test_client.delete(
            f"/api/relay-config/settings/{setting_id}?soft_delete=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["deleted_id"] == setting_id
        assert data["soft_delete"] is True
        assert data["can_undo"] is True
        assert data["undo_expires_at"] is not None
        
        print(f"✅ Soft delete executado: ID={setting_id}")
    
    def test_restore_after_soft_delete(self, test_client, created_setting):
        """Deve permitir restaurar após soft delete"""
        setting_id = created_setting["id"]
        
        # Soft delete
        delete_response = test_client.delete(
            f"/api/relay-config/settings/{setting_id}?soft_delete=true"
        )
        assert delete_response.status_code == 200
        
        # Restore (undo)
        restore_response = test_client.post(
            f"/api/relay-config/settings/{setting_id}/restore"
        )
        
        assert restore_response.status_code == 200
        data = restore_response.json()
        
        assert data["id"] == setting_id
        assert data["is_enabled"] is not None  # Configuração restaurada
        
        print(f"✅ Restore (undo) funcionou: ID={setting_id}")
    
    def test_delete_not_found(self, test_client):
        """Deve retornar 404 ao tentar excluir ID inexistente"""
        response = test_client.delete("/api/relay-config/settings/999999")
        
        assert response.status_code == 404
        
        print("✅ Delete de ID inexistente retorna 404")


# ============================================================================
# TESTE DE HEALTH CHECK
# ============================================================================

def test_health_check(test_client):
    """Verifica se API está rodando e dependências disponíveis"""
    response = test_client.get("/api/relay-config/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["capabilities"]["json"] is True
    assert data["capabilities"]["csv"] is True
    
    print("✅ Health check OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration", "--tb=short"])

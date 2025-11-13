"""
Configurações compartilhadas para todos os testes pytest.
Define fixtures, configurações de banco de dados de teste, e utilitários.
"""

import pytest
import sys
from pathlib import Path
import os

# Adicionar diretório raiz ao Python path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


# ==================== Configurações Gerais ====================

@pytest.fixture(scope="session")
def project_root():
    """Retorna o diretório raiz do projeto"""
    return ROOT_DIR


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """Retorna diretório de dados de teste"""
    test_dir = project_root / "tests" / "test_data"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture(scope="session")
def temp_output_dir(tmp_path_factory):
    """Cria diretório temporário para outputs de teste"""
    return tmp_path_factory.mktemp("test_outputs")


# ==================== Configurações de Banco de Dados ====================

@pytest.fixture(scope="session")
def test_db_config():
    """
    Configuração do banco de dados de teste.
    ATENÇÃO: Configure um banco separado para testes!
    """
    return {
        'host': os.getenv('TEST_DB_HOST', 'localhost'),
        'port': os.getenv('TEST_DB_PORT', '5432'),
        'database': os.getenv('TEST_DB_NAME', 'protecai_db'),
        'user': os.getenv('TEST_DB_USER', 'protecai'),
        'password': os.getenv('TEST_DB_PASSWORD', 'protecai')
    }


@pytest.fixture(scope="function")
def db_session(test_db_config):
    """
    Cria uma sessão SQLAlchemy para testes de integração.
    IMPORTANTE: Usa SQLAlchemy Session (mesma interface dos services).
    Usa transação que é revertida ao final do teste.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Criar connection string do PostgreSQL
    db_url = f"postgresql://{test_db_config['user']}:{test_db_config['password']}@{test_db_config['host']}:{test_db_config['port']}/{test_db_config['database']}"
    
    # Criar engine e session
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    
    try:
        yield session
    finally:
        # Rollback ao final do teste (não persiste mudanças)
        session.rollback()
        session.close()
        engine.dispose()


@pytest.fixture(scope="function")
def clean_db_session(test_db_config):
    """
    Sessão de DB que limpa tabelas antes de cada teste.
    Use apenas quando necessário (testes de integração com DB).
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    conn = psycopg2.connect(**test_db_config)
    conn.autocommit = False
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Limpar tabelas de teste (ordem importa devido a foreign keys)
    cleanup_queries = [
        "TRUNCATE TABLE protec_ai.tokens_valores CASCADE;",
        "TRUNCATE TABLE protec_ai.valores_originais CASCADE;",
        "TRUNCATE TABLE protec_ai.campos_originais CASCADE;",
        "TRUNCATE TABLE protec_ai.relay_settings CASCADE;",
        "TRUNCATE TABLE protec_ai.protection_functions CASCADE;",
        "TRUNCATE TABLE protec_ai.electrical_configuration CASCADE;",
        "TRUNCATE TABLE protec_ai.relay_equipment CASCADE;",
    ]
    
    for query in cleanup_queries:
        try:
            cursor.execute(query)
        except Exception as e:
            print(f"Warning: Could not clean table: {e}")
    
    conn.commit()
    
    yield cursor
    
    # Rollback changes ao final
    conn.rollback()
    cursor.close()
    conn.close()


# ==================== Fixtures de Dados de Teste ====================

@pytest.fixture
def sample_glossary_data():
    """Dados de glossário de exemplo para testes"""
    return {
        'MICON-P122': [
            {
                'codigo': 'M_P001',
                'nome': 'I> (50) Corrente de Pickup',
                'unidade': 'A',
                'exemplo': '5.5',
                'modelo': 'MICON-P122'
            },
            {
                'codigo': 'M_P002',
                'nome': 'U< (27) Subtensão',
                'unidade': 'V',
                'exemplo': '120',
                'modelo': 'MICON-P122'
            },
            {
                'codigo': 'M_P003',
                'nome': 'Habilita 50',
                'unidade': '',
                'exemplo': '1',
                'modelo': 'MICON-P122'
            }
        ],
        'SEPAM-S40': [
            {
                'codigo': 'S_P001',
                'nome': 'I>> (50) Pickup Instantâneo',
                'unidade': 'A',
                'exemplo': '50',
                'modelo': 'SEPAM-S40'
            },
            {
                'codigo': 'S_P002',
                'nome': 'F> (81) Frequência Alta',
                'unidade': 'Hz',
                'exemplo': '62',
                'modelo': 'SEPAM-S40'
            }
        ]
    }


@pytest.fixture
def sample_protection_functions():
    """Funções de proteção de exemplo"""
    return [
        {
            'ansi_code': '50',
            'function_name': 'Instantaneous Overcurrent',
            'description': 'Proteção de sobrecorrente instantânea',
            'category': 'overcurrent'
        },
        {
            'ansi_code': '27',
            'function_name': 'Undervoltage',
            'description': 'Proteção de subtensão',
            'category': 'voltage'
        },
        {
            'ansi_code': '81',
            'function_name': 'Frequency',
            'description': 'Proteção de frequência',
            'category': 'frequency'
        }
    ]


@pytest.fixture
def sample_relay_settings():
    """Configurações de relé de exemplo"""
    return [
        {
            'original_code': 'I>',
            'setting_name': 'Corrente de Pickup',
            'ansi_function': '50',
            'default_value': '5.5',
            'unit': 'A',
            'category': 'protection'
        },
        {
            'original_code': 'U<',
            'setting_name': 'Subtensão',
            'ansi_function': '27',
            'default_value': '120',
            'unit': 'V',
            'category': 'protection'
        }
    ]


@pytest.fixture
def sample_equipment_info():
    """Informações de equipamento de exemplo"""
    return {
        'equipment_id': 1,
        'equipment_name': 'RELE_TEST_001',
        'manufacturer': 'MICON',
        'model': 'P122',
        'serial_number': 'SN12345',
        'installation_date': '2024-01-15',
        'substation_name': 'SE_TEST',
        'bay_name': 'BAY_TEST',
        'voltage_level': '138kV'
    }


# ==================== Utilitários de Teste ====================

@pytest.fixture
def create_temp_excel(tmp_path):
    """Factory para criar arquivos Excel temporários"""
    import pandas as pd
    
    def _create_excel(data_dict, sheet_name='Sheet1'):
        """
        Cria arquivo Excel temporário.
        
        Args:
            data_dict: Dicionário com dados (formato para pd.DataFrame)
            sheet_name: Nome da planilha
            
        Returns:
            Path do arquivo criado
        """
        df = pd.DataFrame(data_dict)
        excel_file = tmp_path / f"test_{sheet_name}.xlsx"
        df.to_excel(excel_file, sheet_name=sheet_name, index=False)
        return excel_file
    
    return _create_excel


@pytest.fixture
def create_temp_json(tmp_path):
    """Factory para criar arquivos JSON temporários"""
    import json
    
    def _create_json(data, filename='test.json'):
        """
        Cria arquivo JSON temporário.
        
        Args:
            data: Dados para serializar
            filename: Nome do arquivo
            
        Returns:
            Path do arquivo criado
        """
        json_file = tmp_path / filename
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return json_file
    
    return _create_json


@pytest.fixture
def assert_sql_valid():
    """Helper para validar sintaxe SQL básica"""
    def _validate(sql_content):
        """
        Valida sintaxe SQL básica.
        
        Args:
            sql_content: Conteúdo SQL para validar
            
        Returns:
            bool: True se válido
            
        Raises:
            AssertionError: Se SQL inválido
        """
        # Verificações básicas
        assert isinstance(sql_content, str), "SQL deve ser string"
        assert len(sql_content) > 0, "SQL não pode estar vazio"
        
        # Verificar estrutura básica de INSERT
        if 'INSERT' in sql_content.upper():
            assert 'INTO' in sql_content.upper(), "INSERT deve ter INTO"
            assert 'VALUES' in sql_content.upper(), "INSERT deve ter VALUES"
        
        # Verificar parênteses balanceados
        assert sql_content.count('(') == sql_content.count(')'), "Parênteses desbalanceados"
        
        return True
    
    return _validate


# ==================== Configurações de Logging para Testes ====================

@pytest.fixture(scope="session", autouse=True)
def configure_test_logging():
    """Configura logging para testes"""
    import logging
    
    # Configurar nível de log para testes
    logging.basicConfig(
        level=logging.WARNING,  # Mostrar apenas warnings e errors durante testes
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Silenciar logs verbosos de bibliotecas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)


# ==================== Marcadores de Teste ====================

def pytest_configure(config):
    """Registra marcadores personalizados"""
    config.addinivalue_line(
        "markers", "integration: marca testes de integração (podem ser lentos)"
    )
    config.addinivalue_line(
        "markers", "requires_db: marca testes que precisam de banco de dados"
    )
    config.addinivalue_line(
        "markers", "slow: marca testes lentos"
    )
    config.addinivalue_line(
        "markers", "unit: marca testes unitários rápidos"
    )


# ==================== Hooks de Teste ====================

def pytest_collection_modifyitems(config, items):
    """Modifica coleção de testes para adicionar marcadores automáticos"""
    for item in items:
        # Marcar testes que usam fixtures de DB
        if 'db_session' in item.fixturenames or 'clean_db_session' in item.fixturenames:
            item.add_marker(pytest.mark.requires_db)
        
        # Marcar testes de integração
        if 'integration' in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)

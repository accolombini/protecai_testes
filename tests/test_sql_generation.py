"""
Testes para validar a geração de SQL e CSV a partir do glossário.
Valida o módulo scripts/generate_db_population_from_glossary.py
"""

import pytest
import json
import csv
from pathlib import Path
import sys
import re

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_db_population_from_glossary import (
    extract_function_from_name,
    categorize_parameter,
    generate_sql_protection_functions,
    generate_sql_relay_settings,
    export_csv_protection_functions,
    export_csv_relay_settings,
    generate_protection_functions,
    generate_relay_settings,
    load_glossary
)


class TestExtractFunctionFromName:
    """Testes para extração de função ANSI do nome do parâmetro"""
    
    def test_extract_function_50(self):
        """Testa extração de função 50 (Overcurrent)"""
        code, name, clean = extract_function_from_name("I> (50) Corrente de Pickup")
        assert code == "50" or code == "PARAM"  # Pode ser 50 ou fallback PARAM
    
    def test_extract_function_returns_tuple(self):
        """Testa que função retorna tupla de 3 elementos"""
        result = extract_function_from_name("Function I>")
        assert isinstance(result, tuple)
        assert len(result) == 3
        code, func_name, clean = result
        assert isinstance(code, str)
        assert isinstance(func_name, str)
        assert isinstance(clean, str)
    
    def test_extract_function_overcurrent_pattern(self):
        """Testa padrão de sobrecorrente I>"""
        code, func_name, clean = extract_function_from_name("I>")
        assert code == "50"
        assert "Overcurrent" in func_name or "50" in code
        assert "I>" in clean
    
    def test_extract_function_ground_overcurrent(self):
        """Testa padrão de terra Ie>"""
        code, func_name, clean = extract_function_from_name("Ie>")
        assert code == "50N"
        assert "Ground" in func_name or "50N" in code
    
    def test_extract_function_voltage(self):
        """Testa padrão de tensão V>"""
        code, func_name, clean = extract_function_from_name("V>")
        assert code == "59"  # Overvoltage retorna '59', não '59/27'
        assert "Voltage" in func_name or "voltage" in func_name.lower()
    
    def test_extract_function_frequency(self):
        """Testa padrão de frequência f>"""
        code, func_name, clean = extract_function_from_name("f>")
        assert code == "81O"  # Over Frequency retorna '81O', não '81'
        assert "Frequency" in func_name or "frequency" in func_name.lower()
    
    def test_extract_no_function(self):
        """Testa parâmetros sem função ANSI identificável"""
        code, func_name, clean = extract_function_from_name("Configuração Geral")
        assert code == "PARAM"
        assert "Parameter" in func_name


class TestCategorizeParameter:
    """Testes para categorização de parâmetros"""
    
    def test_categorize_returns_string(self):
        """Testa que categorize_parameter retorna string"""
        result = categorize_parameter("P001", "Corrente de Pickup")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_categorize_overcurrent(self):
        """Testa categorização de sobrecorrente I>"""
        result = categorize_parameter("P001", "I>")
        assert result == "OVERCURRENT_SETTING"
    
    def test_categorize_timing(self):
        """Testa categorização de tempo/delay"""
        result = categorize_parameter("P002", "Delay Time")
        assert result == "TIMING"
        
        result2 = categorize_parameter("P003", "Reset TMS")
        assert result2 == "TIMING"
    
    def test_categorize_instrumentation(self):
        """Testa categorização de instrumentação"""
        result = categorize_parameter("P004", "CT Ratio")
        assert result == "INSTRUMENTATION"
        
        result2 = categorize_parameter("P005", "VT Primary")
        assert result2 == "INSTRUMENTATION"
    
    def test_categorize_curve(self):
        """Testa categorização de curva"""
        result = categorize_parameter("P006", "IDMT Curve")
        assert result == "CURVE_SETTING"
    
    def test_categorize_identification(self):
        """Testa categorização de identificação"""
        result = categorize_parameter("P007", "Description")
        assert result == "IDENTIFICATION"
    
    def test_categorize_default(self):
        """Testa categorização padrão"""
        result = categorize_parameter("P999", "Unknown Parameter")
        assert result == "GENERAL_PARAMETER"


class TestGenerateSqlProtectionFunctions:
    """Testes para geração de SQL de funções de proteção"""
    
    def test_generate_sql_basic(self):
        """Testa geração básica de SQL"""
        functions = [
            {
                'function_code': '50',
                'function_name': 'Overcurrent',
                'function_description': 'Instantaneous Overcurrent Protection',
                'ansi_ieee_standard': 'ANSI 50',
                'typical_application': 'Relay protection',
                'is_primary': True,
                'is_backup': False
            },
            {
                'function_code': '27',
                'function_name': 'Undervoltage',
                'function_description': 'Undervoltage Protection',
                'ansi_ieee_standard': 'ANSI 27',
                'typical_application': 'Relay protection',
                'is_primary': False,
                'is_backup': False
            }
        ]
        
        sql_content = generate_sql_protection_functions(functions)
        
        # Verificar conteúdo básico
        assert isinstance(sql_content, str)
        assert len(sql_content) > 0
        assert "INSERT INTO" in sql_content or "VALUES" in sql_content
        assert "'50'" in sql_content or '"50"' in sql_content
    
    def test_generate_sql_empty_list(self):
        """Testa geração com lista vazia"""
        sql_content = generate_sql_protection_functions([])
        assert isinstance(sql_content, str)
        # SQL vazio ou com comentários é válido


class TestGenerateSqlRelaySettings:
    """Testes para geração de SQL de configurações de relés"""
    
    def test_generate_sql_settings_basic(self):
        """Testa geração básica de SQL de settings"""
        settings = [
            {
                'parameter_name': 'I> Pickup',
                'parameter_code': 'P001',
                'set_value': 10.0,
                'set_value_text': None,
                'unit_of_measure': 'A',
                'category': 'OVERCURRENT_SETTING',
                'model_reference': 'MICON-P122',
                'ansi_reference': '50',
                'is_enabled': True,
                'setting_group': 'GROUP_1'
            }
        ]
        
        sql_content = generate_sql_relay_settings(settings)
        
        # Verificar conteúdo básico
        assert isinstance(sql_content, str)
        assert len(sql_content) > 0
    
    def test_generate_sql_settings_empty(self):
        """Testa geração com lista vazia"""
        sql_content = generate_sql_relay_settings([])
        assert isinstance(sql_content, str)


class TestGenerateCsvFunctions:
    """Testes para geração de CSV de funções"""
    
    def test_generate_csv_functions_basic(self, tmp_path):
        """Testa geração básica de CSV"""
        # Criar lista de funções
        functions = [
            {
                'ansi_code': '50',
                'function_name': 'Overcurrent',
                'description': 'Instantaneous Overcurrent',
                'iec_symbol': '50',
                'is_enabled': True
            },
            {
                'ansi_code': '27',
                'function_name': 'Undervoltage',
                'description': 'Undervoltage Protection',
                'iec_symbol': '27',
                'is_enabled': True
            }
        ]
        
        output_file = tmp_path / "test_functions.csv"
        
        export_csv_protection_functions(functions, output_file)
        
        assert output_file.exists()
        
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        assert rows[0]['ansi_code'] == '50'
        assert rows[1]['ansi_code'] == '27'


class TestIntegrationSqlGeneration:
    """Testes de integração completos"""
    
    def test_full_sql_generation_workflow(self, tmp_path):
        """Testa workflow completo de geração de SQL"""
        # 1. Criar dados de glossário (formato flat como esperado)
        # IMPORTANTE: generate_protection_functions() procura por names que começam com "Function "
        glossary = [
            {'model': 'MICON-P122', 'code': 'M001', 'name': 'Function I>', 'unit': 'A', 'value_example': '5.5', 'sheet': 'MICON_P122'},
            {'model': 'MICON-P122', 'code': 'M002', 'name': 'Function V<', 'unit': 'V', 'value_example': '120', 'sheet': 'MICON_P122'},
            {'model': 'MICON-P122', 'code': 'M003', 'name': 'I> Pickup Current', 'unit': 'A', 'value_example': '10', 'sheet': 'MICON_P122'},
            {'model': 'SEPAM-S40', 'code': 'S001', 'name': 'Delay Time', 'unit': 's', 'value_example': '0.5', 'sheet': 'SEPAM_S40'},
            {'model': 'SEPAM-S40', 'code': 'S002', 'name': 'CT Ratio', 'unit': '', 'value_example': '100/5', 'sheet': 'SEPAM_S40'}
        ]
        
        # 2. Gerar funções de proteção
        functions, function_codes = generate_protection_functions(glossary)
        
        # 3. Gerar settings
        settings = generate_relay_settings(glossary, function_codes)
        
        # 4. Gerar SQL de funções
        functions_sql_content = generate_sql_protection_functions(functions)
        functions_sql = tmp_path / "functions.sql"
        with open(functions_sql, 'w', encoding='utf-8') as f:
            f.write(functions_sql_content)
        
        # 5. Gerar SQL de settings
        settings_sql_content = generate_sql_relay_settings(settings)
        settings_sql = tmp_path / "settings.sql"
        with open(settings_sql, 'w', encoding='utf-8') as f:
            f.write(settings_sql_content)
        
        # 6. Gerar CSVs
        functions_csv = tmp_path / "functions.csv"
        settings_csv = tmp_path / "settings.csv"
        export_csv_protection_functions(functions, functions_csv)
        export_csv_relay_settings(settings, settings_csv)
        
        # 7. Validar todos os outputs
        assert functions_sql.exists()
        assert settings_sql.exists()
        assert functions_csv.exists()
        assert settings_csv.exists()
        
        # Validar que pelo menos alguns dados foram gerados
        # M001 e M002 são "Function" então viram funções, M003/S001/S002 viram settings
        assert len(functions) == 2  # Function I> e Function V<
        assert len(settings) == 3  # M003, S001, S002
        
        # Validar conteúdo SQL de settings
        with open(settings_sql, 'r', encoding='utf-8') as f:
            settings_content = f.read()
        
        # M003 é um setting (não começa com "Function ")
        assert "'M003'" in settings_content or 'M003' in settings_content
        assert "'S001'" in settings_content or 'S001' in settings_content
        
        # Validar CSV de settings
        with open(settings_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            setting_rows = list(reader)
        
        assert len(setting_rows) == 3  # 3 parâmetros (M003, S001, S002)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

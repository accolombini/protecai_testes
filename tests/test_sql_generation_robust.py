"""
Testes ROBUSTOS baseados em PROPRIEDADES e INVARIANTES do sistema.
Estes testes validam COMPORTAMENTOS ESSENCIAIS, não implementações específicas.

PRINCÍPIOS:
1. CAUSA RAIZ: Validar contratos, não detalhes de implementação
2. ROBUSTEZ: Funcionar com qualquer fabricante/modelo
3. FLEXIBILIDADE: Suportar variações de formato
4. CONFIABILIDADE: Garantir integridade dos dados

Author: ProtecAI Engineering Team
Date: 2025-11-03
Version: 2.0.0 - ROBUST
"""

import pytest
import json
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_db_population_from_glossary import (
    extract_function_from_name,
    categorize_parameter,
    generate_protection_functions,
    generate_relay_settings,
    generate_sql_protection_functions,
    generate_sql_relay_settings,
    export_csv_protection_functions,
    export_csv_relay_settings
)


class TestInvariants:
    """Testes de INVARIANTES do sistema - propriedades que SEMPRE devem ser verdadeiras"""
    
    def test_extract_function_always_returns_tuple_of_3(self):
        """INVARIANTE: extract_function_from_name SEMPRE retorna tupla de 3 strings"""
        test_cases = [
            "Function I>",
            "I> Pickup",
            "Random Text",
            "",
            "50 Overcurrent",
            "V< Undervoltage",
            "f> Frequency",
            "DIFF Protection",
            "Unknown Parameter XYZ123"
        ]
        
        for test_input in test_cases:
            result = extract_function_from_name(test_input)
            
            # INVARIANTE 1: Sempre tupla de 3 elementos
            assert isinstance(result, tuple), f"Falhou para: {test_input}"
            assert len(result) == 3, f"Falhou para: {test_input}"
            
            # INVARIANTE 2: Todos elementos são strings
            code, name, clean = result
            assert isinstance(code, str), f"Code não é string para: {test_input}"
            assert isinstance(name, str), f"Name não é string para: {test_input}"
            assert isinstance(clean, str), f"Clean não é string para: {test_input}"
            
            # INVARIANTE 3: Code nunca é vazio
            assert len(code) > 0, f"Code vazio para: {test_input}"
    
    def test_categorize_always_returns_valid_category(self):
        """INVARIANTE: categorize_parameter SEMPRE retorna categoria válida"""
        valid_categories = {
            'PROTECTION_FUNCTION', 'TIMING', 'INSTRUMENTATION',
            'ELECTRICAL_CONFIG', 'CURVE_SETTING', 'IDENTIFICATION',
            'OVERCURRENT_SETTING', 'SAMPLING', 'GENERAL_PARAMETER'
        }
        
        test_cases = [
            ("P001", "I>"),
            ("P002", "Delay Time"),
            ("P003", "CT Ratio"),
            ("P004", "Unknown Param"),
            ("S001", "Function I>"),
            ("", ""),
        ]
        
        for code, name in test_cases:
            result = categorize_parameter(code, name)
            
            # INVARIANTE: Categoria é sempre uma das válidas
            assert result in valid_categories, f"Categoria inválida '{result}' para: {code}, {name}"
    
    def test_generate_functions_preserves_data_integrity(self):
        """INVARIANTE: generate_protection_functions nunca perde dados"""
        glossary = [
            {'model': 'TEST', 'code': 'C1', 'name': 'Function I>', 'unit': 'A', 'value_example': '10', 'sheet': 'S1'},
            {'model': 'TEST', 'code': 'C2', 'name': 'Function V<', 'unit': 'V', 'value_example': '120', 'sheet': 'S1'},
            {'model': 'TEST', 'code': 'C3', 'name': 'Param X', 'unit': 'A', 'value_example': '5', 'sheet': 'S1'},
        ]
        
        functions, processed_codes = generate_protection_functions(glossary)
        
        # INVARIANTE 1: Retorna lista
        assert isinstance(functions, list)
        assert isinstance(processed_codes, set)
        
        # INVARIANTE 2: Cada função tem estrutura completa
        for func in functions:
            required_keys = ['function_code', 'function_name', 'function_description', 
                           'ansi_ieee_standard', 'typical_application', 'is_primary', 'is_backup']
            for key in required_keys:
                assert key in func, f"Chave '{key}' faltando em função"
                assert func[key] is not None, f"Valor None para chave '{key}'"
    
    def test_generate_settings_excludes_processed_functions(self):
        """INVARIANTE: generate_relay_settings NUNCA duplica códigos processados como funções"""
        glossary = [
            {'model': 'TEST', 'code': 'C1', 'name': 'Function I>', 'unit': 'A', 'value_example': '10', 'sheet': 'S1'},
            {'model': 'TEST', 'code': 'C2', 'name': 'Param Y', 'unit': 'V', 'value_example': '120', 'sheet': 'S1'},
        ]
        
        functions, processed_codes = generate_protection_functions(glossary)
        settings = generate_relay_settings(glossary, processed_codes)
        
        # INVARIANTE: Códigos processados como funções NÃO aparecem em settings
        setting_codes = {s['parameter_code'] for s in settings}
        
        assert len(setting_codes & processed_codes) == 0, \
            f"Códigos duplicados encontrados: {setting_codes & processed_codes}"
    
    def test_sql_generation_always_produces_valid_syntax(self):
        """INVARIANTE: SQL gerado é sempre sintaticamente válido"""
        functions = [
            {
                'function_code': '50',
                'function_name': 'Overcurrent',
                'function_description': 'Test',
                'ansi_ieee_standard': 'ANSI 50',
                'typical_application': 'Protection',
                'is_primary': True,
                'is_backup': False
            }
        ]
        
        sql = generate_sql_protection_functions(functions)
        
        # INVARIANTE 1: SQL não vazio
        assert len(sql) > 0
        
        # INVARIANTE 2: Contém palavras-chave SQL essenciais
        assert 'INSERT INTO' in sql or 'VALUES' in sql
        
        # INVARIANTE 3: Não contém syntax errors óbvios
        assert sql.count('(') == sql.count(')'), "Parênteses desbalanceados"
        assert "INSERT INTO" in sql and "VALUES" in sql, "Estrutura SQL incompleta"


class TestCrossManufacturerCompatibility:
    """Testes de COMPATIBILIDADE entre fabricantes"""
    
    @pytest.mark.parametrize("manufacturer,param_format", [
        ("MICON", "Function I>"),
        ("SEPAM", "I> Pickup"),
        ("ABB", "50 - Overcurrent"),
        ("GE", "Overcurrent Protection (50)"),
        ("SIEMENS", "7SJ Overcurrent"),
    ])
    def test_extract_function_works_for_all_manufacturers(self, manufacturer, param_format):
        """ROBUSTEZ: Sistema deve funcionar com qualquer fabricante"""
        code, name, clean = extract_function_from_name(param_format)
        
        # Deve retornar algo válido independente do formato
        assert len(code) > 0
        assert len(name) > 0
        assert len(clean) > 0
    
    def test_glossary_processing_handles_different_structures(self):
        """FLEXIBILIDADE: Processar glossários com estruturas variadas"""
        # Formato MICON
        glossary_micon = [
            {'model': 'MICON-P122', 'code': 'M001', 'name': 'Function I>', 
             'unit': 'A', 'value_example': '5.5', 'sheet': 'MICON_P122'}
        ]
        
        # Formato SEPAM
        glossary_sepam = [
            {'model': 'SEPAM-S40', 'code': 'S001', 'name': 'Function Ie>', 
             'unit': 'A', 'value_example': '10', 'sheet': 'SEPAM_S40'}
        ]
        
        # Formato genérico (futuro)
        glossary_generic = [
            {'model': 'GENERIC', 'code': 'G001', 'name': 'I> Setting', 
             'unit': 'A', 'value_example': '15', 'sheet': 'GENERIC'}
        ]
        
        # INVARIANTE: Todos devem processar sem erro
        for glossary in [glossary_micon, glossary_sepam, glossary_generic]:
            functions, codes = generate_protection_functions(glossary)
            settings = generate_relay_settings(glossary, codes)
            
            # Deve produzir resultado válido
            assert isinstance(functions, list)
            assert isinstance(settings, list)


class TestDataIntegrity:
    """Testes de INTEGRIDADE de dados"""
    
    def test_no_data_loss_in_full_pipeline(self, tmp_path):
        """CONFIABILIDADE: Pipeline completo não perde dados"""
        # Dados de entrada
        input_glossary = [
            {'model': 'M1', 'code': 'C1', 'name': 'Function I>', 'unit': 'A', 'value_example': '10', 'sheet': 'S1'},
            {'model': 'M1', 'code': 'C2', 'name': 'Param X', 'unit': 'V', 'value_example': '120', 'sheet': 'S1'},
            {'model': 'M2', 'code': 'C3', 'name': 'Function V<', 'unit': 'V', 'value_example': '100', 'sheet': 'S2'},
            {'model': 'M2', 'code': 'C4', 'name': 'Param Y', 'unit': 's', 'value_example': '0.5', 'sheet': 'S2'},
        ]
        
        # Processar
        functions, func_codes = generate_protection_functions(input_glossary)
        settings = generate_relay_settings(input_glossary, func_codes)
        
        # INVARIANTE: Total de registros processados = total de entrada
        total_output = len(functions) + len(settings)
        total_input = len(input_glossary)
        
        assert total_output == total_input, \
            f"Perda de dados: entrada={total_input}, saída={total_output}"
        
        # INVARIANTE: Nenhum código duplicado
        all_codes = func_codes | {s['parameter_code'] for s in settings}
        assert len(all_codes) == total_input, "Códigos duplicados encontrados"
    
    def test_csv_export_preserves_all_data(self, tmp_path):
        """CONFIABILIDADE: Export CSV preserva todos os dados"""
        functions = [
            {
                'function_code': '50',
                'function_name': 'Overcurrent',
                'function_description': 'Test description with special chars: àéíóú',
                'ansi_ieee_standard': 'ANSI 50',
                'typical_application': 'Protection',
                'is_primary': True,
                'is_backup': False
            }
        ]
        
        csv_file = tmp_path / "test.csv"
        export_csv_protection_functions(functions, csv_file)
        
        # Ler de volta
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # INVARIANTE: Todos os dados preservados
        assert len(rows) == len(functions)
        assert rows[0]['function_code'] == '50'
        assert 'special chars' in rows[0]['function_description']


class TestEdgeCases:
    """Testes de CASOS EXTREMOS - o sistema deve ser resiliente"""
    
    def test_empty_glossary_doesnt_crash(self):
        """ROBUSTEZ: Glossário vazio não deve quebrar o sistema"""
        functions, codes = generate_protection_functions([])
        settings = generate_relay_settings([], codes)
        
        assert functions == []
        assert settings == []
        assert codes == set()
    
    def test_malformed_data_handled_gracefully(self):
        """ROBUSTEZ: Dados malformados devem ser tratados"""
        glossary = [
            {'model': '', 'code': '', 'name': '', 'unit': '', 'value_example': '', 'sheet': ''},
            {'model': 'M', 'code': 'C', 'name': 'N', 'unit': None, 'value_example': None, 'sheet': 'S'},
        ]
        
        # Não deve lançar exceção
        try:
            functions, codes = generate_protection_functions(glossary)
            settings = generate_relay_settings(glossary, codes)
            assert True  # Se chegou aqui, não crashou
        except Exception as e:
            pytest.fail(f"Sistema crashou com dados malformados: {e}")
    
    def test_unicode_and_special_characters(self):
        """ROBUSTEZ: Caracteres especiais e unicode devem funcionar"""
        glossary = [
            {'model': 'CÔTÉ', 'code': 'Ç001', 'name': 'Função I> (50) – Sobrecorrente', 
             'unit': 'Â', 'value_example': '10,5', 'sheet': 'Planilha Nº1'}
        ]
        
        functions, codes = generate_protection_functions(glossary)
        settings = generate_relay_settings(glossary, codes)
        
        # Deve processar sem erro
        assert isinstance(functions, list)
        assert isinstance(settings, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

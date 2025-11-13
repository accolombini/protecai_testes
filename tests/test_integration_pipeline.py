"""
Testes de integração end-to-end do pipeline completo.
Testa o fluxo: Extração do Glossário → Geração SQL → População DB → Geração de Relatório
"""

import pytest
import json
import csv
from pathlib import Path
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extract_glossary import read_glossary_sheet, export_to_json, export_to_csv
from scripts.generate_db_population_from_glossary import (
    generate_sql_protection_functions,
    generate_sql_relay_settings
)


class TestEndToEndPipeline:
    """Testes de integração completos do pipeline"""
    
    @pytest.fixture
    def sample_glossary_excel(self, tmp_path):
        """Cria arquivo Excel de exemplo para testes"""
        data = {
            'Código': ['P001', 'P002', 'P003', 'P004', 'P005'],
            'Nome do Parâmetro': [
                'I> (50) Corrente de Pickup',
                'U< (27) Subtensão',
                'F> (81) Frequência Alta',
                'Habilita 50',
                'Tensão Nominal'
            ],
            'Unidade': ['A', 'V', 'Hz', '', 'kV'],
            'Valor Exemplo': ['5.5', '120', '62', '1', '13.8']
        }
        
        df = pd.DataFrame(data)
        excel_file = tmp_path / "test_glossary.xlsx"
        df.to_excel(excel_file, sheet_name='MICON_P122', index=False)
        
        return excel_file
    
    def test_full_pipeline_without_db(self, sample_glossary_excel, tmp_path):
        """
        Testa pipeline completo sem conexão ao banco de dados.
        Etapas: Extração → Geração SQL → Validação de Arquivos
        """
        # ==== ETAPA 1: Extração do Glossário ====
        extracted_data = read_glossary_sheet(
            str(sample_glossary_excel),
            'MICON_P122',
            'MICON-P122'
        )
        
        assert len(extracted_data) == 5
        assert extracted_data[0]['codigo'] == 'P001'
        
        # Organizar por modelo
        glossary_by_model = {'MICON-P122': extracted_data}
        
        # Exportar para JSON
        json_file = tmp_path / "glossary_mapping.json"
        export_to_json(glossary_by_model, str(json_file))
        
        # Exportar para CSV
        csv_file = tmp_path / "glossary_mapping.csv"
        export_to_csv(glossary_by_model, str(csv_file))
        
        # Validar exports
        assert json_file.exists()
        assert csv_file.exists()
        
        # ==== ETAPA 2: Geração de SQL ====
        functions_sql = tmp_path / "populate_protection_functions.sql"
        settings_sql = tmp_path / "populate_relay_settings.sql"
        
        generate_sql_protection_functions(str(json_file), str(functions_sql))
        generate_sql_relay_settings(str(json_file), str(settings_sql))
        
        assert functions_sql.exists()
        assert settings_sql.exists()
        
        # ==== ETAPA 3: Validação do Conteúdo SQL ====
        with open(functions_sql, 'r', encoding='utf-8') as f:
            func_content = f.read()
        
        # Deve conter funções extraídas (50, 27, 81)
        assert "'50'" in func_content
        assert "'27'" in func_content
        assert "'81'" in func_content
        
        with open(settings_sql, 'r', encoding='utf-8') as f:
            settings_content = f.read()
        
        # Deve conter todos os códigos
        assert "'P001'" in settings_content
        assert "'P002'" in settings_content
        assert "'P003'" in settings_content
        assert "'P004'" in settings_content
        assert "'P005'" in settings_content
        
        # ==== ETAPA 4: Validação de Categorização ====
        # P001 (I> Pickup) deve ser categoria 'protection'
        # P004 (Habilita) deve ser categoria 'control'
        # P005 (Tensão Nominal) deve ser categoria 'electrical' ou 'general'
        
        assert "'protection'" in settings_content
        assert "'control'" in settings_content
        
        # ==== RESULTADO ====
        print("\n✅ Pipeline completo executado com sucesso!")
        print(f"   📄 Dados extraídos: {len(extracted_data)} parâmetros")
        print(f"   💾 JSON gerado: {json_file}")
        print(f"   📊 CSV gerado: {csv_file}")
        print(f"   🗃️  SQL funções: {functions_sql}")
        print(f"   ⚙️  SQL settings: {settings_sql}")


class TestPipelineDataIntegrity:
    """Testes de integridade de dados ao longo do pipeline"""
    
    def test_data_preservation_through_pipeline(self, tmp_path):
        """Testa que dados não são perdidos ao longo do pipeline"""
        # Criar dados iniciais
        initial_data = {
            'Código': ['C001', 'C002', 'C003'],
            'Nome do Parâmetro': ['Param 1', 'Param 2', 'Param 3'],
            'Unidade': ['A', 'V', 'Hz'],
            'Valor Exemplo': ['1', '2', '3']
        }
        
        df = pd.DataFrame(initial_data)
        excel_file = tmp_path / "integrity_test.xlsx"
        df.to_excel(excel_file, sheet_name='Test', index=False)
        
        # Extrair
        extracted = read_glossary_sheet(str(excel_file), 'Test', 'TestModel')
        assert len(extracted) == 3
        
        # Exportar para JSON
        json_data = {'TestModel': extracted}
        json_file = tmp_path / "integrity.json"
        export_to_json(json_data, str(json_file))
        
        # Ler JSON e validar
        with open(json_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        assert 'TestModel' in loaded
        assert len(loaded['TestModel']) == 3
        
        # Gerar SQL
        settings_sql = tmp_path / "integrity_settings.sql"
        generate_sql_relay_settings(str(json_file), str(settings_sql))
        
        # Verificar que todos os códigos estão no SQL
        with open(settings_sql, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        for code in ['C001', 'C002', 'C003']:
            assert f"'{code}'" in sql_content
    
    def test_special_characters_preservation(self, tmp_path):
        """Testa preservação de caracteres especiais"""
        data = {
            'Código': ['P001'],
            'Nome do Parâmetro': ['I> (50) - Corrente de Pickup [Fase A]'],
            'Unidade': ['A'],
            'Valor Exemplo': ['5.5']
        }
        
        df = pd.DataFrame(data)
        excel_file = tmp_path / "special_chars.xlsx"
        df.to_excel(excel_file, sheet_name='Test', index=False)
        
        # Extrair
        extracted = read_glossary_sheet(str(excel_file), 'Test', 'TestModel')
        
        # Validar que caracteres especiais foram preservados
        assert '>' in extracted[0]['nome']
        assert '(' in extracted[0]['nome']
        assert '[' in extracted[0]['nome']
        
        # Exportar e validar JSON
        json_data = {'TestModel': extracted}
        json_file = tmp_path / "special.json"
        export_to_json(json_data, str(json_file))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        assert '>' in loaded['TestModel'][0]['nome']


class TestPipelineErrorHandling:
    """Testes de tratamento de erros no pipeline"""
    
    def test_missing_file_handling(self, tmp_path):
        """Testa comportamento com arquivo inexistente"""
        non_existent = tmp_path / "non_existent.xlsx"
        
        with pytest.raises(FileNotFoundError):
            read_glossary_sheet(str(non_existent), 'Sheet1', 'Model')
    
    def test_invalid_json_handling(self, tmp_path):
        """Testa comportamento com JSON inválido"""
        invalid_json = tmp_path / "invalid.json"
        with open(invalid_json, 'w') as f:
            f.write("{ invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            with open(invalid_json, 'r') as f:
                json.load(f)
    
    def test_empty_glossary_handling(self, tmp_path):
        """Testa comportamento com glossário vazio"""
        empty_df = pd.DataFrame(columns=['Código', 'Nome do Parâmetro', 'Unidade', 'Valor Exemplo'])
        excel_file = tmp_path / "empty.xlsx"
        empty_df.to_excel(excel_file, sheet_name='Empty', index=False)
        
        # Extrair (deve retornar lista vazia)
        extracted = read_glossary_sheet(str(excel_file), 'Empty', 'EmptyModel')
        assert extracted == []
        
        # Exportar (não deve falhar)
        json_data = {'EmptyModel': extracted}
        json_file = tmp_path / "empty.json"
        export_to_json(json_data, str(json_file))
        
        assert json_file.exists()


class TestPipelinePerformance:
    """Testes de desempenho básicos"""
    
    def test_large_glossary_processing(self, tmp_path):
        """Testa processamento de glossário grande"""
        import time
        
        # Criar glossário grande (500 parâmetros)
        large_data = {
            'Código': [f'P{i:04d}' for i in range(500)],
            'Nome do Parâmetro': [f'Parâmetro {i}' for i in range(500)],
            'Unidade': ['A'] * 500,
            'Valor Exemplo': [str(i) for i in range(500)]
        }
        
        df = pd.DataFrame(large_data)
        excel_file = tmp_path / "large_glossary.xlsx"
        df.to_excel(excel_file, sheet_name='Large', index=False)
        
        # Medir tempo de extração
        start_time = time.time()
        extracted = read_glossary_sheet(str(excel_file), 'Large', 'LargeModel')
        extraction_time = time.time() - start_time
        
        assert len(extracted) == 500
        assert extraction_time < 5.0  # Deve completar em menos de 5 segundos
        
        # Medir tempo de exportação JSON
        json_data = {'LargeModel': extracted}
        json_file = tmp_path / "large.json"
        
        start_time = time.time()
        export_to_json(json_data, str(json_file))
        export_time = time.time() - start_time
        
        assert export_time < 2.0  # Deve completar em menos de 2 segundos
        
        print(f"\n⏱️  Performance test:")
        print(f"   Extraction time: {extraction_time:.3f}s")
        print(f"   Export time: {export_time:.3f}s")


class TestPipelineValidation:
    """Testes de validação de dados"""
    
    def test_ansi_code_extraction_accuracy(self, tmp_path):
        """Testa precisão da extração de códigos ANSI"""
        test_cases = {
            'Código': ['P001', 'P002', 'P003', 'P004', 'P005'],
            'Nome do Parâmetro': [
                'I> (50) Instantâneo',
                'I>> (50) Alta',
                'U< (27) Subtensão',
                'U> (59) Sobretensão',
                'F> (81) Frequência'
            ],
            'Unidade': ['A', 'A', 'V', 'V', 'Hz'],
            'Valor Exemplo': ['5', '10', '100', '150', '60']
        }
        
        df = pd.DataFrame(test_cases)
        excel_file = tmp_path / "ansi_test.xlsx"
        df.to_excel(excel_file, sheet_name='Test', index=False)
        
        # Extrair e gerar SQL
        extracted = read_glossary_sheet(str(excel_file), 'Test', 'TestModel')
        json_data = {'TestModel': extracted}
        json_file = tmp_path / "ansi.json"
        export_to_json(json_data, str(json_file))
        
        functions_sql = tmp_path / "ansi_functions.sql"
        generate_sql_protection_functions(str(json_file), str(functions_sql))
        
        # Validar que todos os códigos ANSI foram extraídos
        with open(functions_sql, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "'50'" in content  # De P001 e P002
        assert "'27'" in content  # De P003
        assert "'59'" in content  # De P004
        assert "'81'" in content  # De P005
    
    def test_unit_preservation(self, tmp_path):
        """Testa preservação de unidades"""
        data = {
            'Código': ['P001', 'P002', 'P003'],
            'Nome do Parâmetro': ['Corrente', 'Tensão', 'Potência'],
            'Unidade': ['A', 'kV', 'MW'],
            'Valor Exemplo': ['100', '138', '50']
        }
        
        df = pd.DataFrame(data)
        excel_file = tmp_path / "units.xlsx"
        df.to_excel(excel_file, sheet_name='Test', index=False)
        
        extracted = read_glossary_sheet(str(excel_file), 'Test', 'TestModel')
        
        # Validar unidades
        assert extracted[0]['unidade'] == 'A'
        assert extracted[1]['unidade'] == 'kV'
        assert extracted[2]['unidade'] == 'MW'
        
        # Validar no SQL
        json_data = {'TestModel': extracted}
        json_file = tmp_path / "units.json"
        export_to_json(json_data, str(json_file))
        
        settings_sql = tmp_path / "units_settings.sql"
        generate_sql_relay_settings(str(json_file), str(settings_sql))
        
        with open(settings_sql, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "'A'" in content
        assert "'kV'" in content
        assert "'MW'" in content


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

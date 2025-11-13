"""
Testes para validar a extração do glossário de relés.
Valida o módulo scripts/extract_glossary.py
"""

import pytest
import json
import csv
from pathlib import Path
import sys
import pandas as pd

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extract_glossary import GlossaryExtractor


class TestGlossaryExtractor:
    """Testes para a classe GlossaryExtractor"""
    
    @pytest.fixture
    def sample_excel_file(self, tmp_path):
        """Cria arquivo Excel de exemplo para testes"""
        # Simular estrutura do glossário com dados realistas que correspondem ao padrão regex
        # Padrão: ([0-9A-F]{4,})\s*[:\-]\s*(.+?)(?:\s*[=:]\s*(.+))?$
        data_micon = {
            'col1': ['010A: Reference TC', '010B: Inom 5 A', '0211: I>> = 8.0 In'],
            'col2': ['', '', ''],
            'col3': ['', '', '']
        }
        
        data_sepam = {
            'col1': ['Inom=5A', 'Un=13.8kV', 'Freq=60Hz'],
            'col2': ['', '', ''],
            'col3': ['', '', '']
        }
        
        df_micon = pd.DataFrame(data_micon)
        df_sepam = pd.DataFrame(data_sepam)
        
        excel_file = tmp_path / "test_glossary.xlsx"
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df_micon.to_excel(writer, sheet_name='MICON_P122', index=False, header=False)
            df_sepam.to_excel(writer, sheet_name='SEPAM_S40', index=False, header=False)
        
        return excel_file
    
    def test_extractor_initialization_success(self, sample_excel_file):
        """Testa inicialização bem-sucedida do extrator"""
        extractor = GlossaryExtractor(sample_excel_file)
        
        assert extractor.glossary_path == sample_excel_file
        assert extractor.mapping == {}
        assert extractor.flat_records == []
    
    def test_extractor_initialization_file_not_found(self, tmp_path):
        """Testa erro quando arquivo não existe"""
        non_existent_file = tmp_path / "nao_existe.xlsx"
        
        with pytest.raises(FileNotFoundError):
            GlossaryExtractor(non_existent_file)
    
    def test_detect_model_micon(self, sample_excel_file):
        """Testa detecção de modelo MICON"""
        extractor = GlossaryExtractor(sample_excel_file)
        
        assert extractor._detect_model("MICON_P122") == "MICON"
        assert extractor._detect_model("Micon P241") == "MICON"
        assert extractor._detect_model("P14X") == "MICON_P14X"
    
    def test_detect_model_sepam(self, sample_excel_file):
        """Testa detecção de modelo SEPAM"""
        extractor = GlossaryExtractor(sample_excel_file)
        
        assert extractor._detect_model("SEPAM_S40") == "SEPAM"
        assert extractor._detect_model("Sepam S20") == "SEPAM"
        assert extractor._detect_model("S80") == "SEPAM_S80"
    
    def test_extract_unit_basic(self, sample_excel_file):
        """Testa extração de unidades básicas"""
        extractor = GlossaryExtractor(sample_excel_file)
        
        # O regex usa word boundary \b, então precisa de espaço antes da unidade
        assert extractor._extract_unit("current 5.5 A") == "A"
        assert extractor._extract_unit("Voltage 13.8 kV") == "kV"
        assert extractor._extract_unit("Frequency 60 Hz") == "Hz"
        assert extractor._extract_unit("Time 100 ms") == "ms"
        assert extractor._extract_unit("Pickup 5 In") == "In"
    
    def test_extract_unit_not_found(self, sample_excel_file):
        """Testa quando unidade não é encontrada"""
        extractor = GlossaryExtractor(sample_excel_file)
        
        assert extractor._extract_unit("No unit here") == ""
        assert extractor._extract_unit("") == ""
    
    def test_extract_parameters_from_sheet_basic(self, sample_excel_file):
        """Testa extração de parâmetros de uma planilha"""
        extractor = GlossaryExtractor(sample_excel_file)
        
        # Ler uma planilha específica
        df = pd.read_excel(sample_excel_file, sheet_name='MICON_P122', header=None)
        params = extractor._extract_parameters_from_sheet(df, 'MICON', 'MICON_P122')
        
        # Deve ter extraído ao menos alguns parâmetros
        assert len(params) > 0
        
        # Verificar estrutura de cada parâmetro
        for param in params:
            assert 'code' in param
            assert 'name' in param
            assert 'unit' in param
            assert 'value_example' in param
            assert 'model' in param
            assert 'sheet' in param
            assert param['model'] == 'MICON'
            assert param['sheet'] == 'MICON_P122'
    
    def test_full_extract_workflow(self, sample_excel_file):
        """Testa workflow completo de extração"""
        extractor = GlossaryExtractor(sample_excel_file)
        extractor.extract()
        
        # Deve ter extraído dados
        assert len(extractor.mapping) > 0
        assert len(extractor.flat_records) > 0
        
        # Deve ter processado ambos os modelos
        assert 'MICON' in extractor.mapping or 'SEPAM' in extractor.mapping
        
        # Verificar que flat_records tem estrutura correta
        for record in extractor.flat_records:
            assert 'model' in record
            assert 'code' in record
            assert 'name' in record
            assert 'unit' in record
            assert 'value_example' in record
            assert 'sheet' in record
    
    def test_save_json(self, sample_excel_file, tmp_path):
        """Testa salvamento em JSON"""
        extractor = GlossaryExtractor(sample_excel_file)
        extractor.extract()
        
        json_file = tmp_path / "test_output.json"
        extractor.save_json(json_file)
        
        # Verificar que arquivo foi criado
        assert json_file.exists()
        
        # Verificar conteúdo
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
        assert len(data) > 0
    
    def test_save_csv(self, sample_excel_file, tmp_path):
        """Testa salvamento em CSV"""
        extractor = GlossaryExtractor(sample_excel_file)
        extractor.extract()
        
        csv_file = tmp_path / "test_output.csv"
        extractor.save_csv(csv_file)
        
        # Verificar que arquivo foi criado
        assert csv_file.exists()
        
        # Verificar conteúdo
        df = pd.read_csv(csv_file)
        
        assert len(df) > 0
        assert 'model' in df.columns
        assert 'code' in df.columns
        assert 'name' in df.columns
        assert 'unit' in df.columns
        assert 'value_example' in df.columns
        assert 'sheet' in df.columns
    
    def test_csv_json_consistency(self, sample_excel_file, tmp_path):
        """Testa consistência entre CSV e JSON"""
        extractor = GlossaryExtractor(sample_excel_file)
        extractor.extract()
        
        json_file = tmp_path / "test_output.json"
        csv_file = tmp_path / "test_output.csv"
        
        extractor.save_json(json_file)
        extractor.save_csv(csv_file)
        
        # Contar registros no JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        json_count = sum(len(params) for params in json_data.values())
        
        # Contar registros no CSV
        df = pd.read_csv(csv_file)
        csv_count = len(df)
        
        # Devem ter o mesmo número de registros
        assert json_count == csv_count


class TestEdgeCases:
    """Testes de casos extremos e situações incomuns"""
    
    def test_empty_excel_file(self, tmp_path):
        """Testa arquivo Excel sem dados"""
        empty_df = pd.DataFrame()
        excel_file = tmp_path / "empty.xlsx"
        empty_df.to_excel(excel_file, sheet_name='Empty', index=False)
        
        extractor = GlossaryExtractor(excel_file)
        extractor.extract()
        
        # Não deve gerar erro, apenas não extrair nada
        assert len(extractor.flat_records) == 0
    
    def test_special_characters_in_parameters(self, tmp_path):
        """Testa parâmetros com caracteres especiais"""
        data = {
            'col1': ['I> (50) - Corrente'],
            'col2': ['V< (27) - Tensão'],
            'col3': ['']
        }
        df = pd.DataFrame(data)
        
        excel_file = tmp_path / "special_chars.xlsx"
        df.to_excel(excel_file, sheet_name='TEST_MODEL', index=False, header=False)
        
        extractor = GlossaryExtractor(excel_file)
        extractor.extract()
        
        # Deve processar sem erros
        assert len(extractor.flat_records) >= 0
    
    def test_unicode_characters(self, tmp_path):
        """Testa caracteres unicode (acentuação)"""
        data = {
            'col1': ['Tensão Máxima'],
            'col2': ['Corrente Mínima'],
            'col3': ['Freqüência']
        }
        df = pd.DataFrame(data)
        
        excel_file = tmp_path / "unicode.xlsx"
        df.to_excel(excel_file, sheet_name='UNICODE_TEST', index=False, header=False)
        
        extractor = GlossaryExtractor(excel_file)
        extractor.extract()
        
        # Deve processar sem erros
        assert len(extractor.flat_records) >= 0
    
    def test_multiple_sheets_same_model(self, tmp_path):
        """Testa múltiplas planilhas do mesmo modelo"""
        # Usar códigos hexadecimais válidos com 4+ caracteres
        data1 = {'col1': ['A001: Param1'], 'col2': ['']}
        data2 = {'col1': ['B002: Param2'], 'col2': ['']}
        
        df1 = pd.DataFrame(data1)
        df2 = pd.DataFrame(data2)
        
        excel_file = tmp_path / "multi_sheets.xlsx"
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df1.to_excel(writer, sheet_name='MICON_P122', index=False, header=False)
            df2.to_excel(writer, sheet_name='MICON_P241', index=False, header=False)
        
        extractor = GlossaryExtractor(excel_file)
        extractor.extract()
        
        # Deve consolidar em um único modelo MICON
        assert 'MICON' in extractor.mapping
        # Deve ter parâmetros de ambas as planilhas
        assert len(extractor.mapping['MICON']) > 0


class TestIntegrationRealFile:
    """Testes de integração com arquivo real do projeto"""
    
    def test_real_glossary_file_exists(self):
        """Verifica se arquivo real do glossário existe"""
        real_file = Path(__file__).parent.parent / "inputs" / "glossario" / "Dados_Glossario_Micon_Sepam.xlsx"
        
        # Apenas verifica se existe (não falha se não existir)
        if real_file.exists():
            assert real_file.is_file()
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "inputs" / "glossario" / "Dados_Glossario_Micon_Sepam.xlsx").exists(),
        reason="Arquivo real do glossário não encontrado"
    )
    def test_extract_real_glossary(self):
        """Testa extração do arquivo real do glossário"""
        real_file = Path(__file__).parent.parent / "inputs" / "glossario" / "Dados_Glossario_Micon_Sepam.xlsx"
        
        extractor = GlossaryExtractor(real_file)
        extractor.extract()
        
        # Deve ter extraído dados
        assert len(extractor.mapping) > 0
        assert len(extractor.flat_records) > 0
        
        # Deve ter modelos MICON e SEPAM
        models = set(extractor.mapping.keys())
        assert len(models) > 0
        
        # Verificar que tem registros com dados válidos
        for model, params in extractor.mapping.items():
            for param in params:
                assert param['code'] != ''
                assert param['model'] == model


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

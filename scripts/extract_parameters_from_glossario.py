"""
EXTRAÇÃO CORRETA DE PARÂMETROS SEGUINDO O GLOSSÁRIO

OBJETIVO: Extrair parâmetros dos PDFs/TXTs seguindo EXATAMENTE a estrutura do glossário
ENTRADA: inputs/pdf/*.pdf, inputs/txt/*.S40
SAÍDA: outputs/csv/*.csv (RAW mas já estruturado conforme glossário)

CRÍTICO: VIDAS EM RISCO - Este script deve extrair TODOS os parâmetros do glossário
"""

import pandas as pd
import PyPDF2
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/logs/extraction_glossario.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GlossarioExtractor:
    """Extrator que segue EXATAMENTE o glossário"""
    
    def __init__(self, glossario_path: str = "inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx"):
        self.glossario_path = glossario_path
        self.model_parameters = {}
        self.model_sections = {}
        self.observations = {}
        self._load_glossario()
    
    def _load_glossario(self):
        """Carrega TODAS as abas do glossário"""
        logger.info(f"Carregando glossário: {self.glossario_path}")
        
        try:
            xl_file = pd.ExcelFile(self.glossario_path)
            
            for sheet_name in xl_file.sheet_names:
                logger.info(f"Processando aba: {sheet_name}")
                df = pd.read_excel(xl_file, sheet_name=sheet_name)
                
                # Mapear modelo
                model_key = self._map_sheet_to_model(sheet_name)
                
                # Extrair parâmetros
                parameters = []
                sections = {}
                current_section = None
                current_subsection = None
                
                for idx, row in df.iterrows():
                    # Detectar seções
                    if pd.notna(row.get('SEÇÃO', '')):
                        current_section = str(row['SEÇÃO']).strip()
                        if current_section not in sections:
                            sections[current_section] = []
                    
                    # Detectar subseções
                    if pd.notna(row.get('SUBSEÇÃO', '')):
                        current_subsection = str(row['SUBSEÇÃO']).strip()
                    
                    # Extrair parâmetros
                    param_code = row.get('CÓDIGO', row.get('Código', ''))
                    param_name = row.get('PARÂMETRO', row.get('Parâmetro', row.get('NOME', '')))
                    
                    if pd.notna(param_code) and pd.notna(param_name):
                        param = {
                            'code': str(param_code).strip(),
                            'name': str(param_name).strip(),
                            'section': current_section,
                            'subsection': current_subsection,
                            'unit': str(row.get('UNIDADE', row.get('Unidade', ''))).strip() if pd.notna(row.get('UNIDADE', row.get('Unidade', ''))) else '',
                            'category': str(row.get('CATEGORIA', row.get('Categoria', ''))).strip() if pd.notna(row.get('CATEGORIA', row.get('Categoria', ''))) else '',
                            'observation': str(row.get('OBSERVAÇÃO', row.get('Observação', ''))).strip() if pd.notna(row.get('OBSERVAÇÃO', row.get('Observação', ''))) else ''
                        }
                        parameters.append(param)
                        
                        if current_section:
                            sections[current_section].append(param)
                
                self.model_parameters[model_key] = parameters
                self.model_sections[model_key] = sections
                
                logger.info(f"  ✓ {model_key}: {len(parameters)} parâmetros, {len(sections)} seções")
        
        except Exception as e:
            logger.error(f"ERRO ao carregar glossário: {e}")
            raise
    
    def _map_sheet_to_model(self, sheet_name: str) -> str:
        """Mapeia nome da aba para código do modelo"""
        mappings = {
            'P122_52/204': 'P122',
            'P122_205': 'P122_205',
            'P220': 'P220',
            'P241': 'P241',
            'P143': 'P143',
            'P922': 'P922',
            'SEPAM S40': 'SEPAM_S40'
        }
        
        for key, value in mappings.items():
            if key.lower() in sheet_name.lower():
                return value
        
        return sheet_name
    
    def detect_model_from_filename(self, filename: str) -> Optional[str]:
        """Detecta modelo a partir do nome do arquivo"""
        filename_upper = filename.upper()
        
        # Ordem importa! P122_205 antes de P122
        if 'P122_205' in filename_upper or 'P122-205' in filename_upper:
            return 'P122_205'
        elif 'P122' in filename_upper:
            return 'P122'
        elif 'P220' in filename_upper:
            return 'P220'
        elif 'P241' in filename_upper:
            return 'P241'
        elif 'P143' in filename_upper:
            return 'P143'
        elif 'P922' in filename_upper:
            return 'P922'
        elif 'S40' in filename_upper or 'SEPAM' in filename_upper:
            return 'SEPAM_S40'
        
        return None
    
    def extract_from_pdf(self, pdf_path: Path) -> List[Dict]:
        """Extrai parâmetros de PDF seguindo glossário"""
        logger.info(f"Extraindo PDF: {pdf_path.name}")
        
        # Detectar modelo
        model = self.detect_model_from_filename(pdf_path.name)
        if not model:
            logger.warning(f"  ⚠️  Modelo não detectado para {pdf_path.name}")
            return []
        
        if model not in self.model_parameters:
            logger.warning(f"  ⚠️  Modelo {model} não encontrado no glossário")
            return []
        
        logger.info(f"  → Modelo detectado: {model}")
        
        # Extrair texto do PDF
        text = self._extract_pdf_text(pdf_path)
        
        # Buscar parâmetros do glossário no texto
        extracted = []
        expected_params = self.model_parameters[model]
        
        for param in expected_params:
            # Buscar código do parâmetro no texto
            pattern = rf"{re.escape(param['code'])}\s*[:=\-]?\s*([^\n]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                value = match.group(1).strip()
                extracted.append({
                    'parameter_code': param['code'],
                    'parameter_name': param['name'],
                    'set_value': value,
                    'unit_of_measure': param['unit'],
                    'section': param['section'],
                    'subsection': param['subsection'],
                    'category': param['category'],
                    'source_file': pdf_path.name
                })
        
        logger.info(f"  ✓ Extraídos {len(extracted)}/{len(expected_params)} parâmetros")
        return extracted
    
    def extract_from_s40(self, txt_path: Path) -> List[Dict]:
        """Extrai parâmetros de arquivo .S40 seguindo glossário"""
        logger.info(f"Extraindo S40: {txt_path.name}")
        
        model = 'SEPAM_S40'
        if model not in self.model_parameters:
            logger.warning(f"  ⚠️  Modelo SEPAM_S40 não encontrado no glossário")
            return []
        
        # Ler arquivo S40
        with open(txt_path, 'r', encoding='latin-1', errors='ignore') as f:
            content = f.read()
        
        # Buscar parâmetros do glossário
        extracted = []
        expected_params = self.model_parameters[model]
        
        for param in expected_params:
            # Padrão S40: [CODIGO]="valor"
            pattern = rf"\[{re.escape(param['code'])}\]\s*=\s*\"([^\"]+)\""
            match = re.search(pattern, content, re.IGNORECASE)
            
            if match:
                value = match.group(1).strip()
                extracted.append({
                    'parameter_code': param['code'],
                    'parameter_name': param['name'],
                    'set_value': value,
                    'unit_of_measure': param['unit'],
                    'section': param['section'],
                    'subsection': param['subsection'],
                    'category': param['category'],
                    'source_file': txt_path.name
                })
        
        logger.info(f"  ✓ Extraídos {len(extracted)}/{len(expected_params)} parâmetros")
        return extracted
    
    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extrai texto completo do PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Erro ao ler PDF {pdf_path.name}: {e}")
            return ""
    
    def process_all_files(self):
        """Processa TODOS os arquivos de entrada"""
        logger.info("="*80)
        logger.info("INICIANDO EXTRAÇÃO COMPLETA SEGUINDO GLOSSÁRIO")
        logger.info("="*80)
        
        # Criar diretório de saída
        output_dir = Path("outputs/csv")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        total_files = 0
        total_params = 0
        
        # Processar PDFs
        pdf_dir = Path("inputs/pdf")
        if pdf_dir.exists():
            for pdf_file in sorted(pdf_dir.glob("*.pdf")):
                extracted = self.extract_from_pdf(pdf_file)
                
                if extracted:
                    # Salvar CSV
                    output_file = output_dir / f"{pdf_file.stem}.csv"
                    df = pd.DataFrame(extracted)
                    df.to_csv(output_file, index=False, encoding='utf-8')
                    
                    total_files += 1
                    total_params += len(extracted)
                    logger.info(f"  💾 Salvo: {output_file.name}")
        
        # Processar S40
        txt_dir = Path("inputs/txt")
        if txt_dir.exists():
            for txt_file in sorted(txt_dir.glob("*.S40")):
                extracted = self.extract_from_s40(txt_file)
                
                if extracted:
                    # Salvar CSV
                    output_file = output_dir / f"{txt_file.stem}.csv"
                    df = pd.DataFrame(extracted)
                    df.to_csv(output_file, index=False, encoding='utf-8')
                    
                    total_files += 1
                    total_params += len(extracted)
                    logger.info(f"  💾 Salvo: {output_file.name}")
        
        logger.info("="*80)
        logger.info(f"✅ EXTRAÇÃO CONCLUÍDA")
        logger.info(f"   📁 Arquivos processados: {total_files}")
        logger.info(f"   📊 Parâmetros extraídos: {total_params}")
        logger.info("="*80)
        
        # Gerar relatório
        self._generate_report(total_files, total_params)
    
    def _generate_report(self, total_files: int, total_params: int):
        """Gera relatório de extração"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_files_processed': total_files,
            'total_parameters_extracted': total_params,
            'models_in_glossario': list(self.model_parameters.keys()),
            'parameters_per_model': {
                model: len(params) 
                for model, params in self.model_parameters.items()
            }
        }
        
        report_path = Path("outputs/logs/extraction_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📋 Relatório salvo: {report_path}")


def main():
    """Execução principal"""
    try:
        extractor = GlossarioExtractor()
        extractor.process_all_files()
        
    except Exception as e:
        logger.error(f"ERRO CRÍTICO: {e}")
        raise


if __name__ == "__main__":
    main()

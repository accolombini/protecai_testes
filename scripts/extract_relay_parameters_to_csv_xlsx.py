"""
EXTRAÇÃO DE PARÂMETROS DOS RELÉS - GERA CSV + XLSX
Sistema ProtecAI - PETROBRAS
Data: 5 de novembro de 2025

OBJETIVO: Extrair parâmetros dos PDFs/S40 e gerar arquivos CSV + XLSX
ENTRADA: inputs/pdf/*.pdf, inputs/txt/*.S40
SAÍDA: outputs/csv/*.csv E outputs/csv/*.xlsx

CRÍTICO: VIDAS EM RISCO - Zero tolerância a falhas
"""

import pandas as pd
import PyPDF2
import re
from pathlib import Path
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/logs/parameter_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ParameterExtractor:
    """Extrator de parâmetros de relés"""
    
    # Padrões para detectar modelo do arquivo
    MODEL_PATTERNS = {
        'P122_205': [r'P122[_\s-]*205', r'P122-205'],
        'P122': [r'P122[_\s-]*(52|204)', r'P_122'],
        'P220': [r'P220'],
        'P241': [r'P241'],
        'P143': [r'P143'],
        'P922S': [r'P922S'],
        'P922': [r'P922'],
        'SEPAM': [r'S40', r'SEPAM']
    }
    
    def __init__(self):
        self.stats = {
            'total_files': 0,
            'total_parameters': 0,
            'files_processed': [],
            'files_with_errors': []
        }
    
    def detect_model(self, filename: str) -> Optional[str]:
        """Detecta modelo do relé pelo nome do arquivo"""
        filename_upper = filename.upper()
        
        # Ordem importa! P122_205 antes de P122
        for model, patterns in self.MODEL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename_upper, re.IGNORECASE):
                    return model
        
        return None
    
    def extract_from_pdf(self, pdf_path: Path) -> List[Dict]:
        """Extrai parâmetros de arquivo PDF"""
        logger.info(f"📄 Extraindo PDF: {pdf_path.name}")
        
        try:
            # Extrair texto do PDF
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                full_text = ""
                for page in reader.pages:
                    full_text += page.extract_text() + "\n"
            
            # Extrair parâmetros
            parameters = self._parse_parameters(full_text, pdf_path.name)
            
            logger.info(f"  ✅ {len(parameters)} parâmetros extraídos")
            return parameters
            
        except Exception as e:
            logger.error(f"  ❌ Erro ao extrair {pdf_path.name}: {e}")
            self.stats['files_with_errors'].append(pdf_path.name)
            return []
    
    def extract_from_s40(self, txt_path: Path) -> List[Dict]:
        """Extrai parâmetros de arquivo .S40"""
        logger.info(f"📄 Extraindo S40: {txt_path.name}")
        
        try:
            # Tentar múltiplos encodings
            encodings = ['latin-1', 'cp1252', 'utf-8']
            content = None
            
            for encoding in encodings:
                try:
                    with open(txt_path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read()
                    break
                except:
                    continue
            
            if not content:
                logger.error(f"  ❌ Não foi possível ler {txt_path.name}")
                return []
            
            # Extrair parâmetros
            parameters = self._parse_s40_parameters(content, txt_path.name)
            
            logger.info(f"  ✅ {len(parameters)} parâmetros extraídos")
            return parameters
            
        except Exception as e:
            logger.error(f"  ❌ Erro ao extrair {txt_path.name}: {e}")
            self.stats['files_with_errors'].append(txt_path.name)
            return []
    
    def _parse_parameters(self, text: str, filename: str) -> List[Dict]:
        """Parse de parâmetros de texto PDF"""
        parameters = []
        
        # Padrões comuns em PDFs MiCOM
        # Formato: "0200: Function I>: Yes"
        # Formato: "0201: I>: 0.63In"
        pattern = r'(\d{4}):\s*([^:]+?):\s*([^\n]+)'
        
        matches = re.finditer(pattern, text)
        
        for match in matches:
            code = match.group(1).strip()
            name = match.group(2).strip()
            value = match.group(3).strip()
            
            # Limpar valor
            value = value.split('\n')[0].strip()
            
            parameters.append({
                'parameter_code': code,
                'parameter_name': name,
                'set_value': value,
                'source_file': filename,
                'extraction_date': datetime.now().isoformat()
            })
        
        return parameters
    
    def _parse_s40_parameters(self, content: str, filename: str) -> List[Dict]:
        """Parse de parâmetros de arquivo .S40"""
        parameters = []
        
        # Formato S40: [codigo]="valor"
        pattern = r'\[([^\]]+)\]\s*=\s*"([^"]*)"'
        
        matches = re.finditer(pattern, content)
        
        for match in matches:
            code = match.group(1).strip()
            value = match.group(2).strip()
            
            # Nome é o próprio código para S40
            parameters.append({
                'parameter_code': code,
                'parameter_name': code,
                'set_value': value,
                'source_file': filename,
                'extraction_date': datetime.now().isoformat()
            })
        
        return parameters
    
    def save_to_csv_and_xlsx(self, parameters: List[Dict], original_filename: str):
        """Salva parâmetros em CSV e XLSX"""
        if not parameters:
            logger.warning(f"  ⚠️ Nenhum parâmetro para salvar: {original_filename}")
            return
        
        # Criar DataFrame
        df = pd.DataFrame(parameters)
        
        # Nome do arquivo de saída (sem extensão original)
        stem = Path(original_filename).stem
        output_base = Path("outputs/csv") / stem
        
        # Criar diretório se não existir
        output_base.parent.mkdir(parents=True, exist_ok=True)
        
        # Salvar CSV
        csv_file = f"{output_base}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        logger.info(f"  💾 CSV salvo: {Path(csv_file).name}")
        
        # Salvar XLSX
        xlsx_file = f"{output_base}.xlsx"
        with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Parameters', index=False)
            
            # Adicionar estatísticas
            stats_df = pd.DataFrame([{
                'Total Parameters': len(df),
                'Source File': original_filename,
                'Extraction Date': datetime.now().isoformat(),
                'Model Detected': self.detect_model(original_filename) or 'UNKNOWN'
            }])
            stats_df.to_excel(writer, sheet_name='Stats', index=False)
        
        logger.info(f"  💾 XLSX salvo: {Path(xlsx_file).name}")
    
    def process_all_files(self):
        """Processa TODOS os arquivos de entrada"""
        logger.info("="*80)
        logger.info("🚀 INICIANDO EXTRAÇÃO DE PARÂMETROS")
        logger.info("="*80)
        
        # Processar PDFs
        pdf_dir = Path("inputs/pdf")
        if pdf_dir.exists():
            pdf_files = sorted(pdf_dir.glob("*.pdf"))
            logger.info(f"\n📁 Encontrados {len(pdf_files)} arquivos PDF")
            
            for pdf_file in pdf_files:
                parameters = self.extract_from_pdf(pdf_file)
                if parameters:
                    self.save_to_csv_and_xlsx(parameters, pdf_file.name)
                    self.stats['total_files'] += 1
                    self.stats['total_parameters'] += len(parameters)
                    self.stats['files_processed'].append(pdf_file.name)
        
        # Processar S40
        txt_dir = Path("inputs/txt")
        if txt_dir.exists():
            s40_files = sorted(txt_dir.glob("*.S40"))
            logger.info(f"\n📁 Encontrados {len(s40_files)} arquivos S40")
            
            for s40_file in s40_files:
                parameters = self.extract_from_s40(s40_file)
                if parameters:
                    self.save_to_csv_and_xlsx(parameters, s40_file.name)
                    self.stats['total_files'] += 1
                    self.stats['total_parameters'] += len(parameters)
                    self.stats['files_processed'].append(s40_file.name)
        
        # Relatório final
        self._print_final_report()
    
    def _print_final_report(self):
        """Imprime relatório final da extração"""
        logger.info("\n" + "="*80)
        logger.info("✅ EXTRAÇÃO CONCLUÍDA")
        logger.info("="*80)
        logger.info(f"📁 Arquivos processados: {self.stats['total_files']}")
        logger.info(f"📊 Parâmetros extraídos: {self.stats['total_parameters']}")
        
        if self.stats['files_with_errors']:
            logger.warning(f"\n⚠️ Arquivos com erros: {len(self.stats['files_with_errors'])}")
            for filename in self.stats['files_with_errors']:
                logger.warning(f"  - {filename}")
        
        logger.info("\n📋 Arquivos gerados em outputs/csv/:")
        logger.info(f"  - {self.stats['total_files']} arquivos CSV")
        logger.info(f"  - {self.stats['total_files']} arquivos XLSX")
        logger.info("="*80)


def main():
    """Execução principal"""
    try:
        extractor = ParameterExtractor()
        extractor.process_all_files()
        
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO: {e}")
        raise


if __name__ == "__main__":
    main()

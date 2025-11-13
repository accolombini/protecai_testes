"""
VALIDAÇÃO DE COMPLETUDE DA EXTRAÇÃO
====================================

OBJETIVO: Validar se TODOS os parâmetros dos PDFs/TXTs foram extraídos para os CSVs

CRÍTICO: VIDAS EM RISCO - Zero tolerância para dados faltando
"""

import PyPDF2
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Set
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class ExtractionValidator:
    """Valida completude da extração PDF/TXT → CSV"""
    
    def __init__(self):
        self.results = {
            'total_files': 0,
            'files_validated': [],
            'missing_parameters': {},
            'extraction_rate': {}
        }
    
    def extract_parameters_from_pdf(self, pdf_path: Path) -> Set[str]:
        """Extrai TODOS os códigos de parâmetros encontrados no PDF"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📄 VALIDANDO: {pdf_path.name}")
        logger.info(f"{'='*80}")
        
        codes_found = set()
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                full_text = ""
                for page in reader.pages:
                    full_text += page.extract_text() + "\n"
            
            # Padrão para códigos de parâmetros (4 dígitos seguidos de :)
            # Exemplo: "0120: Line CT primary"
            pattern = r'(\d{4}):\s*([^:\n]+)'
            matches = re.finditer(pattern, full_text)
            
            for match in matches:
                code = match.group(1)
                description = match.group(2).strip()
                codes_found.add(code)
                
            logger.info(f"✅ Códigos encontrados no PDF: {len(codes_found)}")
            
            # Mostrar alguns exemplos
            examples = sorted(list(codes_found))[:10]
            logger.info(f"📋 Exemplos: {', '.join(examples)}")
            
            return codes_found
            
        except Exception as e:
            logger.error(f"❌ Erro ao ler PDF: {e}")
            return set()
    
    def extract_parameters_from_txt(self, txt_path: Path) -> Set[str]:
        """Extrai TODOS os códigos de parâmetros encontrados no .S40"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📄 VALIDANDO: {txt_path.name}")
        logger.info(f"{'='*80}")
        
        codes_found = set()
        
        try:
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
                logger.error(f"❌ Não foi possível ler {txt_path.name}")
                return set()
            
            # Padrão S40: [codigo]="valor"
            pattern = r'\[([^\]]+)\]='
            matches = re.finditer(pattern, content)
            
            for match in matches:
                code = match.group(1).strip()
                codes_found.add(code)
            
            logger.info(f"✅ Códigos encontrados no S40: {len(codes_found)}")
            
            # Mostrar alguns exemplos
            examples = sorted(list(codes_found))[:10]
            logger.info(f"📋 Exemplos: {', '.join(examples)}")
            
            return codes_found
            
        except Exception as e:
            logger.error(f"❌ Erro ao ler TXT: {e}")
            return set()
    
    def extract_parameters_from_csv(self, csv_path: Path) -> Set[str]:
        """Extrai TODOS os códigos de parâmetros do CSV gerado"""
        try:
            df = pd.read_csv(csv_path)
            codes = set(df['Code'].astype(str).values)
            logger.info(f"✅ Códigos no CSV: {len(codes)}")
            return codes
        except Exception as e:
            logger.error(f"❌ Erro ao ler CSV: {e}")
            return set()
    
    def validate_file(self, input_file: Path, csv_file: Path):
        """Valida se todos os parâmetros foram extraídos"""
        
        # Extrair do arquivo original
        if input_file.suffix.lower() == '.pdf':
            original_codes = self.extract_parameters_from_pdf(input_file)
        else:  # .S40
            original_codes = self.extract_parameters_from_txt(input_file)
        
        if not original_codes:
            logger.warning(f"⚠️  Nenhum código encontrado no arquivo original")
            return
        
        # Extrair do CSV
        csv_codes = self.extract_parameters_from_csv(csv_file)
        
        # Comparar
        missing = original_codes - csv_codes
        extra = csv_codes - original_codes
        
        extraction_rate = (len(csv_codes) / len(original_codes) * 100) if original_codes else 0
        
        logger.info(f"\n📊 RESULTADO DA VALIDAÇÃO:")
        logger.info(f"   Original: {len(original_codes)} códigos")
        logger.info(f"   CSV:      {len(csv_codes)} códigos")
        logger.info(f"   Taxa:     {extraction_rate:.1f}%")
        
        if missing:
            logger.warning(f"\n⚠️  FALTANDO {len(missing)} CÓDIGOS NO CSV:")
            for code in sorted(list(missing))[:20]:  # Mostrar primeiros 20
                logger.warning(f"      - {code}")
            if len(missing) > 20:
                logger.warning(f"      ... e mais {len(missing) - 20} códigos")
        
        if extra:
            logger.info(f"\n➕ {len(extra)} códigos EXTRAS no CSV (não encontrados no original)")
        
        if not missing and not extra:
            logger.info(f"\n✅ PERFEITO! Todos os parâmetros foram extraídos corretamente!")
        
        # Salvar resultado
        self.results['files_validated'].append(input_file.name)
        self.results['missing_parameters'][input_file.name] = list(missing)
        self.results['extraction_rate'][input_file.name] = extraction_rate
        self.results['total_files'] += 1
    
    def validate_sample(self):
        """Valida amostra de arquivos (1 de cada tipo)"""
        
        samples = {
            'P122 (PDF)': ('inputs/pdf/P122 52-MF-02A_2021-03-08.pdf', 
                          'outputs/csv/P122 52-MF-02A_2021-03-08_params.csv'),
            'P143 (PDF)': ('inputs/pdf/P143 52-MF-03A.pdf',
                          'outputs/csv/P143 52-MF-03A_params.csv'),
            'P220 (PDF)': ('inputs/pdf/P220 52-MP-01A.pdf',
                          'outputs/csv/P220 52-MP-01A_params.csv'),
            'P241 (PDF)': ('inputs/pdf/P241_52-MP-20_2019-08-15.pdf',
                          'outputs/csv/P241_52-MP-20_2019-08-15_params.csv'),
            'P922 (PDF)': ('inputs/pdf/P922 52-MF-01BC.pdf',
                          'outputs/csv/P922 52-MF-01BC_params.csv'),
            'SEPAM (S40)': ('inputs/txt/00-MF-12_2016-03-31.S40',
                           'outputs/csv/00-MF-12_2016-03-31_params.csv')
        }
        
        logger.info("\n" + "="*80)
        logger.info("🔍 VALIDAÇÃO DE COMPLETUDE DA EXTRAÇÃO")
        logger.info("="*80)
        logger.info(f"📋 Validando {len(samples)} arquivos de amostra (1 de cada modelo)")
        
        for model_name, (input_path, csv_path) in samples.items():
            input_file = Path(input_path)
            csv_file = Path(csv_path)
            
            if not input_file.exists():
                logger.warning(f"⚠️  Arquivo de entrada não encontrado: {input_path}")
                continue
            
            if not csv_file.exists():
                logger.warning(f"⚠️  CSV não encontrado: {csv_path}")
                continue
            
            logger.info(f"\n{'='*80}")
            logger.info(f"🔍 {model_name}")
            self.validate_file(input_file, csv_file)
        
        # Resumo final
        self.print_summary()
    
    def print_summary(self):
        """Imprime resumo da validação"""
        logger.info("\n" + "="*80)
        logger.info("📊 RESUMO FINAL DA VALIDAÇÃO")
        logger.info("="*80)
        
        logger.info(f"📁 Arquivos validados: {self.results['total_files']}")
        
        avg_rate = sum(self.results['extraction_rate'].values()) / len(self.results['extraction_rate']) if self.results['extraction_rate'] else 0
        logger.info(f"📈 Taxa média de extração: {avg_rate:.1f}%")
        
        files_with_missing = [f for f, m in self.results['missing_parameters'].items() if m]
        
        if files_with_missing:
            logger.warning(f"\n⚠️  {len(files_with_missing)} arquivos COM parâmetros faltando:")
            for filename in files_with_missing:
                missing_count = len(self.results['missing_parameters'][filename])
                logger.warning(f"   - {filename}: {missing_count} faltando")
        else:
            logger.info(f"\n✅ TODOS os arquivos foram extraídos COMPLETAMENTE!")
        
        logger.info("\n" + "="*80)


def main():
    validator = ExtractionValidator()
    validator.validate_sample()


if __name__ == "__main__":
    main()

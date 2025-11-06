"""
🌍 PROCESSADOR COMPLETO DA PIPELINE
====================================

Processa TODOS os arquivos de entrada (PDFs + TXTs) usando o parser universal
e o glossário como referência de validação.

ENTRADA:
- inputs/pdf/      (47 PDFs de configuração de relés)
- inputs/txt/      (TXTs de configuração)
- inputs/glossario/ (Glossário de referência)

SAÍDA:
- outputs/csv/       (CSVs brutos extraídos)
- outputs/excel/     (Excel brutos extraídos)
- outputs/norm_csv/  (CSVs normalizados)
- outputs/norm_excel/(Excel normalizados)

Autor: ProtecAI Team
Data: 06/11/2025
"""

import sys
import os
from pathlib import Path
import logging
from typing import List, Dict, Any, Tuple
import json
from datetime import datetime

# Adicionar path do projeto
sys.path.append(str(Path(__file__).parent.parent))

from src.universal_glossary_parser import UniversalGlossaryParser
from src.intelligent_relay_extractor import IntelligentRelayExtractor
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class CompletePipelineProcessor:
    """
    Processador completo que:
    1. Carrega glossário como referência
    2. Processa todos os PDFs
    3. Processa todos os TXTs
    4. Valida com glossário
    5. Normaliza e exporta
    """
    
    def __init__(self, project_root: str):
        """
        Inicializa processador
        
        Args:
            project_root: Raiz do projeto
        """
        self.project_root = Path(project_root)
        
        # Pastas de entrada
        self.input_pdf_folder = self.project_root / "inputs" / "pdf"
        self.input_txt_folder = self.project_root / "inputs" / "txt"
        self.input_glossario = self.project_root / "inputs" / "glossario" / "Dados_Glossario_Micon_Sepam.xlsx"
        
        # Pastas de saída
        self.output_csv = self.project_root / "outputs" / "csv"
        self.output_excel = self.project_root / "outputs" / "excel"
        self.output_norm_csv = self.project_root / "outputs" / "norm_csv"
        self.output_norm_excel = self.project_root / "outputs" / "norm_excel"
        
        # Criar pastas de saída
        for folder in [self.output_csv, self.output_excel, 
                      self.output_norm_csv, self.output_norm_excel]:
            folder.mkdir(parents=True, exist_ok=True)
        
        # Glossário (referência universal)
        self.glossario_data = None
        self.extractor = IntelligentRelayExtractor()
        
        logger.info("="*80)
        logger.info("🌍 PROCESSADOR COMPLETO DA PIPELINE INICIALIZADO")
        logger.info("="*80)
    
    def load_glossario_reference(self) -> bool:
        """
        Carrega glossário como referência universal
        
        Returns:
            True se sucesso
        """
        logger.info("\n" + "="*80)
        logger.info("📚 CARREGANDO GLOSSÁRIO DE REFERÊNCIA")
        logger.info("="*80)
        
        if not self.input_glossario.exists():
            logger.error(f"❌ Glossário não encontrado: {self.input_glossario}")
            return False
        
        try:
            parser = UniversalGlossaryParser(str(self.input_glossario))
            parameters = parser.parse_all()
            
            # Converter para dicionário indexado
            self.glossario_data = {
                'parameters': parameters,
                'by_model': {},
                'by_code': {}
            }
            
            # Indexar por modelo e código
            for param in parameters:
                model = param.modelo
                code = param.codigo
                
                if model not in self.glossario_data['by_model']:
                    self.glossario_data['by_model'][model] = []
                self.glossario_data['by_model'][model].append(param)
                
                if code not in self.glossario_data['by_code']:
                    self.glossario_data['by_code'][code] = []
                self.glossario_data['by_code'][code].append(param)
            
            logger.info(f"✅ Glossário carregado: {len(parameters)} parâmetros")
            logger.info(f"   • Modelos: {len(self.glossario_data['by_model'])}")
            logger.info(f"   • Códigos únicos: {len(self.glossario_data['by_code'])}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar glossário: {e}", exc_info=True)
            return False
    
    def discover_input_files(self) -> Dict[str, List[Path]]:
        """
        Descobre todos os arquivos de entrada
        
        Returns:
            Dicionário com listas de arquivos por tipo
        """
        logger.info("\n" + "="*80)
        logger.info("🔍 DESCOBRINDO ARQUIVOS DE ENTRADA")
        logger.info("="*80)
        
        files = {
            'pdf': [],
            'sepam': []
        }
        
        # PDFs
        if self.input_pdf_folder.exists():
            files['pdf'] = sorted(self.input_pdf_folder.glob("*.pdf"))
            logger.info(f"📄 PDFs encontrados: {len(files['pdf'])}")
            if files['pdf']:
                for f in files['pdf'][:3]:
                    logger.info(f"   • {f.name}")
                if len(files['pdf']) > 3:
                    logger.info(f"   ... e mais {len(files['pdf']) - 3} arquivo(s)")
        
        # SEPAMs (.S40 e .s40)
        if self.input_txt_folder.exists():
            sepam_files = []
            sepam_files.extend(self.input_txt_folder.glob("*.S40"))  # Maiúsculo
            sepam_files.extend(self.input_txt_folder.glob("*.s40"))  # Minúsculo
            sepam_files.extend(self.input_txt_folder.glob("*.txt"))  # TXT também
            files['sepam'] = sorted(set(sepam_files))  # Remove duplicatas
            
            logger.info(f"📝 SEPAMs encontrados (.S40/.s40/.txt): {len(files['sepam'])}")
            if files['sepam']:
                for f in files['sepam']:
                    logger.info(f"   • {f.name}")
        
        total = len(files['pdf']) + len(files['sepam'])
        logger.info(f"\n📊 TOTAL: {total} arquivo(s) para processar")
        
        return files
    
    def process_pdf_file(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Processa um arquivo PDF
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            Dicionário com dados extraídos
        """
        logger.info(f"\n📄 Processando PDF: {pdf_path.name}")
        
        try:
            # Detectar tipo de relé
            relay_type = self.extractor.detect_relay_type(pdf_path)
            logger.info(f"   🔍 Tipo detectado: {relay_type}")
            
            # Extrair parâmetros baseado no tipo
            if relay_type == 'easergy':
                df = self.extractor.extract_from_easergy(pdf_path)
            elif relay_type == 'micom':
                df = self.extractor.extract_from_micom(pdf_path)
            else:
                logger.warning(f"   ⚠️  Tipo desconhecido, tentando extração genérica")
                df = self.extractor._extract_all_text_parameters(pdf_path, 'unknown')
            
            if df is not None and not df.empty:
                # Salvar CSV bruto
                csv_path = self.output_csv / f"{pdf_path.stem}_params.csv"
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                
                # Salvar Excel bruto
                excel_path = self.output_excel / f"{pdf_path.stem}_params.xlsx"
                df.to_excel(excel_path, index=False, engine='openpyxl')
                
                logger.info(f"   ✅ Extraído: {len(df)} parâmetros")
                
                return {
                    'dataframe': df,
                    'relay_type': relay_type,
                    'source': pdf_path.name
                }
            else:
                logger.warning(f"   ⚠️  Nenhum parâmetro extraído")
                return None
                
        except Exception as e:
            logger.error(f"   ❌ Erro: {e}")
            return None
    
    def process_sepam_file(self, sepam_path: Path) -> Dict[str, Any]:
        """
        Processa um arquivo SEPAM (.S40/.s40)
        
        Args:
            sepam_path: Caminho do arquivo SEPAM
            
        Returns:
            Dicionário com dados extraídos
        """
        logger.info(f"\n📝 Processando SEPAM: {sepam_path.name}")
        
        try:
            # Usar o extrator inteligente
            df = self.extractor.extract_from_sepam(sepam_path)
            
            if df is not None and not df.empty:
                # Salvar CSV bruto
                csv_path = self.output_csv / f"{sepam_path.stem}_params.csv"
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                
                # Salvar Excel bruto
                excel_path = self.output_excel / f"{sepam_path.stem}_params.xlsx"
                df.to_excel(excel_path, index=False, engine='openpyxl')
                
                logger.info(f"   ✅ Extraído: {len(df)} parâmetros")
                
                return {
                    'dataframe': df,
                    'file_type': 'sepam',
                    'source': sepam_path.name
                }
            else:
                logger.warning(f"   ⚠️  Nenhum parâmetro extraído")
                return None
                
        except Exception as e:
            logger.error(f"   ❌ Erro: {e}")
            return None
    
    def normalize_and_validate(self, extracted_data: Dict[str, Any], 
                              filename: str) -> Dict[str, Any]:
        """
        Normaliza dados extraídos - ATOMIZA campos multivalorados
        
        Args:
            extracted_data: Dados extraídos
            filename: Nome do arquivo original
            
        Returns:
            Dados normalizados e atomizados
        """
        if extracted_data is None:
            return None
        
        if 'dataframe' not in extracted_data:
            return extracted_data
        
        df = extracted_data['dataframe'].copy()
        
        # ATOMIZAÇÃO: Separar Description de Value
        if 'Description' in df.columns:
            for idx, row in df.iterrows():
                desc = str(row['Description']) if pd.notna(row['Description']) else ''
                value = str(row['Value']) if pd.notna(row['Value']) else ''
                
                # Caso 1: "Frequency:60Hz" (valor grudado na descrição)
                if ':' in desc and not value:
                    parts = desc.split(':', 1)
                    clean_desc = parts[0].strip()
                    raw_value = parts[1].strip() if len(parts) > 1 else ''
                    
                    # Extrair unidade do valor
                    unit, clean_value = self._extract_unit(raw_value)
                    
                    df.at[idx, 'Description'] = clean_desc
                    df.at[idx, 'Value'] = clean_value
                    df.at[idx, 'unit'] = unit
                
                # Caso 2: "E/Gnd CT primary: 200" (descrição e valor misturados)
                elif ':' in desc and value:
                    # Limpar descrição (remover : final)
                    clean_desc = desc.rstrip(':').strip()
                    df.at[idx, 'Description'] = clean_desc
                    
                    # Extrair unidade do valor
                    unit, clean_value = self._extract_unit(value)
                    df.at[idx, 'Value'] = clean_value
                    df.at[idx, 'unit'] = unit
                
                # Caso 3: Valor já separado, apenas extrair unidade
                elif value:
                    unit, clean_value = self._extract_unit(value)
                    df.at[idx, 'Value'] = clean_value
                    df.at[idx, 'unit'] = unit if unit else (row.get('unit', '') if 'unit' in df.columns else '')
        
        # Normalizar coluna normalized_name
        if 'normalized_name' not in df.columns:
            df['normalized_name'] = df['Description']
        
        # Garantir category
        if 'category' not in df.columns:
            df['category'] = 'General'
        
        # Garantir extraction_date
        if 'extraction_date' not in df.columns:
            df['extraction_date'] = datetime.now().isoformat()
        
        extracted_data['dataframe'] = df
        return extracted_data
    
    def _extract_unit(self, value_str: str) -> Tuple[str, str]:
        """
        Extrai unidade de medida de um valor
        
        Args:
            value_str: String com valor e possivelmente unidade
            
        Returns:
            (unidade, valor_limpo)
        """
        import re
        
        value_str = str(value_str).strip()
        
        # Unidades conhecidas
        units = ['Hz', 'A', 'V', 'kV', 'mA', 'kA', 's', 'ms', 'Ω', 'ohm', 'W', 'kW', 
                 'var', 'kvar', 'VA', 'kVA', '°', 'deg', '%', 'mm', 'cm', 'm']
        
        # Tentar encontrar unidade no final da string
        for unit in units:
            # Case insensitive match no final
            pattern = rf'(\d+\.?\d*)\s*{re.escape(unit)}$'
            match = re.search(pattern, value_str, re.IGNORECASE)
            if match:
                clean_value = match.group(1)
                return (unit, clean_value)
        
        # Sem unidade encontrada
        return ('', value_str)
    
    def export_normalized(self, data: Dict[str, Any], base_filename: str):
        """
        Exporta dados normalizados
        
        Args:
            data: Dados normalizados
            base_filename: Nome base do arquivo
        """
        if data is None or 'dataframe' not in data:
            logger.warning(f"   ⚠️  Sem dados para normalizar")
            return
        
        df = data['dataframe']
        
        # Salvar CSV normalizado
        csv_path = self.output_norm_csv / f"{base_filename}_params.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # Salvar Excel normalizado
        excel_path = self.output_norm_excel / f"{base_filename}_params.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        # Salvar Excel normalizado
        excel_path = self.output_norm_excel / f"{base_filename}_params.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        logger.info(f"   📁 Normalizado: {len(df)} parâmetros → norm_csv/ e norm_excel/")
    
    def process_all(self) -> Dict[str, Any]:
        """
        Processa todos os arquivos da pipeline
        
        Returns:
            Estatísticas do processamento
        """
        stats = {
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'by_type': {
                'pdf': {'total': 0, 'success': 0, 'failed': 0},
                'sepam': {'total': 0, 'success': 0, 'failed': 0}
            },
            'start_time': datetime.now(),
            'end_time': None
        }
        
        # 1. Carregar glossário
        if not self.load_glossario_reference():
            logger.error("❌ Falha ao carregar glossário. Abortando.")
            return stats
        
        # 2. Descobrir arquivos
        files = self.discover_input_files()
        stats['total_files'] = len(files['pdf']) + len(files['sepam'])
        
        if stats['total_files'] == 0:
            logger.warning("⚠️  Nenhum arquivo para processar!")
            return stats
        
        logger.info("\n" + "="*80)
        logger.info("🚀 INICIANDO PROCESSAMENTO")
        logger.info("="*80)
        
        # 3. Processar PDFs
        stats['by_type']['pdf']['total'] = len(files['pdf'])
        for pdf_file in files['pdf']:
            result = self.process_pdf_file(pdf_file)
            if result:
                stats['by_type']['pdf']['success'] += 1
                stats['processed'] += 1
                
                # Normalizar e validar
                normalized = self.normalize_and_validate(result, pdf_file.stem)
                self.export_normalized(normalized, pdf_file.stem)
            else:
                stats['by_type']['pdf']['failed'] += 1
                stats['failed'] += 1
        
        # 4. Processar SEPAMs
        stats['by_type']['sepam']['total'] = len(files['sepam'])
        for sepam_file in files['sepam']:
            result = self.process_sepam_file(sepam_file)
            if result:
                stats['by_type']['sepam']['success'] += 1
                stats['processed'] += 1
                
                # Normalizar e validar
                normalized = self.normalize_and_validate(result, sepam_file.stem)
                self.export_normalized(normalized, sepam_file.stem)
            else:
                stats['by_type']['sepam']['failed'] += 1
                stats['failed'] += 1
        
        stats['end_time'] = datetime.now()
        
        return stats
    
    def print_statistics(self, stats: Dict[str, Any]):
        """
        Imprime estatísticas do processamento
        
        Args:
            stats: Estatísticas
        """
        logger.info("\n" + "="*80)
        logger.info("📊 ESTATÍSTICAS DO PROCESSAMENTO")
        logger.info("="*80)
        
        logger.info(f"\n📝 Total de Arquivos: {stats['total_files']}")
        logger.info(f"✅ Processados com sucesso: {stats['processed']}")
        logger.info(f"❌ Falhas: {stats['failed']}")
        
        logger.info(f"\n📄 PDFs:")
        logger.info(f"   • Total: {stats['by_type']['pdf']['total']}")
        logger.info(f"   • Sucesso: {stats['by_type']['pdf']['success']}")
        logger.info(f"   • Falhas: {stats['by_type']['pdf']['failed']}")
        
        logger.info(f"\n📝 SEPAMs (.S40):")
        logger.info(f"   • Total: {stats['by_type']['sepam']['total']}")
        logger.info(f"   • Sucesso: {stats['by_type']['sepam']['success']}")
        logger.info(f"   • Falhas: {stats['by_type']['sepam']['failed']}")
        
        if stats['end_time']:
            duration = stats['end_time'] - stats['start_time']
            logger.info(f"\n⏱️  Tempo total: {duration.total_seconds():.2f}s")
        
        logger.info("\n" + "="*80)
        logger.info("✅ PROCESSAMENTO COMPLETO!")
        logger.info("="*80)


def main():
    """Função principal"""
    # Obter raiz do projeto
    project_root = Path(__file__).parent.parent
    
    # Criar processador
    processor = CompletePipelineProcessor(str(project_root))
    
    # Processar tudo
    stats = processor.process_all()
    
    # Mostrar estatísticas
    processor.print_statistics(stats)


if __name__ == "__main__":
    main()

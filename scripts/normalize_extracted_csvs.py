"""
NORMALIZAÇÃO CORRETA - GERA NORM_CSV E NORM_EXCEL

OBJETIVO: Normalizar CSVs extraídos gerando arquivos padronizados
ENTRADA: outputs/csv/*.csv (gerados pelo extract_parameters_from_glossario.py)
SAÍDA: outputs/norm_csv/*.csv E outputs/norm_excel/*.xlsx

CRÍTICO: VIDAS EM RISCO - Normalização deve manter 100% dos dados do glossário
"""

import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import json
from typing import Dict, List

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/logs/normalization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CSVNormalizer:
    """Normalizador de CSVs seguindo estrutura do glossário"""
    
    # Colunas OBRIGATÓRIAS na saída
    REQUIRED_COLUMNS = [
        'parameter_code',
        'parameter_name',
        'set_value',
        'unit_of_measure',
        'section',
        'subsection',
        'category',
        'source_file'
    ]
    
    # Colunas ADICIONAIS úteis
    ADDITIONAL_COLUMNS = [
        'normalized_value',  # Valor convertido para formato padrão
        'is_valid',          # Validação do valor
        'extraction_date'    # Data da extração
    ]
    
    def __init__(self):
        self.stats = {
            'total_files': 0,
            'total_parameters': 0,
            'files_with_errors': [],
            'validation_errors': []
        }
    
    def normalize_csv(self, csv_path: Path) -> pd.DataFrame:
        """Normaliza um arquivo CSV"""
        logger.info(f"Normalizando: {csv_path.name}")
        
        try:
            # Ler CSV
            df = pd.read_csv(csv_path, encoding='utf-8')
            
            # MAPEAR COLUNAS DO CSV EXTRAÍDO PARA O FORMATO NORMALIZADO
            # CSVs extraídos têm: Code, Description, Value, is_active (desde correção)
            # Precisamos mapear para: parameter_code, parameter_name, set_value
            
            if 'Code' in df.columns and 'Description' in df.columns and 'Value' in df.columns:
                # Renomear colunas principais
                df = df.rename(columns={
                    'Code': 'parameter_code',
                    'Description': 'parameter_name',
                    'Value': 'set_value'
                })
                
                # Se is_active já existe no CSV extraído, usar esse valor
                # Se não existir, considerar válido se tiver valor
                if 'is_active' not in df.columns:
                    df['is_active'] = df['set_value'].apply(self._validate_value)
            
            # Adicionar colunas que não existem nos CSVs extraídos
            if 'unit_of_measure' not in df.columns:
                df['unit_of_measure'] = ''
            if 'section' not in df.columns:
                df['section'] = ''
            if 'subsection' not in df.columns:
                df['subsection'] = ''
            if 'category' not in df.columns:
                df['category'] = ''
            if 'source_file' not in df.columns:
                df['source_file'] = csv_path.name
            
            # Adicionar colunas adicionais
            df['normalized_value'] = df['set_value'].apply(self._normalize_value)
            df['is_valid'] = df['is_active']  # is_valid é IGUAL a is_active (não mais baseado em valor não-vazio)
            df['extraction_date'] = datetime.now().isoformat()
            
            # Reordenar colunas
            all_columns = self.REQUIRED_COLUMNS + self.ADDITIONAL_COLUMNS
            df = df[all_columns]
            
            # Validar dados
            self._validate_dataframe(df, csv_path.name)
            
            logger.info(f"  ✓ {len(df)} parâmetros normalizados")
            return df
            
        except Exception as e:
            logger.error(f"  ❌ Erro ao normalizar {csv_path.name}: {e}")
            self.stats['files_with_errors'].append(csv_path.name)
            raise
    
    def _normalize_value(self, value) -> str:
        """Normaliza valor para formato padrão"""
        if pd.isna(value):
            return ''
        
        value_str = str(value).strip()
        
        # Remover caracteres especiais extras
        value_str = value_str.replace('\r', ' ').replace('\n', ' ')
        value_str = ' '.join(value_str.split())  # Normalizar espaços
        
        return value_str
    
    def _validate_value(self, value) -> bool:
        """Valida se o valor está presente e não vazio"""
        if pd.isna(value):
            return False
        
        value_str = str(value).strip()
        return len(value_str) > 0
    
    def _validate_dataframe(self, df: pd.DataFrame, filename: str):
        """Valida DataFrame normalizado"""
        # Verificar parâmetros sem código
        missing_code = df[df['parameter_code'].isna() | (df['parameter_code'] == '')]
        if len(missing_code) > 0:
            self.stats['validation_errors'].append({
                'file': filename,
                'error': f'{len(missing_code)} parâmetros sem código'
            })
        
        # Verificar parâmetros sem nome
        missing_name = df[df['parameter_name'].isna() | (df['parameter_name'] == '')]
        if len(missing_name) > 0:
            self.stats['validation_errors'].append({
                'file': filename,
                'error': f'{len(missing_name)} parâmetros sem nome'
            })
        
        # Verificar parâmetros sem valor
        missing_value = df[df['is_valid'] == False]
        if len(missing_value) > 0:
            logger.warning(f"  ⚠️  {len(missing_value)} parâmetros sem valor válido")
    
    def save_normalized(self, df: pd.DataFrame, original_filename: str):
        """Salva arquivo normalizado em CSV e Excel"""
        stem = Path(original_filename).stem
        
        # Salvar CSV normalizado
        csv_output = Path("outputs/norm_csv") / f"{stem}.csv"
        csv_output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_output, index=False, encoding='utf-8')
        logger.info(f"  💾 CSV: {csv_output.name}")
        
        # Salvar Excel normalizado
        excel_output = Path("outputs/norm_excel") / f"{stem}.xlsx"
        excel_output.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
            # Aba principal com dados
            df.to_excel(writer, sheet_name='Parameters', index=False)
            
            # Aba com estatísticas
            stats_df = pd.DataFrame([{
                'Total Parameters': len(df),
                'Valid Values': df['is_valid'].sum(),
                'Missing Values': (~df['is_valid']).sum(),
                'Unique Sections': df['section'].nunique(),
                'Unique Subsections': df['subsection'].nunique(),
                'Source File': original_filename,
                'Normalized Date': datetime.now().isoformat()
            }])
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)
            
            # Aba com seções
            if not df['section'].isna().all():
                sections = df.groupby('section').size().reset_index(name='count')
                sections.to_excel(writer, sheet_name='Sections', index=False)
        
        logger.info(f"  💾 Excel: {excel_output.name}")
    
    def process_all_csvs(self):
        """Processa TODOS os CSVs de outputs/csv"""
        logger.info("="*80)
        logger.info("INICIANDO NORMALIZAÇÃO COMPLETA")
        logger.info("="*80)
        
        csv_dir = Path("outputs/csv")
        if not csv_dir.exists():
            logger.error(f"❌ Diretório não encontrado: {csv_dir}")
            return
        
        # IMPORTANTE: Normalizar APENAS arquivos _params.csv (não _active_setup.csv)
        # _active_setup.csv são arquivos auxiliares com parâmetros ativos (feature útil)
        # mas não devem ser normalizados nem importados para o banco
        csv_files = sorted(csv_dir.glob("*_params.csv"))
        total_files = len(csv_files)
        
        logger.info(f"📁 Encontrados {total_files} arquivos _params.csv para normalizar")
        logger.info(f"   (Ignorando arquivos _active_setup.csv - são auxiliares)")
        
        for idx, csv_file in enumerate(csv_files, 1):
            logger.info(f"\n[{idx}/{total_files}] Processando {csv_file.name}")
            
            try:
                # Normalizar
                df_normalized = self.normalize_csv(csv_file)
                
                # Salvar
                self.save_normalized(df_normalized, csv_file.name)
                
                # Atualizar estatísticas
                self.stats['total_files'] += 1
                self.stats['total_parameters'] += len(df_normalized)
                
            except Exception as e:
                logger.error(f"❌ Falha ao processar {csv_file.name}: {e}")
        
        # Relatório final
        self._generate_final_report()
    
    def _generate_final_report(self):
        """Gera relatório final da normalização"""
        logger.info("="*80)
        logger.info("✅ NORMALIZAÇÃO CONCLUÍDA")
        logger.info(f"   📁 Arquivos processados: {self.stats['total_files']}")
        logger.info(f"   📊 Parâmetros normalizados: {self.stats['total_parameters']}")
        
        if self.stats['files_with_errors']:
            logger.warning(f"   ⚠️  Arquivos com erros: {len(self.stats['files_with_errors'])}")
            for filename in self.stats['files_with_errors']:
                logger.warning(f"      - {filename}")
        
        if self.stats['validation_errors']:
            logger.warning(f"   ⚠️  Erros de validação: {len(self.stats['validation_errors'])}")
            for error in self.stats['validation_errors']:
                logger.warning(f"      - {error['file']}: {error['error']}")
        
        logger.info("="*80)
        
        # Salvar relatório JSON
        report_path = Path("outputs/logs/normalization_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📋 Relatório salvo: {report_path}")
        
        # Verificar coverage
        self._check_coverage()
    
    def _check_coverage(self):
        """Verifica cobertura dos arquivos normalizados"""
        csv_count = len(list(Path("outputs/csv").glob("*.csv")))
        norm_csv_count = len(list(Path("outputs/norm_csv").glob("*.csv")))
        norm_excel_count = len(list(Path("outputs/norm_excel").glob("*.xlsx")))
        
        logger.info("\n📊 COBERTURA:")
        logger.info(f"   CSVs originais: {csv_count}")
        logger.info(f"   CSVs normalizados: {norm_csv_count}")
        logger.info(f"   Excel normalizados: {norm_excel_count}")
        
        if norm_csv_count == csv_count and norm_excel_count == csv_count:
            logger.info("   ✅ 100% de cobertura!")
        else:
            logger.warning("   ⚠️  Cobertura incompleta!")


def main():
    """Execução principal"""
    try:
        normalizer = CSVNormalizer()
        normalizer.process_all_csvs()
        
    except Exception as e:
        logger.error(f"ERRO CRÍTICO: {e}")
        raise


if __name__ == "__main__":
    main()

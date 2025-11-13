#!/usr/bin/env python3
"""
NORMALIZAÇÃO DE PARÂMETROS DE RELÉS - CONFORME GLOSSÁRIO
=========================================================

Objetivo:
- Ler CSVs brutos de outputs/csv/
- Aplicar mapeamento do glossário
- Gerar NORM_CSV e NORM_EXCEL com estrutura padronizada
- Estrutura de saída: parameter_code, parameter_name, set_value, 
  unit_of_measure, section, subsection, category
"""

import pandas as pd
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Diretórios
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = BASE_DIR / 'outputs/csv'
NORM_CSV_DIR = BASE_DIR / 'outputs/norm_csv'
NORM_EXCEL_DIR = BASE_DIR / 'outputs/norm_excel'
GLOSSARIO_PATH = BASE_DIR / 'inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx'
GLOSSARIO_MAPPING = BASE_DIR / 'inputs/glossario/glossary_mapping.csv'

# Criar diretórios se não existirem
NORM_CSV_DIR.mkdir(parents=True, exist_ok=True)
NORM_EXCEL_DIR.mkdir(parents=True, exist_ok=True)


class GlossarioMapper:
    """Classe para mapear parâmetros usando o glossário."""
    
    def __init__(self):
        self.glossario = {}
        self.load_glossario()
    
    def load_glossario(self):
        """Carrega mapeamentos do glossário."""
        logger.info("📖 Carregando glossário...")
        
        # Tentar carregar CSV primeiro
        if GLOSSARIO_MAPPING.exists():
            try:
                df = pd.read_csv(GLOSSARIO_MAPPING)
                for _, row in df.iterrows():
                    code = str(row.get('code', '')).strip()
                    if code and code != 'nan':
                        self.glossario[code.upper()] = {
                            'name': str(row.get('name', '')),
                            'unit': str(row.get('unit', ''))
                        }
                logger.info(f"   ✅ Carregados {len(self.glossario)} mapeamentos do CSV")
            except Exception as e:
                logger.warning(f"   ⚠️  Erro ao ler CSV: {e}")
        
        # Carregar do Excel se disponível
        if GLOSSARIO_PATH.exists() and len(self.glossario) == 0:
            try:
                self._load_from_excel()
            except Exception as e:
                logger.warning(f"   ⚠️  Erro ao ler Excel: {e}")
    
    def _load_from_excel(self):
        """Carrega do Excel (fallback)."""
        logger.info("   📊 Carregando do Excel...")
        
        excel_file = pd.ExcelFile(GLOSSARIO_PATH)
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
            
            for idx, row in df.iterrows():
                row_str = ' '.join([str(v) for v in row if pd.notna(v)])
                
                # Procurar padrões de código: XXXX: Nome: ou XX.XX: Nome:
                patterns = [
                    r'(\d{4})\s*:\s*([^:]+):',  # 0104: Frequency:
                    r'(\d{2}\.\d{2})\s*:\s*([^:]+):',  # 00.04: Description:
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, row_str)
                    if match:
                        code = match.group(1).strip()
                        name = match.group(2).strip()
                        
                        # Tentar extrair unidade
                        unit = ''
                        remaining = row_str[match.end():]
                        if remaining:
                            unit_match = re.search(r'(Hz|V|A|s|ms|Ω|°|%)', remaining)
                            if unit_match:
                                unit = unit_match.group(1)
                        
                        self.glossario[code.upper()] = {
                            'name': name,
                            'unit': unit
                        }
        
        logger.info(f"   ✅ Carregados {len(self.glossario)} mapeamentos do Excel")
    
    def map_parameter(self, param_name: str) -> Dict[str, str]:
        """
        Mapeia um parâmetro para nomenclatura do glossário.
        
        Returns:
            Dict com 'code', 'name', 'unit'
        """
        # Extrair código do parâmetro
        code_match = re.match(r'^(\d{4}|\d{2}\.\d{2})', param_name.strip())
        
        if code_match:
            code = code_match.group(1).upper()
            if code in self.glossario:
                return {
                    'code': code,
                    'name': self.glossario[code]['name'],
                    'unit': self.glossario[code]['unit']
                }
        
        # Se não encontrou, retorna o próprio nome
        return {
            'code': '',
            'name': param_name,
            'unit': ''
        }


def detect_model_from_filename(filename: str) -> str:
    """Detecta modelo do relé pelo nome do arquivo."""
    filename_upper = filename.upper()
    
    if 'P122' in filename_upper:
        return 'P122'
    elif 'P143' in filename_upper:
        return 'P143'
    elif 'P220' in filename_upper:
        return 'P220'
    elif 'P241' in filename_upper:
        return 'P241'
    elif 'P922S' in filename_upper:
        return 'P922S'
    elif 'P922' in filename_upper:
        return 'P922'
    elif 'SEPAM' in filename_upper or 'MF-' in filename_upper:
        return 'SEPAM'
    else:
        return 'UNKNOWN'


def normalize_csv_file(csv_path: Path, mapper: GlossarioMapper) -> pd.DataFrame:
    """
    Normaliza um CSV bruto aplicando glossário.
    
    Returns:
        DataFrame normalizado com colunas padrão
    """
    logger.info(f"📄 Processando: {csv_path.name}")
    
    # Ler CSV bruto
    try:
        df_raw = pd.read_csv(csv_path)
    except Exception as e:
        logger.error(f"   ❌ Erro ao ler CSV: {e}")
        return pd.DataFrame()
    
    # Detectar modelo
    model = detect_model_from_filename(csv_path.name)
    
    # Preparar DataFrame normalizado
    normalized_rows = []
    
    for idx, row in df_raw.iterrows():
        # Assumir que CSV tem colunas: parameter, value (ou similar)
        # Adaptar conforme estrutura real dos CSVs
        
        param_name = None
        param_value = None
        
        # Tentar diferentes formatos de coluna
        if 'parameter' in df_raw.columns:
            param_name = str(row['parameter'])
        elif 'Parameter' in df_raw.columns:
            param_name = str(row['Parameter'])
        elif 'nome_coluna' in df_raw.columns:
            param_name = str(row['nome_coluna'])
        
        if 'value' in df_raw.columns:
            param_value = str(row['value'])
        elif 'Value' in df_raw.columns:
            param_value = str(row['Value'])
        elif 'valor_original' in df_raw.columns:
            param_value = str(row['valor_original'])
        
        if not param_name or param_name == 'nan':
            continue
        
        # Mapear usando glossário
        mapped = mapper.map_parameter(param_name)
        
        # Detectar seção/categoria do parâmetro
        section = ''
        if any(word in param_name.upper() for word in ['CONFIG', 'CONFIGURATION']):
            section = 'CONFIGURATION'
        elif any(word in param_name.upper() for word in ['PROTECT', 'OVERCURRENT']):
            section = 'PROTECTION'
        elif any(word in param_name.upper() for word in ['SYSTEM', 'DATA']):
            section = 'SYSTEM DATA'
        
        normalized_rows.append({
            'parameter_code': mapped['code'],
            'parameter_name': mapped['name'] if mapped['name'] else param_name,
            'set_value': param_value if param_value and param_value != 'nan' else '',
            'unit_of_measure': mapped['unit'],
            'section': section,
            'subsection': '',
            'category': model,
            'source_file': csv_path.name
        })
    
    df_normalized = pd.DataFrame(normalized_rows)
    logger.info(f"   ✅ {len(df_normalized)} parâmetros normalizados")
    
    return df_normalized


def process_all_csvs():
    """Processa todos os CSVs e gera NORM_CSV e NORM_EXCEL."""
    logger.info("=" * 80)
    logger.info("🔄 NORMALIZAÇÃO DE PARÂMETROS - CONFORME GLOSSÁRIO")
    logger.info("=" * 80)
    
    # Inicializar mapper
    mapper = GlossarioMapper()
    
    if len(mapper.glossario) == 0:
        logger.error("❌ Glossário vazio! Impossível normalizar.")
        return
    
    # Listar CSVs
    csv_files = list(CSV_DIR.glob('*_params.csv'))
    logger.info(f"\n📁 Encontrados {len(csv_files)} CSVs para normalizar")
    
    processed = 0
    errors = 0
    
    for csv_file in csv_files:
        try:
            # Normalizar
            df_norm = normalize_csv_file(csv_file, mapper)
            
            if df_norm.empty:
                logger.warning(f"   ⚠️  CSV vazio ou sem dados: {csv_file.name}")
                errors += 1
                continue
            
            # Salvar NORM_CSV
            output_csv = NORM_CSV_DIR / f"{csv_file.stem}_normalized.csv"
            df_norm.to_csv(output_csv, index=False)
            
            # Salvar NORM_EXCEL
            output_excel = NORM_EXCEL_DIR / f"{csv_file.stem}_normalized.xlsx"
            df_norm.to_excel(output_excel, index=False, engine='openpyxl')
            
            processed += 1
            
        except Exception as e:
            logger.error(f"   ❌ Erro ao processar {csv_file.name}: {e}")
            errors += 1
    
    # Relatório final
    logger.info("\n" + "=" * 80)
    logger.info("📊 RELATÓRIO FINAL")
    logger.info("=" * 80)
    logger.info(f"✅ Processados: {processed}")
    logger.info(f"❌ Erros: {errors}")
    logger.info(f"📁 NORM_CSV: {len(list(NORM_CSV_DIR.glob('*.csv')))}")
    logger.info(f"📊 NORM_EXCEL: {len(list(NORM_EXCEL_DIR.glob('*.xlsx')))}")
    
    if processed == len(csv_files):
        logger.info("\n🎉 NORMALIZAÇÃO COMPLETA!")
    else:
        logger.warning(f"\n⚠️  Alguns arquivos não foram processados ({errors} erros)")


if __name__ == "__main__":
    process_all_csvs()

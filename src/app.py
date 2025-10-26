#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — Extrator de parâmetros de proteção MULTI-FORMATO com controle de processamento

VERSÃO 2.0 - MULTI-FORMATO:
- Suporta: PDF, TXT, XLSX, CSV
- Nova estrutura: inputs/{pdf,txt,xlsx,csv}/
- Controle de arquivos processados (evita reprocessamento)
- Detecção automática de formato (MiCOM S1 Agile, Easergy Studio, etc.)
- FileRegistryManager integrado

FORMATOS SUPORTADOS:
  • PDF: Relatórios MiCOM S1 Agile e Easergy Studio
  • TXT: Arquivos de texto estruturados com parâmetros
  • XLSX: Planilhas Excel com dados de configuração
  • CSV: Arquivos CSV com estrutura Code,Description,Value

Estrutura de diretórios aceita:
  inputs/pdf/      - Relatórios PDF
  inputs/txt/      - Configurações TXT
  inputs/xlsx/     - Planilhas Excel
  inputs/csv/      - Dados CSV

Execução com exemplos:
  python app.py --inputs arquivo1.pdf arquivo2.xlsx --config config.txt
  python app.py --help

Opções específicas:
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import pandas as pd
from PyPDF2 import PdfReader

# Importar o FileRegistryManager
try:
    from .file_registry_manager import FileRegistryManager
except ImportError:
    # Para execução direta
    from file_registry_manager import FileRegistryManager

# ---------------------------
# Pastas padrão do projeto
# ---------------------------

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]          # src/ -> raiz do projeto

# NOVA ESTRUTURA DE INPUTS - MULTI-FORMATO
INPUT_BASE_DIR = PROJECT_ROOT / "inputs"
INPUT_PDF_DIR = INPUT_BASE_DIR / "pdf"
INPUT_TXT_DIR = INPUT_BASE_DIR / "txt"
INPUT_XLSX_DIR = INPUT_BASE_DIR / "xlsx"
INPUT_CSV_DIR = INPUT_BASE_DIR / "csv"
INPUT_REGISTRY_DIR = INPUT_BASE_DIR / "registry"

# Diretórios de saída
OUT_EXCEL_DIR = PROJECT_ROOT / "outputs" / "excel"
OUT_CSV_DIR = PROJECT_ROOT / "outputs" / "csv"

# ---------------------------
# Classes de dados estruturados para análise completa
# ---------------------------

@dataclass
class IdentificationData:
    """Dados de identificação do relé"""
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    software_version: Optional[str] = None
    tag_reference: Optional[str] = None
    plant_reference: Optional[str] = None
    bay_position: Optional[str] = None
    frequency: Optional[str] = None
    description: Optional[str] = None

@dataclass
class ElectricalConfiguration:
    """Configuração elétrica (TCs, TPs)"""
    phase_ct_primary: Optional[str] = None
    phase_ct_secondary: Optional[str] = None
    neutral_ct_primary: Optional[str] = None
    neutral_ct_secondary: Optional[str] = None
    vt_primary: Optional[str] = None
    vt_secondary: Optional[str] = None
    nvd_vt_primary: Optional[str] = None
    nvd_vt_secondary: Optional[str] = None
    vt_connection_mode: Optional[str] = None
    nominal_voltage: Optional[str] = None
    equipment_load: Optional[str] = None

@dataclass
class ProtectionFunction:
    """Função de proteção individual"""
    function_name: str
    code: str
    enabled: bool
    current_setting: Optional[str] = None
    time_setting: Optional[str] = None
    characteristic: Optional[str] = None
    direction: Optional[str] = None
    additional_settings: Optional[Dict[str, str]] = None

@dataclass
class IOConfiguration:
    """Configuração de entradas/saídas"""
    opto_inputs: Optional[Dict[str, str]] = None
    relay_outputs: Optional[Dict[str, str]] = None
    rtd_inputs: Optional[Dict[str, str]] = None
    analog_outputs: Optional[Dict[str, str]] = None

@dataclass
class RelayConfiguration:
    """Configuração completa do relé"""
    identification: IdentificationData
    electrical: ElectricalConfiguration
    protection_functions: List[ProtectionFunction]
    io_configuration: IOConfiguration
    additional_parameters: Dict[str, str]
    raw_data: List[Dict[str, str]]

# Garantir que os diretórios existam
for directory in [INPUT_PDF_DIR, INPUT_TXT_DIR, INPUT_XLSX_DIR, INPUT_CSV_DIR, 
                  INPUT_REGISTRY_DIR, OUT_EXCEL_DIR, OUT_CSV_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ---------------------------
# Extração de texto do PDF
# ---------------------------

def extract_text_pypdf2(pdf_path: Path) -> str:
    """Extrai texto de todas as páginas com PyPDF2."""
    reader = PdfReader(str(pdf_path))
    parts: List[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


# ---------------------------
# Parsers (MiCOM / Easergy)
# ---------------------------

# MiCOM S1 Agile: linhas do tipo "0A.01: Main VT Primary: 13.80 kV"
RE_MICOM = re.compile(r"^([0-9A-F]{2}\.[0-9A-F]{2}):\s*([^:]+):\s*(.*)$")

# Easergy Studio: linhas do tipo "0202: Iteta> =: 0.64In" OU "0005: SOFTWARE VERSION: 6.A"
RE_EASERGY_EQUALS = re.compile(r"^([0-9A-F]{4}):\s*([^=:]+)=:\s*(.*)$")  # Padrão com =:
RE_EASERGY_COLON = re.compile(r"^([0-9A-F]{4}):\s*([^:]+):\s*(.*)$")     # Padrão só com :


def parse_micom(text: str) -> pd.DataFrame:
    """Parser para MiCOM S1 Agile: retorna DataFrame (Code, Description, Value)."""
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        m = RE_MICOM.match(line)
        if m:
            code, desc, val = m.groups()
            rows.append({"Code": code, "Description": desc.strip(), "Value": val.strip()})
    return pd.DataFrame(rows)


def parse_easergy(text: str) -> pd.DataFrame:
    """Parser para Easergy Studio: retorna DataFrame (Code, Description, Value)."""
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        
        # Tentar primeiro padrão: "0000: TYPE =: P220-2"
        m = RE_EASERGY_EQUALS.match(line)
        if m:
            code, desc, val = m.groups()
            rows.append({"Code": code, "Description": desc.strip(), "Value": val.strip()})
            continue
        
        # Tentar segundo padrão: "0005: SOFTWARE VERSION: 6.A"
        m = RE_EASERGY_COLON.match(line)
        if m:
            code, desc, val = m.groups()
            rows.append({"Code": code, "Description": desc.strip(), "Value": val.strip()})
    
    return pd.DataFrame(rows)


# ---------------------------
# Heurística de detecção
# ---------------------------

@dataclass
class ParseResult:
    df: pd.DataFrame
    detected: str  # "micom" | "easergy" | "unknown"


def detect_and_parse(text: str) -> ParseResult:
    """
    Detecta o tipo de relatório e faz o parsing.
    Heurísticas:
      - Presença de marca "MiCOM S1 Agile" => micom
      - Presença de "Easergy Studio" => easergy
      - Caso ambíguo: testa os dois regex e escolhe o que extraiu mais linhas
    """
    lowered = text.lower()
    if "micom s1 agile" in lowered:
        df = parse_micom(text)
        return ParseResult(df=df, detected="micom")
    if "easergy studio" in lowered:
        df = parse_easergy(text)
        return ParseResult(df=df, detected="easergy")

    # fallback: testar ambos
    micom_df = parse_micom(text)
    easergy_df = parse_easergy(text)
    if len(micom_df) >= len(easergy_df) and len(micom_df) > 0:
        return ParseResult(df=micom_df, detected="micom")
    if len(easergy_df) > 0:
        return ParseResult(df=easergy_df, detected="easergy")
    return ParseResult(df=pd.DataFrame(columns=["Code", "Description", "Value"]), detected="unknown")


# ---------------------------
# I/O Helpers
# ---------------------------

def default_output_names(pdf_path: Path) -> Tuple[Path, Path]:
    """
    Gera nomes padrão nas pastas de saída oficiais:
      outputs/excel/<stem>_params.xlsx
      outputs/csv/<stem>_params.csv
      Observação: quando você passa --xlsx (arquivo único consolidado) ou --csv (para 1 PDF), 
      esses caminhos continuam valendo como override — ou seja, salvam exatamente onde você indicar.
    """
    xlsx = OUT_EXCEL_DIR / f"{pdf_path.stem}_params.xlsx"
    csv = OUT_CSV_DIR / f"{pdf_path.stem}_params.csv"
    return xlsx, csv


def write_outputs(
    df: pd.DataFrame,
    pdf_path: Path,
    xlsx_path: Optional[Path],
    csv_path: Optional[Path],
    sheet_name: Optional[str] = None,
) -> Tuple[Path, Path]:
    """
    Escreve Excel e/ou CSV.
    - Se xlsx_path/csv_path forem None, usa nomes padrão ao lado do PDF.
    - Retorna caminhos efetivamente escritos.
    """
    # nomes padrão se não forem fornecidos
    default_xlsx, default_csv = default_output_names(pdf_path)
    out_xlsx = xlsx_path or default_xlsx
    out_csv = csv_path or default_csv

    # Excel
    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name or "parameters")

    # CSV
    df.to_csv(out_csv, index=False)

    return out_xlsx, out_csv


# ---------------------------
# CLI
# ---------------------------

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Extrator MULTI-FORMATO de parâmetros de proteção: PDF, TXT, XLSX, CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Processar arquivos específicos
  python app.py --inputs arquivo1.pdf config.txt
  
  # Processar todos os arquivos PDF não processados
  python app.py --format pdf
  
  # Escanear e processar TODOS os formatos
  python app.py --scan-all
  
  # Processar com saída consolidada
  python app.py --inputs file1.pdf file2.xlsx --xlsx resultado.xlsx
  
  # Verificar status do registro
  python app.py --registry-status

Formatos suportados:
  • PDF: Relatórios MiCOM S1 Agile, Easergy Studio
  • TXT: Arquivos texto estruturados (Code: Description: Value)
  • XLSX: Planilhas Excel com colunas Code, Description, Value  
  • CSV: Arquivos CSV com estrutura similar

Estrutura de inputs:
  inputs/pdf/      - Relatórios PDF
  inputs/txt/      - Documentos texto
  inputs/xlsx/     - Planilhas Excel
  inputs/csv/      - Arquivos CSV
  inputs/registry/ - Controle de processamento
        """
    )
    
    # Grupo de entrada: específica ou por formato
    input_group = p.add_mutually_exclusive_group(required=False)
    
    input_group.add_argument(
        "--inputs",
        nargs="+",
        help="Lista de arquivos específicos para processar (qualquer formato suportado)."
    )
    
    input_group.add_argument(
        "--format",
        choices=['pdf', 'txt', 'xlsx', 'csv'],
        help="Processar todos os arquivos não processados de um formato específico."
    )
    
    input_group.add_argument(
        "--scan-all",
        action="store_true",
        help="Escanear e processar TODOS os formatos não processados."
    )
    
    # Opções de saída
    p.add_argument(
        "--xlsx",
        type=str,
        default=None,
        help="Caminho do Excel de saída único (consolidar múltiplos arquivos)."
    )
    
    p.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Caminho do CSV único de saída (apenas para arquivo único)."
    )
    
    p.add_argument(
        "--sheet-prefix",
        type=str,
        default="Sheet",
        help="Prefixo para abas no Excel consolidado (default: Sheet)."
    )
    
    # Opções de controle
    p.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Forçar reprocessamento mesmo de arquivos já processados."
    )
    
    p.add_argument(
        "--registry-status",
        action="store_true", 
        help="Mostrar estatísticas do registro de arquivos processados."
    )
    
    p.add_argument(
        "--cleanup-registry",
        action="store_true",
        help="Remover do registro arquivos que não existem mais."
    )
    return p


# ---------------------------
# Analisador Avançado de Relés
# ---------------------------

class EnhancedRelayAnalyzer:
    """Analisador avançado para extração completa de configurações de relés"""
    
    def __init__(self):
        self.manufacturer_patterns = {
            'schneider_micom': {
                'patterns': ['P241', 'P243', 'P245', 'MiCOM'],
                'code_format': r'^\d{2}\.\d{2}$'
            },
            'schneider_easergy': {
                'patterns': ['P220', 'P210', 'Easergy'],
                'code_format': r'^\d{4}$'
            },
            'abb': {
                'patterns': ['REF', 'RED', 'REM'],
                'code_format': r'^\d+\.\d+\.\d+$'
            },
            'siemens': {
                'patterns': ['7SJ', '7SA', '7SK'],
                'code_format': r'^\d+$'
            }
        }

    def analyze_relay_data(self, data: pd.DataFrame, source_file: str = "") -> RelayConfiguration:
        """Análise completa dos dados do relé para reprodução do status"""
        
        # Identificar fabricante e formato
        manufacturer_info = self._identify_manufacturer(data)
        
        # Extrair identificação
        identification = self._extract_identification(data, manufacturer_info)
        
        # Extrair configuração elétrica
        electrical = self._extract_electrical_configuration(data, manufacturer_info)
        
        # Extrair funções de proteção
        protection_functions = self._extract_protection_functions(data, manufacturer_info)
        
        # Extrair configuração de I/O
        io_config = self._extract_io_configuration(data, manufacturer_info)
        
        # Parâmetros adicionais
        additional_params = self._extract_additional_parameters(data, manufacturer_info)
        
        # Dados brutos para referência
        raw_data = data.to_dict('records') if not data.empty else []
        
        return RelayConfiguration(
            identification=identification,
            electrical=electrical,
            protection_functions=protection_functions,
            io_configuration=io_config,
            additional_parameters=additional_params,
            raw_data=raw_data
        )

    def _identify_manufacturer(self, data: pd.DataFrame) -> Dict[str, str]:
        """Identifica fabricante e formato dos dados"""
        
        if data.empty:
            return {'manufacturer': 'unknown', 'format': 'unknown'}
            
        # Verificar padrões nos códigos e valores
        codes = data['Code'].astype(str).tolist() if 'Code' in data.columns else []
        values = data['Value'].astype(str).tolist() if 'Value' in data.columns else []
        
        all_text = ' '.join(codes + values).upper()
        
        for manufacturer, info in self.manufacturer_patterns.items():
            if any(pattern in all_text for pattern in info['patterns']):
                return {'manufacturer': manufacturer, 'format': info['code_format']}
        
        return {'manufacturer': 'unknown', 'format': 'unknown'}

    def _extract_identification(self, data: pd.DataFrame, manufacturer_info: Dict) -> IdentificationData:
        """Extrai dados de identificação do equipamento"""
        
        identification = IdentificationData()
        
        if data.empty:
            return identification
            
        # Mapear códigos para identificação
        id_mapping = {
            # MiCOM
            '00.06': 'model',
            '00.08': 'serial_number',
            '00.11': 'software_version',
            '00.04': 'description',
            '00.05': 'plant_reference',
            '00.09': 'frequency',
            
            # Easergy
            '0001': 'model',
            '0002': 'serial_number',
            '0003': 'software_version',
        }
        
        for _, row in data.iterrows():
            code = str(row.get('Code', ''))
            value = str(row.get('Value', ''))
            description = str(row.get('Description', ''))
            
            if code in id_mapping:
                field_name = id_mapping[code]
                setattr(identification, field_name, value)
            
            # Identificação por descrição
            desc_lower = description.lower()
            if 'model' in desc_lower and not identification.model:
                identification.model = value
            elif 'serial' in desc_lower and not identification.serial_number:
                identification.serial_number = value
            elif 'software' in desc_lower and not identification.software_version:
                identification.software_version = value
                
        # Inferir fabricante
        if identification.model:
            if any(pattern in identification.model.upper() for pattern in ['P241', 'P243', 'P245']):
                identification.manufacturer = 'Schneider Electric (MiCOM)'
            elif any(pattern in identification.model.upper() for pattern in ['P220', 'P210']):
                identification.manufacturer = 'Schneider Electric (Easergy)'
        
        return identification

    def _extract_electrical_configuration(self, data: pd.DataFrame, manufacturer_info: Dict) -> ElectricalConfiguration:
        """Extrai configuração elétrica (TCs, TPs, etc.)"""
        
        electrical = ElectricalConfiguration()
        
        if data.empty:
            return electrical
            
        # Mapear códigos para configuração elétrica
        electrical_mapping = {
            # MiCOM
            '0A.01': 'vt_primary',
            '0A.02': 'vt_secondary', 
            '0A.07': 'phase_ct_primary',
            '0A.08': 'phase_ct_secondary',
            '0A.0B': 'neutral_ct_primary',
            '0A.0C': 'neutral_ct_secondary',
            '0A.11': 'vt_connection_mode',
            
            # Easergy
            '0120': 'phase_ct_primary',
            '0121': 'phase_ct_secondary',
            '0122': 'neutral_ct_primary',
            '0123': 'neutral_ct_secondary',
        }
        
        for _, row in data.iterrows():
            code = str(row.get('Code', ''))
            value = str(row.get('Value', ''))
            
            if code in electrical_mapping:
                field_name = electrical_mapping[code]
                setattr(electrical, field_name, value)
        
        return electrical

    def _extract_protection_functions(self, data: pd.DataFrame, manufacturer_info: Dict) -> List[ProtectionFunction]:
        """Extrai funções de proteção configuradas"""
        
        functions = []
        
        if data.empty:
            return functions
            
        # Agrupar por função de proteção
        function_groups = {}
        
        for _, row in data.iterrows():
            code = str(row.get('Code', ''))
            value = str(row.get('Value', ''))
            description = str(row.get('Description', ''))
            
            # Identificar função por código ou descrição
            function_name = self._classify_protection_function(code, description)
            
            if function_name != 'Unknown' and function_name != 'System':
                if function_name not in function_groups:
                    function_groups[function_name] = {
                        'parameters': [],
                        'code': code.split('.')[0] if '.' in code else code[:4]
                    }
                
                function_groups[function_name]['parameters'].append({
                    'code': code,
                    'description': description,
                    'value': value
                })
        
        # Criar objetos ProtectionFunction
        for func_name, func_data in function_groups.items():
            # Determinar se está habilitada
            enabled = self._is_function_enabled(func_data['parameters'])
            
            # Extrair ajustes principais
            current_setting = self._extract_current_setting(func_data['parameters'])
            time_setting = self._extract_time_setting(func_data['parameters'])
            
            # Parâmetros adicionais
            additional_settings = {}
            for param in func_data['parameters']:
                key = param['description']
                value = param['value']
                if key and value:
                    additional_settings[key] = value
            
            function = ProtectionFunction(
                function_name=func_name,
                code=func_data['code'],
                enabled=enabled,
                current_setting=current_setting,
                time_setting=time_setting,
                additional_settings=additional_settings
            )
            
            functions.append(function)
        
        return functions

    def _classify_protection_function(self, code: str, description: str) -> str:
        """Classifica a função de proteção"""
        
        desc_lower = description.lower()
        
        # Classificação por descrição
        if any(term in desc_lower for term in ['thermal', 'ith', 'overload']):
            return 'Thermal'
        elif any(term in desc_lower for term in ['overcurrent', 'i>>', 'i>']):
            return 'Overcurrent'
        elif any(term in desc_lower for term in ['earth', 'ground', 'isef', 'i0']):
            return 'Earth Fault'
        elif any(term in desc_lower for term in ['voltage', 'v<', 'v>']):
            return 'Voltage'
        elif any(term in desc_lower for term in ['negative', 'sequence', 'i2']):
            return 'Negative Sequence'
        elif any(term in desc_lower for term in ['motor', 'start', 'stall']):
            return 'Motor'
        elif any(term in desc_lower for term in ['frequency', 'hz']):
            return 'Frequency'
        elif any(term in desc_lower for term in ['rtd', 'temperature']):
            return 'Temperature'
        elif any(term in desc_lower for term in ['cb fail', 'breaker']):
            return 'CB Fail'
        elif any(term in desc_lower for term in ['system', 'config', 'setting']):
            return 'System'
        else:
            return 'Unknown'

    def _is_function_enabled(self, parameters: List[Dict]) -> bool:
        """Determina se a função está habilitada"""
        
        for param in parameters:
            value = param['value'].lower()
            desc = param['description'].lower()
            
            if 'status' in desc or 'function' in desc:
                if any(term in value for term in ['enabled', 'dt', 'idmt']):
                    return True
                elif any(term in value for term in ['disabled', 'no']):
                    return False
        
        # Se não há indicação clara, assumir desabilitada
        return False

    def _extract_current_setting(self, parameters: List[Dict]) -> Optional[str]:
        """Extrai ajuste de corrente principal"""
        
        for param in parameters:
            desc = param['description'].lower()
            value = param['value']
            
            if any(term in desc for term in ['current set', 'i>>', 'i>', 'ith']):
                if any(unit in value.lower() for unit in ['a', 'amp']):
                    return value
        
        return None

    def _extract_time_setting(self, parameters: List[Dict]) -> Optional[str]:
        """Extrai ajuste de tempo principal"""
        
        for param in parameters:
            desc = param['description'].lower()
            value = param['value']
            
            if any(term in desc for term in ['time', 'delay', 't>']):
                if any(unit in value.lower() for unit in ['s', 'ms', 'min']):
                    return value
        
        return None

    def _extract_io_configuration(self, data: pd.DataFrame, manufacturer_info: Dict) -> IOConfiguration:
        """Extrai configuração de entradas/saídas"""
        
        io_config = IOConfiguration()
        
        if data.empty:
            return io_config
        
        opto_inputs = {}
        relay_outputs = {}
        rtd_inputs = {}
        
        for _, row in data.iterrows():
            code = str(row.get('Code', ''))
            value = str(row.get('Value', ''))
            description = str(row.get('Description', ''))
            
            desc_lower = description.lower()
            
            if 'opto' in desc_lower and 'input' in desc_lower:
                opto_inputs[description] = value
            elif 'relay' in desc_lower and ('output' in desc_lower or any(str(i) in description for i in range(1, 10))):
                relay_outputs[description] = value
            elif 'rtd' in desc_lower:
                rtd_inputs[description] = value
        
        io_config.opto_inputs = opto_inputs if opto_inputs else None
        io_config.relay_outputs = relay_outputs if relay_outputs else None
        io_config.rtd_inputs = rtd_inputs if rtd_inputs else None
        
        return io_config

    def _extract_additional_parameters(self, data: pd.DataFrame, manufacturer_info: Dict) -> Dict[str, str]:
        """Extrai parâmetros adicionais importantes"""
        
        additional = {}
        
        if data.empty:
            return additional
        
        # Parâmetros importantes para reprodução
        important_keywords = [
            'password', 'address', 'group', 'status', 'alarm', 'control',
            'access', 'display', 'measurement', 'supervision', 'record'
        ]
        
        for _, row in data.iterrows():
            description = str(row.get('Description', ''))
            value = str(row.get('Value', ''))
            
            desc_lower = description.lower()
            
            if any(keyword in desc_lower for keyword in important_keywords):
                additional[description] = value
        
        return additional

# ---------------------------
# Geradores de Relatório e JSON
# ---------------------------

def generate_complete_analysis_report(config: RelayConfiguration, output_path: Path) -> None:
    """Gera relatório completo de análise do relé"""
    
    import json
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RELATÓRIO DE CONFIGURAÇÃO COMPLETA DO RELÉ DE PROTEÇÃO\n")
        f.write("Para Reprodução do Status de Configuração\n")
        f.write("=" * 80 + "\n\n")
        
        # 1. IDENTIFICAÇÃO DO EQUIPAMENTO
        f.write("1. IDENTIFICAÇÃO DO EQUIPAMENTO\n")
        f.write("-" * 40 + "\n")
        f.write(f"Modelo: {config.identification.model or 'N/A'}\n")
        f.write(f"Fabricante: {config.identification.manufacturer or 'N/A'}\n")
        f.write(f"Número de Série: {config.identification.serial_number or 'N/A'}\n")
        f.write(f"Versão de Software: {config.identification.software_version or 'N/A'}\n")
        f.write(f"TAG/Referência: {config.identification.tag_reference or 'N/A'}\n")
        f.write(f"Referência da Planta: {config.identification.plant_reference or 'N/A'}\n")
        f.write(f"Frequência: {config.identification.frequency or 'N/A'}\n")
        f.write(f"Descrição: {config.identification.description or 'N/A'}\n\n")
        
        # 2. CONFIGURAÇÃO ELÉTRICA
        f.write("2. CONFIGURAÇÃO ELÉTRICA\n")
        f.write("-" * 40 + "\n")
        f.write(f"TC Primário (Fases): {config.electrical.phase_ct_primary or 'N/A'}\n")
        f.write(f"TC Secundário (Fases): {config.electrical.phase_ct_secondary or 'N/A'}\n")
        f.write(f"TC Primário (Neutro): {config.electrical.neutral_ct_primary or 'N/A'}\n")
        f.write(f"TC Secundário (Neutro): {config.electrical.neutral_ct_secondary or 'N/A'}\n")
        f.write(f"TP Primário: {config.electrical.vt_primary or 'N/A'}\n")
        f.write(f"TP Secundário: {config.electrical.vt_secondary or 'N/A'}\n")
        f.write(f"Modo de Conexão TP: {config.electrical.vt_connection_mode or 'N/A'}\n\n")
        
        # 3. FUNÇÕES DE PROTEÇÃO
        f.write("3. FUNÇÕES DE PROTEÇÃO CONFIGURADAS\n")
        f.write("-" * 40 + "\n")
        for func in config.protection_functions:
            status = "HABILITADA" if func.enabled else "DESABILITADA"
            f.write(f"• {func.function_name} ({func.code}): {status}\n")
            f.write(f"  Ajuste de Corrente: {func.current_setting or 'N/A'}\n")
            f.write(f"  Ajuste de Tempo: {func.time_setting or 'N/A'}\n")
            
            if func.additional_settings:
                for key, value in func.additional_settings.items():
                    f.write(f"  {key}: {value}\n")
            f.write("\n")
        
        # 4. CONFIGURAÇÃO DE I/O
        f.write("4. CONFIGURAÇÃO DE ENTRADAS/SAÍDAS\n")
        f.write("-" * 40 + "\n")
        
        if config.io_configuration.opto_inputs:
            f.write("Entradas Óticas:\n")
            for key, value in config.io_configuration.opto_inputs.items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
        
        if config.io_configuration.relay_outputs:
            f.write("Saídas a Relé:\n")
            for key, value in config.io_configuration.relay_outputs.items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
        
        if config.io_configuration.rtd_inputs:
            f.write("Entradas RTD:\n")
            for key, value in config.io_configuration.rtd_inputs.items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
        
        # 5. PARÂMETROS ADICIONAIS
        f.write("5. PARÂMETROS ADICIONAIS IMPORTANTES\n")
        f.write("-" * 40 + "\n")
        for key, value in config.additional_parameters.items():
            f.write(f"• {key}: {value}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("Relatório gerado pelo PROTECAI - Sistema de Análise de Proteção\n")
        f.write(f"Total de parâmetros analisados: {len(config.raw_data)}\n")
        f.write("=" * 80 + "\n")

def generate_relay_config_json(config: RelayConfiguration, output_path: Path) -> None:
    """Gera configuração estruturada em JSON"""
    
    import json
    from dataclasses import asdict
    
    # Converter dataclasses para dict
    config_dict = {
        "identification": asdict(config.identification),
        "electrical": asdict(config.electrical),
        "protection_functions": [asdict(func) for func in config.protection_functions],
        "io_configuration": asdict(config.io_configuration),
        "additional_parameters": config.additional_parameters,
        "raw_data": config.raw_data
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)

# ---------------------------
# Processadores Multi-Formato
# ---------------------------

def process_txt_file(txt_path: Path) -> pd.DataFrame:
    """
    Processa arquivo TXT estruturado.
    
    Suporta formatos:
    - Code: Description: Value
    - Code | Description | Value  
    - SepaM .S40: key=value (formato INI)
    """
    rows = []
    
    try:
        # Tentar diferentes encodings comuns para arquivos SepaM
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        content = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(txt_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    used_encoding = encoding
                    break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise ValueError(f"Não foi possível decodificar o arquivo com nenhum encoding testado: {encodings}")
        
        # Log do encoding usado (apenas para .S40)
        if txt_path.suffix.upper() == '.S40':
            print(f"[ENCODING] {txt_path.name}: {used_encoding}")
        
        # Detectar se é arquivo SepaM (.S40) pelo conteúdo
        is_sepam = (txt_path.suffix.lower() == '.s40' or 
                   '[Sepam_' in content or 
                   '=' in content and '[' in content)
        
        current_section = "general"
        
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):  # Ignorar comentários
                continue
            
            # SepaM .S40 format: key=value e seções [nome]
            if is_sepam:
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]  # Remove [ ]
                    continue
                elif '=' in line:
                    key, value = line.split('=', 1)
                    code = f"{current_section}.{key.strip()}"
                    rows.append({"Code": code, "Description": key.strip(), "Value": value.strip()})
            
            # Padrão tradicional 1: Code: Description: Value
            elif line.count(':') >= 2:
                parts = line.split(':', 2)
                if len(parts) == 3:
                    code, desc, val = [p.strip() for p in parts]
                    rows.append({"Code": code, "Description": desc, "Value": val})
            
            # Padrão tradicional 2: Code | Description | Value
            elif '|' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    code, desc, val = [p.strip() for p in parts[:3]]
                    rows.append({"Code": code, "Description": desc, "Value": val})
    
    except Exception as e:
        print(f"Erro ao processar TXT {txt_path}: {e}")
        return pd.DataFrame(columns=["Code", "Description", "Value"])
    
    return pd.DataFrame(rows)


def process_xlsx_file(xlsx_path: Path) -> pd.DataFrame:
    """
    Processa arquivo Excel.
    
    Espera colunas: Code, Description, Value (em qualquer ordem)
    """
    try:
        # Tentar ler primeira planilha
        df = pd.read_excel(xlsx_path, sheet_name=0)
        
        # Mapear colunas comuns
        column_mapping = {}
        for col in df.columns:
            col_lower = str(col).lower()
            if 'code' in col_lower or 'código' in col_lower:
                column_mapping[col] = 'Code'
            elif 'desc' in col_lower or 'description' in col_lower:
                column_mapping[col] = 'Description'  
            elif 'value' in col_lower or 'valor' in col_lower:
                column_mapping[col] = 'Value'
        
        # Renomear colunas
        df = df.rename(columns=column_mapping)
        
        # Garantir que temos as colunas necessárias
        required_cols = ['Code', 'Description', 'Value']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Aviso: Colunas ausentes em {xlsx_path}: {missing_cols}")
            # Criar colunas ausentes vazias
            for col in missing_cols:
                df[col] = ""
        
        return df[required_cols]
        
    except Exception as e:
        print(f"Erro ao processar XLSX {xlsx_path}: {e}")
        return pd.DataFrame(columns=["Code", "Description", "Value"])


def process_csv_file(csv_path: Path) -> pd.DataFrame:
    """
    Processa arquivo CSV.
    
    Espera colunas: Code, Description, Value
    """
    try:
        # Tentar diferentes separadores
        for sep in [',', ';', '\t']:
            try:
                df = pd.read_csv(csv_path, sep=sep, encoding='utf-8')
                if len(df.columns) >= 3:
                    break
            except:
                continue
        else:
            # Fallback para vírgula
            df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Mapear colunas (mesmo lógica do XLSX)
        column_mapping = {}
        for col in df.columns:
            col_lower = str(col).lower()
            if 'code' in col_lower or 'código' in col_lower:
                column_mapping[col] = 'Code'
            elif 'desc' in col_lower or 'description' in col_lower:
                column_mapping[col] = 'Description'
            elif 'value' in col_lower or 'valor' in col_lower:
                column_mapping[col] = 'Value'
        
        df = df.rename(columns=column_mapping)
        
        # Garantir colunas necessárias
        required_cols = ['Code', 'Description', 'Value']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        
        return df[required_cols]
        
    except Exception as e:
        print(f"Erro ao processar CSV {csv_path}: {e}")
        return pd.DataFrame(columns=["Code", "Description", "Value"])


def process_file_by_extension(file_path: Path) -> Tuple[pd.DataFrame, str]:
    """
    Processa arquivo baseado na extensão.
    
    Returns:
        Tupla (DataFrame, formato_detectado)
    """
    extension = file_path.suffix.lower()
    
    if extension == '.pdf':
        text = extract_text_pypdf2(file_path)
        result = detect_and_parse(text)
        return result.df, result.detected
    
    elif extension in ['.txt', '.s40', '.S40']:
        df = process_txt_file(file_path)
        format_type = "sepam_s40" if extension.lower() == '.s40' else "structured_text"
        return df, format_type
    
    elif extension in ['.xlsx', '.xls']:
        df = process_xlsx_file(file_path)
        return df, "excel_spreadsheet"
    
    elif extension == '.csv':
        df = process_csv_file(file_path)
        return df, "csv_data"
    
    else:
        print(f"Formato não suportado: {extension}")
        return pd.DataFrame(columns=["Code", "Description", "Value"]), "unsupported"


def scan_and_process_all_formats(registry: FileRegistryManager) -> Dict[str, List[Dict]]:
    """
    Escaneia todos os diretórios de input e processa arquivos não processados.
    
    Returns:
        Dicionário com resultados por formato
    """
    results = {
        'pdf': [],
        'txt': [],
        'xlsx': [],
        'csv': [],
        'skipped': [],
        'errors': []
    }
    
    # Definir diretórios e extensões
    format_dirs = {
        'pdf': (INPUT_PDF_DIR, ['.pdf']),
        'txt': (INPUT_TXT_DIR, ['.txt', '.S40']),
        'xlsx': (INPUT_XLSX_DIR, ['.xlsx', '.xls']),
        'csv': (INPUT_CSV_DIR, ['.csv'])
    }
    
    for format_name, (input_dir, extensions) in format_dirs.items():
        if not input_dir.exists():
            continue
        
        # Buscar arquivos com extensões válidas
        for extension in extensions:
            for file_path in input_dir.glob(f"*{extension}"):
                # Verificar se já foi processado
                is_processed, registry_data = registry.is_file_processed(file_path)
                
                if is_processed:
                    results['skipped'].append({
                        'file': str(file_path),
                        'reason': 'already_processed',
                        'processed_at': registry_data.get('processed_at')
                    })
                    continue
                
                try:
                    # Processar arquivo
                    print(f"Processando {format_name.upper()}: {file_path.name}")
                    
                    df, detected_format = process_file_by_extension(file_path)
                    
                    if not df.empty:
                        # Gerar arquivos de saída
                        xlsx_out, csv_out = default_output_names(file_path)
                        
                        # Escrever saídas tradicionais
                        write_outputs(df, file_path, None, None, detected_format)
                        
                        # === ANÁLISE AVANÇADA INTEGRADA ===
                        try:
                            analyzer = EnhancedRelayAnalyzer()
                            relay_config = analyzer.analyze_relay_data(df, str(file_path))
                            
                            # Gerar relatório de análise completa
                            report_path = OUT_CSV_DIR / f"{file_path.stem}_analysis_report.txt"
                            generate_complete_analysis_report(relay_config, report_path)
                            
                            # Gerar configuração JSON estruturada
                            json_path = OUT_CSV_DIR / f"{file_path.stem}_config.json"
                            generate_relay_config_json(relay_config, json_path)
                            
                            print(f"Relatório salvo em: {report_path}")
                            print(f"Configuração exportada para JSON: {json_path}")
                            print(f"Modelo identificado: {relay_config.identification.model or 'N/A'}")
                            print(f"Fabricante: {relay_config.identification.manufacturer or 'N/A'}")
                            print(f"Funções de proteção encontradas: {len(relay_config.protection_functions)}")
                            
                            # Contar I/Os configurados
                            opto_count = len(relay_config.io_configuration.opto_inputs) if relay_config.io_configuration.opto_inputs else 0
                            relay_count = len(relay_config.io_configuration.relay_outputs) if relay_config.io_configuration.relay_outputs else 0
                            print(f"Entradas/saídas configuradas: {opto_count} óticas, {relay_count} relés")
                            
                            enhanced_outputs = [str(xlsx_out), str(csv_out), str(report_path), str(json_path)]
                            
                        except Exception as e:
                            print(f"Aviso: Análise avançada falhou para {file_path.name}: {e}")
                            enhanced_outputs = [str(xlsx_out), str(csv_out)]
                        
                        # Registrar processamento
                        processing_result = {
                            'status': 'success',
                            'rows_extracted': len(df),
                            'detected_format': detected_format
                        }
                        
                        registry.register_file(
                            file_path, 
                            processing_result,
                            enhanced_outputs
                        )
                        
                        results[format_name].append({
                            'file': str(file_path),
                            'rows': len(df),
                            'format': detected_format,
                            'excel_output': str(xlsx_out),
                            'csv_output': str(csv_out)
                        })
                    
                    else:
                        results['errors'].append({
                            'file': str(file_path),
                            'error': 'no_data_extracted'
                        })
                
                except Exception as e:
                    print(f"Erro ao processar {file_path}: {e}")
                    results['errors'].append({
                        'file': str(file_path),
                        'error': str(e)
                    })
    
    return results


def main() -> None:
    args = build_argparser().parse_args()
    
    # Inicializar FileRegistryManager
    registry = FileRegistryManager()
    
    # === OPÇÕES DE UTILITÁRIO ===
    
    if args.registry_status:
        """Mostrar estatísticas do registro"""
        stats = registry.get_statistics()
        print("\n=== STATUS DO REGISTRO DE ARQUIVOS ===")
        print(f"Total de arquivos processados: {stats['total_files']}")
        print(f"Registro localizado em: {stats['registry_path']}")
        
        if stats['by_extension']:
            print("\nArquivos por formato:")
            for ext, count in stats['by_extension'].items():
                print(f"  {ext}: {count} arquivo(s)")
        
        if stats['oldest_processed']:
            print(f"\nPrimeiro processamento: {stats['oldest_processed']}")
        if stats['newest_processed']:
            print(f"Último processamento: {stats['newest_processed']}")
        
        # Mostrar arquivos processados recentemente
        recent_files = registry.get_processed_files()[:10]
        if recent_files:
            print(f"\nÚltimos 10 arquivos processados:")
            for file_info in recent_files:
                print(f"  - {file_info['file_name']} ({file_info['processed_at']})")
        
        return
    
    if args.cleanup_registry:
        """Limpar registro de arquivos ausentes"""
        removed_count = registry.cleanup_missing_files()
        print(f"[INFO] Limpeza do registro: {removed_count} arquivo(s) removido(s)")
        return
    
    # === PROCESSAMENTO PRINCIPAL ===
    
    if args.scan_all:
        """Processar todos os formatos"""
        print("[INFO] Escaneando todos os diretórios de input...")
        results = scan_and_process_all_formats(registry)
        
        # Mostrar resumo
        print(f"\n=== RESUMO DO PROCESSAMENTO ===")
        for format_name in ['pdf', 'txt', 'xlsx', 'csv']:
            processed = len(results[format_name])
            if processed > 0:
                print(f"{format_name.upper()}: {processed} arquivo(s) processado(s)")
        
        skipped = len(results['skipped'])
        errors = len(results['errors'])
        
        if skipped > 0:
            print(f"Ignorados (já processados): {skipped}")
        if errors > 0:
            print(f"Erros: {errors}")
            for error in results['errors']:
                print(f"  - {error['file']}: {error['error']}")
        
        return
    
    elif args.format:
        """Processar formato específico"""
        format_dirs = {
            'pdf': INPUT_PDF_DIR,
            'txt': INPUT_TXT_DIR, 
            'xlsx': INPUT_XLSX_DIR,
            'csv': INPUT_CSV_DIR
        }
        
        input_dir = format_dirs[args.format]
        
        if not input_dir.exists() or not any(input_dir.iterdir()):
            print(f"[AVISO] Nenhum arquivo encontrado em {input_dir}")
            return
        
        print(f"[INFO] Processando arquivos {args.format.upper()} de {input_dir}")
        
        # Simular scan_all apenas para este formato
        temp_results = scan_and_process_all_formats(registry)
        processed = len(temp_results[args.format])
        
        print(f"[OK] {processed} arquivo(s) {args.format.upper()} processado(s)")
        return
    
    elif args.inputs:
        """Processar arquivos específicos"""
        
        # Resolver caminhos dos arquivos
        file_paths = []
        for raw in args.inputs:
            p = Path(raw).expanduser()
            if not p.is_absolute():
                # Tentar localizar arquivo
                cand = Path.cwd() / raw
                if not cand.exists():
                    # Buscar em diretórios de input baseado na extensão
                    ext = Path(raw).suffix.lower()
                    if ext == '.pdf':
                        cand = INPUT_PDF_DIR / raw
                    elif ext == '.txt':
                        cand = INPUT_TXT_DIR / raw
                    elif ext in ['.xlsx', '.xls']:
                        cand = INPUT_XLSX_DIR / raw
                    elif ext == '.csv':
                        cand = INPUT_CSV_DIR / raw
                p = cand
            
            p = p.resolve()
            if not p.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {p}")
            
            file_paths.append(p)
        
        print(f"[INFO] Processando {len(file_paths)} arquivo(s) específico(s)...")
        
        # === PROCESSAMENTO COM SAÍDA CONSOLIDADA ===
        if args.xlsx:
            """Excel único consolidado"""
            out_xlsx = Path(args.xlsx).expanduser().resolve()
            
            if args.csv and len(file_paths) != 1:
                raise ValueError("--csv só é permitido com --xlsx quando há APENAS 1 arquivo de entrada.")
            
            writer = pd.ExcelWriter(out_xlsx, engine="xlsxwriter")
            consolidated_rows = []
            
            try:
                for idx, file_path in enumerate(file_paths, start=1):
                    # Verificar se já foi processado (a menos que --force-reprocess)
                    if not args.force_reprocess:
                        is_processed, _ = registry.is_file_processed(file_path)
                        if is_processed:
                            print(f"[SKIP] {file_path.name} (já processado)")
                            continue
                    
                    # Processar arquivo
                    df, detected_format = process_file_by_extension(file_path)
                    
                    if df.empty:
                        print(f"[AVISO] Nenhum dado extraído de {file_path.name}")
                        continue
                    
                    # Criar aba no Excel
                    sheet_name = f"{args.sheet_prefix}{idx}"
                    informative = (file_path.stem[:20] + f"_{detected_format}")[:31]
                    sheet_name = informative or sheet_name
                    
                    df.to_excel(writer, index=False, sheet_name=sheet_name)
                    
                    # Acumular dados consolidados
                    tmp = df.copy()
                    tmp.insert(0, "SourceFile", str(file_path.name))
                    tmp.insert(1, "Format", detected_format)
                    consolidated_rows.append(tmp)
                    
                    print(f"[OK] {file_path.name}: {len(df)} linhas ({detected_format})")
                    
                    # Registrar processamento
                    processing_result = {
                        'status': 'success',
                        'rows_extracted': len(df),
                        'detected_format': detected_format
                    }
                    registry.register_file(file_path, processing_result, [str(out_xlsx)])
                
                # CSV único se solicitado
                if args.csv and len(file_paths) == 1 and consolidated_rows:
                    all_df = consolidated_rows[0]
                    out_csv = Path(args.csv).expanduser().resolve()
                    all_df.to_csv(out_csv, index=False)
                    print(f"[OK] CSV salvo em: {out_csv}")
            
            finally:
                writer.close()
            
            print(f"[OK] Excel consolidado salvo em: {out_xlsx}")
            return
        
        # === PROCESSAMENTO INDIVIDUAL ===
        else:
            """Saídas individuais por arquivo"""
            
            if len(file_paths) > 1 and args.csv:
                raise ValueError("--csv único só faz sentido com 1 arquivo ou junto com --xlsx.")
            
            for file_path in file_paths:
                # Verificar se já foi processado
                if not args.force_reprocess:
                    is_processed, _ = registry.is_file_processed(file_path)
                    if is_processed:
                        print(f"[SKIP] {file_path.name} (já processado)")
                        continue
                
                # Processar arquivo
                df, detected_format = process_file_by_extension(file_path)
                
                if df.empty:
                    print(f"[AVISO] Nenhum dado extraído de {file_path.name}")
                    continue
                
                # Gerar saídas
                xlsx_out, csv_out = write_outputs(
                    df=df,
                    pdf_path=file_path,  # função aceita qualquer Path
                    xlsx_path=None,
                    csv_path=None,
                    sheet_name=detected_format or "parameters"
                )
                
                print(f"[OK] {file_path.name}: {len(df)} linhas ({detected_format})")
                print(f"     Excel: {xlsx_out}")
                print(f"     CSV  : {csv_out}")
                
                # Registrar processamento
                processing_result = {
                    'status': 'success',
                    'rows_extracted': len(df),
                    'detected_format': detected_format
                }
                registry.register_file(file_path, processing_result, [str(xlsx_out), str(csv_out)])
            
            return
    
    else:
        """Nenhuma opção de entrada especificada"""
        print("Erro: Especifique uma opção de entrada:")
        print("  --inputs arquivo1.pdf arquivo2.xlsx")
        print("  --format pdf")
        print("  --scan-all")
        print("  --registry-status")
        print("\nUse --help para mais detalhes.")
        return


def run():
    main()

if __name__ == "__main__":
    run()

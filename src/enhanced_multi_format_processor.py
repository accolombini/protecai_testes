#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enhanced_multi_format_processor.py — Processador Multi-formato Aprimorado com Análise Estratégica

VERSÃO 3.0 - ANÁLISE ESTRATÉGICA INTEGRADA:
- Incorpora a lógica do enhanced_relay_analyzer
- Suporta: PDF, TXT, XLSX, CSV com análise profunda
- Extração completa para reprodução do status do relé
- FileRegistryManager integrado
- Relatórios estruturados e configuração JSON

OBJETIVO: Extrair TODOS os dados necessários para reproduzir o status completo de configuração 
dos relés de proteção, independentemente do formato de entrada.
"""

from __future__ import annotations

import argparse
import re
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import pandas as pd
from PyPDF2 import PdfReader

# Importar classes do enhanced_relay_analyzer
try:
    from .file_registry_manager import FileRegistryManager
except ImportError:
    from file_registry_manager import FileRegistryManager

# ---------------------------
# Classes de configuração (do enhanced_relay_analyzer)
# ---------------------------

@dataclass
class RelayIdentification:
    """Identificação completa do relé"""
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
    """Configuração elétrica do relé"""
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
    additional_settings: Dict[str, str] = None

    def __post_init__(self):
        if self.additional_settings is None:
            self.additional_settings = {}

@dataclass
class IOConfiguration:
    """Configuração de entradas/saídas"""
    opto_inputs: Dict[str, str] = None
    relay_outputs: Dict[str, str] = None
    rtd_inputs: Dict[str, str] = None
    analog_outputs: Dict[str, str] = None

    def __post_init__(self):
        for attr in ['opto_inputs', 'relay_outputs', 'rtd_inputs', 'analog_outputs']:
            if getattr(self, attr) is None:
                setattr(self, attr, {})

@dataclass
class RelayConfiguration:
    """Configuração completa do relé"""
    identification: RelayIdentification
    electrical: ElectricalConfiguration
    protection_functions: List[ProtectionFunction]
    io_configuration: IOConfiguration
    additional_parameters: Dict[str, str]
    raw_data: List[Dict[str, str]]

# ---------------------------
# Configuração de diretórios
# ---------------------------

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]

INPUT_BASE_DIR = PROJECT_ROOT / "inputs"
INPUT_PDF_DIR = INPUT_BASE_DIR / "pdf"
INPUT_TXT_DIR = INPUT_BASE_DIR / "txt"
INPUT_XLSX_DIR = INPUT_BASE_DIR / "xlsx"
INPUT_CSV_DIR = INPUT_BASE_DIR / "csv"
INPUT_REGISTRY_DIR = INPUT_BASE_DIR / "registry"

OUT_EXCEL_DIR = PROJECT_ROOT / "outputs" / "excel"
OUT_CSV_DIR = PROJECT_ROOT / "outputs" / "csv"

# Garantir que os diretórios existam
for directory in [INPUT_PDF_DIR, INPUT_TXT_DIR, INPUT_XLSX_DIR, INPUT_CSV_DIR, 
                  INPUT_REGISTRY_DIR, OUT_EXCEL_DIR, OUT_CSV_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ---------------------------
# Processador Multi-formato Aprimorado
# ---------------------------

class EnhancedRelayAnalyzer:
    """
    Analisador aprimorado que incorpora lógica estratégica
    para extrair configuração completa de relés de proteção
    """
    
    def __init__(self):
        # Regex patterns melhorados
        self.re_micom = re.compile(r"^([0-9A-F]{2}\.[0-9A-F]{2}):\s*([^:]+):\s*(.*)$")
        self.re_easergy_equals = re.compile(r"^([0-9A-F]{4}):\s*([^=:]+)=:\s*(.*)$")
        self.re_easergy_colon = re.compile(r"^([0-9A-F]{4}):\s*([^:]+):\s*(.*)$")
        
        # Padrões para arquivos estruturados
        self.re_structured = re.compile(r"^([^:]+):\s*([^:]+):\s*(.*)$")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extrai texto do PDF usando PyPDF2"""
        reader = PdfReader(str(pdf_path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    
    def parse_text_to_dataframe(self, text: str, source_format: str) -> Tuple[pd.DataFrame, str]:
        """
        Converte texto em DataFrame estruturado
        
        Returns:
            Tupla (DataFrame, formato_detectado)
        """
        rows = []
        detected_format = "unknown"
        
        # Detectar formato baseado no conteúdo
        lowered = text.lower()
        if "micom s1 agile" in lowered:
            detected_format = "micom"
        elif "easergy studio" in lowered:
            detected_format = "easergy"
        
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
                
            # Tentar padrões MiCOM
            m = self.re_micom.match(line)
            if m:
                code, desc, val = m.groups()
                rows.append({"Code": code, "Description": desc.strip(), "Value": val.strip()})
                if detected_format == "unknown":
                    detected_format = "micom"
                continue
            
            # Tentar padrões Easergy
            m = self.re_easergy_equals.match(line)
            if m:
                code, desc, val = m.groups()
                rows.append({"Code": code, "Description": desc.strip(), "Value": val.strip()})
                if detected_format == "unknown":
                    detected_format = "easergy"
                continue
                
            m = self.re_easergy_colon.match(line)
            if m:
                code, desc, val = m.groups()
                rows.append({"Code": code, "Description": desc.strip(), "Value": val.strip()})
                if detected_format == "unknown":
                    detected_format = "easergy"
                continue
            
            # Padrão genérico estruturado (para TXT)
            m = self.re_structured.match(line)
            if m:
                code, desc, val = m.groups()
                rows.append({"Code": code.strip(), "Description": desc.strip(), "Value": val.strip()})
                if detected_format == "unknown":
                    detected_format = "structured_text"
        
        df = pd.DataFrame(rows)
        return df, detected_format
    
    def process_xlsx_file(self, xlsx_path: Path) -> pd.DataFrame:
        """Processa arquivo XLSX com mapeamento inteligente de colunas"""
        try:
            # Tentar diferentes sheets
            df = None
            xls = pd.ExcelFile(xlsx_path)
            
            for sheet_name in xls.sheet_names:
                temp_df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
                if len(temp_df.columns) >= 3:
                    df = temp_df
                    break
            
            if df is None:
                df = pd.read_excel(xlsx_path)
            
            # Mapear colunas inteligentemente
            column_mapping = {}
            for col in df.columns:
                col_lower = str(col).lower()
                if any(term in col_lower for term in ['code', 'código', 'cod']):
                    column_mapping[col] = 'Code'
                elif any(term in col_lower for term in ['desc', 'description', 'descrição']):
                    column_mapping[col] = 'Description'
                elif any(term in col_lower for term in ['value', 'valor', 'val']):
                    column_mapping[col] = 'Value'
            
            df = df.rename(columns=column_mapping)
            
            # Garantir colunas necessárias
            required_cols = ['Code', 'Description', 'Value']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = ""
            
            return df[required_cols]
            
        except Exception as e:
            print(f"Erro ao processar XLSX {xlsx_path}: {e}")
            return pd.DataFrame(columns=["Code", "Description", "Value"])
    
    def process_csv_file(self, csv_path: Path) -> pd.DataFrame:
        """Processa arquivo CSV com detecção automática de separador"""
        try:
            # Tentar diferentes separadores
            for sep in [',', ';', '\t', '|']:
                try:
                    df = pd.read_csv(csv_path, sep=sep, encoding='utf-8')
                    if len(df.columns) >= 3:
                        break
                except:
                    continue
            else:
                df = pd.read_csv(csv_path, encoding='utf-8')
            
            # Mesmo mapeamento do XLSX
            column_mapping = {}
            for col in df.columns:
                col_lower = str(col).lower()
                if any(term in col_lower for term in ['code', 'código', 'cod']):
                    column_mapping[col] = 'Code'
                elif any(term in col_lower for term in ['desc', 'description', 'descrição']):
                    column_mapping[col] = 'Description'
                elif any(term in col_lower for term in ['value', 'valor', 'val']):
                    column_mapping[col] = 'Value'
            
            df = df.rename(columns=column_mapping)
            
            required_cols = ['Code', 'Description', 'Value']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = ""
            
            return df[required_cols]
            
        except Exception as e:
            print(f"Erro ao processar CSV {csv_path}: {e}")
            return pd.DataFrame(columns=["Code", "Description", "Value"])
    
    def process_txt_file(self, txt_path: Path) -> pd.DataFrame:
        """Processa arquivo TXT estruturado"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            df, _ = self.parse_text_to_dataframe(text, "txt")
            return df
            
        except Exception as e:
            print(f"Erro ao processar TXT {txt_path}: {e}")
            return pd.DataFrame(columns=["Code", "Description", "Value"])
            
    def process_file_by_extension(self, file_path: Path) -> Tuple[pd.DataFrame, str]:
        """
        Processa arquivo baseado na extensão com análise aprimorada
        
        Returns:
            Tupla (DataFrame, formato_detectado)
        """
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            text = self.extract_text_from_pdf(file_path)
            return self.parse_text_to_dataframe(text, "pdf")
        
        elif extension == '.txt':
            df = self.process_txt_file(file_path)
            return df, "structured_text"
        
        elif extension in ['.xlsx', '.xls']:
            df = self.process_xlsx_file(file_path)
            return df, "excel_spreadsheet"
        
        elif extension == '.csv':
            df = self.process_csv_file(file_path)
            return df, "csv_data"
        
        else:
            print(f"Formato não suportado: {extension}")
            return pd.DataFrame(columns=["Code", "Description", "Value"]), "unsupported"
    
    def analyze_relay_configuration(self, data: pd.DataFrame) -> RelayConfiguration:
        """
        Análise completa da configuração do relé
        Incorpora toda a lógica do enhanced_relay_analyzer
        """
        # Extrair identificação
        identification = self._extract_relay_identification(data)
        
        # Extrair configuração elétrica
        electrical = self._extract_electrical_configuration(data, identification)
        
        # Extrair funções de proteção
        protection_functions = self._extract_protection_functions(data, identification)
        
        # Extrair configuração I/O
        io_configuration = self._extract_io_configuration(data, identification)
        
        # Extrair parâmetros adicionais
        additional_parameters = self._extract_additional_parameters(data, identification)
        
        # Preparar raw data
        raw_data = data.to_dict('records') if not data.empty else []
        
        return RelayConfiguration(
            identification=identification,
            electrical=electrical,
            protection_functions=protection_functions,
            io_configuration=io_configuration,
            additional_parameters=additional_parameters,
            raw_data=raw_data
        )
    
    def _extract_relay_identification(self, data: pd.DataFrame) -> RelayIdentification:
        """Extrai identificação completa do relé"""
        identification = RelayIdentification()
        
        if data.empty:
            return identification
            
        # Mapear códigos conhecidos para identificação
        id_mapping = {
            # MiCOM
            '00.06': 'model',
            '00.08': 'serial_number',
            '00.11': 'software_version',
            '00.04': 'description',
            '00.05': 'plant_reference',
            '00.09': 'frequency',
            
            # Easergy
            '0000': 'model',
            '0005': 'software_version',
            '0001': 'tag_reference'
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
    
    def _extract_electrical_configuration(self, data: pd.DataFrame, identification: RelayIdentification) -> ElectricalConfiguration:
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
            '0A.12': 'nvd_vt_primary',
            '0A.13': 'nvd_vt_secondary',
            
            # Easergy
            '0120': 'phase_ct_primary',
            '0121': 'phase_ct_secondary',
            '0122': 'neutral_ct_primary',
            '0123': 'neutral_ct_secondary'
        }
        
        for _, row in data.iterrows():
            code = str(row.get('Code', ''))
            value = str(row.get('Value', ''))
            
            if code in electrical_mapping:
                field_name = electrical_mapping[code]
                setattr(electrical, field_name, value)
        
        return electrical
    
    def _extract_protection_functions(self, data: pd.DataFrame, identification: RelayIdentification) -> List[ProtectionFunction]:
        """Extrai todas as funções de proteção configuradas"""
        functions = []
        
        if data.empty:
            return functions
            
        # Agrupar por tipo de função
        function_groups = {}
        
        for _, row in data.iterrows():
            code = str(row.get('Code', ''))
            description = str(row.get('Description', ''))
            value = str(row.get('Value', ''))
            
            # Identificar função de proteção
            function_type = self._classify_protection_function(code, description, value)
            
            if function_type:
                if function_type not in function_groups:
                    function_groups[function_type] = []
                    
                function_groups[function_type].append({
                    'code': code,
                    'description': description,
                    'value': value
                })
        
        # Criar objetos ProtectionFunction
        for func_type, params in function_groups.items():
            function = self._build_protection_function(func_type, params)
            if function:
                functions.append(function)
        
        return functions
    
    def _classify_protection_function(self, code: str, description: str, value: str) -> Optional[str]:
        """Classifica o tipo de função de proteção"""
        desc_lower = description.lower()
        
        # Motor protection
        if any(term in desc_lower for term in ['motor', 'starting', 'stall', 'rotor']):
            return 'Motor'
        
        # Thermal protection
        elif any(term in desc_lower for term in ['thermal', 'overload', 'ith']):
            return 'Thermal'
        
        # Overcurrent
        elif any(term in desc_lower for term in ['overcurrent', 'i>']) or code.startswith('31.'):
            return 'Overcurrent'
        
        # Earth fault
        elif any(term in desc_lower for term in ['earth', 'ground', 'sef', 'i0']):
            return 'Earth Fault'
        
        # Voltage protection
        elif any(term in desc_lower for term in ['voltage', 'v<', 'v>', 'under voltage', 'overvoltage']):
            return 'Voltage'
        
        # Negative sequence
        elif any(term in desc_lower for term in ['negative', 'i2']):
            return 'Negative Sequence'
        
        return None
    
    def _build_protection_function(self, func_type: str, params: List[Dict]) -> Optional[ProtectionFunction]:
        """Constrói objeto ProtectionFunction a partir dos parâmetros"""
        if not params:
            return None
        
        # Determinar se está habilitada
        enabled = False
        main_code = ""
        current_setting = None
        time_setting = None
        additional_settings = {}
        
        for param in params:
            code = param['code']
            description = param['description']
            value = param['value']
            
            desc_lower = description.lower()
            
            # Verificar se está habilitada
            if any(term in desc_lower for term in ['status', 'function']) and not main_code:
                main_code = code
                enabled = value.lower() in ['enabled', 'dt', 'idmt', 'yes']
            
            # Ajustes de corrente
            if any(term in desc_lower for term in ['current', 'set', 'pickup']) and 'time' not in desc_lower:
                current_setting = value
            
            # Ajustes de tempo
            elif any(term in desc_lower for term in ['time', 'delay']):
                time_setting = value
            
            # Outros parâmetros
            else:
                additional_settings[description] = value
        
        if not main_code:
            main_code = params[0]['code']
        
        return ProtectionFunction(
            function_name=func_type,
            code=main_code,
            enabled=enabled,
            current_setting=current_setting,
            time_setting=time_setting,
            additional_settings=additional_settings
        )
    
    def _extract_io_configuration(self, data: pd.DataFrame, identification: RelayIdentification) -> IOConfiguration:
        """Extrai configuração de entradas/saídas"""
        io_config = IOConfiguration()
        
        if data.empty:
            return io_config
            
        for _, row in data.iterrows():
            code = str(row.get('Code', ''))
            description = str(row.get('Description', ''))
            value = str(row.get('Value', ''))
            
            desc_lower = description.lower()
            
            # Entradas óticas
            if 'opto' in desc_lower and 'input' in desc_lower:
                io_config.opto_inputs[description] = value
            
            # Saídas a relé
            elif 'relay' in desc_lower and any(term in desc_lower for term in ['output', 'contact']):
                io_config.relay_outputs[description] = value
            
            # RTDs
            elif 'rtd' in desc_lower or code.startswith('4C.'):
                io_config.rtd_inputs[description] = value
                
            # Saídas analógicas
            elif 'analog' in desc_lower and 'output' in desc_lower:
                io_config.analog_outputs[description] = value
        
        return io_config
    
    def _extract_additional_parameters(self, data: pd.DataFrame, identification: RelayIdentification) -> Dict[str, str]:
        """Extrai parâmetros adicionais importantes"""
        additional = {}
        
        if data.empty:
            return additional
            
        # Parâmetros de configuração geral
        important_keywords = [
            'communication', 'comms', 'address', 'protocol',
            'group', 'setting', 'password', 'access',
            'display', 'alarm', 'trip', 'close',
            'supervision', 'control', 'disturbance',
            'record', 'measurement', 'demand'
        ]
        
        for _, row in data.iterrows():
            description = str(row.get('Description', ''))
            value = str(row.get('Value', ''))
            
            desc_lower = description.lower()
            
            if any(keyword in desc_lower for keyword in important_keywords):
                additional[description] = value
        
        return additional
    
    def generate_configuration_report(self, config: RelayConfiguration, output_file: Optional[Path] = None) -> str:
        """Gera relatório completo da configuração para reprodução do status"""
        
        report_lines = []
        
        # Cabeçalho
        report_lines.extend([
            "=" * 80,
            "RELATÓRIO DE CONFIGURAÇÃO COMPLETA DO RELÉ DE PROTEÇÃO",
            "Para Reprodução do Status de Configuração",
            "=" * 80,
            ""
        ])
        
        # Identificação
        report_lines.extend([
            "1. IDENTIFICAÇÃO DO EQUIPAMENTO",
            "-" * 40,
            f"Modelo: {config.identification.model or 'N/A'}",
            f"Fabricante: {config.identification.manufacturer or 'N/A'}",
            f"Número de Série: {config.identification.serial_number or 'N/A'}",
            f"Versão de Software: {config.identification.software_version or 'N/A'}",
            f"TAG/Referência: {config.identification.tag_reference or 'N/A'}",
            f"Referência da Planta: {config.identification.plant_reference or 'N/A'}",
            f"Frequência: {config.identification.frequency or 'N/A'}",
            f"Descrição: {config.identification.description or 'N/A'}",
            ""
        ])
        
        # Configuração elétrica
        report_lines.extend([
            "2. CONFIGURAÇÃO ELÉTRICA",
            "-" * 40,
            f"TC Primário (Fases): {config.electrical.phase_ct_primary or 'N/A'}",
            f"TC Secundário (Fases): {config.electrical.phase_ct_secondary or 'N/A'}",
            f"TC Primário (Neutro): {config.electrical.neutral_ct_primary or 'N/A'}",
            f"TC Secundário (Neutro): {config.electrical.neutral_ct_secondary or 'N/A'}",
            f"TP Primário: {config.electrical.vt_primary or 'N/A'}",
            f"TP Secundário: {config.electrical.vt_secondary or 'N/A'}",
            f"Modo de Conexão TP: {config.electrical.vt_connection_mode or 'N/A'}",
            ""
        ])
        
        # Funções de proteção
        report_lines.extend([
            "3. FUNÇÕES DE PROTEÇÃO CONFIGURADAS",
            "-" * 40
        ])
        
        if config.protection_functions:
            for func in config.protection_functions:
                status = "HABILITADA" if func.enabled else "DESABILITADA"
                report_lines.extend([
                    f"• {func.function_name} ({func.code}): {status}",
                    f"  Ajuste de Corrente: {func.current_setting or 'N/A'}",
                    f"  Ajuste de Tempo: {func.time_setting or 'N/A'}"
                ])
                if func.additional_settings:
                    for key, value in func.additional_settings.items():
                        report_lines.append(f"  {key}: {value}")
                report_lines.append("")
        else:
            report_lines.append("Nenhuma função de proteção identificada.")
            report_lines.append("")
        
        # I/O Configuration
        report_lines.extend([
            "4. CONFIGURAÇÃO DE ENTRADAS/SAÍDAS",
            "-" * 40
        ])
        
        if config.io_configuration.opto_inputs:
            report_lines.append("Entradas Óticas:")
            for desc, value in config.io_configuration.opto_inputs.items():
                report_lines.append(f"  {desc}: {value}")
            report_lines.append("")
        
        if config.io_configuration.relay_outputs:
            report_lines.append("Saídas a Relé:")
            for desc, value in config.io_configuration.relay_outputs.items():
                report_lines.append(f"  {desc}: {value}")
            report_lines.append("")
        
        if config.io_configuration.rtd_inputs:
            report_lines.append("Entradas RTD:")
            for desc, value in config.io_configuration.rtd_inputs.items():
                report_lines.append(f"  {desc}: {value}")
            report_lines.append("")
        
        # Parâmetros adicionais
        if config.additional_parameters:
            report_lines.extend([
                "5. PARÂMETROS ADICIONAIS IMPORTANTES",
                "-" * 40
            ])
            for desc, value in config.additional_parameters.items():
                report_lines.append(f"• {desc}: {value}")
            report_lines.append("")
        
        # Rodapé
        report_lines.extend([
            "=" * 80,
            "Relatório gerado pelo PROTECAI - Sistema de Análise de Proteção",
            f"Total de parâmetros analisados: {len(config.raw_data)}",
            "=" * 80
        ])
        
        report_text = "\n".join(report_lines)
        
        # Salvar arquivo se especificado
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"Relatório salvo em: {output_file}")
        
        return report_text
    
    def export_configuration_json(self, config: RelayConfiguration, output_file: Path) -> None:
        """Exporta configuração como JSON estruturado"""
        
        # Converter para dicionário serializável
        config_dict = {
            "identification": asdict(config.identification),
            "electrical": asdict(config.electrical),
            "protection_functions": [asdict(func) for func in config.protection_functions],
            "io_configuration": asdict(config.io_configuration),
            "additional_parameters": config.additional_parameters,
            "raw_data": config.raw_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        
        print(f"Configuração exportada para JSON: {output_file}")


# ---------------------------
# Função principal de processamento
# ---------------------------

def process_and_analyze_files(file_paths: List[Path], registry: FileRegistryManager) -> Dict[str, Any]:
    """
    Processa e analisa arquivos multi-formato com análise estratégica completa
    """
    analyzer = EnhancedRelayAnalyzer()
    results = {
        'processed': [],
        'skipped': [],
        'errors': [],
        'summary': {}
    }
    
    for file_path in file_paths:
        try:
            # Verificar se já foi processado
            is_processed, registry_data = registry.is_file_processed(file_path)
            
            if is_processed:
                results['skipped'].append({
                    'file': str(file_path),
                    'reason': 'already_processed',
                    'processed_at': registry_data.get('processed_at')
                })
                continue
            
            print(f"\n--- Analisando {file_path.name} ---")
            
            # Processar arquivo
            df, detected_format = analyzer.process_file_by_extension(file_path)
            
            if df.empty:
                results['errors'].append({
                    'file': str(file_path),
                    'error': 'no_data_extracted'
                })
                continue
            
            # Análise estratégica completa
            config = analyzer.analyze_relay_configuration(df)
            
            # Gerar relatório
            report_path = OUT_CSV_DIR / f"{file_path.stem}_analysis_report.txt"
            analyzer.generate_configuration_report(config, report_path)
            
            # Exportar JSON
            json_path = OUT_CSV_DIR / f"{file_path.stem}_config.json"
            analyzer.export_configuration_json(config, json_path)
            
            # Salvar CSV tradicional
            csv_path = OUT_CSV_DIR / f"{file_path.stem}_params.csv"
            df.to_csv(csv_path, index=False)
            
            # Registrar processamento
            processing_result = {
                'status': 'success',
                'rows_extracted': len(df),
                'detected_format': detected_format,
                'protection_functions': len(config.protection_functions),
                'io_configured': len(config.io_configuration.opto_inputs) + len(config.io_configuration.relay_outputs)
            }
            
            registry.register_file(
                file_path,
                processing_result,
                [str(report_path), str(json_path), str(csv_path)]
            )
            
            # Informações do resultado
            print(f"Relatório salvo em: {report_path}")
            print(f"Configuração exportada para JSON: {json_path}")
            print(f"Modelo identificado: {config.identification.model or 'N/A'}")
            print(f"Fabricante: {config.identification.manufacturer or 'N/A'}")
            print(f"Funções de proteção encontradas: {len(config.protection_functions)}")
            print(f"Entradas/saídas configuradas: {len(config.io_configuration.opto_inputs)} óticas, {len(config.io_configuration.relay_outputs)} relés")
            
            results['processed'].append({
                'file': str(file_path),
                'rows': len(df),
                'format': detected_format,
                'model': config.identification.model,
                'manufacturer': config.identification.manufacturer,
                'protection_functions': len(config.protection_functions),
                'outputs': {
                    'report': str(report_path),
                    'json': str(json_path),
                    'csv': str(csv_path)
                }
            })
            
        except Exception as e:
            print(f"Erro ao processar {file_path}: {e}")
            results['errors'].append({
                'file': str(file_path),
                'error': str(e)
            })
    
    # Resumo
    results['summary'] = {
        'total_files': len(file_paths),
        'processed': len(results['processed']),
        'skipped': len(results['skipped']),
        'errors': len(results['errors'])
    }
    
    return results


# ---------------------------
# Interface de linha de comando
# ---------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Processador Multi-formato Aprimorado com Análise Estratégica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Processar arquivos específicos
  python enhanced_multi_format_processor.py arquivo1.pdf config.xlsx
  
  # Processar todos os CSVs gerados pelo app.py
  python enhanced_multi_format_processor.py outputs/csv/*_params.csv
  
  # Processar arquivo único
  python enhanced_multi_format_processor.py arquivo.pdf

Funcionalidades:
  • Análise estratégica completa para reprodução do status do relé
  • Suporte a PDF, TXT, XLSX, CSV
  • Relatórios estruturados e configuração JSON
  • Integração com FileRegistryManager
  • Detecção automática de formato (MiCOM, Easergy, etc.)
        """
    )
    
    parser.add_argument(
        'files',
        nargs='*',
        help='Arquivos para processar (PDF, TXT, XLSX, CSV)'
    )
    
    parser.add_argument(
        '--scan-csv',
        action='store_true',
        help='Processar todos os CSVs em outputs/csv/*_params.csv'
    )
    
    args = parser.parse_args()
    
    # Inicializar FileRegistryManager
    registry = FileRegistryManager()
    
    # Determinar arquivos para processar
    file_paths = []
    
    if args.scan_csv:
        # Processar CSVs gerados pelo app.py
        csv_pattern = OUT_CSV_DIR / "*_params.csv"
        file_paths.extend(Path().glob(str(csv_pattern)))
    
    if args.files:
        # Arquivos específicos
        for file_str in args.files:
            path = Path(file_str)
            if path.exists():
                file_paths.append(path)
            else:
                print(f"Arquivo não encontrado: {file_str}")
    
    if not file_paths:
        print("Nenhum arquivo especificado. Use --help para ver opções.")
        return
    
    # Processar arquivos
    results = process_and_analyze_files(file_paths, registry)
    
    # Mostrar resumo
    print(f"\n=== RESUMO DO PROCESSAMENTO ===")
    print(f"Total de arquivos: {results['summary']['total_files']}")
    print(f"Processados: {results['summary']['processed']}")
    print(f"Ignorados: {results['summary']['skipped']}")
    print(f"Erros: {results['summary']['errors']}")


if __name__ == "__main__":
    main()
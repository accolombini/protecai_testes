#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enhanced_relay_analyzer.py — Analisador Estratégico para Reprodução Completa do Status do Relé

OBJETIVO ESTRATÉGICO:
Extrair TODOS os dados necessários para reproduzir completamente o status de configuração 
do relé de proteção, permitindo:

1. IDENTIFICAÇÃO COMPLETA:
   - Modelo, fabricante, série, software
   - TAG/referência da instalação
   - Posição na barra/bay

2. CONFIGURAÇÃO ELÉTRICA:
   - TCs (primário/secundário) 
   - TPs (primário/secundário)
   - Carga do equipamento protegido
   - Configuração de medição

3. PARAMETRIZAÇÃO DE PROTEÇÃO:
   - Todas as funções habilitadas/desabilitadas
   - Ajustes de corrente e tempo
   - Curvas características
   - Lógicas de proteção

4. CONFIGURAÇÃO OPERACIONAL:
   - I/Os digitais e analógicos
   - Comunicação
   - Alarmes e sinalizações
   - Configurações especiais

FORMATOS SUPORTADOS: PDF, TXT, XLSX, CSV
"""

import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import json
from dataclasses import dataclass, asdict

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
    additional_parameters: Dict[str, str] = None
    raw_data: List[Dict[str, str]] = None

    def __post_init__(self):
        if self.additional_parameters is None:
            self.additional_parameters = {}
        if self.raw_data is None:
            self.raw_data = []

class EnhancedRelayAnalyzer:
    """Analisador avançado para reprodução completa do status do relé"""

    def __init__(self):
        self.protection_function_mapping = self._build_protection_mapping()
        self.manufacturer_patterns = self._build_manufacturer_patterns()

    def _build_protection_mapping(self) -> Dict[str, Dict[str, str]]:
        """Mapeia códigos de proteção para funções padronizadas"""
        return {
            # Sobrecorrente
            'overcurrent': {
                'I>1': 'Overcurrent Stage 1',
                'I>2': 'Overcurrent Stage 2', 
                'I>3': 'Overcurrent Stage 3',
                'I>>': 'Instantaneous Overcurrent',
                '30.01': 'Thermal Overload Current',
                '31.01': 'Overcurrent Function',
                '0210': 'I>> Function',
                '0211': 'I>> Setting'
            },
            
            # Terra
            'earth_fault': {
                'ISEF>1': 'Earth Fault Stage 1',
                'I0>': 'Residual Current',
                'I0>>': 'Instantaneous Earth Fault',
                '32.01': 'SEF Function',
                '0220': 'I0> Function',
                '0223': 'I0>> Function'
            },
            
            # Sobrecarga térmica
            'thermal': {
                'Thermal Overload': 'Thermal Protection',
                'Ith Current Set': 'Thermal Current Setting',
                'K Coefficient': 'Thermal K Factor',
                '30.01': 'Thermal Current',
                '0200': 'Thermal Function',
                '0202': 'Thermal Current Setting'
            },
            
            # Sequência negativa
            'negative_sequence': {
                'I2>1': 'Negative Sequence Stage 1',
                'I2>2': 'Negative Sequence Stage 2',
                '33.01': 'Negative Sequence Function',
                '0230': 'I2> Function'
            },
            
            # Subtensão/Sobretensão
            'voltage': {
                'V<1': 'Undervoltage Stage 1',
                'V<2': 'Undervoltage Stage 2',
                'V>1': 'Overvoltage Stage 1',
                'V>2': 'Overvoltage Stage 2',
                '42.01': 'Voltage Protection'
            },
            
            # Motor específico
            'motor': {
                'Stall Detection': 'Locked Rotor',
                'Prolonged Start': 'Long Start',
                'Limit nb Starts': 'Start Limitation',
                '39.01': 'Start Protection',
                '0240': 'Long Start Function',
                '0244': 'Blocked Rotor Function'
            }
        }

    def _build_manufacturer_patterns(self) -> Dict[str, Dict[str, str]]:
        """Padrões para identificar fabricantes e formatos"""
        return {
            'schneider_micom': {
                'patterns': ['P241', 'P243', 'P245', 'MiCOM'],
                'code_format': r'^[0-9A-F]{2}\.[0-9A-F]{2}$',
                'line_format': r'^([0-9A-F]{2}\.[0-9A-F]{2}):\s*([^:]+):\s*(.*)$'
            },
            'schneider_easergy': {
                'patterns': ['P220', 'P210', 'Easergy'],
                'code_format': r'^[0-9A-F]{4}$',
                'line_format_1': r'^([0-9A-F]{4}):\s*([^=:]+)=:\s*(.*)$',
                'line_format_2': r'^([0-9A-F]{4}):\s*([^:]+):\s*(.*)$'
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
        
        # Dados brutos para referência (com limpeza de NaN)
        if not data.empty:
            # Substituir NaN por string vazia antes de converter para dict
            clean_data = data.fillna('')
            raw_data = clean_data.to_dict('records')
        else:
            raw_data = []
        
        return RelayConfiguration(
            identification=identification,
            electrical=electrical,
            protection_functions=protection_functions,
            io_configuration=io_config,
            additional_parameters=additional_params,
            raw_data=raw_data
        )

    def _identify_manufacturer(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Identifica fabricante e formato dos dados"""
        
        if data.empty:
            return {'manufacturer': 'unknown', 'format': 'unknown'}
            
        # Verificar padrões nos códigos e valores
        codes = data['Code'].astype(str).tolist() if 'Code' in data.columns else []
        descriptions = data['Description'].astype(str).tolist() if 'Description' in data.columns else []
        values = data['Value'].astype(str).tolist() if 'Value' in data.columns else []
        
        all_text = ' '.join(codes + descriptions + values).upper()
        
        for manufacturer, info in self.manufacturer_patterns.items():
            for pattern in info['patterns']:
                if pattern.upper() in all_text:
                    return {
                        'manufacturer': manufacturer,
                        'format': manufacturer,
                        'patterns': info
                    }
        
        # Análise por formato de código
        if codes:
            if any(re.match(r'^[0-9A-F]{2}\.[0-9A-F]{2}$', code) for code in codes):
                return {'manufacturer': 'schneider_micom', 'format': 'micom'}
            elif any(re.match(r'^[0-9A-F]{4}$', code) for code in codes):
                return {'manufacturer': 'schneider_easergy', 'format': 'easergy'}
        
        return {'manufacturer': 'generic', 'format': 'generic'}

    def _extract_identification(self, data: pd.DataFrame, manufacturer_info: Dict) -> RelayIdentification:
        """Extrai informações de identificação do relé"""
        
        identification = RelayIdentification()
        
        if data.empty:
            return identification
            
        # Mapear códigos para campos de identificação
        id_mapping = {
            # Schneider MiCOM
            '00.04': 'description',
            '00.05': 'plant_reference', 
            '00.06': 'model',
            '00.08': 'serial_number',
            '00.09': 'frequency',
            '00.11': 'software_version',
            
            # Schneider Easergy
            '0000': 'model',
            '010A': 'tag_reference',
            '0005': 'software_version',
            '0104': 'frequency'
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

    def _extract_protection_functions(self, data: pd.DataFrame, manufacturer_info: Dict) -> List[ProtectionFunction]:
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
        
        # Sobrecorrente
        if any(keyword in desc_lower for keyword in ['overcurrent', 'i>>', 'i>', 'short circuit']):
            return 'overcurrent'
            
        # Terra
        if any(keyword in desc_lower for keyword in ['earth', 'ground', 'residual', 'i0>', 'sef']):
            return 'earth_fault'
            
        # Térmica
        if any(keyword in desc_lower for keyword in ['thermal', 'overload', 'temperature', 'ith']):
            return 'thermal'
            
        # Sequência negativa  
        if any(keyword in desc_lower for keyword in ['negative', 'i2>', 'unbalance']):
            return 'negative_sequence'
            
        # Tensão
        if any(keyword in desc_lower for keyword in ['voltage', 'v<', 'v>', 'under', 'over']):
            return 'voltage'
            
        # Motor
        if any(keyword in desc_lower for keyword in ['stall', 'start', 'motor', 'rotor', 'locked']):
            return 'motor'
            
        return None

    def _build_protection_function(self, func_type: str, params: List[Dict]) -> Optional[ProtectionFunction]:
        """Constrói objeto ProtectionFunction a partir dos parâmetros"""
        
        if not params:
            return None
            
        # Determinar se função está habilitada
        enabled = False
        current_setting = None
        time_setting = None
        additional_settings = {}
        
        function_name = func_type.replace('_', ' ').title()
        primary_code = params[0]['code']
        
        for param in params:
            value = param['value'].lower()
            desc = param['description'].lower()
            
            # Verificar se está habilitada
            if any(keyword in value for keyword in ['enabled', 'yes', 'dt']):
                enabled = True
            elif any(keyword in value for keyword in ['disabled', 'no']):
                enabled = False
                
            # Extrair ajuste de corrente
            if any(keyword in desc for keyword in ['current', 'set', 'amp']) and not current_setting:
                current_setting = param['value']
                
            # Extrair ajuste de tempo
            if any(keyword in desc for keyword in ['time', 'delay', 'ms', 's']) and not time_setting:
                time_setting = param['value']
                
            # Outros parâmetros
            additional_settings[param['description']] = param['value']
        
        return ProtectionFunction(
            function_name=function_name,
            code=primary_code,
            enabled=enabled,
            current_setting=current_setting,
            time_setting=time_setting,
            additional_settings=additional_settings
        )

    def _extract_io_configuration(self, data: pd.DataFrame, manufacturer_info: Dict) -> IOConfiguration:
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
            if 'opto' in desc_lower or code.startswith('4A.'):
                io_config.opto_inputs[description] = value
                
            # Saídas a relé
            elif 'relay' in desc_lower or code.startswith('4B.'):
                io_config.relay_outputs[description] = value
                
            # RTDs
            elif 'rtd' in desc_lower or code.startswith('4C.'):
                io_config.rtd_inputs[description] = value
                
            # Saídas analógicas
            elif 'analog' in desc_lower and 'output' in desc_lower:
                io_config.analog_outputs[description] = value
        
        return io_config

    def _extract_additional_parameters(self, data: pd.DataFrame, manufacturer_info: Dict) -> Dict[str, str]:
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
            value = row.get('Value', '')
            
            # Corrigir valores NaN na origem - MELHOR PRÁTICA
            if pd.isna(value) or str(value).lower() in ['nan', 'null', '']:
                value = None
            else:
                value = str(value)
            
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
        
        # Configuração de I/O
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
            output_file.write_text(report_text, encoding='utf-8')
            print(f"Relatório salvo em: {output_file}")
        
        return report_text

    def export_to_json(self, config: RelayConfiguration, output_file: Path) -> None:
        """Exporta configuração completa para JSON"""
        
        # Converter para dicionário
        config_dict = asdict(config)
        
        # Salvar JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        
        print(f"Configuração exportada para JSON: {output_file}")

def main():
    """Exemplo de uso do analisador avançado"""
    
    analyzer = EnhancedRelayAnalyzer()
    
    # Carregar dados de exemplo (CSV existente)
    project_root = Path(__file__).parent
    tela1_csv = project_root / "outputs" / "csv" / "tela1_params.csv"
    tela3_csv = project_root / "outputs" / "csv" / "tela3_params.csv"
    
    for csv_file in [tela1_csv, tela3_csv]:
        if csv_file.exists():
            print(f"\n--- Analisando {csv_file.name} ---")
            
            # Carregar dados
            data = pd.read_csv(csv_file)
            
            # Analisar
            config = analyzer.analyze_relay_data(data, str(csv_file))
            
            # Gerar relatório
            report_file = csv_file.parent / f"{csv_file.stem}_analysis_report.txt"
            report = analyzer.generate_configuration_report(config, report_file)
            
            # Exportar JSON
            json_file = csv_file.parent / f"{csv_file.stem}_config.json"
            analyzer.export_to_json(config, json_file)
            
            print(f"Modelo identificado: {config.identification.model}")
            print(f"Fabricante: {config.identification.manufacturer}")
            print(f"Funções de proteção encontradas: {len(config.protection_functions)}")
            print(f"Entradas/saídas configuradas: {len(config.io_configuration.opto_inputs)} óticas, {len(config.io_configuration.relay_outputs)} relés")

if __name__ == "__main__":
    main()
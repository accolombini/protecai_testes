"""
CSV Bridge - Compatibility Layer
===============================

Ponte de compatibilidade para manter o fluxo CSV atual enquanto
prepara migração para etapPy™ API.

Baseado na análise profunda dos CSVs reais da Petrobras.
"""

import pandas as pd
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DeviceType(str, Enum):
    """Tipos de dispositivos identificados"""
    MICOM_P143 = "micom_p143"
    EASERGY_P3 = "easergy_p3"
    GENERAL_RELAY = "general_relay"

class FieldCategory(str, Enum):
    """Categorias de campos baseadas na análise real"""
    IDENTIFICATION = "identification"
    ELECTRICAL_CONFIG = "electrical_configuration"
    PROTECTION_FUNCTIONS = "protection_functions"
    IO_CONFIGURATION = "io_configuration"
    ADDITIONAL_PARAMS = "additional_parameters"

@dataclass
class CSVFieldMapping:
    """Mapeamento de campo CSV para estrutura ETAP"""
    csv_code: str
    description: str
    category: FieldCategory
    etap_field: str
    data_type: str
    unit_conversion: Optional[str] = None
    validation_rule: Optional[str] = None
    is_critical: bool = False

class CSVBridge:
    """
    Ponte de compatibilidade CSV baseada na estrutura real dos dados Petrobras
    
    Funcionalidades:
    - Parsear CSVs no formato Code,Description,Value
    - Mapear para estrutura ETAP compatível
    - Manter compatibilidade com fluxo atual
    - Preparar dados para futura API Python
    """
    
    def __init__(self, db=None):
        self.db = db
        self.field_mappings = self._initialize_field_mappings()
        self.device_configs = {}
        
    def _initialize_field_mappings(self) -> Dict[str, CSVFieldMapping]:
        """
        Inicializa mapeamentos baseados na análise real dos CSVs
        
        Estrutura identificada:
        - MiCOM P143: 338 parâmetros
        - Easergy P3: 151 parâmetros
        - Formato: Code, Description, Value
        """
        mappings = {}
        
        # ================================
        # IDENTIFICATION FIELDS
        # ================================
        
        # Baseado na análise real dos CSVs
        identification_fields = [
            ("00.04", "Description", "device_description"),
            ("00.05", "Plant Reference", "plant_reference"), 
            ("00.06", "Model Number", "model_number"),
            ("00.08", "Serial Number", "serial_number"),
            ("00.09", "Frequency", "frequency"),
            ("00.11", "Software Ref. 1", "software_version"),
            ("010A", "REFERENCE", "tag_reference"),  # Easergy format
            ("0005", "SOFTWARE VERSION", "software_version"),  # Easergy format
            ("0104", "FREQUENCY", "frequency"),  # Easergy format
        ]
        
        for code, desc, etap_field in identification_fields:
            mappings[code] = CSVFieldMapping(
                csv_code=code,
                description=desc,
                category=FieldCategory.IDENTIFICATION,
                etap_field=etap_field,
                data_type="string",
                is_critical=True
            )
        
        # ================================
        # ELECTRICAL CONFIGURATION
        # ================================
        
        electrical_fields = [
            ("0A.01", "Main VT Primary", "vt_primary", "voltage"),
            ("0A.02", "Main VT Sec'y", "vt_secondary", "voltage"),
            ("0A.07", "Phase CT Primary", "phase_ct_primary", "current"),
            ("0A.08", "Phase CT Sec'y", "phase_ct_secondary", "current"),
            ("0A.0B", "SEF CT Primary", "neutral_ct_primary", "current"),
            ("0A.0C", "SEF CT Secondary", "neutral_ct_secondary", "current"),
            ("0A.11", "VT Connect. Mode", "vt_connection_mode", "string"),
            ("0120", "PRIM PH", "phase_ct_primary", "current"),  # Easergy
            ("0121", "SEC PH", "phase_ct_secondary", "current"),  # Easergy
            ("0122", "PRIM E", "neutral_ct_primary", "current"),  # Easergy
            ("0123", "SEC E", "neutral_ct_secondary", "current"),  # Easergy
        ]
        
        for code, desc, etap_field, data_type in electrical_fields:
            unit_conv = f"{data_type}_conversion" if data_type in ["voltage", "current"] else None
            mappings[code] = CSVFieldMapping(
                csv_code=code,
                description=desc,
                category=FieldCategory.ELECTRICAL_CONFIG,
                etap_field=etap_field,
                data_type=data_type,
                unit_conversion=unit_conv,
                is_critical=True
            )
        
        # ================================
        # PROTECTION FUNCTIONS
        # ================================
        
        protection_fields = [
            # Thermal Protection
            ("30.01", "Ith Current Set", "thermal_current_setting", "current"),
            ("30.03", "Thermal Const T1", "thermal_constant_t1", "time"),
            ("30.04", "Thermal Const T2", "thermal_constant_t2", "time"),
            ("30.06", "Thermal Trip", "thermal_trip_enabled", "boolean"),
            ("30.07", "Thermal Alarm", "thermal_alarm_enabled", "boolean"),
            
            # Overcurrent Protection
            ("31.01", "I>1 Function", "overcurrent_function", "string"),
            ("31.02", "I>1 Current Set", "overcurrent_setting", "current"),
            ("31.03", "I>1 Time Delay", "overcurrent_time_delay", "time"),
            
            # Earth Fault
            ("32.01", "ISEF>1 Function", "earth_fault_function", "string"),
            ("32.03", "ISEF>1 Current", "earth_fault_setting", "current"),
            ("32.04", "ISEF>1 T. Delay", "earth_fault_time_delay", "time"),
            
            # Negative Sequence
            ("33.01", "I2>1 Status", "negative_sequence_function", "string"),
            ("33.02", "I2>1 Current Set", "negative_sequence_setting", "current"),
            ("33.03", "I2>1 Time Delay", "negative_sequence_time_delay", "time"),
            
            # Motor Protection
            ("39.01", "Prolonged Start", "prolonged_start_enabled", "boolean"),
            ("39.03", "Starting Current", "starting_current", "current"),
            ("39.04", "Prol. Start Time", "prolonged_start_time", "time"),
            ("39.07", "Stall Setting", "stall_current_setting", "current"),
            ("39.08", "Stall Time", "stall_time_delay", "time"),
            
            # Voltage Protection
            ("42.05", "V<1 Voltage Set", "undervoltage_setting", "voltage"),
            ("42.06", "V<1 Time Delay", "undervoltage_time_delay", "time"),
            
            # Easergy Protection Functions
            ("0200", "THERMAL OVERLOAD FUNCT ?", "thermal_function_enabled", "boolean"),
            ("0210", "I>> FUNCTION ?", "overcurrent_function_enabled", "boolean"),
            ("0220", "I0> FUNCTION ?", "earth_fault_function_enabled", "boolean"),
            ("0230", "I2> FUNCTION ?", "negative_sequence_function_enabled", "boolean"),
        ]
        
        for code, desc, etap_field, data_type in protection_fields:
            unit_conv = f"{data_type}_conversion" if data_type in ["voltage", "current", "time"] else None
            mappings[code] = CSVFieldMapping(
                csv_code=code,
                description=desc,
                category=FieldCategory.PROTECTION_FUNCTIONS,
                etap_field=etap_field,
                data_type=data_type,
                unit_conversion=unit_conv,
                is_critical=True
            )
        
        # ================================
        # I/O CONFIGURATION
        # ================================
        
        io_fields = [
            ("4A.01", "Opto Input 1", "opto_input_1", "string"),
            ("4A.02", "Opto Input 2", "opto_input_2", "string"),
            ("4A.03", "Opto Input 3", "opto_input_3", "string"),
            ("4B.01", "Relay 1", "relay_output_1", "string"),
            ("4B.02", "Relay 2", "relay_output_2", "string"),
            ("4B.03", "Relay 3", "relay_output_3", "string"),
            ("4C.01", "RTD 1", "rtd_input_1", "string"),
            ("4C.02", "RTD 2", "rtd_input_2", "string"),
            ("4C.03", "RTD 3", "rtd_input_3", "string"),
        ]
        
        for code, desc, etap_field, data_type in io_fields:
            mappings[code] = CSVFieldMapping(
                csv_code=code,
                description=desc,
                category=FieldCategory.IO_CONFIGURATION,
                etap_field=etap_field,
                data_type=data_type,
                is_critical=False
            )
        
        return mappings
    
    def parse_csv_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parseia arquivo CSV no formato real identificado
        
        Args:
            file_path: Caminho para arquivo CSV
            
        Returns:
            Dict com dados estruturados para ETAP
        """
        try:
            # Ler CSV no formato Code,Description,Value
            df = pd.read_csv(file_path)
            
            # Validar estrutura
            required_columns = ["Code", "Description", "Value"]
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"CSV must have columns: {required_columns}")
            
            # Identificar tipo de dispositivo
            device_type = self._identify_device_type(df)
            
            # Processar dados
            etap_config = self._process_csv_data(df, device_type)
            
            logger.info(f"Parsed CSV {file_path}: {len(df)} parameters, device: {device_type}")
            return etap_config
            
        except Exception as e:
            logger.error(f"Error parsing CSV {file_path}: {e}")
            raise
    
    def _identify_device_type(self, df: pd.DataFrame) -> DeviceType:
        """
        Identifica tipo de dispositivo baseado nos códigos presentes
        """
        codes = set(df['Code'].astype(str))
        
        # Códigos específicos do MiCOM P143
        micom_indicators = {"00.06", "0A.01", "30.01", "31.01"}
        
        # Códigos específicos do Easergy P3  
        easergy_indicators = {"010A", "0005", "0104", "0200"}
        
        if micom_indicators.intersection(codes):
            return DeviceType.MICOM_P143
        elif easergy_indicators.intersection(codes):
            return DeviceType.EASERGY_P3
        else:
            return DeviceType.GENERAL_RELAY
    
    def _process_csv_data(self, df: pd.DataFrame, device_type: DeviceType) -> Dict[str, Any]:
        """
        Processa dados CSV para estrutura ETAP
        """
        etap_config = {
            "device_type": device_type.value,
            "identification": {},
            "electrical_configuration": {},
            "protection_functions": {},
            "io_configuration": {},
            "additional_parameters": {},
            "raw_parameters": []
        }
        
        for _, row in df.iterrows():
            code = str(row['Code'])
            description = str(row['Description'])
            value = str(row['Value'])
            
            # Adicionar aos parâmetros brutos
            etap_config["raw_parameters"].append({
                "code": code,
                "description": description,
                "value": value
            })
            
            # Mapear se conhecido
            if code in self.field_mappings:
                mapping = self.field_mappings[code]
                processed_value = self._convert_value(value, mapping)
                
                category_key = mapping.category.value
                etap_config[category_key][mapping.etap_field] = processed_value
            else:
                # Parâmetro adicional não mapeado
                etap_config["additional_parameters"][code] = {
                    "description": description,
                    "value": value
                }
        
        # Pós-processamento baseado no tipo de dispositivo
        etap_config = self._post_process_device_config(etap_config, device_type)
        
        return etap_config
    
    def _convert_value(self, value: str, mapping: CSVFieldMapping) -> Any:
        """
        Converte valor baseado no tipo de dados
        """
        try:
            if mapping.data_type == "boolean":
                return self._parse_boolean(value)
            elif mapping.data_type == "current":
                return self._parse_current(value)
            elif mapping.data_type == "voltage":
                return self._parse_voltage(value)
            elif mapping.data_type == "time":
                return self._parse_time(value)
            else:
                return value
        except Exception as e:
            logger.warning(f"Error converting value '{value}' for field {mapping.etap_field}: {e}")
            return value
    
    def _parse_boolean(self, value: str) -> bool:
        """Converte string para boolean"""
        true_values = {"enabled", "yes", "true", "1", "on"}
        return value.lower().strip() in true_values
    
    def _parse_current(self, value: str) -> float:
        """Converte string de corrente para float (A)"""
        # Remove unidades e converte
        clean_value = value.replace('A', '').replace(' ', '').strip()
        return float(clean_value)
    
    def _parse_voltage(self, value: str) -> float:
        """Converte string de tensão para float (V)"""
        # Remove unidades e converte para V
        clean_value = value.replace('kV', '').replace('V', '').replace(' ', '').strip()
        voltage = float(clean_value)
        
        # Converter kV para V se necessário
        if 'kV' in value:
            voltage *= 1000
        
        return voltage
    
    def _parse_time(self, value: str) -> float:
        """Converte string de tempo para float (segundos)"""
        # Remove unidades e converte para segundos
        clean_value = value.replace('ms', '').replace('s', '').replace('min', '').replace(' ', '').strip()
        time_val = float(clean_value)
        
        # Converter unidades para segundos
        if 'ms' in value:
            time_val /= 1000
        elif 'min' in value:
            time_val *= 60
        
        return time_val
    
    def _post_process_device_config(self, config: Dict[str, Any], device_type: DeviceType) -> Dict[str, Any]:
        """
        Pós-processamento específico por tipo de dispositivo
        """
        if device_type == DeviceType.MICOM_P143:
            # Processamento específico MiCOM P143
            config = self._process_micom_specifics(config)
        elif device_type == DeviceType.EASERGY_P3:
            # Processamento específico Easergy P3
            config = self._process_easergy_specifics(config)
        
        return config
    
    def _process_micom_specifics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Processamento específico para MiCOM P143"""
        # Processar códigos específicos do MiCOM
        # Baseado na estrutura real identificada nos CSVs
        
        # Configurar funções de proteção padrão
        if "protection_functions" in config:
            # Motor protection típica do MiCOM P143
            if "thermal_current_setting" in config["protection_functions"]:
                config["protection_functions"]["thermal_protection_enabled"] = True
        
        return config
    
    def _process_easergy_specifics(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Processamento específico para Easergy P3"""
        # Processar códigos específicos do Easergy
        # Baseado na estrutura real identificada nos CSVs
        
        return config
    
    def export_to_etap_format(self, config: Dict[str, Any], output_path: str) -> str:
        """
        Exporta configuração para formato compatível com ETAP
        
        Args:
            config: Configuração processada
            output_path: Caminho para arquivo de saída
            
        Returns:
            Caminho do arquivo gerado
        """
        try:
            # Estruturar dados no formato ETAP
            etap_data = self._structure_for_etap(config)
            
            # Gerar CSV no formato esperado pelo ETAP
            etap_df = pd.DataFrame(etap_data)
            etap_df.to_csv(output_path, index=False)
            
            logger.info(f"Exported ETAP format to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting to ETAP format: {e}")
            raise
    
    def _structure_for_etap(self, config: Dict[str, Any]) -> List[Dict]:
        """
        Estrutura dados para formato ETAP
        """
        etap_data = []
        
        # Processar cada categoria
        for category, data in config.items():
            if isinstance(data, dict) and category != "raw_parameters":
                for field, value in data.items():
                    etap_data.append({
                        "Parameter": field,
                        "Value": value,
                        "Category": category,
                        "Type": type(value).__name__
                    })
        
        return etap_data
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Valida configuração para conformidade ETAP
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, validation_errors)
        """
        errors = []
        
        # Validações críticas baseadas na análise real
        critical_fields = [
            ("identification", "device_description"),
            ("identification", "model_number"),
            ("electrical_configuration", "phase_ct_primary"),
            ("electrical_configuration", "phase_ct_secondary"),
        ]
        
        for category, field in critical_fields:
            if category not in config or field not in config[category]:
                errors.append(f"Missing critical field: {category}.{field}")
        
        # Validações específicas de proteção
        if "protection_functions" in config:
            prot_funcs = config["protection_functions"]
            
            # Validar coerência de ajustes
            if "thermal_current_setting" in prot_funcs and "phase_ct_primary" in config.get("electrical_configuration", {}):
                thermal_setting = prot_funcs["thermal_current_setting"]
                ct_primary = config["electrical_configuration"]["phase_ct_primary"]
                
                if isinstance(thermal_setting, (int, float)) and isinstance(ct_primary, (int, float)):
                    if thermal_setting > ct_primary * 2:
                        errors.append("Thermal setting too high compared to CT primary")
        
        is_valid = len(errors) == 0
        return is_valid, errors

# ================================
# Factory Functions
# ================================

def create_csv_bridge() -> CSVBridge:
    """Factory function para criar instância do CSV Bridge"""
    return CSVBridge()

def process_petrobras_csv(file_path: str) -> Dict[str, Any]:
    """
    Função de conveniência para processar CSV no formato Petrobras
    
    Args:
        file_path: Caminho para arquivo CSV
        
    Returns:
        Dict com configuração processada
    """
    bridge = create_csv_bridge()
    return bridge.parse_csv_file(file_path)
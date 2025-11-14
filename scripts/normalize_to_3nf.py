#!/usr/bin/env python3
"""
NORMALIZADOR PARA 3FN - PASSO 2
================================

Lê CSVs brutos de outputs/csv/ e gera CSVs normalizados/atomizados em outputs/norm_csv/
seguindo as regras de 3FN (Terceira Forma Normal).

REGRAS DE ATOMIZAÇÃO:
1. LEDs multipart (ex: LED 5 part 1, LED 5 part 2) → 1 linha por part
2. Valores com unidade grudada (60Hz) → separar em value + unit
3. Booleanos (Yes/No) → converter para True/False
4. Remover metadados (Page, File) → extrair separadamente
5. Descrições compostas → manter originais mas normalizar espaços
6. Integrar detecção de checkbox (is_active) dos arquivos *_active_setup.csv

ENTRADA: 
- outputs/csv/*_params.csv (dados brutos)
- outputs/csv/*_active_setup.csv (checkboxes detectados)

SAÍDA: outputs/norm_csv/*_normalized.csv
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Optional, Set
import json
import sys

# Adicionar src ao path para importar UniversalSetupDetector
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


class Normalizer3NF:
    """Normalizador para 3FN (Terceira Forma Normal)"""
    
        # Padrões de unidades conhecidas (ordenar por tamanho decrescente para evitar match parcial)
    UNITS = [
        # Frequência
        'MHz', 'kHz', 'Hz',
        # Corrente
        'kA', 'mA', 'A',
        # Tensão
        'kV', 'mV', 'V',
        # Tempo
        'μs', 'ms', 's',
        # Resistência
        'Ω', 'ohm',
        # Potência
        'MVA', 'kVA', 'VA',
        'MW', 'kW', 'W',
        'kvar', 'var',
        # Temperatura
        '°C', '°F',
        # Ângulo
        'deg', '°',
        # Outros
        '%',
        'km', 'm', 'cm', 'mm',
        # Multiplicadores especiais
        'In', 'Vn'
    ]
    
    # Mapeamento de unidades compostas para normalização
    UNIT_NORMALIZATION = {
        'ohm': 'Ω',
        'Ohm': 'Ω',
        'OHM': 'Ω'
    }
    
    # Mapeamento de aliases para unidades padrão
    UNIT_ALIASES = {
        'ohm': 'Ω',
        'deg': '°',
        'us': 'μs',
        'mohm': 'mΩ',
        'kohm': 'kΩ'
    }
    
    # Códigos de metadados do relé (não são parâmetros de configuração)
    RELAY_METADATA_CODES = {
        # P122/P143 (Easergy/MiCOM) - extraídos de PDF
        '0079': 'relay_description',  # Código do equipamento/projeto (ex: P122B00Z172EC0)
        '0081': 'serial_number',       # Número de série
        '0005': 'software_version',    # Versão do software
        '010A': 'reference',           # Referência
        
        # SEPAM - extraídos de arquivo TXT/INI
        'SEPAM_REPERE': 'sepam_repere',     # Identificador do equipamento (ex: 00-MF-12 NS08170043)
        'SEPAM_MODELE': 'sepam_modele',     # Modelo do SEPAM
        'SEPAM_MES': 'sepam_mes',           # Tipo de medição
        'SEPAM_GAMME': 'sepam_gamme',       # Gama/família
        'SEPAM_TYPEMAT': 'sepam_typemat',   # Tipo de material
    }
    
    # Padrões de campos de STATUS/BINARY que devem ser text mesmo se parecerem numéricos
    STATUS_FIELD_PATTERNS = [
        r'status', r'alarm', r'opto.*i/p', r'relay.*o/p',
        r'control\s+status', r'plant\s+status', r'input\s+status',
        r'output\s+status', r'digital\s+status', r'flags',
        r'ddb', r'test\s+pattern', r'bit\s+mask', r'binary'
    ]
    
    def __init__(self):
        self.stats = {
            'total_files': 0,
            'total_rows_input': 0,
            'total_rows_output': 0,
            'multipart_expanded': 0,
            'units_separated': 0,
            'booleans_converted': 0,
            'metadata_removed': 0,
            'active_params_marked': 0,
            'status_fields_corrected': 0,
            'errors': []
        }
    
    def load_active_setup(self, csv_path: Path) -> Set[str]:
        """
        Carrega lista de códigos ativos do arquivo *_active_setup.csv.
        
        Returns:
            Set com códigos dos parâmetros marcados como ativos
        """
        # Construir nome do arquivo active_setup
        base_name = csv_path.stem.replace('_params', '')
        active_setup_path = csv_path.parent / f"{base_name}_active_setup.csv"
        
        if not active_setup_path.exists():
            logger.warning(f"   ⚠️  Active setup não encontrado: {active_setup_path.name}")
            return set()
        
        try:
            df_active = pd.read_csv(active_setup_path, encoding='utf-8')
            
            # **CORRIGIDO: Filtrar apenas parâmetros com is_active=True**
            if 'is_active' in df_active.columns:
                active_params = df_active[df_active['is_active'] == True]
                active_codes = set(active_params['Code'].astype(str))
                logger.info(f"   ✅ Active setup carregado: {len(active_codes)} parâmetros ativos (de {len(df_active)} totais)")
            else:
                # Fallback: se não há coluna is_active, assumir todos ativos (comportamento antigo)
                active_codes = set(df_active['Code'].astype(str))
                logger.warning(f"   ⚠️  Coluna is_active não encontrada, assumindo todos ativos: {len(active_codes)} parâmetros")
            
            return active_codes
        except Exception as e:
            logger.error(f"   ❌ Erro ao carregar active setup: {e}")
            return set()
    
    def is_status_field(self, description: str) -> bool:
        """
        Detecta se o campo é de STATUS/ALARM que deve ser text mesmo parecendo numérico.
        
        Args:
            description: Descrição do parâmetro
            
        Returns:
            True se for campo de status
        """
        if not description:
            return False
        
        desc_lower = description.lower()
        for pattern in self.STATUS_FIELD_PATTERNS:
            if re.search(pattern, desc_lower):
                return True
        return False
    
    def extract_relay_metadata(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Extrai metadados do relé (Description, Serial Number, etc.).
        
        Returns:
            Dict com metadados do relé
        """
        metadata = {}
        
        for code, field_name in self.RELAY_METADATA_CODES.items():
            row = df[df['Code'] == code]
            if not row.empty:
                value = row.iloc[0].get('Value', '')
                if value and str(value).strip() and str(value).strip() != 'nan':
                    metadata[field_name] = str(value).strip()
        
        return metadata
    
    def extract_value_and_unit(self, value_str: str) -> Tuple[str, str]:
        """
        Extrai valor e unidade de uma string com regex robusto.
        
        Exemplos:
            '60Hz' → ('60', 'Hz')
            '13800kV' → ('13800', 'kV')
            '1.5s' → ('1.5', 's')
            '0.10In' → ('0.10', 'In')
            '50 Ω' → ('50', 'Ω')
            '4.20 mA' → ('4.20', 'mA')
            '25°C' → ('25', '°C')
            '200' → ('200', '')
            'DMT' → ('DMT', '')
            
        Returns:
            (valor_limpo, unidade_normalizada)
        """
        if not value_str or pd.isna(value_str):
            return ('', '')
        
        value_str = str(value_str).strip()
        
        # ESTRATÉGIA 1: Tentar encontrar unidade conhecida no final (case-insensitive)
        for unit in self.UNITS:
            # Procurar padrão: número (inteiro ou decimal) + opcional espaço + unidade
            # Aceita: 60Hz, 60 Hz, 1.5s, 0.10In, -5.2kV, +3.14°, 25°C
            pattern = rf'^([-+]?\d+\.?\d*)\s*{re.escape(unit)}$'
            match = re.match(pattern, value_str, re.IGNORECASE)
            if match:
                clean_value = match.group(1)
                # Normalizar unidade usando mapeamento
                normalized_unit = self.UNIT_NORMALIZATION.get(unit, unit)
                return (clean_value, normalized_unit)
        
        # ESTRATÉGIA 2: Fallback regex genérico
        # Captura número decimal + qualquer sequência de letras/símbolos adjacente
        # Exemplos: 13800kV, 0.5μs, 100%
        fallback_pattern = r'^([-+]?\d+\.?\d*)\s*([a-zA-ZΩ°μ%]+)$'
        fallback_match = re.match(fallback_pattern, value_str)
        if fallback_match:
            clean_value = fallback_match.group(1)
            potential_unit = fallback_match.group(2)
            
            # Verificar se a unidade está na lista conhecida (case-insensitive)
            for known_unit in self.UNITS:
                if potential_unit.lower() == known_unit.lower():
                    normalized_unit = self.UNIT_NORMALIZATION.get(potential_unit, known_unit)
                    return (clean_value, normalized_unit)
            
            # Unidade desconhecida mas padrão válido - manter mesmo assim
            logger.debug(f"   ⚠️  Unidade desconhecida encontrada: '{potential_unit}' em '{value_str}'")
            return (clean_value, potential_unit)
        
        # ESTRATÉGIA 3: Apenas número (sem unidade)
        # Exemplos: 200, 1.5, -10, +5.2
        number_only_pattern = r'^[-+]?\d+\.?\d*$'
        if re.match(number_only_pattern, value_str):
            return (value_str, '')
        
        # ESTRATÉGIA 4: Não é número - retornar como texto puro
        # Exemplos: 'DMT', 'Yes', 'tU<', 'EDGE'
        return (value_str, '')
    
    def convert_boolean(self, value_str: str) -> Optional[bool]:
        """
        Converte Yes/No para True/False.
        
        Returns:
            True, False ou None (se não for booleano)
        """
        if not value_str or pd.isna(value_str):
            return None
        
        value_lower = str(value_str).strip().lower()
        
        if value_lower in ['yes', 'sim', 'true', '1']:
            return True
        elif value_lower in ['no', 'não', 'nao', 'false', '0']:
            return False
        else:
            return None
    
    def identify_multipart_groups(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """
        Identifica grupos multipart com regex robusto.
        
        Padrões suportados:
            'LED 5 part 1' → base='LED 5', part=1
            'LED 5 PART 1:' → base='LED 5', part=1
            '0150: LED 5 PART 1: tU<' → base='LED 5', part=1, extra='tU<'
            'Input 1 (1/4)' → base='Input 1', part=1
            'Blocking Logic 1 part 2' → base='Blocking Logic 1', part=2
        
        Returns:
            Dict com estrutura:
            {
                'LED 5': [
                    {'code': '0150', 'part': 1, 'value': 'tU<', 'description': '0150: LED 5 PART 1: tU<', ...},
                    {'code': '0154', 'part': 2, 'value': '', 'description': 'LED 5 part 2', ...},
                    ...
                ],
                ...
            }
        """
        multipart_groups = {}
        
        # Padrão robusto: captura variações de multipart
        # Grupo 1: prefixo opcional com código (ex: '0150:')
        # Grupo 2: nome base (ex: 'LED 5', 'Blocking Logic 1')
        # Grupo 3: 'part' ou 'PART' (case-insensitive)
        # Grupo 4: número da parte
        # Grupo 5: sufixo opcional (ex: ': tU<', ' (text)')
        # OU formato alternativo (X/Y) para Input/Output
        pattern = r'^(?:\d+:\s*)?(.+?)\s+(?:part|PART)\s+(\d+)(?::\s*(.*))?$|^(?:\d+:\s*)?(.+?)\s+\((\d+)/\d+\)(?:\s*(.*))?$'
        
        for idx, row in df.iterrows():
            desc = str(row.get('Description', '')).strip()
            value_raw = str(row.get('Value', '')).strip()
            
            match = re.match(pattern, desc, re.IGNORECASE)
            if match:
                if match.group(1):  # "LED X part Y" ou "0150: LED X PART Y: extra"
                    base_name = match.group(1).strip()
                    part_num = int(match.group(2))
                    extra_suffix = match.group(3).strip() if match.group(3) else ''
                else:  # "Input X (Y/Z)" ou "0150: Input X (Y/Z) extra"
                    base_name = match.group(4).strip()
                    part_num = int(match.group(5))
                    extra_suffix = match.group(6).strip() if match.group(6) else ''
                
                # Limpar base_name de prefixos numéricos residuais (ex: '0150: LED 5' → 'LED 5')
                base_name = re.sub(r'^\d+:\s*', '', base_name).strip()
                
                # Determinar valor final: usar extra_suffix se existir, senão value_raw
                final_value = extra_suffix if extra_suffix else value_raw
                
                if base_name not in multipart_groups:
                    multipart_groups[base_name] = []
                
                multipart_groups[base_name].append({
                    'code': row.get('Code', ''),
                    'part': part_num,
                    'value': final_value,
                    'description': desc,
                    'original_idx': idx
                })
        
        # Ordenar parts dentro de cada grupo
        for base_name in multipart_groups:
            multipart_groups[base_name].sort(key=lambda x: x['part'])
        
        return multipart_groups
    
    def normalize_csv(self, csv_path: Path) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Normaliza um CSV bruto para 3FN.
        
        Returns:
            (DataFrame normalizado, metadados do relé)
        """
        logger.info(f"\n📄 Normalizando: {csv_path.name}")
        
        # Ler CSV bruto
        df = pd.read_csv(csv_path, encoding='utf-8')
        self.stats['total_rows_input'] += len(df)
        
        # 0. CARREGAR ACTIVE SETUP (códigos com checkbox marcado)
        active_codes = self.load_active_setup(csv_path)
        
        # 1. EXTRAIR METADADOS DO RELÉ
        relay_metadata = self.extract_relay_metadata(df)
        if relay_metadata:
            logger.info(f"   📋 Metadados do relé:")
            for key, value in relay_metadata.items():
                logger.info(f"      • {key}: {value}")
        
        # 2. REMOVER METADADOS (Page, File, e códigos de metadados do relé)
        metadata_codes = set(self.RELAY_METADATA_CODES.keys())
        metadata_mask = df['Code'].isin(['Page', 'File']) | df['Code'].isin(metadata_codes)
        metadata_rows = df[metadata_mask]
        df_clean = df[~metadata_mask].copy()
        
        self.stats['metadata_removed'] += len(metadata_rows)
        logger.info(f"   📋 Metadados removidos: {len(metadata_rows)}")
        
        # 3. IDENTIFICAR GRUPOS MULTIPART
        multipart_groups = self.identify_multipart_groups(df_clean)
        
        if multipart_groups:
            logger.info(f"   🔗 Grupos multipart identificados: {len(multipart_groups)}")
            for base_name, parts in multipart_groups.items():
                logger.info(f"      • {base_name}: {len(parts)} parts")
        
        # 3. IDENTIFICAR GRUPOS MULTIPART
        multipart_groups = self.identify_multipart_groups(df_clean)
        
        if multipart_groups:
            logger.info(f"   🔗 Grupos multipart identificados: {len(multipart_groups)}")
            for base_name, parts in multipart_groups.items():
                logger.info(f"      • {base_name}: {len(parts)} parts")
        
        # 4. CRIAR DATAFRAME NORMALIZADO
        normalized_rows = []
        processed_indices = set()
        
        # 4a. Processar grupos multipart
        for base_name, parts in multipart_groups.items():
            for part_info in parts:
                # Separar valor e unidade
                value, unit = self.extract_value_and_unit(part_info['value'])
                
                # Verificar se está ativo
                is_active = part_info['code'] in active_codes
                if is_active:
                    self.stats['active_params_marked'] += 1
                
                # Identificar tipo
                bool_value = self.convert_boolean(part_info['value'])
                if bool_value is not None:
                    value_type = 'boolean'
                    value = str(bool_value)
                elif self.is_status_field(part_info['description']):
                    # Campo de STATUS: sempre text, mesmo se parecer numérico
                    value_type = 'text'
                    self.stats['status_fields_corrected'] += 1
                elif value and unit:
                    value_type = 'numeric'
                    self.stats['units_separated'] += 1
                elif value:
                    # Verificar se é valor muito grande (binário/status)
                    try:
                        num_val = float(value)
                        if len(str(value).replace('.', '').replace('-', '')) > 15 or abs(num_val) >= 1e9:
                            value_type = 'text'
                            self.stats['status_fields_corrected'] += 1
                        else:
                            value_type = 'numeric'
                    except:
                        value_type = 'text'
                else:
                    value_type = 'null'
                
                normalized_rows.append({
                    'parameter_code': part_info['code'],
                    'parameter_description': part_info['description'],
                    'parameter_value': value,
                    'value_unit': unit,
                    'value_type': value_type,
                    'is_active': is_active,
                    'multipart_base': base_name,
                    'multipart_part': part_info['part'],
                    'is_multipart': True
                })
                
                processed_indices.add(part_info['original_idx'])
                self.stats['multipart_expanded'] += 1
        
        # 4b. Processar parâmetros simples (não-multipart)
        for idx, row in df_clean.iterrows():
            if idx in processed_indices:
                continue
            
            code = row.get('Code', '')
            desc = row.get('Description', '')
            value_raw = row.get('Value', '')
            
            # Verificar se está ativo
            is_active = code in active_codes
            if is_active:
                self.stats['active_params_marked'] += 1
            
            # Separar valor e unidade
            value, unit = self.extract_value_and_unit(value_raw)
            
            # Identificar tipo
            bool_value = self.convert_boolean(value_raw)
            if bool_value is not None:
                value_type = 'boolean'
                value = str(bool_value)
                self.stats['booleans_converted'] += 1
            elif self.is_status_field(desc):
                # Campo de STATUS: sempre text, mesmo se parecer numérico
                value_type = 'text'
                self.stats['status_fields_corrected'] += 1
            elif value and unit:
                value_type = 'numeric'
                self.stats['units_separated'] += 1
            elif value:
                # Tentar identificar se é numérico
                try:
                    num_val = float(value)
                    # Se valor tem mais de 15 dígitos ou é maior que 10^9, forçar text
                    if len(str(value).replace('.', '').replace('-', '')) > 15 or abs(num_val) >= 1e9:
                        value_type = 'text'
                        self.stats['status_fields_corrected'] += 1
                    else:
                        value_type = 'numeric'
                except:
                    value_type = 'text'
            else:
                value_type = 'null'
            
            normalized_rows.append({
                'parameter_code': code,
                'parameter_description': desc,
                'parameter_value': value,
                'value_unit': unit,
                'value_type': value_type,
                'is_active': is_active,
                'multipart_base': '',
                'multipart_part': 0,
                'is_multipart': False
            })
        
        # Criar DataFrame normalizado
        df_normalized = pd.DataFrame(normalized_rows)
        
        # Adicionar metadados do arquivo
        df_normalized['source_file'] = csv_path.stem.replace('_params', '')
        df_normalized['extraction_date'] = datetime.now().isoformat()
        
        # Adicionar metadados do relé (se existirem)
        for key, value in relay_metadata.items():
            df_normalized[key] = value
        
        # Reordenar colunas
        columns_order = [
            'parameter_code',
            'parameter_description',
            'parameter_value',
            'value_unit',
            'value_type',
            'is_active',
            'is_multipart',
            'multipart_base',
            'multipart_part',
            'source_file',
            'extraction_date'
        ]
        
        # Adicionar colunas de metadados do relé
        for key in relay_metadata.keys():
            columns_order.append(key)
        
        df_normalized = df_normalized[columns_order]
        
        self.stats['total_rows_output'] += len(df_normalized)
        
        logger.info(f"   ✅ Normalizado: {len(df_clean)} → {len(df_normalized)} linhas")
        logger.info(f"   📊 Tipos: {df_normalized['value_type'].value_counts().to_dict()}")
        logger.info(f"   ☑️  Parâmetros ativos: {df_normalized['is_active'].sum()}")
        
        return df_normalized, relay_metadata
    
    def save_normalized(self, df: pd.DataFrame, relay_metadata: Dict[str, str], original_filename: str):
        """Salva CSV e Excel normalizados"""
        base_name = Path(original_filename).stem.replace('_params', '')
        
        # CSV
        csv_path = Path('outputs/norm_csv') / f"{base_name}_normalized.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"   💾 CSV: {csv_path.name}")
        
        # Excel
        excel_path = Path('outputs/norm_excel') / f"{base_name}_normalized.xlsx"
        excel_path.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Aba principal
            df.to_excel(writer, sheet_name='Normalized_Parameters', index=False)
            
            # Aba de estatísticas
            stats_data = {
                'Total Parameters': [len(df)],
                'Active Parameters': [df['is_active'].sum()],
                'Inactive Parameters': [(~df['is_active']).sum()],
                'Null Values': [(df['value_type'] == 'null').sum()],
                'Numeric Values': [(df['value_type'] == 'numeric').sum()],
                'Text Values': [(df['value_type'] == 'text').sum()],
                'Boolean Values': [(df['value_type'] == 'boolean').sum()],
                'Multipart Parameters': [df['is_multipart'].sum()],
                'Unique Multipart Groups': [df[df['is_multipart']]['multipart_base'].nunique()],
                'Parameters with Units': [(df['value_unit'] != '').sum()]
            }
            pd.DataFrame(stats_data).to_excel(writer, sheet_name='Statistics', index=False)
            
            # Aba de metadados do relé
            if relay_metadata:
                relay_meta_df = pd.DataFrame([relay_metadata])
                relay_meta_df.to_excel(writer, sheet_name='Relay_Metadata', index=False)
            
            # Aba de grupos multipart (se houver)
            if df['is_multipart'].any():
                multipart_df = df[df['is_multipart']][
                    ['multipart_base', 'multipart_part', 'parameter_code', 
                     'parameter_value', 'value_unit', 'is_active']
                ].sort_values(['multipart_base', 'multipart_part'])
                multipart_df.to_excel(writer, sheet_name='Multipart_Groups', index=False)
            
            # Aba de parâmetros ativos
            if df['is_active'].any():
                active_df = df[df['is_active']][
                    ['parameter_code', 'parameter_description', 'parameter_value', 
                     'value_unit', 'value_type']
                ]
                active_df.to_excel(writer, sheet_name='Active_Parameters', index=False)
        
        logger.info(f"   💾 Excel: {excel_path.name}")
    
    def process_all(self):
        """Processa todos os CSVs de outputs/csv/"""
        logger.info("\n" + "="*100)
        logger.info("🚀 NORMALIZAÇÃO PARA 3FN - INICIANDO")
        logger.info("="*100)
        
        csv_dir = Path('outputs/csv')
        if not csv_dir.exists():
            logger.error(f"❌ Diretório não encontrado: {csv_dir}")
            return
        
        csv_files = sorted([f for f in csv_dir.glob('*.csv') if '_active_setup' not in f.name])
        total = len(csv_files)
        
        logger.info(f"📁 Total de arquivos: {total}")
        
        start_time = datetime.now()
        
        for i, csv_file in enumerate(csv_files, 1):
            logger.info(f"\n{'─'*100}")
            logger.info(f"[{i}/{total}] {csv_file.name}")
            logger.info(f"{'─'*100}")
            
            try:
                df_normalized, relay_metadata = self.normalize_csv(csv_file)
                self.save_normalized(df_normalized, relay_metadata, csv_file.name)
                self.stats['total_files'] += 1
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar {csv_file.name}: {e}")
                self.stats['errors'].append({
                    'file': csv_file.name,
                    'error': str(e)
                })
        
        # Relatório final
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "="*100)
        logger.info("📊 RELATÓRIO FINAL")
        logger.info("="*100)
        logger.info(f"⏱️  Tempo total: {elapsed:.2f}s")
        logger.info(f"✅ Arquivos processados: {self.stats['total_files']}/{total}")
        logger.info(f"📊 Total de linhas:")
        logger.info(f"   Entrada: {self.stats['total_rows_input']}")
        logger.info(f"   Saída: {self.stats['total_rows_output']}")
        logger.info(f"\n🔧 Transformações:")
        logger.info(f"   Metadados removidos: {self.stats['metadata_removed']}")
        logger.info(f"   Multipart expandidos: {self.stats['multipart_expanded']}")
        logger.info(f"   Unidades separadas: {self.stats['units_separated']}")
        logger.info(f"   Booleanos convertidos: {self.stats['booleans_converted']}")
        logger.info(f"   Parâmetros ativos marcados: {self.stats['active_params_marked']}")
        logger.info(f"   ✅ Campos de status corrigidos: {self.stats['status_fields_corrected']}")
        
        if self.stats['errors']:
            logger.warning(f"\n⚠️  Erros encontrados: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.warning(f"   • {error['file']}: {error['error']}")
        
        # Salvar relatório JSON
        report_path = Path('outputs/logs/normalization_3nf_report.json')
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📋 Relatório salvo: {report_path}")
        logger.info("="*100)
        logger.info("✅ NORMALIZAÇÃO CONCLUÍDA!")
        logger.info("="*100 + "\n")


def main():
    """Execução principal"""
    normalizer = Normalizer3NF()
    normalizer.process_all()


if __name__ == '__main__':
    main()

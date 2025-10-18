#!/usr/bin/env python3
"""
Importador de Configurações de Relés para Schema Estruturado
============================================================

Este script importa as configurações JSON geradas pelo enhanced_relay_analyzer
para o schema PostgreSQL especializado em configurações de relés.

Funcionalidades:
- Importa identificação do equipamento
- Importa configuração elétrica (TCs, TPs)
- Importa funções de proteção com ajustes
- Importa configuração de I/Os
- Mantém rastreabilidade e histórico

Autor: ProtecAI System
Data: 2025-10-17
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.extras

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('outputs/logs/importacao_configuracoes.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class RelayConfigImporter:
    """Importador de configurações de relés para PostgreSQL."""
    
    def __init__(self, host='localhost', port=5432, user='protecai', password='protecai', database='protecai_db'):
        """Inicializa o importador com configurações de conexão."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Estabelece conexão com PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                cursor_factory=RealDictCursor
            )
            self.conn.autocommit = False
            self.cursor = self.conn.cursor()
            logger.info("✅ Conexão com PostgreSQL estabelecida")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Fecha conexão com PostgreSQL."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("🔌 Conexão fechada")
    
    def get_or_create_manufacturer(self, name: str) -> int:
        """Obtém ou cria fabricante e retorna o ID."""
        try:
            # Procura fabricante existente
            self.cursor.execute(
                "SELECT id FROM relay_configs.manufacturers WHERE LOWER(name) = LOWER(%s)",
                (name,)
            )
            result = self.cursor.fetchone()
            
            if result:
                return result['id']
            
            # Cria novo fabricante
            self.cursor.execute(
                "INSERT INTO relay_configs.manufacturers (name, created_at) VALUES (%s, %s) RETURNING id",
                (name, datetime.now())
            )
            result = self.cursor.fetchone()
            logger.info(f"📦 Fabricante criado: {name}")
            return result['id']
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar fabricante {name}: {e}")
            raise
    
    def get_or_create_model(self, manufacturer_id: int, name: str, model_type: str = 'protection') -> int:
        """Obtém ou cria modelo e retorna o ID."""
        try:
            # Procura modelo existente
            self.cursor.execute(
                "SELECT id FROM relay_configs.relay_models WHERE manufacturer_id = %s AND LOWER(name) = LOWER(%s)",
                (manufacturer_id, name)
            )
            result = self.cursor.fetchone()
            
            if result:
                return result['id']
            
            # Cria novo modelo
            self.cursor.execute(
                """INSERT INTO relay_configs.relay_models 
                   (manufacturer_id, name, model_type, created_at) 
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (manufacturer_id, name, model_type, datetime.now())
            )
            result = self.cursor.fetchone()
            logger.info(f"🔧 Modelo criado: {name}")
            return result['id']
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar modelo {name}: {e}")
            raise
    
    def import_relay_equipment(self, config: Dict) -> int:
        """Importa dados do equipamento e retorna o ID."""
        try:
            identification = config.get('identification', {})
            
            # Processa fabricante e modelo
            manufacturer_name = identification.get('manufacturer', 'Unknown')
            model_name = identification.get('model', 'Unknown')
            
            manufacturer_id = self.get_or_create_manufacturer(manufacturer_name)
            model_id = self.get_or_create_model(manufacturer_id, model_name)
            
            # Insere equipamento
            self.cursor.execute(
                """INSERT INTO relay_configs.relay_equipment 
                   (model_id, serial_number, tag_reference, plant_reference, bay_position, 
                    software_version, frequency, description, installation_date, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (
                    model_id,
                    identification.get('serial_number'),
                    identification.get('tag_reference'),
                    identification.get('plant_reference'),
                    identification.get('bay_position'),
                    identification.get('software_version'),
                    self._parse_frequency(identification.get('frequency')),
                    identification.get('description'),
                    datetime.now(),  # installation_date
                    datetime.now()   # created_at
                )
            )
            
            equipment_id = self.cursor.fetchone()['id']
            logger.info(f"⚡ Equipamento importado: {identification.get('tag_reference', 'N/A')}")
            return equipment_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao importar equipamento: {e}")
            raise
    
    def import_electrical_config(self, equipment_id: int, config: Dict) -> int:
        """Importa configuração elétrica."""
        try:
            electrical = config.get('electrical', {})
            
            self.cursor.execute(
                """INSERT INTO relay_configs.electrical_configuration 
                   (equipment_id, phase_ct_primary, phase_ct_secondary, neutral_ct_primary, 
                    neutral_ct_secondary, vt_primary, vt_secondary, nvd_vt_primary, 
                    nvd_vt_secondary, vt_connection_mode, nominal_voltage, equipment_load, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (
                    equipment_id,
                    self._parse_current(electrical.get('phase_ct_primary')),
                    self._parse_current(electrical.get('phase_ct_secondary')),
                    self._parse_current(electrical.get('neutral_ct_primary')),
                    self._parse_current(electrical.get('neutral_ct_secondary')),
                    self._parse_voltage(electrical.get('vt_primary')),
                    self._parse_voltage(electrical.get('vt_secondary')),
                    self._parse_voltage(electrical.get('nvd_vt_primary')),
                    self._parse_voltage(electrical.get('nvd_vt_secondary')),
                    electrical.get('vt_connection_mode'),
                    self._parse_voltage(electrical.get('nominal_voltage')),
                    self._parse_power(electrical.get('equipment_load')),
                    datetime.now()
                )
            )
            
            config_id = self.cursor.fetchone()['id']
            logger.info("⚡ Configuração elétrica importada")
            return config_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao importar configuração elétrica: {e}")
            raise
    
    def import_protection_functions(self, equipment_id: int, config: Dict):
        """Importa funções de proteção."""
        try:
            functions = config.get('protection_functions', [])
            
            for func in functions:
                self.cursor.execute(
                    """INSERT INTO relay_configs.protection_functions 
                       (equipment_id, function_name, ansi_code, enabled, current_setting, 
                        time_setting, characteristic, direction, pickup_value, time_delay, 
                        additional_settings_json, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        equipment_id,
                        func.get('function_name'),
                        func.get('code'),
                        func.get('enabled', False),
                        self._parse_current(func.get('current_setting')),
                        self._parse_time(func.get('time_setting')),
                        func.get('characteristic'),
                        func.get('direction'),
                        self._parse_current(func.get('current_setting')),  # pickup_value
                        self._parse_time(func.get('time_setting')),        # time_delay
                        json.dumps(func.get('additional_settings', {})),
                        datetime.now()
                    )
                )
            
            logger.info(f"🛡️  {len(functions)} funções de proteção importadas")
            
        except Exception as e:
            logger.error(f"❌ Erro ao importar funções de proteção: {e}")
            raise
    
    def import_io_configuration(self, equipment_id: int, config: Dict):
        """Importa configuração de I/Os."""
        try:
            io_config = config.get('io_configuration', {})
            
            # Entradas óticas
            opto_inputs = io_config.get('opto_inputs', {})
            for key, value in opto_inputs.items():
                if key.startswith('Opto Input'):
                    channel = key.split()[-1]
                    self.cursor.execute(
                        """INSERT INTO relay_configs.io_configuration 
                           (equipment_id, io_type, channel_number, label, signal_type, 
                            function_assignment, status, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            equipment_id,
                            'digital_input',
                            channel,
                            value,
                            'optical',
                            value,
                            'active',
                            datetime.now()
                        )
                    )
            
            # Saídas a relé
            relay_outputs = io_config.get('relay_outputs', {})
            for key, value in relay_outputs.items():
                if key.startswith('Relay'):
                    channel = key.split()[-1]
                    self.cursor.execute(
                        """INSERT INTO relay_configs.io_configuration 
                           (equipment_id, io_type, channel_number, label, signal_type, 
                            function_assignment, status, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            equipment_id,
                            'relay_output',
                            channel,
                            value,
                            'contact',
                            value,
                            'active',
                            datetime.now()
                        )
                    )
            
            # RTDs
            rtd_inputs = io_config.get('rtd_inputs', {})
            for key, value in rtd_inputs.items():
                if key.startswith('RTD') and not key.endswith(('Set', 'Dly', 'Type', 'Unit')):
                    channel = key.split()[-1]
                    self.cursor.execute(
                        """INSERT INTO relay_configs.io_configuration 
                           (equipment_id, io_type, channel_number, label, signal_type, 
                            function_assignment, status, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            equipment_id,
                            'analog_input',
                            channel,
                            value,
                            'rtd',
                            'temperature',
                            'active',
                            datetime.now()
                        )
                    )
            
            logger.info("🔌 Configuração de I/Os importada")
            
        except Exception as e:
            logger.error(f"❌ Erro ao importar I/Os: {e}")
            raise
    
    def import_configuration_version(self, equipment_id: int, config: Dict, source_file: str) -> int:
        """Registra versão da configuração."""
        try:
            # Limpa valores NaN do JSON antes de salvar
            clean_config = self._clean_nan_values(config)
            
            self.cursor.execute(
                """INSERT INTO relay_configs.configuration_versions 
                   (equipment_id, version_number, source_file, configuration_json, 
                    import_timestamp, created_by, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (
                    equipment_id,
                    '1.0',  # Primeira versão
                    source_file,
                    json.dumps(clean_config),
                    datetime.now(),
                    'ProtecAI System',
                    datetime.now()
                )
            )
            
            version_id = self.cursor.fetchone()['id']
            logger.info(f"📋 Versão da configuração registrada: {source_file}")
            return version_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao registrar versão: {e}")
            raise
    
    def import_configuration_file(self, file_path: str):
        """Importa arquivo de configuração JSON."""
        try:
            logger.info(f"📂 Processando: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Inicia transação
            self.conn.rollback()  # Limpa qualquer transação pendente
            
            # Importa componentes
            equipment_id = self.import_relay_equipment(config)
            self.import_electrical_config(equipment_id, config)
            self.import_protection_functions(equipment_id, config)
            self.import_io_configuration(equipment_id, config)
            version_id = self.import_configuration_version(equipment_id, config, os.path.basename(file_path))
            
            # Confirma transação
            self.conn.commit()
            logger.info(f"✅ Configuração importada com sucesso: {file_path}")
            
            return equipment_id
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Erro ao importar {file_path}: {e}")
            raise
    
    def import_all_configurations(self, directory: str = 'outputs/csv'):
        """Importa todas as configurações JSON do diretório."""
        try:
            config_files = []
            
            # Busca arquivos JSON de configuração
            for file_path in Path(directory).glob('*_config.json'):
                config_files.append(str(file_path))
            
            if not config_files:
                logger.warning(f"⚠️  Nenhum arquivo de configuração encontrado em {directory}")
                return
            
            logger.info(f"🗂️  Encontrados {len(config_files)} arquivo(s) de configuração")
            
            imported_count = 0
            for file_path in config_files:
                try:
                    self.import_configuration_file(file_path)
                    imported_count += 1
                except Exception as e:
                    logger.error(f"❌ Falha ao importar {file_path}: {e}")
                    continue
            
            logger.info(f"🎯 Importação concluída: {imported_count}/{len(config_files)} arquivos")
            
        except Exception as e:
            logger.error(f"❌ Erro no processo de importação: {e}")
            raise
    
    # Métodos auxiliares de parsing
    def _parse_frequency(self, value: str) -> Optional[float]:
        """Extrai frequência em Hz."""
        if not value:
            return None
        try:
            return float(value.replace('Hz', '').strip())
        except:
            return None
    
    def _parse_current(self, value: str) -> Optional[float]:
        """Extrai corrente em A."""
        if not value:
            return None
        try:
            return float(value.replace('A', '').strip())
        except:
            return None
    
    def _parse_voltage(self, value: str) -> Optional[float]:
        """Extrai tensão em V."""
        if not value:
            return None
        try:
            # Remove unidades comuns
            clean_value = value.replace('kV', '000').replace('V', '').strip()
            return float(clean_value)
        except:
            return None
    
    def _parse_time(self, value: str) -> Optional[float]:
        """Extrai tempo em segundos."""
        if not value:
            return None
        try:
            if 'ms' in value:
                return float(value.replace('ms', '').strip()) / 1000
            elif 'min' in value:
                return float(value.replace('min', '').strip()) * 60
            elif 's' in value:
                return float(value.replace('s', '').strip())
            else:
                return float(value)
        except:
            return None
    
    def _parse_power(self, value: str) -> Optional[float]:
        """Extrai potência em W."""
        if not value:
            return None
        try:
            if 'kW' in value:
                return float(value.replace('kW', '').strip()) * 1000
            elif 'MW' in value:
                return float(value.replace('MW', '').strip()) * 1000000
            elif 'W' in value:
                return float(value.replace('W', '').strip())
            else:
                return float(value)
        except:
            return None
    
    def _clean_nan_values(self, obj):
        """Remove valores NaN recursivamente de dicionários e listas."""
        import math
        
        if isinstance(obj, dict):
            return {k: self._clean_nan_values(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_nan_values(item) for item in obj]
        elif isinstance(obj, float) and math.isnan(obj):
            return None
        elif isinstance(obj, str) and obj.lower() in ['nan', 'null']:
            return None
        else:
            return obj

def main():
    """Função principal."""
    logger.info("🚀 Iniciando importação de configurações de relés")
    
    importer = RelayConfigImporter()
    
    try:
        if not importer.connect():
            return False
        
        # Importa todas as configurações
        importer.import_all_configurations()
        
        logger.info("🎉 Importação concluída com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na importação: {e}")
        return False
        
    finally:
        importer.disconnect()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Script para importar dados normalizados (3FN) para PostgreSQL
Importa os CSVs de outputs/norm_csv/ para o schema protec_ai
"""

import sys
import os
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
import logging
import re
try:
    import fitz  # PyMuPDF para ler PDFs
except ImportError:
    fitz = None

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/logs/import_normalized_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuração do banco de dados
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

# Diretórios
NORMALIZED_CSV_DIR = Path("outputs/norm_csv")

class NormalizedDataImporter:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.manufacturer_patterns = {}  # Carregado do banco
        self.stats = {
            'equipments_inserted': 0,
            'equipments_existing': 0,
            'settings_inserted': 0,
            'multipart_groups_inserted': 0,
            'units_created': 0,
            'files_processed': 0,
            'errors': []
        }
        
    def connect(self):
        """Conectar ao banco PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            logger.info("✓ Conectado ao PostgreSQL")
            self.load_manufacturer_patterns()
            return True
        except Exception as e:
            logger.error(f"✗ Erro ao conectar: {e}")
            return False
    
    def load_manufacturer_patterns(self):
        """Carregar padrões de detecção do banco de dados"""
        try:
            self.cursor.execute("""
                SELECT codigo_fabricante, detection_patterns, software_signatures
                FROM protec_ai.fabricantes
                WHERE detection_patterns IS NOT NULL
            """)
            
            for row in self.cursor.fetchall():
                code, patterns, signatures = row
                self.manufacturer_patterns[code] = {
                    'filename': patterns.get('filename', []) if patterns else [],
                    'content': patterns.get('content', []) if patterns else [],
                    'software': signatures or []
                }
            
            logger.info(f"✓ Carregados padrões de {len(self.manufacturer_patterns)} fabricantes")
        except Exception as e:
            logger.warning(f"⚠ Erro ao carregar padrões: {e}")
            self.manufacturer_patterns = {}
    
    def close(self):
        """Fechar conexão"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Conexão fechada")
    
    def get_or_create_unit(self, unit_symbol):
        """Obter ID da unidade ou retornar None"""
        if not unit_symbol or pd.isna(unit_symbol):
            return None
        
        try:
            self.cursor.execute(
                "SELECT id FROM protec_ai.units WHERE unit_symbol = %s",
                (unit_symbol,)
            )
            result = self.cursor.fetchone()
            
            if result:
                return result[0]
            else:
                # Inserir nova unidade
                self.cursor.execute(
                    """INSERT INTO protec_ai.units (unit_symbol, unit_name, unit_category) 
                       VALUES (%s, %s, 'unknown') 
                       ON CONFLICT (unit_symbol) DO NOTHING
                       RETURNING id""",
                    (unit_symbol, unit_symbol)
                )
                self.conn.commit()
                result = self.cursor.fetchone()
                if result:
                    logger.info(f"  → Nova unidade criada: {unit_symbol}")
                    self.stats['units_created'] += 1
                    return result[0]
                return None
        except Exception as e:
            logger.warning(f"  ⚠ Erro ao buscar/criar unidade {unit_symbol}: {e}")
            self.conn.rollback()
            return None
    
    def detect_manufacturer_from_source(self, filename):
        """
        Detectar fabricante lendo o arquivo original (PDF ou .S40)
        USA PADRÕES DO BANCO DINAMICAMENTE
        
        Returns:
            tuple: (manufacturer_code, software_name) ou (None, None)
        """
        # Reconstruir nome do arquivo original (remover _normalized.csv)
        original_name = filename.replace('_normalized.csv', '').replace('_params.csv', '')
        
        # Buscar arquivo original em inputs/
        possible_paths = [
            Path("inputs/pdf") / f"{original_name}.pdf",
            Path("inputs/txt") / f"{original_name}.S40",
            Path("inputs/txt") / f"{original_name}.txt",
        ]
        
        for source_path in possible_paths:
            if not source_path.exists():
                continue
            
            try:
                if source_path.suffix.upper() == '.PDF':
                    # Extrair texto do PDF
                    if not fitz:
                        logger.warning("  ⚠️ PyMuPDF não instalado, pulando detecção por PDF")
                        continue
                    
                    doc = fitz.open(source_path)
                    pages_to_check = [0, len(doc) - 1] if len(doc) > 1 else [0]
                    
                    for page_num in pages_to_check:
                        page = doc[page_num]
                        text = page.get_text()
                        
                        # Buscar usando padrões do banco
                        for mfr_code, mfr_data in self.manufacturer_patterns.items():
                            # Testar software signatures
                            for software in mfr_data['software']:
                                if software in text:
                                    doc.close()
                                    return mfr_code, software
                            
                            # Testar content patterns
                            for pattern in mfr_data['content']:
                                if re.search(pattern, text, re.IGNORECASE):
                                    doc.close()
                                    return mfr_code, pattern
                    
                    doc.close()
                
                elif source_path.suffix.upper() in ['.S40', '.TXT']:
                    # Ler arquivo de texto
                    encodings = ['latin-1', 'cp1252', 'utf-8']
                    for encoding in encodings:
                        try:
                            with open(source_path, 'r', encoding=encoding, errors='ignore') as f:
                                content = f.read(5000)  # Primeiros 5KB
                            
                            # Buscar usando padrões do banco
                            for mfr_code, mfr_data in self.manufacturer_patterns.items():
                                for pattern in mfr_data['content']:
                                    if re.search(pattern, content, re.IGNORECASE):
                                        return mfr_code, pattern
                            break
                        except:
                            continue
            
            except Exception as e:
                logger.warning(f"  ⚠️ Erro ao ler {source_path.name}: {e}")
                continue
        
        return None, None
    
    def detect_model_and_manufacturer(self, filename):
        """
        Detectar modelo e fabricante usando padrões do banco de dados
        
        ESTRATÉGIA ROBUSTA:
        1. Detectar fabricante lendo conteúdo do arquivo original (PRIORIDADE)
        2. Detectar modelo usando padrões regex do banco
        3. Se não achar, tentar detectar modelo e inferir fabricante por padrões do banco
        """
        filename_upper = filename.upper()
        
        # 1. DETECTAR FABRICANTE lendo arquivo original (mais confiável)
        manufacturer_code, software = self.detect_manufacturer_from_source(filename)
        
        # 2. DETECTAR MODELO usando padrões do banco
        model_code = None
        detected_manufacturer = manufacturer_code  # Pode ser sobrescrito
        
        # Se já temos fabricante, usar apenas seus padrões
        if manufacturer_code and manufacturer_code in self.manufacturer_patterns:
            patterns = self.manufacturer_patterns[manufacturer_code]['filename']
            for pattern in patterns:
                if re.search(pattern, filename_upper):
                    # Extrair modelo do match
                    match = re.search(pattern, filename_upper)
                    model_code = match.group(0).replace('_', '').replace(' ', '')
                    break
        
        # Se não encontrou, tentar TODOS os fabricantes
        if not model_code:
            for mfr_code, mfr_data in self.manufacturer_patterns.items():
                for pattern in mfr_data['filename']:
                    if re.search(pattern, filename_upper):
                        match = re.search(pattern, filename_upper)
                        model_code = match.group(0).replace('_', '').replace(' ', '')
                        if not manufacturer_code:  # Inferir fabricante se não tiver
                            detected_manufacturer = mfr_code
                        break
                if model_code:
                    break
        
        # Log resultado
        if detected_manufacturer and model_code:
            if software:
                logger.info(f"  ✓ Detectado: {model_code} | Fabricante: {detected_manufacturer} ({software})")
            else:
                logger.info(f"  ✓ Detectado: {model_code} | Fabricante: {detected_manufacturer} (inferido por padrão)")
            return model_code, detected_manufacturer
        
        logger.warning(f"  ❌ Não foi possível detectar modelo/fabricante para: {filename}")
        return None, None
    
    def get_manufacturer_id(self, manufacturer_code):
        """Obter ID do fabricante pelo código"""
        try:
            self.cursor.execute(
                "SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = %s",
                (manufacturer_code,)
            )
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.warning(f"  ⚠ Erro ao buscar fabricante {manufacturer_code}: {e}")
            return None
    
    def get_or_create_model(self, model_code, manufacturer_id=None):
        """Obter ou criar modelo de relé"""
        if not model_code or pd.isna(model_code):
            return None
        
        try:
            # Buscar modelo existente
            self.cursor.execute(
                "SELECT id FROM protec_ai.relay_models WHERE model_code = %s",
                (model_code,)
            )
            result = self.cursor.fetchone()
            
            if result:
                # SEMPRE atualizar manufacturer_id se fornecido (corrigir associações erradas)
                model_id = result[0]
                if manufacturer_id:
                    self.cursor.execute(
                        """UPDATE protec_ai.relay_models 
                           SET manufacturer_id = %s 
                           WHERE id = %s""",
                        (manufacturer_id, model_id)
                    )
                    self.conn.commit()
                return model_id
            else:
                # Criar novo modelo
                self.cursor.execute(
                    """INSERT INTO protec_ai.relay_models (model_code, model_name, manufacturer_id) 
                       VALUES (%s, %s, %s) 
                       ON CONFLICT (model_code) DO UPDATE 
                       SET manufacturer_id = EXCLUDED.manufacturer_id
                       RETURNING id""",
                    (model_code, model_code, manufacturer_id)
                )
                self.conn.commit()
                result = self.cursor.fetchone()
                if result:
                    logger.info(f"  → Modelo criado: {model_code} (fabricante: {manufacturer_id})")
                    return result[0]
                return None
        except Exception as e:
            logger.warning(f"  ⚠ Erro ao buscar/criar modelo {model_code}: {e}")
            self.conn.rollback()
            return None
    
    def extract_metadata_from_df(self, df, source_file):
        """Extrair metadados do DataFrame"""
        metadata = {
            'source_file': source_file,
            'extraction_date': datetime.now(),
            'sepam_repere': None,
            'sepam_modele': None,
            'sepam_mes': None,
            'sepam_gamme': None,
            'sepam_typemat': None,
            'code_0079': None,
            'code_0081': None,
            'code_010a': None,
            'code_0005': None
        }
        
        # Buscar metadados SEPAM
        for col in ['sepam_repere', 'sepam_modele', 'sepam_mes', 'sepam_gamme', 'sepam_typemat']:
            if col in df.columns:
                values = df[col].dropna().unique()
                if len(values) > 0:
                    metadata[col] = str(values[0])
        
        # Buscar metadados PDF
        for col in ['code_0079', 'code_0081', 'code_010a', 'code_0005']:
            if col in df.columns:
                values = df[col].dropna().unique()
                if len(values) > 0:
                    metadata[col] = str(values[0])
        
        return metadata
    
    def create_equipment(self, source_file, metadata):
        """Criar equipamento no banco"""
        try:
            # Gerar equipment_tag a partir do source_file
            equipment_tag = source_file.replace('_normalized.csv', '').replace('_params.csv', '').replace('_norm.csv', '')
            
            # Detectar modelo e fabricante do nome do arquivo
            model_code, manufacturer_code = self.detect_model_and_manufacturer(source_file)
            
            # Obter IDs do modelo e fabricante
            relay_model_id = None
            if model_code and manufacturer_code:
                manufacturer_id = self.get_manufacturer_id(manufacturer_code)
                relay_model_id = self.get_or_create_model(model_code, manufacturer_id)
                logger.info(f"  → Modelo detectado: {model_code} | Fabricante: {manufacturer_code}")
            else:
                logger.warning(f"  ⚠ Não foi possível detectar modelo/fabricante para: {source_file}")
            
            # Verificar se já existe
            self.cursor.execute(
                "SELECT id FROM protec_ai.relay_equipment WHERE equipment_tag = %s",
                (equipment_tag,)
            )
            result = self.cursor.fetchone()
            
            if result:
                # SEMPRE atualizar relay_model_id (corrigir associações erradas)
                equipment_id = result[0]
                if relay_model_id:
                    self.cursor.execute(
                        """UPDATE protec_ai.relay_equipment 
                           SET relay_model_id = %s 
                           WHERE id = %s""",
                        (relay_model_id, equipment_id)
                    )
                    self.conn.commit()
                logger.info(f"  → Equipamento já existe: {equipment_tag} (atualizado relay_model_id)")
                self.stats['equipments_existing'] += 1
                return equipment_id
            
            # Inserir novo equipamento com relay_model_id
            self.cursor.execute(
                """INSERT INTO protec_ai.relay_equipment 
                   (equipment_tag, relay_model_id, source_file, extraction_date,
                    sepam_repere, sepam_modele, sepam_mes, sepam_gamme, sepam_typemat,
                    code_0079, code_0081, code_010a, code_0005, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                   RETURNING id""",
                (equipment_tag, relay_model_id, metadata['source_file'], metadata['extraction_date'],
                 metadata['sepam_repere'], metadata['sepam_modele'], metadata['sepam_mes'],
                 metadata['sepam_gamme'], metadata['sepam_typemat'],
                 metadata['code_0079'], metadata['code_0081'], metadata['code_010a'],
                 metadata['code_0005'])
            )
            self.conn.commit()
            
            equipment_id = self.cursor.fetchone()[0]
            self.stats['equipments_inserted'] += 1
            logger.info(f"  ✓ Equipamento criado: {equipment_tag} (ID: {equipment_id})")
            return equipment_id
            
        except Exception as e:
            logger.error(f"  ✗ Erro ao criar equipamento: {e}")
            self.conn.rollback()
            return None
    
    def import_settings_batch(self, equipment_id, df):
        """Importar settings em lote para um equipamento"""
        settings_data = []
        
        for _, row in df.iterrows():
            # Obter unit_id
            unit_id = None
            if 'value_unit' in row and pd.notna(row['value_unit']):
                unit_id = self.get_or_create_unit(row['value_unit'])
            
            # Preparar valores
            param_code = row.get('parameter_code', '')
            param_desc = row.get('parameter_description', '')
            param_value = row.get('parameter_value', '')
            value_type = row.get('value_type', 'text')
            is_active = bool(row.get('is_active', False))
            is_multipart = bool(row.get('is_multipart', False))
            multipart_base = row.get('multipart_base', None) if is_multipart else None
            multipart_part = int(row.get('multipart_part', 0)) if is_multipart else 0
            
            # Converter valor para numérico se possível
            set_value = None
            set_value_text = str(param_value) if pd.notna(param_value) else None
            
            if value_type == 'numeric':
                try:
                    set_value = float(param_value)
                except:
                    pass
            
            settings_data.append((
                equipment_id, None,  # function_id será NULL por enquanto
                param_desc, param_code, set_value, set_value_text,
                unit_id, is_active, is_multipart, multipart_base, multipart_part,
                value_type
            ))
        
        # Inserir em lote
        if settings_data:
            execute_batch(
                self.cursor,
                """INSERT INTO protec_ai.relay_settings 
                   (equipment_id, function_id, parameter_name, parameter_code, 
                    set_value, set_value_text, unit_id, is_active, is_multipart,
                    multipart_base, multipart_part, value_type)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                settings_data
            )
            self.conn.commit()
            self.stats['settings_inserted'] += len(settings_data)
            logger.info(f"  ✓ {len(settings_data)} settings inseridos")
    
    def create_multipart_groups(self, equipment_id, df):
        """Criar grupos multipart"""
        if 'is_multipart' not in df.columns:
            return
        
        multipart_df = df[df['is_multipart'] == True]
        if multipart_df.empty:
            return
        
        # Agrupar por multipart_base
        groups = multipart_df.groupby('multipart_base')
        
        for base, group in groups:
            total_parts = int(group['multipart_part'].max())  # Converter numpy.int64 para int
            
            try:
                self.cursor.execute(
                    """INSERT INTO protec_ai.multipart_groups 
                       (equipment_id, multipart_base, total_parts)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (equipment_id, multipart_base) DO NOTHING""",
                    (equipment_id, base, total_parts)
                )
                self.conn.commit()
                self.stats['multipart_groups_inserted'] += 1
            except Exception as e:
                logger.warning(f"  ⚠ Erro ao criar multipart group {base}: {e}")
                self.conn.rollback()
    
    def process_file(self, csv_path):
        """Processar um arquivo CSV normalizado"""
        try:
            logger.info(f"\n📄 Processando: {csv_path.name}")
            
            # Ler CSV
            df = pd.read_csv(csv_path)
            logger.info(f"  → {len(df)} linhas lidas")
            
            # Extrair metadados
            metadata = self.extract_metadata_from_df(df, csv_path.name)
            
            # Criar equipamento
            equipment_id = self.create_equipment(csv_path.name, metadata)
            if not equipment_id:
                raise Exception("Falha ao criar equipamento")
            
            # Importar settings
            self.import_settings_batch(equipment_id, df)
            
            # Criar grupos multipart
            self.create_multipart_groups(equipment_id, df)
            
            self.stats['files_processed'] += 1
            logger.info(f"  ✅ Arquivo processado com sucesso!")
            
        except Exception as e:
            error_msg = f"Erro ao processar {csv_path.name}: {e}"
            logger.error(f"  ✗ {error_msg}")
            self.stats['errors'].append(error_msg)
    
    def run(self):
        """Executar importação completa"""
        logger.info("="*80)
        logger.info("IMPORTAÇÃO DE DADOS NORMALIZADOS PARA POSTGRESQL")
        logger.info("="*80)
        
        if not self.connect():
            return False
        
        # Listar arquivos CSV
        csv_files = sorted(NORMALIZED_CSV_DIR.glob("*_normalized.csv"))
        logger.info(f"\n📁 {len(csv_files)} arquivos CSV encontrados em {NORMALIZED_CSV_DIR}")
        
        if not csv_files:
            logger.error("✗ Nenhum arquivo CSV normalizado encontrado!")
            return False
        
        # Processar cada arquivo
        for i, csv_path in enumerate(csv_files, 1):
            logger.info(f"\n[{i}/{len(csv_files)}] Processando...")
            self.process_file(csv_path)
        
        # Relatório final
        self.print_summary()
        self.close()
        
        return len(self.stats['errors']) == 0
    
    def print_summary(self):
        """Imprimir relatório final"""
        logger.info("\n" + "="*80)
        logger.info("RELATÓRIO FINAL DE IMPORTAÇÃO")
        logger.info("="*80)
        logger.info(f"Arquivos processados:     {self.stats['files_processed']}")
        logger.info(f"Equipamentos novos:       {self.stats['equipments_inserted']}")
        logger.info(f"Equipamentos existentes:  {self.stats['equipments_existing']}")
        logger.info(f"Settings inseridos:       {self.stats['settings_inserted']}")
        logger.info(f"Grupos multipart criados: {self.stats['multipart_groups_inserted']}")
        logger.info(f"Unidades criadas:         {self.stats['units_created']}")
        logger.info(f"Erros:                    {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            logger.info("\n⚠️  ERROS ENCONTRADOS:")
            for error in self.stats['errors']:
                logger.info(f"  - {error}")
        else:
            logger.info("\n✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        
        logger.info("="*80)

def main():
    importer = NormalizedDataImporter()
    success = importer.run()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

"""
🔧 CORREÇÃO ROBUSTA: Fabricantes e Modelos de Relés
===================================================

OBJETIVO:
- Re-escanear os 50 arquivos processados
- Detectar fabricante correto via rodapé PDF
- Extrair modelo real do relé
- Atualizar banco de dados
- Gerar log detalhado de mudanças

PRINCÍPIOS:
✅ ROBUSTO - Detecta padrões automaticamente
✅ FLEXÍVEL - Adapta-se a novos fabricantes/modelos
✅ 100% REAL - Sem mocks ou dados fictícios
✅ AUDITÁVEL - Log completo de todas as mudanças

Data: 01/11/2025
"""

import os
import sys
import re
import PyPDF2
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import psycopg2
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/logs/manufacturer_correction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurações do banco
DB_CONFIG = {
    'host': 'localhost',
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai',
    'port': 5432
}

# 🔍 PADRÕES DE DETECÇÃO ROBUSTA
# =================================

# 1️⃣ Padrões de RODAPÉ (PDFs)
PDF_FOOTER_PATTERNS = {
    'MICOM S1 Agile': ('GE', 'General Electric'),
    'MiCOM': ('GE', 'General Electric'),
    'Easergy Studio': ('SCHN', 'Schneider Electric'),
    'EcoStruxure': ('SCHN', 'Schneider Electric'),
    'SEL': ('SEL', 'SEL (Schweitzer Engineering Laboratories)'),
    'Schweitzer': ('SEL', 'SEL (Schweitzer Engineering Laboratories)'),
    'ABB': ('ABB', 'ABB Ltd'),
    'REF': ('ABB', 'ABB Ltd'),
    'Siemens': ('SIEM', 'Siemens AG'),
    'SIPROTEC': ('SIEM', 'Siemens AG')
}

# 2️⃣ Padrões de CABEÇALHO (TXTs e S40)
TXT_HEADER_PATTERNS = {
    '[Sepam_Caracteristiques]': ('SCHN', 'Schneider Electric', 'SEPAM'),  # Arquivos .S40
    'Sepam': ('SCHN', 'Schneider Electric', 'SEPAM'),
    'application=S': ('SCHN', 'Schneider Electric', 'SEPAM'),  # Ex: application=S40
    'MiCOM': ('GE', 'General Electric', 'MiCOM P Series'),
    'MULTILIN': ('GE', 'General Electric', 'GE Multilin'),
    'SEL-': ('SEL', 'SEL (Schweitzer Engineering Laboratories)', 'SEL Protection Relay'),
    'SIPROTEC': ('SIEM', 'Siemens AG', 'SIPROTEC'),
    'REF6': ('ABB', 'ABB Ltd', 'ABB REF Series')
}

# 3️⃣ Padrões de EXTENSÃO DE ARQUIVO
FILE_EXTENSION_PATTERNS = {
    '.S40': ('SCHN', 'Schneider Electric', 'SEPAM S40'),
    '.S41': ('SCHN', 'Schneider Electric', 'SEPAM S41'),
    '.S80': ('SCHN', 'Schneider Electric', 'SEPAM S80')
}

# Padrões de modelos conhecidos
MODEL_PATTERNS = {
    # Schneider Electric
    r'SEPAM\s*S\d+': 'SEPAM Series',
    r'P\d{3}': 'MiCOM P Series',
    
    # GE
    r'SR\s*\d+': 'GE SR Series',
    r'F\d{3}': 'GE Multilin F Series',
    r'D\d{2}': 'GE Multilin D Series',
    
    # SEL
    r'SEL-\d{3,4}': 'SEL Protection Relay',
    
    # ABB
    r'REF\d{3}': 'ABB REF Series',
    r'REM\d{3}': 'ABB REM Series',
    
    # Siemens
    r'7S[A-Z]\d{2}': 'SIPROTEC 7S Series',
    r'7U[A-Z]\d{2}': 'SIPROTEC 7U Series'
}


class ManufacturerDetector:
    """Detector robusto de fabricantes e modelos"""
    
    def __init__(self):
        self.stats = {
            'files_processed': 0,
            'manufacturers_detected': {},
            'models_detected': {},
            'updates_made': 0,
            'errors': []
        }
    
    def detect_from_pdf(self, pdf_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Detecta fabricante e modelo de um PDF
        
        Returns:
            (manufacturer_code, manufacturer_name, model_name)
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extrair texto de todas as páginas
                full_text = ""
                for page in pdf_reader.pages:
                    full_text += page.extract_text()
                
                # Detectar fabricante pelo rodapé
                manufacturer_code, manufacturer_name = self._detect_manufacturer(full_text)
                
                # Detectar modelo
                model_name = self._detect_model(full_text, manufacturer_code)
                
                return manufacturer_code, manufacturer_name, model_name
                
        except Exception as e:
            logger.error(f"Erro ao processar PDF {pdf_path}: {e}")
            self.stats['errors'].append(f"{pdf_path}: {str(e)}")
            return None, None, None
    
    def detect_from_txt(self, txt_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Detecta fabricante e modelo de um TXT/S40 (ROBUSTO E FLEXÍVEL)
        
        Estratégia de detecção:
        1. PRIORIDADE 1: Extensão do arquivo (.S40 → SEPAM)
        2. PRIORIDADE 2: Cabeçalho específico ([Sepam_Caracteristiques])
        3. PRIORIDADE 3: Padrões no conteúdo
        4. PRIORIDADE 4: Metadados no arquivo (repere=, application=)
        
        Returns:
            (manufacturer_code, manufacturer_name, model_name)
        """
        try:
            file_path = Path(txt_path)
            file_ext = file_path.suffix.upper()
            
            # 🔍 PASSO 1: Detectar por EXTENSÃO
            if file_ext in FILE_EXTENSION_PATTERNS:
                code, name, model = FILE_EXTENSION_PATTERNS[file_ext]
                logger.info(f"✅ Fabricante detectado pela extensão {file_ext}: {name}")
                self.stats['manufacturers_detected'][name] = self.stats['manufacturers_detected'].get(name, 0) + 1
                
                # Tentar refinar o modelo lendo o arquivo
                with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_lines = ''.join(f.readlines()[:50])
                    
                    # Buscar application=S40, S41, S80, etc.
                    app_match = re.search(r'application=([S]\d{2})', first_lines)
                    if app_match:
                        model = f'SEPAM {app_match.group(1)}'
                        logger.info(f"✅ Modelo refinado: {model}")
                    
                    # Buscar repere= para pegar o tag do equipamento
                    repere_match = re.search(r'repere=([^\s\n]+)', first_lines)
                    if repere_match:
                        logger.info(f"📋 Tag do equipamento: {repere_match.group(1)}")
                
                self.stats['models_detected'][model] = self.stats['models_detected'].get(model, 0) + 1
                return code, name, model
            
            # 🔍 PASSO 2: Ler conteúdo para detecção por CABEÇALHO
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read()
                first_1000_chars = text[:1000]  # Primeiros 1000 caracteres
                
                # Detectar por padrões de cabeçalho
                for pattern, (code, name, default_model) in TXT_HEADER_PATTERNS.items():
                    if pattern in first_1000_chars:
                        logger.info(f"✅ Fabricante detectado pelo cabeçalho '{pattern}': {name}")
                        self.stats['manufacturers_detected'][name] = self.stats['manufacturers_detected'].get(name, 0) + 1
                        
                        # Detectar modelo
                        model_name = self._detect_model_from_txt_content(text, code, default_model)
                        
                        return code, name, model_name
                
                # 🔍 PASSO 3: Busca genérica no conteúdo completo
                manufacturer_code, manufacturer_name = self._detect_manufacturer_generic(text)
                model_name = self._detect_model(text, manufacturer_code)
                
                return manufacturer_code, manufacturer_name, model_name
                
        except Exception as e:
            logger.error(f"Erro ao processar TXT {txt_path}: {e}")
            self.stats['errors'].append(f"{txt_path}: {str(e)}")
            return None, None, None
    
    def _detect_model_from_txt_content(self, text: str, manufacturer_code: str, default_model: str) -> str:
        """
        Detecta modelo específico do conteúdo de arquivo TXT
        
        Para SEPAM: busca application=S40, S41, S80, etc.
        Para MiCOM: busca códigos P1xx, P2xx, P4xx, P9xx
        """
        
        # Para Schneider SEPAM: buscar application=
        if manufacturer_code == 'SCHN':
            app_match = re.search(r'application=([S]\d{2})', text)
            if app_match:
                model = f'SEPAM {app_match.group(1)}'
                logger.info(f"✅ Modelo SEPAM detectado: {model}")
                self.stats['models_detected'][model] = self.stats['models_detected'].get(model, 0) + 1
                return model
            
            # Buscar modele=
            modele_match = re.search(r'modele=(\d+)', text)
            if modele_match:
                model_code = modele_match.group(1)
                model = f'SEPAM Model {model_code}'
                logger.info(f"✅ Modelo SEPAM por código: {model}")
                self.stats['models_detected'][model] = self.stats['models_detected'].get(model, 0) + 1
                return model
        
        # Para GE MiCOM: buscar códigos P
        elif manufacturer_code == 'GE':
            p_series_match = re.search(r'P(\d{3})', text)
            if p_series_match:
                model = f'P{p_series_match.group(1)}'
                logger.info(f"✅ Modelo MiCOM detectado: {model}")
                self.stats['models_detected'][model] = self.stats['models_detected'].get(model, 0) + 1
                return model
        
        # Retornar modelo padrão
        logger.info(f"📋 Usando modelo padrão: {default_model}")
        self.stats['models_detected'][default_model] = self.stats['models_detected'].get(default_model, 0) + 1
        return default_model
    
    def detect_from_csv(self, csv_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Detecta fabricante e modelo de um CSV (baseado no nome do arquivo)
        
        Returns:
            (manufacturer_code, manufacturer_name, model_name)
        """
        try:
            # Para CSV, vamos usar heurísticas do nome do arquivo
            filename = os.path.basename(csv_path).upper()
            
            # Tentar detectar pelo nome do arquivo
            for pattern, (code, name) in PDF_FOOTER_PATTERNS.items():
                if pattern.upper() in filename:
                    model = self._extract_model_from_filename(filename)
                    return code, name, model
            
            # Se não detectou, retornar padrão genérico
            return 'UNKN', 'Unknown Manufacturer', 'Unknown Model'
            
        except Exception as e:
            logger.error(f"Erro ao processar CSV {csv_path}: {e}")
            self.stats['errors'].append(f"{csv_path}: {str(e)}")
            return None, None, None
    
    def _detect_manufacturer(self, text: str) -> Tuple[str, str]:
        """
        Detecta fabricante baseado em padrões de RODAPÉ (PDFs)
        
        NOTA: Este método é usado APENAS para PDFs.
        Para TXTs, usar detect_from_txt() que tem lógica específica.
        """
        
        # Normalizar texto
        text_upper = text.upper()
        
        # Buscar padrões de rodapé (PDFs)
        for pattern, (code, name) in PDF_FOOTER_PATTERNS.items():
            if pattern.upper() in text_upper:
                logger.info(f"✅ Fabricante detectado (PDF): {name} (padrão: {pattern})")
                self.stats['manufacturers_detected'][name] = self.stats['manufacturers_detected'].get(name, 0) + 1
                return code, name
        
        # Padrão: Unknown (não deve acontecer em produção)
        logger.warning("⚠️ Fabricante não detectado em PDF")
        return 'UNKN', 'Unknown Manufacturer'
    
    def _detect_manufacturer_generic(self, text: str) -> Tuple[str, str]:
        """
        Detecta fabricante de forma genérica (fallback para casos não cobertos)
        """
        
        text_upper = text.upper()
        
        # Tentar todos os padrões conhecidos
        all_patterns = {**PDF_FOOTER_PATTERNS, **{k: (v[0], v[1]) for k, v in TXT_HEADER_PATTERNS.items()}}
        
        for pattern, (code, name, *_) in all_patterns.items():
            if pattern.upper() in text_upper:
                logger.info(f"✅ Fabricante detectado (genérico): {name}")
                self.stats['manufacturers_detected'][name] = self.stats['manufacturers_detected'].get(name, 0) + 1
                return code, name
        
        logger.warning("⚠️ Fabricante não identificado")
        return 'UNKN', 'Unknown Manufacturer'
    
    def _detect_model(self, text: str, manufacturer_code: str) -> str:
        """Detecta modelo do relé baseado em padrões"""
        
        # Normalizar texto
        text_upper = text.upper()
        
        # Buscar padrões de modelos
        for pattern, model_family in MODEL_PATTERNS.items():
            matches = re.findall(pattern, text_upper)
            if matches:
                # Pegar o primeiro match e limpar
                model = matches[0].strip()
                logger.info(f"✅ Modelo detectado: {model} (família: {model_family})")
                self.stats['models_detected'][model] = self.stats['models_detected'].get(model, 0) + 1
                return model
        
        # Tentar extrair do cabeçalho (primeiras 500 palavras)
        header = ' '.join(text.split()[:500])
        
        # Padrões genéricos
        generic_patterns = [
            r'[A-Z]{2,5}[\-\s]?\d{2,4}',  # Ex: SEPAM-S40, P122, SR489
            r'REL[ÉE]\s+[A-Z0-9\-]+',      # Ex: RELÉ P122
        ]
        
        for pattern in generic_patterns:
            matches = re.findall(pattern, header)
            if matches:
                model = matches[0].strip()
                logger.info(f"📋 Modelo extraído (genérico): {model}")
                return model
        
        # Padrão baseado no fabricante
        default_models = {
            'SCHN': 'Schneider Relay',
            'GE': 'GE Multilin Relay',
            'SEL': 'SEL Relay',
            'ABB': 'ABB Protection Relay',
            'SIEM': 'SIPROTEC Relay'
        }
        
        return default_models.get(manufacturer_code, 'Unknown Model')
    
    def _extract_model_from_filename(self, filename: str) -> str:
        """Extrai modelo do nome do arquivo"""
        
        # Remover extensão
        name = filename.replace('.CSV', '').replace('.PDF', '').replace('.TXT', '')
        
        # Buscar padrões
        for pattern in MODEL_PATTERNS.keys():
            match = re.search(pattern, name)
            if match:
                return match.group(0)
        
        return 'Model from CSV'


class DatabaseUpdater:
    """Atualiza banco de dados com informações corrigidas"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.changes_log = []
    
    def connect(self):
        """Conecta ao banco de dados"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            logger.info("✅ Conectado ao banco de dados")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao banco: {e}")
            raise
    
    def ensure_manufacturer_exists(self, code: str, name: str, country: str = None) -> int:
        """Garante que o fabricante existe no banco"""
        
        # Buscar fabricante
        self.cursor.execute("""
            SELECT id FROM protec_ai.fabricantes 
            WHERE codigo_fabricante = %s OR nome_completo = %s
        """, (code, name))
        
        result = self.cursor.fetchone()
        if result:
            return result[0]
        
        # Criar novo fabricante
        if not country:
            country_map = {
                'SCHN': 'França',
                'GE': 'Estados Unidos',
                'SEL': 'Estados Unidos',
                'ABB': 'Suíça',
                'SIEM': 'Alemanha'
            }
            country = country_map.get(code, 'Unknown')
        
        self.cursor.execute("""
            INSERT INTO protec_ai.fabricantes 
            (codigo_fabricante, nome_completo, pais_origem, ativo, created_at, updated_at)
            VALUES (%s, %s, %s, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """, (code, name, country))
        
        manufacturer_id = self.cursor.fetchone()[0]
        self.conn.commit()
        
        logger.info(f"✅ Novo fabricante criado: {name} (ID: {manufacturer_id})")
        self.changes_log.append(f"Novo fabricante: {name}")
        
        return manufacturer_id
    
    def ensure_model_exists(self, manufacturer_id: int, model_name: str, model_code: str = None) -> int:
        """Garante que o modelo existe no banco"""
        
        if not model_code:
            model_code = model_name[:20]  # Usar primeiros 20 chars como código
        
        # Buscar modelo
        self.cursor.execute("""
            SELECT id FROM protec_ai.relay_models 
            WHERE manufacturer_id = %s AND model_name = %s
        """, (manufacturer_id, model_name))
        
        result = self.cursor.fetchone()
        if result:
            return result[0]
        
        # Criar novo modelo
        self.cursor.execute("""
            INSERT INTO protec_ai.relay_models 
            (model_code, manufacturer_id, model_name, technology, created_at, updated_at)
            VALUES (%s, %s, %s, 'Digital', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (model_code) DO UPDATE 
            SET 
                manufacturer_id = EXCLUDED.manufacturer_id,
                model_name = EXCLUDED.model_name,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (model_code, manufacturer_id, model_name))
        
        model_id = self.cursor.fetchone()[0]
        self.conn.commit()
        
        logger.info(f"✅ Modelo garantido: {model_name} (ID: {model_id})")
        self.changes_log.append(f"Modelo garantido: {model_name}")
        
        return model_id
    
    def update_equipment(self, equipment_id: int, new_model_id: int, old_model_id: int):
        """Atualiza equipamento com novo modelo"""
        
        if new_model_id == old_model_id:
            return  # Sem mudanças
        
        self.cursor.execute("""
            UPDATE protec_ai.relay_equipment
            SET relay_model_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_model_id, equipment_id))
        
        self.conn.commit()
        
        logger.info(f"✅ Equipamento {equipment_id} atualizado: modelo {old_model_id} → {new_model_id}")
        self.changes_log.append(f"Equipment {equipment_id}: model {old_model_id} → {new_model_id}")
    
    def get_all_equipment_with_files(self) -> List[Dict]:
        """Busca todos os equipamentos com seus arquivos de origem"""
        
        self.cursor.execute("""
            SELECT 
                re.id,
                re.equipment_tag,
                re.relay_model_id,
                re.position_description,
                rm.model_name as current_model,
                f.nome_completo as current_manufacturer
            FROM protec_ai.relay_equipment re
            JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
            JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
            ORDER BY re.id
        """)
        
        rows = self.cursor.fetchall()
        
        equipment_list = []
        for row in rows:
            # Extrair nome do arquivo da position_description
            position_description = row[3]
            filename = None
            
            if position_description and 'Processado de' in position_description:
                filename = position_description.split('Processado de')[1].strip()
            
            equipment_list.append({
                'id': row[0],
                'tag': row[1],
                'model_id': row[2],
                'description': position_description,
                'current_model': row[4],
                'current_manufacturer': row[5],
                'filename': filename
            })
        
        return equipment_list
    
    def close(self):
        """Fecha conexão com banco"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("✅ Conexão com banco fechada")


def find_source_file(filename: str, base_path: Path) -> Optional[Path]:
    """
    Encontra arquivo de origem baseado no nome (ROBUSTO E FLEXÍVEL)
    
    Busca em múltiplos formatos e pastas:
    - PDFs (GE e Schneider)
    - TXTs/S40 (Schneider SEPAM)
    - CSVs processados
    - XLSX futuros
    """
    
    if not filename:
        return None
    
    # Limpar nome do arquivo e remover sufixo _params.csv
    clean_name = filename.strip().replace('_params.csv', '').replace('.csv', '')
    
    # 🔍 BUSCA INTELIGENTE: Tentar múltiplas extensões
    search_combinations = [
        # PDFs (prioridade - GE MiCOM com rodapé)
        (base_path / 'inputs' / 'pdf', f"{clean_name}.pdf"),
        
        # TXTs e S40 (Schneider SEPAM com cabeçalho)
        (base_path / 'inputs' / 'txt', f"{clean_name}.txt"),
        (base_path / 'inputs' / 'txt', f"{clean_name}.S40"),
        (base_path / 'inputs' / 'txt', f"{clean_name}.S41"),
        (base_path / 'inputs' / 'txt', f"{clean_name}.S80"),
        
        # CSVs processados (outputs e inputs)
        (base_path / 'outputs' / 'csv', filename),
        (base_path / 'inputs' / 'csv', filename),
        
        # XLSX futuros
        (base_path / 'inputs' / 'xlsx', f"{clean_name}.xlsx"),
    ]
    
    for search_dir, file_to_search in search_combinations:
        if not search_dir.exists():
            continue
        
        # Buscar arquivo exato
        file_path = search_dir / file_to_search
        if file_path.exists():
            logger.debug(f"   ✅ Arquivo encontrado: {file_path}")
            return file_path
        
        # Buscar similar (sem considerar case e com wildcards)
        for file in search_dir.iterdir():
            if file.name.lower() == file_to_search.lower():
                logger.debug(f"   ✅ Arquivo encontrado (case insensitive): {file}")
                return file
            
            # Tentar match aproximado (para casos como 00-MF-12 vs 00-MF-12_params.csv)
            if clean_name.lower() in file.name.lower():
                logger.debug(f"   ✅ Arquivo encontrado (match parcial): {file}")
                return file
    
    logger.debug(f"   ⚠️ Arquivo não encontrado: {clean_name}")
    return None


def main():
    """Função principal de correção"""
    
    logger.info("="*80)
    logger.info("🔧 INICIANDO CORREÇÃO DE FABRICANTES E MODELOS")
    logger.info("="*80)
    
    # Definir paths
    base_path = Path(__file__).parent.parent
    
    # Inicializar componentes
    detector = ManufacturerDetector()
    db_updater = DatabaseUpdater()
    
    try:
        # Conectar ao banco
        db_updater.connect()
        
        # Buscar todos os equipamentos
        logger.info("\n📋 Buscando equipamentos no banco...")
        equipment_list = db_updater.get_all_equipment_with_files()
        logger.info(f"✅ Encontrados {len(equipment_list)} equipamentos")
        
        # Processar cada equipamento
        updates_count = 0
        errors_count = 0
        
        for idx, equipment in enumerate(equipment_list, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"[{idx}/{len(equipment_list)}] Processando: {equipment['tag']}")
            logger.info(f"  Arquivo: {equipment['filename']}")
            logger.info(f"  Modelo atual: {equipment['current_model']}")
            logger.info(f"  Fabricante atual: {equipment['current_manufacturer']}")
            
            # Encontrar arquivo de origem
            source_file = find_source_file(equipment['filename'], base_path)
            
            if not source_file:
                logger.warning(f"⚠️ Arquivo de origem não encontrado: {equipment['filename']}")
                errors_count += 1
                continue
            
            logger.info(f"  Arquivo encontrado: {source_file}")
            
            # Detectar fabricante e modelo baseado na EXTENSÃO DO ARQUIVO
            manufacturer_code = None
            manufacturer_name = None
            model_name = None
            
            file_extension = source_file.suffix.lower()
            
            if file_extension == '.pdf':
                manufacturer_code, manufacturer_name, model_name = detector.detect_from_pdf(str(source_file))
            elif file_extension in ['.txt', '.s40', '.s41', '.s80']:
                # Arquivos de texto: TXT genérico ou S40/S41/S80 (SEPAM)
                manufacturer_code, manufacturer_name, model_name = detector.detect_from_txt(str(source_file))
            elif file_extension == '.csv':
                manufacturer_code, manufacturer_name, model_name = detector.detect_from_csv(str(source_file))
            else:
                logger.warning(f"⚠️ Extensão desconhecida: {file_extension}")
                errors_count += 1
                continue
            
            if not all([manufacturer_code, manufacturer_name, model_name]):
                logger.warning(f"⚠️ Não foi possível detectar informações do arquivo")
                errors_count += 1
                continue
            
            logger.info(f"  ✅ Detectado:")
            logger.info(f"    Fabricante: {manufacturer_name}")
            logger.info(f"    Modelo: {model_name}")
            
            # Garantir que fabricante existe
            manufacturer_id = db_updater.ensure_manufacturer_exists(manufacturer_code, manufacturer_name)
            
            # Garantir que modelo existe
            new_model_id = db_updater.ensure_model_exists(manufacturer_id, model_name)
            
            # Atualizar equipamento se necessário
            if new_model_id != equipment['model_id']:
                db_updater.update_equipment(equipment['id'], new_model_id, equipment['model_id'])
                updates_count += 1
                logger.info(f"  ✅ Equipamento atualizado!")
            else:
                logger.info(f"  ℹ️ Equipamento já estava correto")
            
            detector.stats['files_processed'] += 1
        
        # Relatório final
        logger.info("\n" + "="*80)
        logger.info("📊 RELATÓRIO FINAL")
        logger.info("="*80)
        logger.info(f"Arquivos processados: {detector.stats['files_processed']}")
        logger.info(f"Atualizações realizadas: {updates_count}")
        logger.info(f"Erros encontrados: {errors_count}")
        
        logger.info("\n📈 Fabricantes detectados:")
        for mfg, count in detector.stats['manufacturers_detected'].items():
            logger.info(f"  - {mfg}: {count} arquivos")
        
        logger.info("\n🔧 Modelos detectados:")
        for model, count in detector.stats['models_detected'].items():
            logger.info(f"  - {model}: {count} arquivos")
        
        if detector.stats['errors']:
            logger.info("\n❌ Erros:")
            for error in detector.stats['errors']:
                logger.info(f"  - {error}")
        
        logger.info("\n✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
        
    except Exception as e:
        logger.error(f"\n❌ ERRO FATAL: {e}")
        raise
    
    finally:
        db_updater.close()


if __name__ == '__main__':
    main()

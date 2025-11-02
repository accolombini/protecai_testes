"""
Extract Substations and Bays - Normalização 3FN
================================================

Extrai subestações e bays dos nomes de arquivos e CSVs,
estabelecendo integridade referencial completa.

CAUSA RAIZ: Dados importados sem estrutura 3FN (substations/bays)
SOLUÇÃO: Análise de padrões + extração + normalização
"""

import re
import os
import csv
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch

@dataclass
class BayInfo:
    """Informações extraídas do bay"""
    code: str              # Ex: "00-MF-12", "52-MF-02A"
    substation_code: str   # Ex: "00", "52"
    device_type: str       # Ex: "MF", "MP", "MK"
    position: str          # Ex: "12", "02A"
    voltage_level: Optional[str] = None
    description: Optional[str] = None

@dataclass
class SubstationInfo:
    """Informações extraídas da subestação"""
    code: str
    name: str
    voltage_level: Optional[str] = None

class FilePatternAnalyzer:
    """
    Analisa padrões de nomes de arquivos para extrair metadados
    """
    
    # Padrões de nome de arquivo
    PATTERNS = {
        's40': r'(\d+)-([A-Z]+)-(\d+[A-Z]*)_',           # 00-MF-12_2016-03-31.S40
        'pdf_p122': r'P122\s+(\d+)-([A-Z]+)-(\d+[A-Z]*)', # P122 52-MF-02A
        'pdf_p220': r'P220\s+(\d+)-([A-Z]+)-(\d+[A-Z]*)', # P220 52-MP-01A
        'pdf_p143': r'P143\s+(\d+)-([A-Z]+)-(\d+[A-Z]*)', # P143 204-MF-03B
        'pdf_p241': r'P241_(\d+)-([A-Z]+)-(\d+[A-Z]*)',   # P241_52-MP-20
        'pdf_p922': r'P922\s+(\d+)-([A-Z]+)-(\d+[A-Z]*)', # P922 52-MF-01BC
    }
    
    # Mapeamento de códigos para nomes
    SUBSTATION_NAMES = {
        '00': 'Subestação Principal',
        '52': 'Subestação 52-MF',
        '204': 'Subestação 204',
        '205': 'Subestação 205',
        '223': 'Subestação 223',
        '241': 'Subestação 241'
    }
    
    # Tipos de dispositivos
    DEVICE_TYPES = {
        'MF': 'Motor Feeder',
        'MP': 'Main Protection',
        'MK': 'Mains Keeper',
        'PN': 'Panel',
        'TF': 'Transformer Feeder',
        'Z': 'Zone'
    }
    
    def __init__(self):
        self.bays_found: Dict[str, BayInfo] = {}
        self.substations_found: Dict[str, SubstationInfo] = {}
    
    def analyze_filename(self, filename: str) -> Optional[BayInfo]:
        """Analisa nome de arquivo e extrai informações"""
        
        # Tentar todos os padrões
        for pattern_name, pattern in self.PATTERNS.items():
            match = re.search(pattern, filename)
            if match:
                sub_code, device_type, position = match.groups()
                
                bay_code = f"{sub_code}-{device_type}-{position}"
                
                bay_info = BayInfo(
                    code=bay_code,
                    substation_code=sub_code,
                    device_type=device_type,
                    position=position,
                    description=f"{self.DEVICE_TYPES.get(device_type, device_type)} - Position {position}"
                )
                
                return bay_info
        
        return None
    
    def analyze_csv_content(self, csv_path: str) -> Dict[str, str]:
        """Extrai informações adicionais do CSV"""
        metadata = {}
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get('Code', '').lower()
                    value = row.get('Value', '')
                    
                    # Extrair informações relevantes
                    if 'serial' in code or 'numero' in code:
                        metadata['serial_number'] = value
                    elif 'description' in code or 'descricao' in code:
                        metadata['description'] = value
                    elif 'repere' in code or 'reference' in code:
                        metadata['reference'] = value
                    elif 'tension' in code or 'voltage' in code:
                        if 'primaire' in code or 'primary' in code:
                            metadata['voltage_primary'] = value
                    elif 'frequence' in code or 'frequency' in code:
                        metadata['frequency'] = value
                        
        except Exception as e:
            print(f"⚠️  Erro ao ler CSV {csv_path}: {e}")
        
        return metadata
    
    def scan_files(self, csv_dir: str) -> Tuple[Dict[str, BayInfo], Dict[str, SubstationInfo]]:
        """Scanneia todos os arquivos CSV"""
        
        print("🔍 ANALISANDO ARQUIVOS CSV...")
        print("=" * 60)
        
        if not os.path.exists(csv_dir):
            print(f"❌ Diretório não encontrado: {csv_dir}")
            return {}, {}
        
        csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
        print(f"📁 Encontrados {len(csv_files)} arquivos CSV\n")
        
        for filename in sorted(csv_files):
            csv_path = os.path.join(csv_dir, filename)
            
            # Analisar nome do arquivo
            bay_info = self.analyze_filename(filename)
            
            if bay_info:
                # Analisar conteúdo do CSV
                metadata = self.analyze_csv_content(csv_path)
                
                # Adicionar metadata ao bay_info
                if 'voltage_primary' in metadata:
                    bay_info.voltage_level = metadata['voltage_primary']
                
                # Armazenar bay
                self.bays_found[bay_info.code] = bay_info
                
                # Criar/atualizar subestação
                if bay_info.substation_code not in self.substations_found:
                    sub_info = SubstationInfo(
                        code=bay_info.substation_code,
                        name=self.SUBSTATION_NAMES.get(
                            bay_info.substation_code, 
                            f"Subestação {bay_info.substation_code}"
                        ),
                        voltage_level=bay_info.voltage_level
                    )
                    self.substations_found[bay_info.substation_code] = sub_info
                
                print(f"✅ {filename}")
                print(f"   Bay: {bay_info.code}")
                print(f"   Substation: {bay_info.substation_code}")
                print(f"   Type: {self.DEVICE_TYPES.get(bay_info.device_type, bay_info.device_type)}")
                if metadata:
                    print(f"   Metadata: {len(metadata)} campos extraídos")
                print()
            else:
                print(f"⚠️  {filename} - padrão não reconhecido")
        
        print("=" * 60)
        print(f"📊 RESUMO:")
        print(f"   Subestações encontradas: {len(self.substations_found)}")
        print(f"   Bays encontrados: {len(self.bays_found)}")
        print()
        
        return self.bays_found, self.substations_found


class DatabaseNormalizer:
    """
    Normaliza dados no PostgreSQL seguindo 3FN
    """
    
    def __init__(self, connection_string: str):
        self.conn_string = connection_string
    
    def connect(self):
        """Conecta ao PostgreSQL"""
        return psycopg2.connect(self.conn_string)
    
    def create_tables_if_not_exist(self):
        """Cria tabelas substations e bays se não existirem"""
        
        conn = self.connect()
        cur = conn.cursor()
        
        try:
            print("🔧 CRIANDO TABELAS (se não existirem)...")
            
            # Tabela substations
            cur.execute("""
                CREATE TABLE IF NOT EXISTS protec_ai.substations (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    voltage_level VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_substations_code 
                ON protec_ai.substations(code);
            """)
            
            # Tabela bays
            cur.execute("""
                CREATE TABLE IF NOT EXISTS protec_ai.bays (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    substation_id INTEGER REFERENCES protec_ai.substations(id),
                    device_type VARCHAR(50),
                    position VARCHAR(50),
                    voltage_level VARCHAR(50),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_bays_code 
                ON protec_ai.bays(code);
                
                CREATE INDEX IF NOT EXISTS idx_bays_substation 
                ON protec_ai.bays(substation_id);
            """)
            
            # Adicionar coluna bay_id em relay_equipment (se não existir)
            cur.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'protec_ai' 
                        AND table_name = 'relay_equipment' 
                        AND column_name = 'bay_id'
                    ) THEN
                        ALTER TABLE protec_ai.relay_equipment 
                        ADD COLUMN bay_id INTEGER REFERENCES protec_ai.bays(id);
                        
                        CREATE INDEX idx_relay_equipment_bay 
                        ON protec_ai.relay_equipment(bay_id);
                    END IF;
                END $$;
            """)
            
            conn.commit()
            print("✅ Tabelas criadas/verificadas com sucesso\n")
            
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
    
    def populate_substations(self, substations: Dict[str, SubstationInfo]):
        """Popula tabela de subestações"""
        
        conn = self.connect()
        cur = conn.cursor()
        
        try:
            print("📥 POPULANDO SUBESTAÇÕES...")
            
            data = [
                (sub.code, sub.name, sub.voltage_level)
                for sub in substations.values()
            ]
            
            execute_batch(cur, """
                INSERT INTO protec_ai.substations (code, name, voltage_level)
                VALUES (%s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    voltage_level = COALESCE(EXCLUDED.voltage_level, protec_ai.substations.voltage_level),
                    updated_at = CURRENT_TIMESTAMP
            """, data)
            
            conn.commit()
            print(f"✅ {len(data)} subestações inseridas/atualizadas\n")
            
        except Exception as e:
            print(f"❌ Erro ao popular subestações: {e}")
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
    
    def populate_bays(self, bays: Dict[str, BayInfo]):
        """Popula tabela de bays"""
        
        conn = self.connect()
        cur = conn.cursor()
        
        try:
            print("📥 POPULANDO BAYS...")
            
            # Primeiro, buscar IDs das subestações
            cur.execute("SELECT id, code FROM protec_ai.substations")
            sub_ids = {code: id for id, code in cur.fetchall()}
            
            data = []
            for bay in bays.values():
                sub_id = sub_ids.get(bay.substation_code)
                if sub_id:
                    data.append((
                        bay.code,
                        sub_id,
                        bay.device_type,
                        bay.position,
                        bay.voltage_level,
                        bay.description
                    ))
            
            execute_batch(cur, """
                INSERT INTO protec_ai.bays 
                (code, substation_id, device_type, position, voltage_level, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                    substation_id = EXCLUDED.substation_id,
                    device_type = EXCLUDED.device_type,
                    position = EXCLUDED.position,
                    voltage_level = COALESCE(EXCLUDED.voltage_level, protec_ai.bays.voltage_level),
                    description = COALESCE(EXCLUDED.description, protec_ai.bays.description),
                    updated_at = CURRENT_TIMESTAMP
            """, data)
            
            conn.commit()
            print(f"✅ {len(data)} bays inseridos/atualizados\n")
            
        except Exception as e:
            print(f"❌ Erro ao popular bays: {e}")
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
    
    def link_equipment_to_bays(self):
        """Liga equipamentos aos bays usando bay_name"""
        
        conn = self.connect()
        cur = conn.cursor()
        
        try:
            print("🔗 LINKANDO EQUIPAMENTOS AOS BAYS...")
            
            # Atualizar bay_id baseado no bay_name
            cur.execute("""
                UPDATE protec_ai.relay_equipment re
                SET bay_id = b.id
                FROM protec_ai.bays b
                WHERE re.bay_name = b.code
                AND re.bay_id IS NULL
            """)
            
            linked = cur.rowcount
            conn.commit()
            
            print(f"✅ {linked} equipamentos linkados aos bays\n")
            
            # Verificar integridade
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE bay_id IS NOT NULL) as with_bay,
                    COUNT(*) FILTER (WHERE bay_id IS NULL) as without_bay,
                    COUNT(*) as total
                FROM protec_ai.relay_equipment
            """)
            
            with_bay, without_bay, total = cur.fetchone()
            
            print("📊 INTEGRIDADE REFERENCIAL:")
            print(f"   ✅ Com bay: {with_bay}/{total}")
            print(f"   ⚠️  Sem bay: {without_bay}/{total}")
            print()
            
        except Exception as e:
            print(f"❌ Erro ao linkar equipamentos: {e}")
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()


def main():
    """Execução principal"""
    
    print("=" * 60)
    print("🔧 NORMALIZAÇÃO 3FN - SUBSTATIONS E BAYS")
    print("=" * 60)
    print()
    
    # Configuração
    CSV_DIR = "/Users/accol/Library/Mobile Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes/outputs/csv"
    DB_CONN = "postgresql://protecai:protecai@localhost:5432/protecai_db"
    
    # FASE 1: Análise de arquivos
    analyzer = FilePatternAnalyzer()
    bays, substations = analyzer.scan_files(CSV_DIR)
    
    if not bays or not substations:
        print("❌ Nenhum padrão encontrado nos arquivos")
        return
    
    # FASE 2: Normalização no banco
    normalizer = DatabaseNormalizer(DB_CONN)
    
    normalizer.create_tables_if_not_exist()
    normalizer.populate_substations(substations)
    normalizer.populate_bays(bays)
    normalizer.link_equipment_to_bays()
    
    print("=" * 60)
    print("✅ NORMALIZAÇÃO 3FN CONCLUÍDA COM SUCESSO!")
    print("=" * 60)


if __name__ == "__main__":
    main()

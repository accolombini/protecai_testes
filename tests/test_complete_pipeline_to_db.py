#!/usr/bin/env python3
"""
TESTE COMPLETO DA PIPELINE - EXTRAÇÃO ATÉ POSTGRESQL
====================================================

FLUXO:
1. Limpa outputs intermediários
2. Processa TODOS os PDFs (EASERGY, MiCOM) + TXTs (SEPAM)
3. Importa dados normalizados para PostgreSQL (protec_ai)
4. Valida dados no banco

Autor: ProtecAI Team
Data: 17/11/2025
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import psycopg2
from datetime import datetime

# Adiciona src/ ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from intelligent_relay_extractor import IntelligentRelayExtractor

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompletePipelineTester:
    """Testa pipeline completa até PostgreSQL"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.inputs_pdf = self.base_dir / "inputs" / "pdf"
        self.inputs_txt = self.base_dir / "inputs" / "txt"
        self.outputs_csv = self.base_dir / "outputs" / "csv"
        
        # Configuração do banco
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'protecai_db',
            'user': 'protecai',
            'password': 'protecai'
        }
        
        # Estatísticas
        self.stats = {
            'pdfs_processados': 0,
            'sepams_processados': 0,
            'total_parametros': 0,
            'parametros_ativos': 0,
            'equipamentos_importados': 0
        }
    
    def limpar_outputs(self):
        """Limpa diretórios de saída intermediários"""
        logger.info("\n" + "="*80)
        logger.info("🧹 LIMPANDO OUTPUTS INTERMEDIÁRIOS")
        logger.info("="*80)
        
        dirs_to_clean = [
            self.outputs_csv,
            self.base_dir / "outputs" / "excel",
            self.base_dir / "outputs" / "norm_csv",
            self.base_dir / "outputs" / "norm_excel"
        ]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                for file in dir_path.glob("*"):
                    if file.is_file():
                        file.unlink()
                logger.info(f"  ✓ Limpo: {dir_path.name}/")
        
        logger.info("✅ Limpeza concluída\n")
    
    def processar_todos_arquivos(self):
        """Processa todos os PDFs e TXTs"""
        logger.info("\n" + "="*80)
        logger.info("🔄 PROCESSANDO ARQUIVOS DE ENTRADA")
        logger.info("="*80)
        
        # Criar diretório de saída
        self.outputs_csv.mkdir(parents=True, exist_ok=True)
        
        # Criar extrator
        extractor = IntelligentRelayExtractor()
        
        # Processar PDFs (EASERGY + MiCOM)
        pdf_files = sorted(self.inputs_pdf.glob("*.pdf"))
        logger.info(f"\n📄 PDFs encontrados: {len(pdf_files)}")
        
        for pdf_path in pdf_files:
            try:
                logger.info(f"  → {pdf_path.name}")
                df = extractor.extract(pdf_path)
                
                if not df.empty:
                    # Salvar CSV
                    output_path = self.outputs_csv / f"{pdf_path.stem}_params.csv"
                    df.to_csv(output_path, index=False)
                    
                    # Estatísticas
                    self.stats['pdfs_processados'] += 1
                    self.stats['total_parametros'] += len(df)
                    if 'is_active' in df.columns:
                        self.stats['parametros_ativos'] += df['is_active'].sum()
                    
                    logger.info(f"    ✓ {len(df)} parâmetros extraídos")
                else:
                    logger.warning(f"    ⚠️  Nenhum parâmetro extraído")
                    
            except Exception as e:
                logger.error(f"    ❌ Erro: {e}")
        
        # Processar TXTs (SEPAM)
        txt_files = sorted(self.inputs_txt.glob("*.S40"))
        logger.info(f"\n📝 SEPAM files encontrados: {len(txt_files)}")
        
        for txt_path in txt_files:
            try:
                logger.info(f"  → {txt_path.name}")
                df = extractor.extract(txt_path)
                
                if not df.empty:
                    # Salvar CSV
                    output_path = self.outputs_csv / f"{txt_path.stem}_params.csv"
                    df.to_csv(output_path, index=False)
                    
                    # Estatísticas
                    self.stats['sepams_processados'] += 1
                    self.stats['total_parametros'] += len(df)
                    
                    logger.info(f"    ✓ {len(df)} parâmetros extraídos")
                else:
                    logger.warning(f"    ⚠️  Nenhum parâmetro extraído")
                    
            except Exception as e:
                logger.error(f"    ❌ Erro: {e}")
        
        logger.info(f"\n✅ Processamento concluído:")
        logger.info(f"   PDFs: {self.stats['pdfs_processados']}")
        logger.info(f"   SEPAMs: {self.stats['sepams_processados']}")
        logger.info(f"   Total parâmetros: {self.stats['total_parametros']}")
        logger.info(f"   Parâmetros ativos: {self.stats['parametros_ativos']}")
    
    def importar_para_postgresql(self):
        """Importa CSVs gerados para PostgreSQL"""
        logger.info("\n" + "="*80)
        logger.info("💾 IMPORTANDO PARA POSTGRESQL")
        logger.info("="*80)
        
        try:
            # Conectar ao banco
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            logger.info(f"✓ Conectado ao banco: {self.db_config['database']}")
            
            # Processar cada CSV
            csv_files = sorted(self.outputs_csv.glob("*_params.csv"))
            logger.info(f"\n📊 CSVs para importar: {len(csv_files)}")
            
            for csv_path in csv_files:
                try:
                    self._importar_csv(cursor, csv_path)
                    self.stats['equipamentos_importados'] += 1
                except Exception as e:
                    logger.error(f"  ❌ Erro importando {csv_path.name}: {e}")
            
            # Commit
            conn.commit()
            logger.info(f"\n✅ Importação concluída: {self.stats['equipamentos_importados']} equipamentos")
            
            # Fechar conexão
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            logger.error(f"❌ Erro de conexão PostgreSQL: {e}")
            logger.error(f"   Verifique se o container está rodando: docker ps | grep postgres")
    
    def _importar_csv(self, cursor, csv_path: Path):
        """Importa um CSV individual para o banco"""
        logger.info(f"  → {csv_path.name}")
        
        # Ler CSV
        df = pd.read_csv(csv_path)
        
        # Detectar tipo de relé do nome do arquivo
        relay_type = self._detectar_tipo_rele(csv_path.stem)
        
        # Criar/obter equipment_id
        equipment_id = self._criar_equipment(cursor, csv_path.stem, relay_type, df)
        
        # Inserir parâmetros
        parametros_inseridos = 0
        for _, row in df.iterrows():
            parameter_id = self._criar_parameter(cursor, row)
            self._criar_parameter_value(cursor, equipment_id, parameter_id, row)
            parametros_inseridos += 1
        
        logger.info(f"    ✓ {parametros_inseridos} parâmetros importados")
    
    def _detectar_tipo_rele(self, filename: str) -> str:
        """Detecta tipo de relé pelo nome do arquivo"""
        filename_lower = filename.lower()
        
        if 'p122' in filename_lower or 'p_122' in filename_lower:
            return 'EASERGY_P122'
        elif 'p220' in filename_lower or 'p_220' in filename_lower:
            return 'EASERGY_P220'
        elif 'p922' in filename_lower or 'p_922' in filename_lower:
            return 'EASERGY_P922'
        elif 'p143' in filename_lower or 'p_143' in filename_lower:
            return 'MICOM_P143'
        elif 'p241' in filename_lower or 'p_241' in filename_lower:
            return 'MICOM_P241'
        elif 's40' in filename_lower or 'sepam' in filename_lower:
            return 'SEPAM'
        else:
            return 'UNKNOWN'
    
    def _criar_equipment(self, cursor, source_file: str, relay_type: str, df: pd.DataFrame) -> int:
        """Cria registro de equipamento e retorna ID"""
        
        # Obter relay_type_id
        cursor.execute("SELECT id FROM protec_ai.relay_types WHERE type_name = %s", (relay_type,))
        result = cursor.fetchone()
        relay_type_id = result[0] if result else None
        
        # Extrair metadados do CSV (se existirem)
        metadata = self._extrair_metadados(df)
        
        # Inserir equipment
        cursor.execute("""
            INSERT INTO protec_ai.equipments (
                relay_type_id, source_file, extraction_date,
                code_0079, code_0081, code_010a, code_0005
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_file, extraction_date) DO UPDATE
            SET relay_type_id = EXCLUDED.relay_type_id
            RETURNING id
        """, (
            relay_type_id,
            source_file,
            datetime.now(),
            metadata.get('code_0079'),
            metadata.get('code_0081'),
            metadata.get('code_010a'),
            metadata.get('code_0005')
        ))
        
        return cursor.fetchone()[0]
    
    def _extrair_metadados(self, df: pd.DataFrame) -> dict:
        """Extrai metadados de códigos específicos do DataFrame"""
        metadata = {}
        
        if 'Code' in df.columns:
            for code in ['0079', '0081', '010A', '0005']:
                row = df[df['Code'] == code]
                if not row.empty and 'Value' in df.columns:
                    metadata[f'code_{code.lower()}'] = str(row['Value'].iloc[0])
        
        return metadata
    
    def _criar_parameter(self, cursor, row) -> int:
        """Cria/obtém parameter_id"""
        
        code = str(row.get('Code', ''))
        description = str(row.get('Description', ''))
        
        # Inserir ou obter parameter
        cursor.execute("""
            INSERT INTO protec_ai.parameters (parameter_code, parameter_description, is_metadata)
            VALUES (%s, %s, %s)
            ON CONFLICT (parameter_code) DO UPDATE
            SET parameter_description = EXCLUDED.parameter_description
            RETURNING id
        """, (code, description, False))
        
        return cursor.fetchone()[0]
    
    def _criar_parameter_value(self, cursor, equipment_id: int, parameter_id: int, row):
        """Cria parameter_value"""
        
        value = str(row.get('Value', ''))
        is_active = bool(row.get('is_active', False))
        
        # Inserir parameter_value
        cursor.execute("""
            INSERT INTO protec_ai.parameter_values (
                equipment_id, parameter_id, parameter_value, is_active,
                value_type, is_multipart, multipart_part
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (equipment_id, parameter_id, multipart_part) DO UPDATE
            SET parameter_value = EXCLUDED.parameter_value,
                is_active = EXCLUDED.is_active
        """, (
            equipment_id,
            parameter_id,
            value,
            is_active,
            'text',
            False,
            0
        ))
    
    def validar_dados_no_banco(self):
        """Valida dados importados no PostgreSQL"""
        logger.info("\n" + "="*80)
        logger.info("✅ VALIDANDO DADOS NO BANCO")
        logger.info("="*80)
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 1. Contar equipamentos
            cursor.execute("SELECT COUNT(*) FROM protec_ai.equipments")
            total_equipments = cursor.fetchone()[0]
            logger.info(f"\n📊 Total de equipamentos: {total_equipments}")
            
            # 2. Contar parâmetros ativos
            cursor.execute("SELECT COUNT(*) FROM protec_ai.parameter_values WHERE is_active = TRUE")
            total_active = cursor.fetchone()[0]
            logger.info(f"✓ Parâmetros ativos: {total_active}")
            
            # 3. Verificar LED 5 e LED 6 (0150, 0151)
            cursor.execute("""
                SELECT p.parameter_code, p.parameter_description, pv.parameter_value, pv.is_active
                FROM protec_ai.parameter_values pv
                JOIN protec_ai.parameters p ON pv.parameter_id = p.id
                WHERE p.parameter_code IN ('0150', '0151')
                AND pv.is_active = TRUE
                LIMIT 10
            """)
            
            led_results = cursor.fetchall()
            if led_results:
                logger.info(f"\n🔍 Amostra de LEDs ativos (0150, 0151):")
                for code, desc, value, active in led_results:
                    logger.info(f"   {code} | {desc} | {value} | Ativo: {active}")
            
            # 4. Estatísticas por tipo de relé
            cursor.execute("""
                SELECT rt.type_name, COUNT(DISTINCT e.id) as total
                FROM protec_ai.equipments e
                LEFT JOIN protec_ai.relay_types rt ON e.relay_type_id = rt.id
                GROUP BY rt.type_name
                ORDER BY total DESC
            """)
            
            logger.info(f"\n📈 Equipamentos por tipo:")
            for relay_type, total in cursor.fetchall():
                logger.info(f"   {relay_type or 'UNKNOWN'}: {total}")
            
            cursor.close()
            conn.close()
            
            logger.info(f"\n✅ Validação concluída!")
            
        except psycopg2.Error as e:
            logger.error(f"❌ Erro na validação: {e}")
    
    def run(self):
        """Executa pipeline completa"""
        logger.info("\n" + "="*80)
        logger.info("🚀 TESTE COMPLETO DA PIPELINE")
        logger.info(f"   Database: {self.db_config['database']}")
        logger.info(f"   Schema: protec_ai")
        logger.info(f"   Usuário: {self.db_config['user']}")
        logger.info("="*80)
        
        # Etapa 1: Limpar outputs
        self.limpar_outputs()
        
        # Etapa 2: Processar arquivos
        self.processar_todos_arquivos()
        
        # Etapa 3: Importar para PostgreSQL
        self.importar_para_postgresql()
        
        # Etapa 4: Validar dados
        self.validar_dados_no_banco()
        
        logger.info("\n" + "="*80)
        logger.info("🎉 PIPELINE COMPLETA EXECUTADA COM SUCESSO!")
        logger.info("="*80 + "\n")

if __name__ == "__main__":
    tester = CompletePipelineTester()
    tester.run()

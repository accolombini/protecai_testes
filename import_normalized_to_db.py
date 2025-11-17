#!/usr/bin/env python3
"""
IMPORTADOR DE DADOS NORMALIZADOS PARA POSTGRESQL
=================================================

Importa dados dos arquivos norm_csv/ para o schema protec_ai:
- relay_types
- equipments  
- parameters
- parameter_values (COM is_active)

Autor: ProtecAI Team
Data: 17/11/2025
"""

import sys
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from pathlib import Path
from typing import Dict, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImportadorNormalizado:
    """Importa dados normalizados para PostgreSQL protec_ai schema."""
    
    # Mapeamento de modelos de relé para IDs
    RELAY_TYPE_MAP = {
        'P122': 1, 'P122_52': 1, 'P122_204': 1, 'P122_205': 1,
        'P143': 2, 'P143_204': 2,
        'P220': 3,
        'P241': 4,
        'P922': 5, 'P922S': 5,
        'SEPAM': 6, 'S40': 6
    }
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.equipment_cache = {}  # {nome_arquivo: equipment_id}
        self.parameter_cache = {}  # {parameter_code: parameter_id}
    
    def conectar(self) -> bool:
        """Conecta ao PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                host='localhost',
                database='protecai_db',
                user='protecai',
                password='protecai',
                port=5432
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            self.cursor.execute("SET search_path TO protec_ai;")
            self.conn.commit()
            
            logger.info("✅ Conectado ao PostgreSQL (protecai_db / protec_ai)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar: {e}")
            return False
    
    def desconectar(self):
        """Fecha conexão."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("🔌 Desconectado do PostgreSQL")
    
    def detectar_relay_type_id(self, filename: str) -> Optional[int]:
        """Detecta o tipo de relé pelo nome do arquivo."""
        filename_upper = filename.upper()
        
        # Buscar padrões na ordem de especificidade
        for pattern, relay_id in sorted(self.RELAY_TYPE_MAP.items(), 
                                        key=lambda x: len(x[0]), 
                                        reverse=True):
            if pattern.upper() in filename_upper:
                return relay_id
        
        return None
    
    def extrair_tag_equipamento(self, filename: str) -> str:
        """Extrai a tag do equipamento do nome do arquivo."""
        # Remove extensão
        base = filename.replace('_params.csv', '').replace('.csv', '')
        
        # Remove prefixo de modelo (P122, P220, etc)
        for model in ['P122_205', 'P122_204', 'P122_52', 'P122', 'P143_204', 'P143', 
                      'P220', 'P241', 'P922S', 'P922', 'P_122']:
            if base.startswith(model):
                base = base[len(model):].strip()
                break
        
        # Remove espaços iniciais/finais e datas
        base = base.strip()
        base = base.split('_')[0]  # Pega primeira parte antes de _
        
        return base
    
    def obter_ou_criar_equipment(self, filename: str, relay_type_id: int) -> int:
        """Obtém ou cria equipment no banco."""
        if filename in self.equipment_cache:
            return self.equipment_cache[filename]
        
        # Buscar equipment existente por source_file
        self.cursor.execute(
            "SELECT id FROM equipments WHERE source_file = %s",
            (filename,)
        )
        result = self.cursor.fetchone()
        
        if result:
            equipment_id = result['id']
        else:
            # Criar novo equipment (SEM equipment_tag - campo não existe!)
            self.cursor.execute(
                """
                INSERT INTO equipments (relay_type_id, source_file, extraction_date)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                (relay_type_id, filename)
            )
            equipment_id = self.cursor.fetchone()['id']
            logger.info(f"   📌 Equipment criado: {filename} (ID: {equipment_id})")
        
        self.equipment_cache[filename] = equipment_id
        return equipment_id
    
    def obter_ou_criar_parameter(self, code: str, name: str) -> int:
        """Obtém ou cria parameter no banco (SEM relay_type_id)."""
        cache_key = code
        
        if cache_key in self.parameter_cache:
            return self.parameter_cache[cache_key]
        
        # Buscar parameter existente (apenas por código)
        self.cursor.execute(
            "SELECT id FROM parameters WHERE parameter_code = %s",
            (code,)
        )
        result = self.cursor.fetchone()
        
        if result:
            parameter_id = result['id']
        else:
            # Criar novo parameter (usar parameter_description ao invés de parameter_name)
            self.cursor.execute(
                """
                INSERT INTO parameters (parameter_code, parameter_description)
                VALUES (%s, %s)
                RETURNING id
                """,
                (code, name)
            )
            parameter_id = self.cursor.fetchone()['id']
        
        self.parameter_cache[cache_key] = parameter_id
        return parameter_id
    
    def processar_arquivo_csv(self, csv_path: Path) -> Dict[str, int]:
        """Processa um arquivo CSV normalizado."""
        logger.info(f"\n📄 Processando: {csv_path.name}")
        
        # Detectar tipo de relé
        relay_type_id = self.detectar_relay_type_id(csv_path.name)
        if not relay_type_id:
            logger.warning(f"   ⚠️  Tipo de relé não detectado, usando P122 como padrão")
            relay_type_id = 1
        
        # Obter/criar equipment
        equipment_id = self.obter_ou_criar_equipment(csv_path.name, relay_type_id)
        
        # Carregar CSV
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            logger.error(f"   ❌ Erro ao ler CSV: {e}")
            return {'erros': 1}
        
        stats = {
            'total': len(df),
            'inseridos': 0,
            'ativos': 0,
            'erros': 0
        }
        
        # Processar cada linha
        for _, row in df.iterrows():
            try:
                # Extrair dados
                code = str(row.get('parameter_code', row.get('Code', '')))
                name = str(row.get('parameter_name', row.get('Description', '')))
                value = str(row.get('set_value', row.get('Value', '')))
                unit = str(row.get('unit_of_measure', ''))
                
                # Determinar se é ativo (baseado em is_active ou is_valid)
                is_active = False
                if 'is_active' in df.columns:
                    is_active = row['is_active'] in [True, 'True', 'true', 1, '1']
                elif 'is_valid' in df.columns:
                    is_active = row['is_valid'] in [True, 'True', 'true', 1, '1']
                
                # Obter/criar parameter (SEM relay_type_id)
                parameter_id = self.obter_ou_criar_parameter(code, name)
                
                # Inserir parameter_value (usando parameter_value e ignorando unit_of_measure)
                self.cursor.execute(
                    """
                    INSERT INTO parameter_values 
                    (equipment_id, parameter_id, parameter_value, is_active)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (equipment_id, parameter_id, multipart_part) 
                    DO UPDATE SET 
                        parameter_value = EXCLUDED.parameter_value,
                        is_active = EXCLUDED.is_active
                    """,
                    (equipment_id, parameter_id, value, is_active)
                )
                
                stats['inseridos'] += 1
                if is_active:
                    stats['ativos'] += 1
                
            except Exception as e:
                logger.error(f"   ❌ Erro na linha: {e}")
                stats['erros'] += 1
                continue
        
        self.conn.commit()
        
        logger.info(f"   ✅ {stats['inseridos']} parâmetros | {stats['ativos']} ativos | {stats['erros']} erros")
        return stats
    
    def importar_todos(self, norm_csv_dir: str) -> Dict[str, int]:
        """Importa todos os arquivos CSV do diretório."""
        logger.info("\n" + "="*80)
        logger.info("📦 IMPORTANDO DADOS NORMALIZADOS PARA POSTGRESQL")
        logger.info("="*80)
        
        path = Path(norm_csv_dir)
        arquivos = list(path.glob("*.csv"))
        
        if not arquivos:
            logger.warning(f"❌ Nenhum arquivo CSV encontrado em {norm_csv_dir}")
            return {}
        
        logger.info(f"📊 {len(arquivos)} arquivo(s) encontrado(s)")
        
        stats_total = {
            'arquivos_processados': 0,
            'total_parametros': 0,
            'total_ativos': 0,
            'total_erros': 0
        }
        
        for csv_file in sorted(arquivos):
            stats = self.processar_arquivo_csv(csv_file)
            
            stats_total['arquivos_processados'] += 1
            stats_total['total_parametros'] += stats.get('inseridos', 0)
            stats_total['total_ativos'] += stats.get('ativos', 0)
            stats_total['total_erros'] += stats.get('erros', 0)
        
        # Resumo final
        logger.info("\n" + "="*80)
        logger.info("🎉 IMPORTAÇÃO CONCLUÍDA!")
        logger.info("="*80)
        logger.info(f"📁 Arquivos processados: {stats_total['arquivos_processados']}")
        logger.info(f"📊 Total de parâmetros: {stats_total['total_parametros']}")
        logger.info(f"✅ Parâmetros ativos: {stats_total['total_ativos']}")
        logger.info(f"❌ Erros: {stats_total['total_erros']}")
        
        # Verificar totais no banco
        self.cursor.execute("SELECT COUNT(*) as total FROM equipments")
        total_equipments = self.cursor.fetchone()['total']
        
        self.cursor.execute("SELECT COUNT(*) as total FROM parameter_values")
        total_values = self.cursor.fetchone()['total']
        
        self.cursor.execute("SELECT COUNT(*) as total FROM parameter_values WHERE is_active = TRUE")
        total_active = self.cursor.fetchone()['total']
        
        logger.info("\n📊 TOTAIS NO BANCO:")
        logger.info(f"   Equipments: {total_equipments}")
        logger.info(f"   Parameter Values: {total_values}")
        logger.info(f"   Values Ativos: {total_active}")
        
        return stats_total

def main():
    """Função principal."""
    project_root = Path(__file__).parent
    norm_csv_dir = project_root / "outputs" / "norm_csv"
    
    if not norm_csv_dir.exists():
        logger.error(f"❌ Diretório não encontrado: {norm_csv_dir}")
        return 1
    
    importador = ImportadorNormalizado()
    
    try:
        if not importador.conectar():
            return 1
        
        importador.importar_todos(str(norm_csv_dir))
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        importador.desconectar()

if __name__ == "__main__":
    sys.exit(main())

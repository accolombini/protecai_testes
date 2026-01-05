#!/usr/bin/env python3
"""
Script para extrair e atualizar bay_name (barramento) dos nomes dos arquivos originais.

CAUSA RAIZ IDENTIFICADA:
- bay_name está como 'Unknown' no banco de dados
- Informação do barramento está nos nomes dos arquivos originais
- position_description contém: "Processado de <arquivo_original>"

PADRÕES DE EXTRAÇÃO:
1. Formato underscore: P122_204-MF-2B1_data.pdf → 204-MF-2B1
2. Formato espaço: P220 52-MP-01A.pdf → 52-MP-01A
3. Formato S40: 00-MF-12_data.S40 → 00-MF-12
"""

import re
import psycopg2
from pathlib import Path
from typing import Optional, Tuple
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração do banco de dados
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

class BayNameExtractor:
    """Extrai bay_name de nomes de arquivos usando padrões inteligentes."""
    
    # Padrões regex para diferentes formatos de arquivo
    PATTERNS = {
        'underscore_format': [
            # P122_204-MF-2B1_2014-07-28.pdf → 204-MF-2B1
            r'^[A-Z]\d+_([0-9]+[-][A-Z]+[-][A-Z0-9]+)',
            # P922S_204-MF-1AC_2014-07-28.pdf → 204-MF-1AC (variante com letra extra)
            r'^[A-Z]\d+[A-Z]?_([0-9]+[-][A-Z]+[-][A-Z0-9]+)',
            # P122_52-Z-08_L_PATIO_2014-08-06.pdf → 52-Z-08
            r'^[A-Z]\d+_([0-9]+[-][A-Z]+[-][0-9]+)',
        ],
        'space_format': [
            # P220 52-MP-01A.pdf → 52-MP-01A
            r'^[A-Z]\d+\s+([0-9]+[-][A-Z]+[-][A-Z0-9]+)',
            # P143 52-MF-03A.pdf → 52-MF-03A
            r'^[A-Z]\d+\s+([0-9]+[-][A-Z]+[-][0-9]+[A-Z]?)',
        ],
        's40_format': [
            # 00-MF-12_2016-03-31.S40 → 00-MF-12
            r'^([0-9]+[-][A-Z]+[-][0-9]+)',
        ]
    }
    
    def extract_from_filename(self, filename: str) -> Optional[str]:
        """
        Extrai bay_name do nome do arquivo usando múltiplos padrões.
        
        Args:
            filename: Nome do arquivo (com ou sem extensão)
            
        Returns:
            Bay name extraído ou None se não encontrado
        """
        # Remove extensão se presente
        name_without_ext = Path(filename).stem
        
        # Tenta cada grupo de padrões
        for format_name, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.match(pattern, name_without_ext)
                if match:
                    bay_name = match.group(1)
                    logger.debug(f"✅ Padrão '{format_name}' encontrou: {bay_name} em {filename}")
                    return bay_name
        
        logger.warning(f"⚠️ Nenhum padrão correspondeu para: {filename}")
        return None
    
    def extract_from_description(self, position_description: str) -> Optional[str]:
        """
        Extrai nome do arquivo de position_description.
        
        Args:
            position_description: Texto como "Processado de P122_204-MF-2B1_2014-07-28_params.csv"
            
        Returns:
            Nome do arquivo extraído ou None
        """
        # Padrão: "Processado de <filename>"
        match = re.search(r'Processado de (.+?)(?:_params)?\.(?:csv|pdf|txt|S40)', position_description)
        if match:
            filename = match.group(1)
            logger.debug(f"📄 Arquivo extraído de description: {filename}")
            return filename
        
        logger.warning(f"⚠️ Não foi possível extrair arquivo de: {position_description}")
        return None


class DatabaseUpdater:
    """Atualiza bay_name no banco de dados."""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.extractor = BayNameExtractor()
    
    def connect(self):
        """Estabelece conexão com o banco de dados."""
        return psycopg2.connect(**self.db_config)
    
    def get_equipment_with_unknown_bay(self) -> list:
        """
        Busca equipamentos com bay_name Unknown, vazio ou NULL.
        
        Returns:
            Lista de tuplas (equipment_tag, position_description, current_bay_name)
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT equipment_tag, position_description, bay_name
                    FROM protec_ai.relay_equipment
                    WHERE bay_name IS NULL 
                       OR bay_name = '' 
                       OR bay_name = 'Unknown'
                    ORDER BY equipment_tag;
                """
                cur.execute(query)
                results = cur.fetchall()
                logger.info(f"📊 Encontrados {len(results)} equipamentos com bay_name Unknown/NULL")
                return results
        finally:
            conn.close()
    
    def update_bay_name(self, equipment_tag: str, new_bay_name: str) -> bool:
        """
        Atualiza bay_name de um equipamento.
        
        Args:
            equipment_tag: Tag do equipamento
            new_bay_name: Novo nome do barramento
            
        Returns:
            True se atualizado com sucesso
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                query = """
                    UPDATE protec_ai.relay_equipment
                    SET bay_name = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE equipment_tag = %s;
                """
                cur.execute(query, (new_bay_name, equipment_tag))
                conn.commit()
                
                if cur.rowcount > 0:
                    logger.info(f"✅ Atualizado {equipment_tag}: bay_name = '{new_bay_name}'")
                    return True
                else:
                    logger.warning(f"⚠️ Nenhuma linha atualizada para {equipment_tag}")
                    return False
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erro ao atualizar {equipment_tag}: {e}")
            return False
        finally:
            conn.close()
    
    def process_all_equipment(self) -> Tuple[int, int, int]:
        """
        Processa todos os equipamentos com bay_name Unknown.
        
        Returns:
            Tupla (total_processados, atualizados_com_sucesso, falhas)
        """
        equipment_list = self.get_equipment_with_unknown_bay()
        
        total = len(equipment_list)
        updated = 0
        failed = 0
        
        logger.info("🔄 Iniciando processamento de equipamentos...")
        logger.info("=" * 80)
        
        for equipment_tag, position_description, current_bay in equipment_list:
            logger.info(f"\n📌 Processando: {equipment_tag}")
            logger.info(f"   Descrição: {position_description}")
            logger.info(f"   Bay atual: {current_bay}")
            
            # Extrai nome do arquivo da descrição
            filename = self.extractor.extract_from_description(position_description)
            
            if not filename:
                logger.warning(f"   ⚠️ Não foi possível extrair nome do arquivo")
                failed += 1
                continue
            
            # Extrai bay_name do nome do arquivo
            bay_name = self.extractor.extract_from_filename(filename)
            
            if not bay_name:
                logger.warning(f"   ⚠️ Não foi possível extrair bay_name de: {filename}")
                failed += 1
                continue
            
            # Atualiza no banco de dados
            if self.update_bay_name(equipment_tag, bay_name):
                updated += 1
            else:
                failed += 1
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESUMO DO PROCESSAMENTO")
        logger.info("=" * 80)
        logger.info(f"Total de equipamentos processados: {total}")
        logger.info(f"✅ Atualizados com sucesso: {updated} ({updated/total*100:.1f}%)")
        logger.info(f"❌ Falhas: {failed} ({failed/total*100:.1f}%)")
        logger.info("=" * 80)
        
        return total, updated, failed
    
    def verify_results(self):
        """Verifica estado final após processamento."""
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                # Conta equipamentos ainda com bay_name Unknown
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM protec_ai.relay_equipment
                    WHERE bay_name IS NULL 
                       OR bay_name = '' 
                       OR bay_name = 'Unknown';
                """)
                unknown_count = cur.fetchone()[0]
                
                # Conta total de equipamentos
                cur.execute("SELECT COUNT(*) FROM protec_ai.relay_equipment;")
                total_count = cur.fetchone()[0]
                
                # Mostra distribuição de bay_names
                cur.execute("""
                    SELECT bay_name, COUNT(*) as count
                    FROM protec_ai.relay_equipment
                    GROUP BY bay_name
                    ORDER BY count DESC
                    LIMIT 10;
                """)
                distribution = cur.fetchall()
                
                logger.info("\n" + "=" * 80)
                logger.info("🔍 VERIFICAÇÃO FINAL")
                logger.info("=" * 80)
                logger.info(f"Total de equipamentos: {total_count}")
                logger.info(f"Equipamentos com bay_name Unknown/NULL: {unknown_count}")
                logger.info(f"Equipamentos com bay_name válido: {total_count - unknown_count}")
                logger.info("\n📊 Top 10 bay_names mais comuns:")
                for bay_name, count in distribution:
                    logger.info(f"   {bay_name}: {count} equipamentos")
                logger.info("=" * 80)
        finally:
            conn.close()


def main():
    """Função principal do script."""
    logger.info("🚀 Iniciando extração e atualização de bay_names")
    logger.info("=" * 80)
    
    try:
        updater = DatabaseUpdater(DB_CONFIG)
        
        # Processa todos os equipamentos
        total, updated, failed = updater.process_all_equipment()
        
        # Verifica resultados
        updater.verify_results()
        
        logger.info("\n✅ Script concluído com sucesso!")
        
        return 0 if failed == 0 else 1
        
    except Exception as e:
        logger.error(f"\n❌ Erro fatal: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())

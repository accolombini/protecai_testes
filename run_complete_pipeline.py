#!/usr/bin/env python3
"""
PIPELINE COMPLETA - EXTRAÇÃO → NORMALIZAÇÃO → POSTGRESQL
=========================================================

FLUXO CORRETO:
1. Extração: inputs/ → outputs/csv/ + outputs/excel/
2. Normalização: outputs/csv/ → outputs/norm_csv/ + outputs/norm_excel/
3. Importação: outputs/norm_csv/ → PostgreSQL (protecai_db / protec_ai schema)

Autor: ProtecAI Team
Data: 17/11/2025
"""

import sys
from pathlib import Path
import subprocess
import logging

# Adiciona src/ ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def executar_etapa_1_extracao():
    """Etapa 1: Extrair parâmetros de PDFs/TXTs"""
    logger.info("\n" + "="*80)
    logger.info("📄 ETAPA 1: EXTRAÇÃO DE PARÂMETROS")
    logger.info("="*80)
    
    from complete_pipeline_processor import CompletePipelineProcessor
    
    processor = CompletePipelineProcessor(str(project_root))
    stats = processor.process_all()
    
    logger.info(f"\n✅ Extração concluída:")
    logger.info(f"   Arquivos processados: {stats['processed']}")
    logger.info(f"   Falhas: {stats['failed']}")
    
    return stats['processed'] > 0

def executar_etapa_2_normalizacao():
    """Etapa 2: Normalizar CSVs extraídos"""
    logger.info("\n" + "="*80)
    logger.info("🔄 ETAPA 2: NORMALIZAÇÃO")
    logger.info("="*80)
    
    script_path = project_root / "scripts" / "normalize_extracted_csvs.py"
    
    if not script_path.exists():
        logger.error(f"❌ Script não encontrado: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Normalização concluída")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            logger.error(f"❌ Erro na normalização: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exceção: {e}")
        return False

def executar_etapa_3_importacao():
    """Etapa 3: Importar para PostgreSQL (2 passos: equipamentos + settings)"""
    logger.info("\n" + "="*80)
    logger.info("💾 ETAPA 3: IMPORTAÇÃO PARA POSTGRESQL")
    logger.info("="*80)
    
    # PASSO 3A: Criar equipamentos (fabricantes, modelos, relay_equipment)
    logger.info("\n📦 3A. Criando estrutura de equipamentos...")
    script_equipment = project_root / "scripts" / "universal_robust_relay_processor.py"
    
    if script_equipment.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(script_equipment)],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ Equipamentos criados")
            else:
                logger.error(f"❌ Erro criando equipamentos: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"❌ Exceção: {e}")
            return False
    
    # PASSO 3B: Importar settings dos equipamentos
    logger.info("\n📊 3B. Importando settings dos equipamentos...")
    script_settings = project_root / "scripts" / "import_all_relay_params_universal.py"
    
    if not script_settings.exists():
        logger.warning(f"⚠️  Script de settings não encontrado: {script_settings}")
        return True
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_settings)],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Settings importados")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            logger.error(f"❌ Erro importando settings: {result.stderr}")
            if result.stderr:
                print(result.stderr)
            return False
            
    except Exception as e:
        logger.error(f"❌ Exceção: {e}")
        return False

def main():
    """Executa pipeline completa"""
    logger.info("\n" + "="*80)
    logger.info("🚀 PIPELINE COMPLETA - PROTECAI")
    logger.info("   Database: protecai_db")
    logger.info("   Schema: protec_ai")
    logger.info("="*80)
    
    try:
        # Etapa 1: Extração
        if not executar_etapa_1_extracao():
            logger.error("❌ Falha na extração. Abortando.")
            return False
        
        # Etapa 2: Normalização
        if not executar_etapa_2_normalizacao():
            logger.error("❌ Falha na normalização. Abortando.")
            return False
        
        # Etapa 3: Importação (opcional)
        executar_etapa_3_importacao()
        
        logger.info("\n" + "="*80)
        logger.info("🎉 PIPELINE COMPLETA EXECUTADA COM SUCESSO!")
        logger.info("="*80)
        
        # Verificar outputs gerados
        logger.info("\n📊 Outputs gerados:")
        for pasta in ['csv', 'excel', 'norm_csv', 'norm_excel']:
            dir_path = project_root / "outputs" / pasta
            if dir_path.exists():
                count = len(list(dir_path.glob("*")))
                logger.info(f"   {pasta}/: {count} arquivos")
            else:
                logger.warning(f"   {pasta}/: NÃO EXISTE")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

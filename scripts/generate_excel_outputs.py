#!/usr/bin/env python3
"""
Script para gerar arquivos Excel dos dados brutos extraídos.
Completa o PASSO 1 da pipeline.

Entrada: outputs/csv/*_params.csv (dados brutos)
Saída: outputs/excel/*_params.xlsx
"""

import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


def convert_csv_to_excel(csv_path: Path, output_dir: Path) -> bool:
    """
    Converte um arquivo CSV para Excel (.xlsx).
    
    Args:
        csv_path: Caminho do arquivo CSV
        output_dir: Diretório de saída
        
    Returns:
        True se sucesso, False se erro
    """
    try:
        # Ler CSV
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Gerar nome do arquivo Excel
        excel_filename = csv_path.stem + '.xlsx'
        excel_path = output_dir / excel_filename
        
        # Salvar como Excel
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        logger.info(f"  ✅ {excel_filename}")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Erro ao converter {csv_path.name}: {e}")
        return False


def main():
    """Processa todos os CSVs e gera arquivos Excel."""
    
    logger.info("\n" + "="*80)
    logger.info("🎯 GERAÇÃO DE ARQUIVOS EXCEL - PASSO 1")
    logger.info("="*80)
    
    # Diretórios (usar CSVs brutos em outputs/csv)
    base_dir = Path(__file__).parent.parent
    csv_dir = base_dir / 'outputs' / 'csv'
    excel_dir = base_dir / 'outputs' / 'excel'
    
    logger.info(f"📂 Diretório CSV: {csv_dir}")
    logger.info(f"📂 Diretório Excel: {excel_dir}")
    
    # Criar diretório de saída
    excel_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Diretório de saída criado/verificado")
    
    # Listar todos os arquivos *_params.csv
    csv_files = sorted(csv_dir.glob('*_params.csv'))
    
    # Filtrar apenas arquivos que NÃO são active_setup
    csv_files = [f for f in csv_files if '_active_setup' not in f.name]
    
    total_files = len(csv_files)
    logger.info(f"📄 Total de arquivos CSV (dados brutos): {total_files}")
    logger.info("="*80)
    
    # Processar cada arquivo
    start_time = datetime.now()
    success_count = 0
    error_count = 0
    
    for i, csv_file in enumerate(csv_files, 1):
        logger.info(f"\n📄 [{i}/{total_files}] Processando: {csv_file.name}")
        
        if convert_csv_to_excel(csv_file, excel_dir):
            success_count += 1
        else:
            error_count += 1
    
    # Relatório final
    elapsed = (datetime.now() - start_time).total_seconds()
    
    logger.info("\n" + "="*80)
    logger.info("📊 RELATÓRIO FINAL")
    logger.info("="*80)
    logger.info(f"⏱️  Tempo total: {elapsed:.2f}s")
    logger.info(f"✅ Sucessos: {success_count}/{total_files}")
    logger.info(f"❌ Erros: {error_count}/{total_files}")
    
    if error_count == 0:
        logger.info("\n🎉 PASSO 1 - 100% CONCLUÍDO!")
        logger.info(f"📁 {success_count} arquivos Excel salvos em: {excel_dir}")
    else:
        logger.warning(f"\n⚠️  PASSO 1 concluído com {error_count} erro(s)")
    
    logger.info("="*80)


if __name__ == '__main__':
    main()

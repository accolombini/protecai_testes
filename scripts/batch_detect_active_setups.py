#!/usr/bin/env python3
"""
Batch Active Setup Detection
Processa todos os CSVs brutos em outputs/csv/ e gera arquivos *_active_setup.csv
com detecção de checkboxes e cálculo de confiança.
"""

import sys
import os
from pathlib import Path
import logging
import time
from collections import defaultdict
import pandas as pd

# Adiciona src/ ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Importar sem "src." prefix pois já adicionamos o path
try:
    from src.universal_setup_detector import UniversalSetupDetector
except ImportError:
    from universal_setup_detector import UniversalSetupDetector

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

def _find_pdf_for_csv(csv_path: Path, pdf_dir: Path) -> Path | None:
    """
    Localiza o PDF correspondente ao CSV.
    
    Estratégia:
    1. Remove sufixo _params.csv do nome
    2. Busca por arquivo .pdf com nome base
    
    Args:
        csv_path: Caminho do CSV (ex: P122 52-MF-02A_2021-03-08_params.csv)
        pdf_dir: Diretório onde buscar PDFs
    
    Returns:
        Path do PDF ou None se não encontrado
    """
    # Remove _params.csv para obter nome base
    base_name = csv_path.stem.replace('_params', '')
    
    # Tenta localizar PDF
    pdf_path = pdf_dir / f"{base_name}.pdf"
    
    if pdf_path.exists():
        logger.debug(f"  📄 PDF localizado: {pdf_path.name}")
        return pdf_path
    
    # Se não encontrou, tenta buscar por similaridade
    for pdf_file in pdf_dir.glob("*.pdf"):
        if base_name in pdf_file.stem:
            logger.debug(f"  📄 PDF localizado (similaridade): {pdf_file.name}")
            return pdf_file
    
    logger.debug(f"  ⚠️  PDF não encontrado para: {base_name}")
    return None

def main():
    """Processa todos os CSVs e gera setups ativos."""
    
    # Diretórios (usar CSVs brutos gerados pelo pipeline)
    csv_dir = project_root / "outputs" / "csv"
    pdf_dir = project_root / "inputs" / "pdf"
    
    # Lista todos os CSVs que NÃO são _active_setup
    csv_files = sorted([
        f for f in csv_dir.glob("*.csv")
        if "_active_setup" not in f.name
    ])
    
    if not csv_files:
        logger.error(f"❌ Nenhum CSV encontrado em {csv_dir}")
        return
    
    logger.info(f"\n{'='*80}")
    total_files = len(csv_files)
    
    logger.info(f"🎯 BATCH ACTIVE SETUP DETECTION")
    logger.info(f"{'='*80}")
    logger.info(f"📂 Diretório: {csv_dir}")
    logger.info(f"📄 Total de arquivos: {total_files}")
    logger.info(f"{'='*80}\n")
    
    # Inicializa detector
    detector = UniversalSetupDetector()
    
    # Estatísticas gerais
    stats = {
        'total': total_files,
        'sucesso': 0,
        'falha': 0,
        'por_tipo': defaultdict(lambda: {'count': 0, 'confidence': [], 'ativos': []}),
        'confidences': []
    }
    
    start_time = time.time()
    
    # Processar cada arquivo
    for i, csv_file in enumerate(csv_files, 1):
        print("")  # Print direto para aparecer imediatamente
        print("=" * 80)
        print(f"📄 [{i}/{total_files}] Processando: {csv_file.name}")
        print("=" * 80)
        logger.info("")
        logger.info("─" * 80)
        logger.info(f"📄 [{i}/{total_files}] Processando: {csv_file.name}")
        logger.info("─" * 80)
        
        try:
            # Localizar PDF correspondente
            pdf_path = _find_pdf_for_csv(csv_file, pdf_dir)
            
            # Detectar setup ativo (com PDF se disponível)
            active_params = detector.detect_active_setup(csv_file, pdf_path=pdf_path)
            
            # Detectar tipo pelo filename
            relay_type = 'unknown'
            if 'P122' in csv_file.name or 'P220' in csv_file.name or 'P922' in csv_file.name:
                relay_type = 'easergy'
            elif 'P143' in csv_file.name or 'P241' in csv_file.name:
                relay_type = 'micom'
            elif '00-MF' in csv_file.name:
                relay_type = 'sepam'
            
            if active_params and len(active_params) > 0:
                # Calcular confiança média
                confidence = sum(p.confidence for p in active_params) / len(active_params)
                
                # CRIAR CSV COM is_active
                # Ler CSV original
                df_original = pd.read_csv(csv_file)
                
                # Adicionar coluna is_active (False por padrão)
                df_original['is_active'] = False
                
                # Marcar parâmetros ativos
                active_codes = {p.code for p in active_params}
                # Detectar nome correto da coluna (Code ou code)
                code_col = 'Code' if 'Code' in df_original.columns else 'code'
                df_original.loc[df_original[code_col].isin(active_codes), 'is_active'] = True
                
                # Salvar CSV com _active_setup
                output_path = csv_file.parent / csv_file.name.replace('_params.csv', '_active_setup.csv')
                df_original.to_csv(output_path, index=False)
                logger.info(f"  💾 Salvo: {output_path.name}")
                
                stats['sucesso'] += 1
                stats['confidences'].append(confidence)
                stats['por_tipo'][relay_type]['count'] += 1
                stats['por_tipo'][relay_type]['confidence'].append(confidence)
                stats['por_tipo'][relay_type]['ativos'].append(len(active_params))
                
                logger.info(f"  ✅ {len(active_params)} parâmetros ativos")
                logger.info(f"  📊 Confiança: {confidence:.2f}")
                logger.info(f"  🏷️  Tipo: {relay_type}")
            else:
                # Mesmo sem ativos, criar CSV com is_active=False para todos
                df_original = pd.read_csv(csv_file)
                df_original['is_active'] = False
                output_path = csv_file.parent / csv_file.name.replace('_params.csv', '_active_setup.csv')
                df_original.to_csv(output_path, index=False)
                logger.info(f"  💾 Salvo: {output_path.name} (todos inativos)")
                
                stats['falha'] += 1
                logger.warning(f"  ⚠️  Nenhum parâmetro ativo detectado")
                
        except Exception as e:
            stats['falha'] += 1
            logger.error(f"  ❌ Erro: {str(e)}")
    
    # Relatório final
    elapsed = time.time() - start_time
    
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 RELATÓRIO FINAL")
    logger.info(f"{'='*80}")
    logger.info(f"⏱️  Tempo total: {elapsed:.2f}s")
    logger.info(f"✅ Sucessos: {stats['sucesso']}/{stats['total']}")
    logger.info(f"❌ Falhas: {stats['falha']}/{stats['total']}")
    
    if stats['confidences']:
        avg_confidence = sum(stats['confidences']) / len(stats['confidences'])
        min_confidence = min(stats['confidences'])
        max_confidence = max(stats['confidences'])
        
        logger.info(f"\n📈 CONFIANÇA GERAL:")
        logger.info(f"  Média: {avg_confidence:.3f}")
        logger.info(f"  Mínima: {min_confidence:.3f}")
        logger.info(f"  Máxima: {max_confidence:.3f}")
        
        # Verifica meta
        if avg_confidence >= 0.93:
            logger.info(f"  🎯 META ATINGIDA! (≥0.93)")
        else:
            logger.warning(f"  ⚠️  Abaixo da meta (0.93)")
    
    logger.info(f"\n📊 POR TIPO DE RELÉ:")
    for relay_type, data in sorted(stats['por_tipo'].items()):
        if data['confidence']:
            avg = sum(data['confidence']) / len(data['confidence'])
            avg_ativos = sum(data['ativos']) / len(data['ativos'])
            logger.info(f"\n  🏷️  {relay_type.upper()}:")
            logger.info(f"    Arquivos: {data['count']}")
            logger.info(f"    Confiança média: {avg:.3f}")
            logger.info(f"    Params ativos (média): {avg_ativos:.1f}")
    
    logger.info(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()

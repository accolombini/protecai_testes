#!/usr/bin/env python3
"""
REPROCESSAMENTO COMPLETO DA PIPELINE
Sistema ProtecAI - PETROBRAS
Data: 13 de novembro de 2025

OBJETIVO:
1. Extrair parâmetros de TODOS os PDFs MICON (com checkboxes)
2. Processar arquivos SEPAM (.S40)
3. Detectar funções ativas em TODOS os relés
4. Gerar relatório consolidado

PRINCÍPIOS: ROBUSTO, FLEXÍVEL, EXTENSÍVEL
"""

import sys
from pathlib import Path
import logging
import pandas as pd
from typing import Dict, List
import json

# Adiciona src/ ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.intelligent_relay_extractor import IntelligentRelayExtractor

# Importa detector genérico
from detect_active_functions import detect_active_functions, load_relay_config

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineReprocessor:
    """Reprocessa pipeline completa com extração robusta."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.inputs_pdf = self.base_dir / "inputs" / "pdf"
        self.inputs_txt = self.base_dir / "inputs" / "txt"
        self.outputs_csv = self.base_dir / "outputs" / "csv"
        self.outputs_reports = self.base_dir / "outputs" / "reports"
        
        # Estatísticas
        self.stats = {
            'pdfs_processados': 0,
            'pdfs_erro': 0,
            'sepam_processados': 0,
            'funcoes_detectadas': {}
        }
        
        # Carrega configuração
        self.config = load_relay_config()
    
    def extract_pdf_parameters(self, pdf_path: Path) -> bool:
        """
        Extrai parâmetros de um PDF com detecção de checkboxes.
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            logger.info(f"  📄 Extraindo: {pdf_path.name}")
            
            # Cria extrator
            extractor = IntelligentRelayExtractor()
            
            # Extrai parâmetros (com checkboxes)
            df = extractor.extract(pdf_path)
            
            if df.empty:
                logger.warning(f"    ⚠️  Nenhum parâmetro extraído")
                return False
            
            # Salva CSV
            output_path = self.outputs_csv / f"{pdf_path.stem}_params.csv"
            df.to_csv(output_path, index=False)
            
            logger.info(f"    ✅ {len(df)} parâmetros extraídos → {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"    ❌ Erro: {e}")
            return False
    
    def process_all_pdfs(self):
        """Processa todos os PDFs MICON."""
        logger.info("\n" + "="*80)
        logger.info("📁 PROCESSANDO PDFs MICON")
        logger.info("="*80)
        
        pdf_files = sorted(self.inputs_pdf.glob("*.pdf"))
        total = len(pdf_files)
        
        logger.info(f"Total de PDFs: {total}")
        logger.info("="*80 + "\n")
        
        for i, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"[{i}/{total}] {pdf_path.name}")
            
            if self.extract_pdf_parameters(pdf_path):
                self.stats['pdfs_processados'] += 1
            else:
                self.stats['pdfs_erro'] += 1
        
        logger.info(f"\n✅ PDFs processados: {self.stats['pdfs_processados']}/{total}")
        logger.info(f"❌ Erros: {self.stats['pdfs_erro']}/{total}")
    
    def detect_all_functions(self) -> List[Dict]:
        """
        Detecta funções ativas em TODOS os relés.
        
        Returns:
            Lista de resultados da detecção
        """
        logger.info("\n" + "="*80)
        logger.info("🔍 DETECTANDO FUNÇÕES ATIVAS")
        logger.info("="*80)
        
        results = []
        
        # Processa SEPAMs
        logger.info("\n📁 SEPAM (.S40):")
        sepam_files = sorted(self.inputs_txt.glob("*.S40"))
        
        for sepam_file in sepam_files:
            result = detect_active_functions(sepam_file)
            results.append(result)
            
            if result['success']:
                logger.info(f"  ✅ {result['relay_file']}: {', '.join(result['active_functions'])}")
                self.stats['sepam_processados'] += 1
                
                # Conta funções
                for func in result['active_functions']:
                    self.stats['funcoes_detectadas'][func] = \
                        self.stats['funcoes_detectadas'].get(func, 0) + 1
            else:
                logger.warning(f"  ⚠️  {result['relay_file']}: {result.get('error')}")
        
        # Processa MICONs (via CSVs gerados)
        logger.info("\n📁 MICON (PDFs):")
        pdf_files = sorted(self.inputs_pdf.glob("*.pdf"))
        
        for pdf_file in pdf_files:
            result = detect_active_functions(pdf_file)
            results.append(result)
            
            if result['success']:
                if result['active_functions']:
                    logger.info(f"  ✅ {result['relay_file']}: {', '.join(result['active_functions'])}")
                else:
                    logger.info(f"  ℹ️  {result['relay_file']}: Nenhuma função ativa detectada")
                
                # Conta funções
                for func in result['active_functions']:
                    self.stats['funcoes_detectadas'][func] = \
                        self.stats['funcoes_detectadas'].get(func, 0) + 1
            else:
                logger.warning(f"  ⚠️  {result['relay_file']}: {result.get('error')}")
        
        return results
    
    def generate_report(self, results: List[Dict]):
        """
        Gera relatório consolidado de funções ativas.
        
        Args:
            results: Lista de resultados da detecção
        """
        logger.info("\n" + "="*80)
        logger.info("📊 GERANDO RELATÓRIO")
        logger.info("="*80)
        
        # Cria diretório de relatórios
        self.outputs_reports.mkdir(exist_ok=True)
        
        # Relatório detalhado por relé
        report_data = []
        for result in results:
            if result['success']:
                report_data.append({
                    'relay_file': result['relay_file'],
                    'model': result['model'],
                    'detection_method': result['detection_method'],
                    'active_functions': ', '.join(result['active_functions']),
                    'total_active': len(result['active_functions']),
                    'total_functions': result['total_functions']
                })
        
        df_report = pd.DataFrame(report_data)
        
        # Salva CSV
        report_path = self.outputs_reports / "funcoes_ativas_consolidado.csv"
        df_report.to_csv(report_path, index=False)
        logger.info(f"\n✅ Relatório salvo: {report_path}")
        
        # Estatísticas gerais
        logger.info("\n" + "="*80)
        logger.info("📈 ESTATÍSTICAS GERAIS")
        logger.info("="*80)
        logger.info(f"PDFs processados: {self.stats['pdfs_processados']}")
        logger.info(f"SEPAMs processados: {self.stats['sepam_processados']}")
        logger.info(f"\nFunções detectadas (consolidado):")
        
        for func, count in sorted(self.stats['funcoes_detectadas'].items()):
            logger.info(f"  {func}: {count} relés")
        
        # Salva estatísticas em JSON
        stats_path = self.outputs_reports / "estatisticas_processamento.json"
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        logger.info(f"\n✅ Estatísticas salvas: {stats_path}")
    
    def run(self):
        """Executa pipeline completa."""
        logger.info("\n" + "="*80)
        logger.info("🚀 INICIANDO REPROCESSAMENTO COMPLETO DA PIPELINE")
        logger.info("="*80)
        
        # ETAPA 1: Extrair parâmetros dos PDFs
        self.process_all_pdfs()
        
        # ETAPA 2: Detectar funções ativas
        results = self.detect_all_functions()
        
        # ETAPA 3: Gerar relatório
        self.generate_report(results)
        
        logger.info("\n" + "="*80)
        logger.info("✅ PIPELINE CONCLUÍDA COM SUCESSO!")
        logger.info("="*80 + "\n")


def main():
    """Ponto de entrada."""
    processor = PipelineReprocessor()
    processor.run()


if __name__ == "__main__":
    main()

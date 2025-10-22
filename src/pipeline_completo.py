#!/usr/bin/env python3
"""
Pipeline Completo ProtecAI - Orquestrador de Processo UNIFICADO
==============================================================

NOVA ARQUITETURA UNIFICADA:
1. Conversão Universal (inputs/{pdf,txt,xlsx,csv} → outputs/csv/ padronizado)
2. Limpeza de dados (outputs/csv/ → outputs/atrib_limpos/)
3. Normalização (outputs/atrib_limpos/ → outputs/norm_*)
4. Importação para PostgreSQL (outputs/norm_csv/ → DB)

BENEFÍCIOS DA UNIFICAÇÃO:
- Pipeline único e consistente para todos os formatos
- Facilita manutenção e debugging
- Padronização de dados desde o início
- Análise comparativa simplificada

Uso:
    python src/pipeline_completo.py
    python src/pipeline_completo.py --skip-normalization
    python src/pipeline_completo.py --only-extract

Autor: Sistema ProtecAI
Data: 2025-10-18
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import subprocess
import json
import shutil

# Configurações
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]
SRC_DIR = PROJECT_ROOT / "src"

class ProtecaiPipelineOrchestrator:
    """Orquestrador do pipeline completo ProtecAI."""
    
    def __init__(self, verbose: bool = False):
        """
        Inicializa o orquestrador.
        
        Args:
            verbose: Se True, mostra saída detalhada
        """
        self.verbose = verbose
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.stats = {
            'inicio': datetime.now().isoformat(),
            'etapas_executadas': [],
            'arquivos_processados': {},
            'erros': [],
            'warnings': []
        }
        
        print(f"🚀 ProtecAI Pipeline - Iniciado em {self.timestamp}")
        if self.verbose:
            print(f"📁 Diretório do projeto: {PROJECT_ROOT}")
    
    def log_info(self, msg: str):
        """Log de informação."""
        print(f"ℹ️  {msg}")
    
    def log_success(self, msg: str):
        """Log de sucesso."""
        print(f"✅ {msg}")
    
    def log_warning(self, msg: str):
        """Log de warning."""
        print(f"⚠️  {msg}")
        self.stats['warnings'].append(msg)
    
    def log_error(self, msg: str):
        """Log de erro."""
        print(f"❌ {msg}")
        self.stats['erros'].append(msg)
    
    def verificar_ambiente(self) -> bool:
        """Verifica se o ambiente está configurado corretamente."""
        self.log_info("Verificando ambiente...")
        
        # Verificar estrutura de diretórios
        dirs_necessarios = [
            PROJECT_ROOT / "inputs" / "pdf",
            PROJECT_ROOT / "inputs" / "txt", 
            PROJECT_ROOT / "inputs" / "xlsx",
            PROJECT_ROOT / "inputs" / "csv",
            PROJECT_ROOT / "inputs" / "registry",
            PROJECT_ROOT / "outputs" / "csv",
            PROJECT_ROOT / "outputs" / "atrib_limpos",
            PROJECT_ROOT / "outputs" / "norm_csv",
            PROJECT_ROOT / "outputs" / "norm_excel",
            PROJECT_ROOT / "outputs" / "logs"
        ]
        
        for dir_path in dirs_necessarios:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                self.log_info(f"Criado diretório: {dir_path.relative_to(PROJECT_ROOT)}")
        
        # Verificar scripts principais
        scripts_necessarios = [
            SRC_DIR / "app.py",
            SRC_DIR / "normalizador.py"
        ]
        
        for script in scripts_necessarios:
            if not script.exists():
                self.log_error(f"Script não encontrado: {script}")
                return False
        
        self.log_success("Ambiente verificado e configurado")
        return True
    
    def contar_arquivos_entrada(self) -> Dict[str, int]:
        """Conta arquivos de entrada por formato."""
        contadores = {}
        
        formatos = {
            'pdf': PROJECT_ROOT / "inputs" / "pdf",
            'txt': PROJECT_ROOT / "inputs" / "txt",
            'xlsx': PROJECT_ROOT / "inputs" / "xlsx", 
            'csv': PROJECT_ROOT / "inputs" / "csv"
        }
        
        for formato, dir_path in formatos.items():
            if dir_path.exists():
                if formato == 'txt':
                    # Incluir arquivos .txt e .S40
                    arquivos = list(dir_path.glob("*.txt")) + list(dir_path.glob("*.S40"))
                else:
                    arquivos = list(dir_path.glob(f"*.{formato}"))
                contadores[formato] = len(arquivos)
                
                if arquivos and self.verbose:
                    self.log_info(f"Arquivos {formato.upper()}: {[f.name for f in arquivos]}")
            else:
                contadores[formato] = 0
        
        return contadores
    
    def executar_conversao_universal(self) -> bool:
        """
        Executa a conversão universal de todos os formatos para CSV padronizado.
        
        Returns:
            True se sucesso
        """
        self.log_info("Etapa 1: Conversão Universal Multi-formato")
        
        # Contar arquivos de entrada
        contadores = self.contar_arquivos_entrada()
        total_arquivos = sum(contadores.values())
        
        if total_arquivos == 0:
            self.log_warning("Nenhum arquivo de entrada encontrado")
            return True  # Não é erro, apenas não há trabalho
        
        self.log_info(f"Arquivos encontrados: {contadores}")
        
        try:
            # Executar conversor universal
            cmd = [sys.executable, str(SRC_DIR / "universal_format_converter.py")]
            
            if self.verbose:
                cmd.append("--verbose")
                self.log_info(f"Executando: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log_success("Conversão universal concluída com sucesso")
                if self.verbose and result.stdout:
                    print(result.stdout)
            elif result.returncode == 2:
                self.log_warning("Nenhum arquivo foi convertido (pode ser normal)")
                if self.verbose and result.stdout:
                    print(result.stdout)
            else:
                self.log_error(f"Erro na conversão universal: {result.stderr}")
                return False
            
            self.stats['etapas_executadas'].append('conversao_universal')
            self.stats['arquivos_processados']['entrada'] = contadores
            return True
            
        except Exception as e:
            self.log_error(f"Erro na conversão universal: {e}")
            return False
    
    def sincronizar_dados_limpos(self) -> bool:
        """
        Sincroniza outputs/csv/ -> outputs/atrib_limpos/ para o normalizador.
        
        Returns:
            True se sucesso
        """
        self.log_info("Etapa 2: Sincronização de Dados Limpos")
        
        csv_dir = PROJECT_ROOT / "outputs" / "csv"
        atrib_limpos_dir = PROJECT_ROOT / "outputs" / "atrib_limpos"
        
        if not csv_dir.exists():
            self.log_warning("Diretório outputs/csv/ não encontrado")
            return True
        
        # Buscar CSVs de parâmetros (não os de análise)
        csv_files = list(csv_dir.glob("*_params.csv"))
        
        if not csv_files:
            self.log_warning("Nenhum arquivo *_params.csv encontrado")
            return True
        
        arquivos_sincronizados = 0
        
        for csv_file in csv_files:
            # Converter CSV para Excel limpo
            excel_name = csv_file.stem + "_clean.xlsx"
            excel_path = atrib_limpos_dir / excel_name
            
            try:
                # Usar pandas para converter CSV -> Excel
                import pandas as pd
                
                df = pd.read_csv(csv_file)
                df.to_excel(excel_path, index=False, engine='openpyxl')
                
                self.log_success(f"Sincronizado: {csv_file.name} -> {excel_name}")
                arquivos_sincronizados += 1
                
            except Exception as e:
                self.log_error(f"Erro ao sincronizar {csv_file.name}: {e}")
                return False
        
        self.stats['etapas_executadas'].append('sincronizacao_dados_limpos')
        self.stats['arquivos_processados']['limpos'] = arquivos_sincronizados
        return True
    
    def executar_normalizacao(self) -> bool:
        """
        Executa normalização usando normalizador.py.
        
        Returns:
            True se sucesso
        """
        self.log_info("Etapa 3: Normalização de Códigos")
        
        try:
            cmd = [sys.executable, str(SRC_DIR / "normalizador.py")]
            
            if self.verbose:
                self.log_info(f"Executando: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log_success("Normalização concluída com sucesso")
                if self.verbose and result.stdout:
                    print(result.stdout)
            else:
                self.log_error(f"Erro na normalização: {result.stderr}")
                return False
            
            self.stats['etapas_executadas'].append('normalizacao')
            return True
            
        except Exception as e:
            self.log_error(f"Erro na normalização: {e}")
            return False
    
    def executar_importacao_db(self) -> bool:
        """
        Executa importação para PostgreSQL (opcional).
        
        Returns:
            True se sucesso
        """
        self.log_info("Etapa 4: Importação para PostgreSQL")
        
        # Verificar se há dados normalizados
        norm_csv_dir = PROJECT_ROOT / "outputs" / "norm_csv"
        if not norm_csv_dir.exists() or not list(norm_csv_dir.glob("*_normalized.csv")):
            self.log_warning("Nenhum arquivo normalizado encontrado para importação")
            return True
        
        try:
            cmd = [sys.executable, str(SRC_DIR / "importar_dados_normalizado.py")]
            
            if self.verbose:
                self.log_info(f"Executando: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log_success("Importação para PostgreSQL concluída")
                if self.verbose and result.stdout:
                    print(result.stdout)
            else:
                self.log_warning(f"Importação DB falhou (pode ser normal se DB não estiver ativo): {result.stderr}")
                # Não retornamos False pois DB pode não estar ativo
            
            self.stats['etapas_executadas'].append('importacao_db')
            return True
            
        except Exception as e:
            self.log_warning(f"Erro na importação DB: {e}")
            return True  # Não é erro crítico
    
    def executar_pipeline_completo(self, skip_normalization: bool = False, 
                                  skip_db: bool = False) -> Dict:
        """
        Executa o pipeline completo.
        
        Args:
            skip_normalization: Se True, pula normalização
            skip_db: Se True, pula importação para DB
            
        Returns:
            Dicionário com estatísticas
        """
        inicio = datetime.now()
        
        # Verificar ambiente
        if not self.verificar_ambiente():
            self.stats['fim'] = datetime.now().isoformat()
            self.stats['sucesso'] = False
            return self.stats
        
        # Etapa 1: Conversão universal multi-formato
        if not self.executar_conversao_universal():
            self.stats['fim'] = datetime.now().isoformat()
            self.stats['sucesso'] = False
            return self.stats
        
        # Etapa 2: Sincronização de dados limpos
        if not self.sincronizar_dados_limpos():
            self.stats['fim'] = datetime.now().isoformat()
            self.stats['sucesso'] = False
            return self.stats
        
        # Etapa 3: Normalização (opcional)
        if not skip_normalization:
            if not self.executar_normalizacao():
                self.stats['fim'] = datetime.now().isoformat()
                self.stats['sucesso'] = False
                return self.stats
        
        # Etapa 4: Importação DB (opcional)
        if not skip_db:
            self.executar_importacao_db()  # Não falha o pipeline se der erro
        
        # Estatísticas finais
        fim = datetime.now()
        self.stats.update({
            'fim': fim.isoformat(),
            'duracao_segundos': (fim - inicio).total_seconds(),
            'sucesso': True
        })
        
        self.log_success("Pipeline completo executado com sucesso! 🎉")
        return self.stats
    
    def mostrar_resumo(self):
        """Mostra resumo final do processamento."""
        print("\n" + "="*60)
        print("📊 RESUMO DO PIPELINE PROTECAI")
        print("="*60)
        
        print(f"⏱️  Duração: {self.stats.get('duracao_segundos', 0):.1f}s")
        print(f"🎯 Sucesso: {'✅ Sim' if self.stats.get('sucesso') else '❌ Não'}")
        print()
        
        print("🔄 Etapas Executadas:")
        for etapa in self.stats['etapas_executadas']:
            print(f"  • {etapa}")
        
        if self.stats['arquivos_processados']:
            print("\n📁 Arquivos Processados:")
            for categoria, dados in self.stats['arquivos_processados'].items():
                if isinstance(dados, dict):
                    print(f"  • {categoria}: {dados}")
                else:
                    print(f"  • {categoria}: {dados}")
        
        if self.stats['warnings']:
            print(f"\n⚠️  Warnings ({len(self.stats['warnings'])}):")
            for warning in self.stats['warnings']:
                print(f"  • {warning}")
        
        if self.stats['erros']:
            print(f"\n❌ Erros ({len(self.stats['erros'])}):")
            for erro in self.stats['erros']:
                print(f"  • {erro}")
        
        print("\n🗂️  Saídas Geradas:")
        print("  • outputs/csv/*_params.csv (dados extraídos)")
        print("  • outputs/csv/*_analysis_report.txt (relatórios)")  
        print("  • outputs/csv/*_config.json (configurações)")
        print("  • outputs/atrib_limpos/*_clean.xlsx (dados limpos)")
        print("  • outputs/norm_excel/*_normalized.xlsx (normalizados)")
        print("  • outputs/norm_csv/*_normalized.csv (normalizados)")
        print("  • outputs/logs/ (logs do sistema)")
        
        print("="*60)


def build_argparser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos."""
    parser = argparse.ArgumentParser(
        description="Pipeline Completo ProtecAI - Orquestrador de Processo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Pipeline completo
  python src/pipeline_completo.py
  
  # Apenas conversão universal (sem normalização)
  python src/pipeline_completo.py --only-extract
  
  # Pular normalização
  python src/pipeline_completo.py --skip-normalization
  
  # Pular importação DB
  python src/pipeline_completo.py --skip-db
  
  # Modo verbose
  python src/pipeline_completo.py --verbose

        """
    )
    
    parser.add_argument(
        '--only-extract',
        action='store_true',
        help='Executar apenas conversão universal multi-formato'
    )
    
    parser.add_argument(
        '--skip-normalization',
        action='store_true', 
        help='Pular etapa de normalização'
    )
    
    parser.add_argument(
        '--skip-db',
        action='store_true',
        help='Pular importação para PostgreSQL'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Saída detalhada'
    )
    
    return parser


def main() -> int:
    """Função principal."""
    args = build_argparser().parse_args()
    
    try:
        # Criar orquestrador
        pipeline = ProtecaiPipelineOrchestrator(verbose=args.verbose)
        
        if args.only_extract:
            # Apenas conversão universal
            pipeline.verificar_ambiente()
            sucesso = pipeline.executar_conversao_universal()
            pipeline.stats['sucesso'] = sucesso
        else:
            # Pipeline completo
            stats = pipeline.executar_pipeline_completo(
                skip_normalization=args.skip_normalization,
                skip_db=args.skip_db
            )
        
        # Mostrar resumo
        pipeline.mostrar_resumo()
        
        # Salvar relatório
        relatorio_path = PROJECT_ROOT / "outputs" / "logs" / f"pipeline_report_{pipeline.timestamp}.json"
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            json.dump(pipeline.stats, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Relatório salvo: {relatorio_path.relative_to(PROJECT_ROOT)}")
        
        return 0 if pipeline.stats.get('sucesso', False) else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  Pipeline interrompido pelo usuário")
        return 130
        
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
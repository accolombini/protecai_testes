# -*- coding: utf-8 -*-
"""
Script principal para normalização de códigos multivalorados de proteção.

Este script executa todo o pipeline de normalização:
1. Lê arquivos de outputs/atrib_limpos/
2. Detecta e normaliza códigos multivalorados 
3. Gera Excel consolidado normalizado
4. Gera documentação DOCX explicativa
5. Salva ambos em outputs/doc/

Uso:
    python -m src.normalizador
    python src/normalizador.py
    python src/normalizador.py --input-dir custom_dir --output-dir custom_out

Autor: Sistema ProtecAI
Data: 2025-10-03
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Imports dos módulos de normalização
try:
    from .utils.generate_normalized_excel import NormalizedExcelGenerator
    from .utils.generate_docx_documentation import DocxDocumentationGenerator
    from .utils.code_parser import CodeParser
except ImportError:
    # Para execução direta
    sys.path.append(str(Path(__file__).parent))
    from utils.generate_normalized_excel import NormalizedExcelGenerator
    from utils.generate_docx_documentation import DocxDocumentationGenerator
    from utils.code_parser import CodeParser


# Configurações padrão
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1] if 'src' in THIS_FILE.parts else THIS_FILE.parent
DEFAULT_INPUT_DIR = REPO_ROOT / "outputs" / "atrib_limpos"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "doc"


class ProtecaiNormalizer:
    """Classe principal para normalização de códigos de proteção."""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        """
        Inicializa o normalizador.
        
        Args:
            input_dir: Diretório com arquivos a processar
            output_dir: Diretório para salvar resultados
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Garantir que diretórios existem
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Diretório de entrada não encontrado: {self.input_dir}")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Componentes
        self.parser = CodeParser()
        self.excel_generator = NormalizedExcelGenerator()
        self.docx_generator = DocxDocumentationGenerator()
        
        print(f"[INFO] Normalizador inicializado:")
        print(f"       Entrada: {self.input_dir}")
        print(f"       Saída: {self.output_dir}")
    
    def run_full_pipeline(self) -> dict:
        """
        Executa o pipeline completo de normalização.
        
        Returns:
            Dicionário com caminhos dos arquivos gerados e estatísticas
        """
        print("[INFO] Iniciando pipeline completo de normalização...")
        
        results = {
            'excel_path': None,
            'docx_path': None,
            'stats': {},
            'timestamp': self.timestamp,
            'success': False
        }
        
        try:
            # Etapa 1: Processar dados e gerar Excel normalizado
            print("\n[ETAPA 1] Processando dados e gerando Excel normalizado...")
            excel_path = self._generate_normalized_excel()
            results['excel_path'] = excel_path
            
            # Etapa 2: Gerar documentação DOCX
            print("\n[ETAPA 2] Gerando documentação DOCX...")
            docx_path = self._generate_docx_documentation()
            results['docx_path'] = docx_path
            
            # Etapa 3: Coletar estatísticas
            results['stats'] = self.excel_generator.stats.copy()
            results['success'] = True
            
            print("\n[SUCESSO] Pipeline concluído com sucesso!")
            self._print_summary(results)
            
            return results
            
        except Exception as e:
            print(f"\n[ERRO] Falha no pipeline: {e}")
            import traceback
            traceback.print_exc()
            results['error'] = str(e)
            return results
    
    def _generate_normalized_excel(self) -> Path:
        """Gera o Excel normalizado."""
        # Processar dados
        self.excel_generator.process_directory(self.input_dir)
        
        if not self.excel_generator.normalized_rows:
            raise ValueError("Nenhum dado foi processado para normalização.")
        
        # Gerar Excel com nome timestamped
        excel_filename = f"codigos_normalizados_{self.timestamp}.xlsx"
        excel_path = self.output_dir / excel_filename
        
        generated_path = self.excel_generator.generate_excel(excel_path)
        
        # Também gerar versão "latest" para facilitar uso
        latest_path = self.output_dir / "codigos_normalizados_latest.xlsx"
        import shutil
        shutil.copy2(generated_path, latest_path)
        print(f"[INFO] Cópia 'latest' criada: {latest_path}")
        
        return generated_path
    
    def _generate_docx_documentation(self) -> Path:
        """Gera a documentação DOCX."""
        # Reutilizar dados já processados pelo excel_generator
        self.docx_generator.excel_generator = self.excel_generator
        self.docx_generator.distinct_values = self.excel_generator.get_distinct_values_for_doc()
        self.docx_generator.stats = self.excel_generator.stats.copy()
        
        # Gerar DOCX com nome timestamped
        docx_filename = f"documentacao_codigos_{self.timestamp}.docx"
        docx_path = self.output_dir / docx_filename
        
        generated_path = self.docx_generator.generate_documentation(docx_path)
        
        # Também gerar versão "latest"
        latest_path = self.output_dir / "documentacao_codigos_latest.docx"
        import shutil
        shutil.copy2(generated_path, latest_path)
        print(f"[INFO] Cópia 'latest' criada: {latest_path}")
        
        return generated_path
    
    def _print_summary(self, results: dict) -> None:
        """Imprime resumo dos resultados."""
        print("\n" + "="*60)
        print("RESUMO DO PROCESSAMENTO")
        print("="*60)
        
        stats = results.get('stats', {})
        
        print(f"Timestamp: {results['timestamp']}")
        print(f"Entrada: {self.input_dir}")
        print(f"Saída: {self.output_dir}")
        print()
        
        print("ESTATÍSTICAS:")
        print(f"  • Arquivos processados: {stats.get('files_processed', 0)}")
        print(f"  • Total de valores analisados: {stats.get('total_values', 0)}")
        print(f"  • Valores multivalorados: {stats.get('multivalued_found', 0)}")
        print(f"  • Valores atômicos: {stats.get('atomic_values', 0)}")
        print(f"  • Tokens extraídos: {stats.get('tokens_extracted', 0)}")
        
        if stats.get('total_values', 0) > 0:
            multivalued_pct = (stats.get('multivalued_found', 0) / stats['total_values']) * 100
            print(f"  • % Multivalorados: {multivalued_pct:.1f}%")
        
        print()
        print("ARQUIVOS GERADOS:")
        if results.get('excel_path'):
            print(f"  • Excel normalizado: {results['excel_path'].name}")
        if results.get('docx_path'):
            print(f"  • Documentação DOCX: {results['docx_path'].name}")
        
        print()
        print("ARQUIVOS 'LATEST' (para uso fácil):")
        print(f"  • {self.output_dir / 'codigos_normalizados_latest.xlsx'}")
        print(f"  • {self.output_dir / 'documentacao_codigos_latest.docx'}")
        
        print("="*60)
    
    def generate_excel_only(self) -> Path:
        """Gera apenas o Excel normalizado."""
        print("[INFO] Gerando apenas Excel normalizado...")
        return self._generate_normalized_excel()
    
    def generate_docx_only(self) -> Path:
        """Gera apenas a documentação DOCX."""
        print("[INFO] Gerando apenas documentação DOCX...")
        
        # Precisamos processar os dados primeiro
        self.docx_generator.process_data(self.input_dir)
        
        # Gerar DOCX
        docx_filename = f"documentacao_codigos_{self.timestamp}.docx"
        docx_path = self.output_dir / docx_filename
        
        return self.docx_generator.generate_documentation(docx_path)
    
    def test_parser(self, test_values: list) -> None:
        """
        Testa o parser com valores específicos.
        
        Args:
            test_values: Lista de valores para testar
        """
        print("[INFO] Testando parser com valores fornecidos...")
        
        parser = CodeParser()
        
        for value in test_values:
            print(f"\n--- Testando: '{value}' ---")
            result = parser.parse_value(value)
            
            print(f"Padrão detectado: {result.pattern_detected}")
            print(f"É atômico: {result.is_atomic}")
            
            if result.tokens:
                print("Tokens extraídos:")
                for i, token in enumerate(result.tokens):
                    print(f"  {i+1}. '{token.value}' [{token.token_type.value}] = {token.meaning} (conf: {token.confidence:.2f})")
            else:
                print("Nenhum token extraído.")


def build_argparser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Normalizador de códigos multivalorados de proteção ProtecAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Pipeline completo (padrão)
  python src/normalizador.py
  
  # Apenas Excel
  python src/normalizador.py --excel-only
  
  # Apenas DOCX  
  python src/normalizador.py --docx-only
  
  # Diretórios customizados
  python src/normalizador.py --input-dir /path/to/data --output-dir /path/to/output
  
  # Testar parser
  python src/normalizador.py --test "52-MP-20" "P241311B2M0600J"

        """
    )
    
    parser.add_argument(
        '--input-dir',
        type=str,
        default=DEFAULT_INPUT_DIR,
        help=f'Diretório de entrada (padrão: {DEFAULT_INPUT_DIR})'
    )
    
    parser.add_argument(
        '--output-dir', 
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f'Diretório de saída (padrão: {DEFAULT_OUTPUT_DIR})'
    )
    
    # Opções de execução
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--excel-only',
        action='store_true',
        help='Gerar apenas Excel normalizado'
    )
    
    group.add_argument(
        '--docx-only',
        action='store_true', 
        help='Gerar apenas documentação DOCX'
    )
    
    group.add_argument(
        '--test',
        nargs='+',
        metavar='VALUE',
        help='Testar parser com valores específicos'
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
        # Modo de teste
        if args.test:
            normalizer = ProtecaiNormalizer(args.input_dir, args.output_dir)
            normalizer.test_parser(args.test)
            return 0
        
        # Criar normalizador
        normalizer = ProtecaiNormalizer(args.input_dir, args.output_dir)
        
        # Executar modo selecionado
        if args.excel_only:
            path = normalizer.generate_excel_only()
            print(f"[SUCESSO] Excel gerado: {path}")
            
        elif args.docx_only:
            path = normalizer.generate_docx_only()
            print(f"[SUCESSO] DOCX gerado: {path}")
            
        else:
            # Pipeline completo
            results = normalizer.run_full_pipeline()
            if not results.get('success'):
                return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n[INFO] Processamento interrompido pelo usuário.")
        return 130
        
    except Exception as e:
        print(f"[ERRO] Falha na execução: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
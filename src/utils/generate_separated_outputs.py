# -*- coding: utf-8 -*-
"""
Gerador de saídas normalizadas separadas por arquivo com duplo formato.

Este módulo:
1. Processa cada arquivo de entrada separadamente  
2. Gera Excel + CSV para cada arquivo (tela1, tela3, etc.)
3. Estrutura preparada para identificação de fabricantes
4. Foco na normalização para futuras tabelas de BD

Estrutura de saída:
- outputs/norm_excel/tela1_params_normalized.xlsx
- outputs/norm_csv/tela1_params_normalized.csv
- outputs/norm_excel/tela3_params_normalized.xlsx  
- outputs/norm_csv/tela3_params_normalized.csv

Autor: Sistema ProtecAI
Data: 2025-10-05
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from datetime import datetime

# Importar o parser de códigos
try:
    from .code_parser import CodeParser, ParseResult
except ImportError:
    sys.path.append(str(Path(__file__).parent))
    from code_parser import CodeParser, ParseResult


# Configurações de diretórios
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[2]
INPUT_DIR = REPO_ROOT / "outputs" / "atrib_limpos"
OUTPUT_EXCEL_DIR = REPO_ROOT / "outputs" / "norm_excel"
OUTPUT_CSV_DIR = REPO_ROOT / "outputs" / "norm_csv"

# Garantir que os diretórios de saída existem
OUTPUT_EXCEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV_DIR.mkdir(parents=True, exist_ok=True)


class SeparatedOutputsGenerator:
    """Gerador de saídas normalizadas separadas por arquivo."""
    
    def __init__(self):
        self.parser = CodeParser()
        self.processed_files: List[Dict[str, Any]] = []
        self.global_stats = {
            'files_processed': 0,
            'total_values': 0,
            'multivalued_found': 0,
            'atomic_values': 0,
            'tokens_extracted': 0
        }
    
    def process_all_files(self, input_dir: Path = INPUT_DIR) -> None:
        """
        Processa todos os arquivos do diretório de entrada.
        
        Args:
            input_dir: Diretório contendo os arquivos a processar
        """
        if not input_dir.exists():
            raise FileNotFoundError(f"Diretório de entrada não encontrado: {input_dir}")
        
        # Buscar arquivos válidos
        valid_extensions = {'.xlsx', '.xls', '.csv'}
        files = [
            f for f in input_dir.iterdir() 
            if f.suffix.lower() in valid_extensions and not f.name.startswith('~$')
        ]
        
        if not files:
            print(f"[AVISO] Nenhum arquivo válido encontrado em {input_dir}")
            return
        
        print(f"[INFO] Processando {len(files)} arquivo(s) separadamente...")
        
        for file_path in sorted(files):
            self._process_single_file(file_path)
        
        # Gerar resumo consolidado
        self._generate_summary()
        
        print(f"\\n[INFO] Processamento completo concluído:")
        print(f"  - Arquivos processados: {self.global_stats['files_processed']}")
        print(f"  - Total de valores: {self.global_stats['total_values']}")
        print(f"  - Valores multivalorados: {self.global_stats['multivalued_found']}")
        print(f"  - Valores atômicos: {self.global_stats['atomic_values']}")
        print(f"  - Tokens extraídos: {self.global_stats['tokens_extracted']}")
    
    def _process_single_file(self, file_path: Path) -> None:
        """
        Processa um arquivo individual.
        
        Args:
            file_path: Caminho para o arquivo a processar
        """
        print(f"\\n[INFO] Processando: {file_path.name}")
        
        try:
            # Extrair identificador do arquivo (tela1, tela3, etc.)
            file_identifier = self._extract_file_identifier(file_path.name)
            
            # Detectar fabricante (placeholder - pode ser melhorado)
            manufacturer = self._detect_manufacturer(file_path.name)
            
            # Ler o arquivo
            df = self._read_file(file_path)
            
            if df.empty:
                print(f"[AVISO] Arquivo {file_path.name} está vazio")
                return
            
            # Processar dados do arquivo
            normalized_data = self._normalize_file_data(df, file_path.name, file_identifier, manufacturer)
            
            # Gerar saídas (Excel + CSV)
            self._generate_file_outputs(normalized_data, file_identifier)
            
            # Atualizar estatísticas globais
            self._update_global_stats(normalized_data)
            
            # Salvar informações do arquivo processado
            self.processed_files.append({
                'file_path': str(file_path),
                'file_identifier': file_identifier,
                'manufacturer': manufacturer,
                'total_rows': len(normalized_data),
                'multivalued_count': len([r for r in normalized_data if not r['eh_atomico']]),
                'atomic_count': len([r for r in normalized_data if r['eh_atomico']])
            })
            
            print(f"[OK] {file_path.name} processado: {len(normalized_data)} registros")
            
        except Exception as e:
            print(f"[ERRO] Falha ao processar {file_path.name}: {e}")
    
    def _extract_file_identifier(self, filename: str) -> str:
        """Extrai identificador do arquivo (tela1, tela3, etc.)."""
        filename_lower = filename.lower()
        
        # Padrões conhecidos
        if 'tela1' in filename_lower:
            return 'tela1'
        elif 'tela3' in filename_lower:
            return 'tela3'
        else:
            # Tentar extrair padrão genérico
            import re
            match = re.search(r'(tela\d+)', filename_lower)
            if match:
                return match.group(1)
            else:
                # Usar base do nome do arquivo
                return Path(filename).stem.split('_')[0]
    
    def _detect_manufacturer(self, filename: str) -> str:
        """Detecta fabricante baseado no nome do arquivo (placeholder)."""
        filename_lower = filename.lower()
        
        # Heurísticas simples baseadas nos exemplos
        if 'tela1' in filename_lower:
            return 'schneider'  # Exemplo: tela1 = Schneider
        elif 'tela3' in filename_lower:
            return 'abb'        # Exemplo: tela3 = ABB
        else:
            return 'unknown'
    
    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Lê arquivo Excel ou CSV."""
        if file_path.suffix.lower() == '.csv':
            return pd.read_csv(file_path, dtype=str)
        else:
            # Excel - ler primeira aba
            return pd.read_excel(file_path, dtype=str)
    
    def _normalize_file_data(
        self, 
        df: pd.DataFrame, 
        filename: str, 
        file_identifier: str, 
        manufacturer: str
    ) -> List[Dict[str, Any]]:
        """
        Normaliza dados de um arquivo.
        
        Args:
            df: DataFrame com dados do arquivo
            filename: Nome do arquivo
            file_identifier: Identificador do arquivo (tela1, tela3)
            manufacturer: Fabricante detectado
            
        Returns:
            Lista de registros normalizados
        """
        normalized_rows = []
        
        # Detectar colunas importantes
        value_columns = []
        code_column = None
        desc_column = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'code' in col_lower or 'codigo' in col_lower:
                code_column = col
            elif 'description' in col_lower or 'desc' in col_lower or 'descricao' in col_lower:
                desc_column = col
            elif 'value' in col_lower or 'valor' in col_lower:
                value_columns.append(col)
        
        if not value_columns:
            value_columns = [col for col in df.columns if df[col].dtype == object]
        
        # Processar cada linha
        for idx, row in df.iterrows():
            row_code = str(row.get(code_column, f"Row_{idx}")) if code_column else f"Row_{idx}"
            row_desc = str(row.get(desc_column, "")) if desc_column else ""
            
            # Processar cada coluna de valores
            for col in value_columns:
                if col in [code_column, desc_column]:
                    continue
                
                value = row.get(col)
                if pd.isna(value) or value == "" or str(value).strip() == "":
                    continue
                
                # Normalizar o valor
                normalized_row = self._normalize_single_value(
                    filename=filename,
                    file_identifier=file_identifier,
                    manufacturer=manufacturer,
                    field_code=row_code,
                    field_description=row_desc,
                    column_name=col,
                    value=str(value).strip()
                )
                
                if normalized_row:
                    normalized_rows.append(normalized_row)
        
        return normalized_rows
    
    def _normalize_single_value(
        self,
        filename: str,
        file_identifier: str,
        manufacturer: str,
        field_code: str,
        field_description: str,
        column_name: str,
        value: str
    ) -> Optional[Dict[str, Any]]:
        """
        Normaliza um único valor.
        
        Returns:
            Dicionário com dados normalizados ou None se inválido
        """
        # Fazer parsing do valor
        parse_result = self.parser.parse_value(value)
        
        # Estrutura base para BD
        base_data = {
            'arquivo_origem': filename,
            'identificador_arquivo': file_identifier,
            'fabricante': manufacturer,
            'codigo_campo': field_code,
            'descricao_campo': field_description,
            'nome_coluna': column_name,
            'valor_original': value,
            'eh_atomico': parse_result.is_atomic,
            'padrao_detectado': parse_result.pattern_detected,
            'processado_em': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if parse_result.is_atomic:
            # Valor atômico
            base_data.update({
                'num_partes': 1,
                'parte_1': value,
                'tipo_1': 'atomic',
                'significado_1': 'Valor atômico (não requer desmembramento)',
                'confianca_1': 1.0,
                'confianca_geral': 1.0
            })
        else:
            # Valor multivalorado
            if parse_result.tokens:
                base_data['num_partes'] = len(parse_result.tokens)
                
                # Adicionar cada parte/token
                for i, token in enumerate(parse_result.tokens, 1):
                    base_data[f'parte_{i}'] = token.value
                    base_data[f'tipo_{i}'] = token.token_type.value
                    base_data[f'significado_{i}'] = token.meaning
                    base_data[f'confianca_{i}'] = round(token.confidence, 3)
                
                # Confiança geral
                total_confidence = sum(token.confidence for token in parse_result.tokens)
                base_data['confianca_geral'] = round(total_confidence / len(parse_result.tokens), 3)
            else:
                # Valor não interpretado
                base_data.update({
                    'num_partes': 0,
                    'parte_1': '',
                    'tipo_1': 'unknown',
                    'significado_1': 'Valor não reconhecido - revisar manualmente',
                    'confianca_1': 0.0,
                    'confianca_geral': 0.0
                })
        
        return base_data
    
    def _generate_file_outputs(self, normalized_data: List[Dict[str, Any]], file_identifier: str) -> None:
        """
        Gera saídas Excel + CSV para um arquivo.
        
        Args:
            normalized_data: Dados normalizados
            file_identifier: Identificador do arquivo (tela1, tela3)
        """
        if not normalized_data:
            print(f"[AVISO] Nenhum dado para gerar saída para {file_identifier}")
            return
        
        # Converter para DataFrame
        df = pd.DataFrame(normalized_data)
        
        # Definir nomes dos arquivos de saída
        base_filename = f"{file_identifier}_params_normalized"
        excel_path = OUTPUT_EXCEL_DIR / f"{base_filename}.xlsx"
        csv_path = OUTPUT_CSV_DIR / f"{base_filename}.csv"
        
        # Gerar Excel
        self._generate_excel_output(df, excel_path, file_identifier)
        
        # Gerar CSV
        self._generate_csv_output(df, csv_path, file_identifier)
        
        print(f"[OK] Saídas geradas para {file_identifier}:")
        print(f"     Excel: {excel_path}")
        print(f"     CSV: {csv_path}")
    
    def _generate_excel_output(self, df: pd.DataFrame, output_path: Path, file_identifier: str) -> None:
        """Gera saída Excel com formatação."""
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Aba principal com dados normalizados
            df.to_excel(writer, sheet_name='Dados Normalizados', index=False)
            
            # Aba de estatísticas do arquivo
            file_stats = [
                ['Arquivo', file_identifier],
                ['Total de registros', len(df)],
                ['Valores multivalorados', len(df[df['eh_atomico'] == False])],
                ['Valores atômicos', len(df[df['eh_atomico'] == True])],
                ['Data do processamento', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            ]
            
            stats_df = pd.DataFrame(file_stats, columns=['Métrica', 'Valor'])
            stats_df.to_excel(writer, sheet_name='Estatísticas', index=False)
            
            # Aba apenas com multivalorados
            multivalued_df = df[df['eh_atomico'] == False].copy()
            if not multivalued_df.empty:
                multivalued_df.to_excel(writer, sheet_name='Apenas Multivalorados', index=False)
    
    def _generate_csv_output(self, df: pd.DataFrame, output_path: Path, file_identifier: str) -> None:
        """Gera saída CSV."""
        df.to_csv(output_path, index=False, encoding='utf-8')
    
    def _update_global_stats(self, normalized_data: List[Dict[str, Any]]) -> None:
        """Atualiza estatísticas globais."""
        self.global_stats['files_processed'] += 1
        self.global_stats['total_values'] += len(normalized_data)
        
        for row in normalized_data:
            if row['eh_atomico']:
                self.global_stats['atomic_values'] += 1
            else:
                self.global_stats['multivalued_found'] += 1
                self.global_stats['tokens_extracted'] += row.get('num_partes', 0)
    
    def _generate_summary(self) -> None:
        """Gera resumo consolidado de todos os arquivos."""
        if not self.processed_files:
            return
        
        # Criar DataFrame de resumo
        summary_df = pd.DataFrame(self.processed_files)
        
        # Adicionar estatísticas globais
        global_summary = pd.DataFrame([
            ['Total de arquivos', self.global_stats['files_processed']],
            ['Total de valores', self.global_stats['total_values']],
            ['Valores multivalorados', self.global_stats['multivalued_found']],
            ['Valores atômicos', self.global_stats['atomic_values']],
            ['Tokens extraídos', self.global_stats['tokens_extracted']],
            ['Processado em', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ], columns=['Métrica', 'Valor'])
        
        # Gerar Excel de resumo
        summary_excel_path = OUTPUT_EXCEL_DIR / "summary_normalization.xlsx"
        with pd.ExcelWriter(summary_excel_path, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Resumo por Arquivo', index=False)
            global_summary.to_excel(writer, sheet_name='Estatísticas Globais', index=False)
        
        # Gerar CSV de resumo
        summary_csv_path = OUTPUT_CSV_DIR / "summary_normalization.csv"
        summary_df.to_csv(summary_csv_path, index=False, encoding='utf-8')
        
        print(f"\\n[OK] Resumo consolidado gerado:")
        print(f"     Excel: {summary_excel_path}")
        print(f"     CSV: {summary_csv_path}")


def main() -> int:
    """Função principal do script."""
    try:
        print("[INFO] Iniciando geração de saídas separadas...")
        
        # Criar o gerador
        generator = SeparatedOutputsGenerator()
        
        # Processar todos os arquivos
        generator.process_all_files()
        
        print("\\n[SUCESSO] Processamento completo concluído!")
        return 0
        
    except Exception as e:
        print(f"[ERRO] Falha no processamento: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
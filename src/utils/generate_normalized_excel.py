# -*- coding: utf-8 -*-
"""
Gerador de Excel normalizado para códigos multivalorados de proteção.

Este script:
1. Varre todos os arquivos em outputs/atrib_limpos/
2. Identifica campos multivalorados usando o parser
3. Gera Excel com colunas normalizadas
4. Salva em outputs/doc/

Colunas do Excel de saída:
- arquivo_origem: Nome do arquivo fonte
- codigo_campo: Código/ID do campo original  
- descricao_campo: Descrição do campo original
- valor_original: Valor bruto antes da normalização
- token: Parte/token individual extraído
- tipo_token: Tipo do token (ansi_code, protection_type, etc.)
- significado: Significado do token
- confianca: Nível de confiança da interpretação (0.0-1.0)
- posicao: Posição do token no valor original
- padrao_detectado: Padrão usado no parsing
- eh_atomico: True se o valor não precisa normalização

    ||> Nota: codigos_normalizados_latest.xlsx

Autor: Sistema ProtecAI
Data: 2025-10-03
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

# Importar o parser de códigos
try:
    from .code_parser import CodeParser, ParseResult, ParsedToken, TokenType
except ImportError:
    # Para execução direta
    sys.path.append(str(Path(__file__).parent))
    from code_parser import CodeParser, ParseResult, ParsedToken, TokenType


# Configurações de diretórios
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[2]
INPUT_DIR = REPO_ROOT / "outputs" / "atrib_limpos"
OUTPUT_DIR = REPO_ROOT / "outputs" / "doc"

# Garantir que o diretório de saída existe
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class NormalizedExcelGenerator:
    """Gerador de Excel normalizado para códigos multivalorados."""
    
    def __init__(self):
        self.parser = CodeParser()
        self.normalized_rows: List[Dict[str, Any]] = []
        self.max_tokens = 0  # Controla o número máximo de tokens encontrados
        self.stats = {
            'files_processed': 0,
            'total_values': 0,
            'multivalued_found': 0,
            'tokens_extracted': 0,
            'atomic_values': 0
        }
    
    def process_directory(self, input_dir: Path = INPUT_DIR) -> None:
        """
        Processa todos os arquivos Excel/CSV no diretório de entrada.
        
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
        
        print(f"[INFO] Processando {len(files)} arquivo(s)...")
        
        for file_path in sorted(files):
            self._process_file(file_path)
        
        print(f"[INFO] Processamento concluído:")
        print(f"  - Arquivos processados: {self.stats['files_processed']}")
        print(f"  - Valores analisados: {self.stats['total_values']}")
        print(f"  - Valores multivalorados: {self.stats['multivalued_found']}")
        print(f"  - Valores atômicos: {self.stats['atomic_values']}")
        print(f"  - Tokens extraídos: {self.stats['tokens_extracted']}")
    
    def _process_file(self, file_path: Path) -> None:
        """
        Processa um arquivo individual.
        
        Args:
            file_path: Caminho para o arquivo a processar
        """
        print(f"[INFO] Processando: {file_path.name}")
        
        try:
            # Ler o arquivo
            if file_path.suffix.lower() == '.csv':
                dataframes = [pd.read_csv(file_path, dtype=str)]
            else:
                # Excel pode ter múltiplas abas
                excel_file = pd.ExcelFile(file_path)
                dataframes = [
                    excel_file.parse(sheet, dtype=str) 
                    for sheet in excel_file.sheet_names
                ]
            
            # Processar cada DataFrame
            for i, df in enumerate(dataframes):
                sheet_name = f"Sheet{i+1}" if len(dataframes) > 1 else "Sheet1"
                self._process_dataframe(df, file_path.name, sheet_name)
            
            self.stats['files_processed'] += 1
            
        except Exception as e:
            print(f"[ERRO] Falha ao processar {file_path.name}: {e}")
    
    def _process_dataframe(self, df: pd.DataFrame, filename: str, sheet_name: str) -> None:
        """
        Processa um DataFrame individual.
        
        Args:
            df: DataFrame a processar
            filename: Nome do arquivo fonte
            sheet_name: Nome da aba (para arquivos Excel)
        """
        if df.empty:
            return
        
        # Assumir estrutura típica com colunas: Code, Description, Value
        # Mas ser flexível para outras estruturas
        value_columns = []
        code_column = None
        desc_column = None
        
        # Detectar colunas importantes
        for col in df.columns:
            col_lower = str(col).lower()
            if 'code' in col_lower or 'codigo' in col_lower:
                code_column = col
            elif 'description' in col_lower or 'desc' in col_lower or 'descricao' in col_lower:
                desc_column = col
            elif 'value' in col_lower or 'valor' in col_lower:
                value_columns.append(col)
        
        # Se não encontrou colunas específicas, usar todas as de texto
        if not value_columns:
            value_columns = [col for col in df.columns if df[col].dtype == object]
        
        # Processar cada linha
        for idx, row in df.iterrows():
            row_code = str(row.get(code_column, f"Row_{idx}")) if code_column else f"Row_{idx}"
            row_desc = str(row.get(desc_column, "")) if desc_column else ""
            
            # Processar cada coluna de valores
            for col in value_columns:
                if col in [code_column, desc_column]:
                    continue  # Não processar as próprias colunas de código/descrição
                
                value = row.get(col)
                if pd.isna(value) or value == "" or str(value).strip() == "":
                    continue
                
                self._process_value(
                    filename=filename,
                    sheet_name=sheet_name,
                    field_code=row_code,
                    field_description=row_desc,
                    column_name=col,
                    value=str(value).strip()
                )
    
    def _process_value(
        self, 
        filename: str, 
        sheet_name: str,
        field_code: str, 
        field_description: str,
        column_name: str,
        value: str
    ) -> None:
        """
        Processa um valor individual usando o parser.
        
        Args:
            filename: Nome do arquivo fonte
            sheet_name: Nome da aba
            field_code: Código do campo
            field_description: Descrição do campo
            column_name: Nome da coluna
            value: Valor a ser processado
        """
        self.stats['total_values'] += 1
        
        # Fazer parsing do valor
        parse_result = self.parser.parse_value(value)
        
        # Criar linha base com informações comuns
        row_data = {
            'arquivo_origem': filename,
            'aba': sheet_name,
            'codigo_campo': field_code,
            'descricao_campo': field_description,
            'nome_coluna': column_name,
            'valor_original': value,
            'eh_atomico': parse_result.is_atomic,
            'padrao_detectado': parse_result.pattern_detected,
            'num_tokens': len(parse_result.tokens),
            'processado_em': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if parse_result.is_atomic:
            # Valor atômico
            self.stats['atomic_values'] += 1
            row_data['confianca_geral'] = 1.0
        else:
            # Valor multivalorado
            self.stats['multivalued_found'] += 1
            
            if parse_result.tokens:
                # Atualizar número máximo de tokens se necessário
                if len(parse_result.tokens) > self.max_tokens:
                    self.max_tokens = len(parse_result.tokens)
                
                # Adicionar tokens como colunas horizontais
                for i, token in enumerate(parse_result.tokens):
                    token_num = i + 1
                    row_data[f'token_{token_num}_value'] = token.value
                    row_data[f'token_{token_num}_type'] = token.token_type.value
                    row_data[f'token_{token_num}_meaning'] = token.meaning
                    row_data[f'token_{token_num}_confidence'] = round(token.confidence, 3)
                    self.stats['tokens_extracted'] += 1
                
                # Calcular confiança geral como média das confianças dos tokens
                total_confidence = sum(token.confidence for token in parse_result.tokens)
                row_data['confianca_geral'] = round(total_confidence / len(parse_result.tokens), 3)
            else:
                # Caso especial: detectado como não-atômico mas sem tokens
                row_data['confianca_geral'] = 0.0
                row_data['token_1_value'] = ""
                row_data['token_1_type'] = "unknown"
                row_data['token_1_meaning'] = "Valor não reconhecido - revisar manualmente"
                row_data['token_1_confidence'] = 0.0
        
        # Adicionar a linha aos dados normalizados
        self.normalized_rows.append(row_data)
    
    def generate_excel(self, output_path: Optional[Path] = None) -> Path:
        """
        Gera o arquivo Excel normalizado.
        
        Args:
            output_path: Caminho de saída (opcional)
            
        Returns:
            Caminho do arquivo gerado
        """
        if not self.normalized_rows:
            raise ValueError("Nenhum dado foi processado. Execute process_directory() primeiro.")
        
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = OUTPUT_DIR / f"codigos_normalizados_{timestamp}.xlsx"
        
        # Converter para DataFrame
        df = pd.DataFrame(self.normalized_rows)
        
        # Garantir que todas as colunas de tokens existam (preenchendo com valores vazios)
        for i in range(1, self.max_tokens + 1):
            for suffix in ['_value', '_type', '_meaning', '_confidence']:
                col_name = f'token_{i}{suffix}'
                if col_name not in df.columns:
                    df[col_name] = ""
        
        # Definir ordem das colunas
        base_columns = [
            'arquivo_origem', 'aba', 'codigo_campo', 'descricao_campo', 
            'nome_coluna', 'valor_original', 'eh_atomico', 'padrao_detectado',
            'num_tokens', 'confianca_geral'
        ]
        
        # Adicionar colunas de tokens dinamicamente
        token_columns = []
        for i in range(1, self.max_tokens + 1):
            token_columns.extend([
                f'token_{i}_value',
                f'token_{i}_type', 
                f'token_{i}_meaning',
                f'token_{i}_confidence'
            ])
        
        # Coluna final
        final_columns = ['processado_em']
        
        # Reordenar colunas
        column_order = base_columns + token_columns + final_columns
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        # Ordenar por arquivo, campo
        df = df.sort_values(['arquivo_origem', 'codigo_campo', 'nome_coluna'])
        
        # Criar Excel com formatação
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Aba principal com todos os dados
            df.to_excel(writer, sheet_name='Códigos Normalizados', index=False)
            
            # Aba de estatísticas
            stats_df = pd.DataFrame([
                ['Arquivos processados', self.stats['files_processed']],
                ['Total de valores analisados', self.stats['total_values']],
                ['Valores multivalorados encontrados', self.stats['multivalued_found']],
                ['Valores atômicos', self.stats['atomic_values']],
                ['Tokens extraídos', self.stats['tokens_extracted']],
                ['Máximo de tokens por valor', self.max_tokens],
                ['Data/hora do processamento', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            ], columns=['Métrica', 'Valor'])
            stats_df.to_excel(writer, sheet_name='Estatísticas', index=False)
            
            # Aba de resumo por tipo de token (se houver dados)
            if not df.empty and self.max_tokens > 0:
                # Coletar todos os tipos de tokens
                token_types = []
                for i in range(1, self.max_tokens + 1):
                    type_col = f'token_{i}_type'
                    if type_col in df.columns:
                        types = df[type_col].dropna()
                        types = types[types != ""]
                        token_types.extend(types.tolist())
                
                if token_types:
                    from collections import Counter
                    type_counts = Counter(token_types)
                    summary_df = pd.DataFrame([
                        [token_type, count] 
                        for token_type, count in type_counts.most_common()
                    ], columns=['Tipo de Token', 'Quantidade'])
                    summary_df.to_excel(writer, sheet_name='Resumo por Tipo', index=False)
            
            # Aba apenas com valores multivalorados
            multivalued_df = df[df['eh_atomico'] == False].copy()
            if not multivalued_df.empty:
                multivalued_df.to_excel(writer, sheet_name='Apenas Multivalorados', index=False)
            
            # Configurar formatação básica
            workbook = writer.book
            
            # Formatação da aba principal
            worksheet = workbook['Códigos Normalizados']
            
            # Auto-ajustar largura das colunas (limitado para não ficar muito largo)
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                # Limitar largura máxima e definir mínima
                adjusted_width = min(max(max_length + 2, 10), 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return output_path
    
    def get_distinct_values_for_doc(self) -> pd.DataFrame:
        """
        Retorna DataFrame com valores distintos para geração de documentação.
        
        Returns:
            DataFrame com valores únicos e suas interpretações
        """
        if not self.normalized_rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.normalized_rows)
        
        # Agrupar por valor original e pegar as interpretações únicas
        distinct_values = []
        
        for original_value in df['valor_original'].unique():
            if not original_value or str(original_value).strip() == "":
                continue
                
            # Pegar informações do registro (uma linha por valor original)
            record = df[df['valor_original'] == original_value].iloc[0]
            
            # Construir interpretação dos tokens
            if record['eh_atomico']:
                interpretation = "Valor atômico (não requer desmembramento)"
                tokens_list = [original_value]
            else:
                tokens_info = []
                tokens_list = []
                
                # Iterar pelos tokens horizontais
                for i in range(1, self.max_tokens + 1):
                    token_value = record.get(f'token_{i}_value', '')
                    token_meaning = record.get(f'token_{i}_meaning', '')
                    
                    if token_value and str(token_value).strip():
                        tokens_info.append(f"{token_value} = {token_meaning}")
                        tokens_list.append(str(token_value))
                
                interpretation = " | ".join(tokens_info) if tokens_info else "Não interpretado"
            
            distinct_values.append({
                'valor_original': original_value,
                'interpretacao': interpretation,
                'tokens': " + ".join(tokens_list),
                'padrao_detectado': record['padrao_detectado'],
                'eh_atomico': record['eh_atomico'],
                'confianca_geral': record.get('confianca_geral', 0.0)
            })
        
        return pd.DataFrame(distinct_values).sort_values('valor_original')


def main() -> int:
    """Função principal do script."""
    try:
        print("[INFO] Iniciando geração de Excel normalizado...")
        
        # Criar o gerador
        generator = NormalizedExcelGenerator()
        
        # Processar todos os arquivos
        generator.process_directory()
        
        if not generator.normalized_rows:
            print("[AVISO] Nenhum dado foi processado.")
            return 0
        
        # Gerar Excel
        output_path = generator.generate_excel()
        
        print(f"[SUCESSO] Processamento concluído!")
        print(f"           Arquivo gerado: {output_path}")
        
        return 0
        
    except Exception as e:
        print(f"[ERRO] Falha no processamento: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
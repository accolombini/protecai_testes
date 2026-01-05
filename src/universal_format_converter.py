#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
universal_format_converter.py — Conversor Universal para CSV

OBJETIVO: Converter TODOS os formatos (PDF, TXT, XLSX, CSV) para CSV padronizado
para que o pipeline tenha uma única entrada uniforme.

ARQUITETURA UNIFICADA:
inputs/{pdf,txt,xlsx,csv} → [CONVERSOR UNIVERSAL] → outputs/csv/ → [PIPELINE ÚNICO]

Benefícios:
- Pipeline único e consistente
- Fácil manutenção
- Padronização de dados
- Facilita análise comparativa

Autor: Sistema ProtecAI
Data: 2025-10-18
"""

from __future__ import annotations
import sys
import argparse
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

import pandas as pd
from PyPDF2 import PdfReader
import json

# Imports locais
import os
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.file_registry_manager import FileRegistryManager
from src.precise_parameter_extractor import PreciseParameterExtractor

# ---------------------------
# Configuração de diretórios
# ---------------------------

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]

INPUT_BASE_DIR = PROJECT_ROOT / "inputs"
INPUT_PDF_DIR = INPUT_BASE_DIR / "pdf"
INPUT_TXT_DIR = INPUT_BASE_DIR / "txt"
INPUT_XLSX_DIR = INPUT_BASE_DIR / "xlsx"
INPUT_CSV_DIR = INPUT_BASE_DIR / "csv"

OUTPUT_CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
OUTPUT_LOGS_DIR = PROJECT_ROOT / "outputs" / "logs"

# Garantir diretórios
for directory in [INPUT_PDF_DIR, INPUT_TXT_DIR, INPUT_XLSX_DIR, INPUT_CSV_DIR, 
                  OUTPUT_CSV_DIR, OUTPUT_LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


class UniversalFormatConverter:
    """
    Conversor universal que padroniza todos os formatos para CSV.
    
    Entrada: PDF, TXT, XLSX, CSV (em inputs/)
    Saída: CSV padronizado (Code, Description, Value) em outputs/csv/
    """
    
    def __init__(self, verbose: bool = False):
        """
        Inicializa o conversor.
        
        Args:
            verbose: Se True, mostra output detalhado
        """
        self.verbose = verbose
        self.stats = {
            'inicio': datetime.now().isoformat(),
            'arquivos_processados': [],
            'arquivos_ignorados': [],
            'erros': [],
            'formatos_encontrados': {}
        }
        
        # Patterns para parsing de texto
        self.re_micom = re.compile(r"^([0-9A-F]{2}\.[0-9A-F]{2}):\s*([^:]+):\s*(.*)$")
        self.re_easergy_equals = re.compile(r"^([0-9A-F]{4}):\s*([^=:]+)=:\s*(.*)$")
        self.re_easergy_colon = re.compile(r"^([0-9A-F]{4}):\s*([^:]+):\s*(.*)$")
        self.re_structured = re.compile(r"^([^:]+):\s*([^:]+):\s*(.*)$")
        
        # Carregar configuração de modelos de relés
        self.relay_config = self._load_relay_config()
        
        # Inicializar extrator preciso para checkboxes
        self.precise_extractor = PreciseParameterExtractor()
        
        if self.verbose:
            print(f"🔧 Conversor Universal iniciado")
    
    def _load_relay_config(self) -> Dict:
        """Carrega configuração dos modelos de relés."""
        config_path = PROJECT_ROOT / "inputs" / "glossario" / "relay_models_config.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log_warning(f"Não foi possível carregar relay_models_config.json: {e}")
            return {"models": {}}
    
    def _identify_relay_model(self, filename: str) -> Optional[str]:
        """Identifica o modelo do relé pelo nome do arquivo."""
        filename_upper = filename.upper()
        
        # Padrões de identificação (mais específico primeiro)
        patterns = {
            'MICON_P122_205': ['P122_205', 'P122-205'],
            'MICON_P122_52': ['P122_52', 'P122-52', 'P_122_52', 'P122 52', 'P_122 52'],
            'MICON_P122_204': ['P122_204', 'P122-204'],
            'MICON_P143': ['P143'],
            'MICON_P220': ['P220'],
            'MICON_P922': ['P922', 'P922S'],
            'MICON_P241': ['P241'],
            'SEPAM_S40': ['.S40']
        }
        
        # Verificar extensão .S40 (SEPAM)
        if filename.endswith('.S40') or filename.endswith('.s40'):
            return 'SEPAM_S40'
        
        # Buscar padrões no nome
        for model_name, model_patterns in patterns.items():
            if model_name == 'SEPAM_S40':
                continue
            for pattern in model_patterns:
                if pattern in filename_upper:
                    if model_name in self.relay_config.get('models', {}):
                        return model_name
        
        return None
    
    def log_info(self, msg: str):
        """Log de informação"""
        if self.verbose:
            print(f"ℹ️  {msg}")
    
    def log_success(self, msg: str):
        """Log de sucesso"""
        print(f"✅ {msg}")
    
    def log_warning(self, msg: str):
        """Log de warning"""
        print(f"⚠️  {msg}")
    
    def log_error(self, msg: str):
        """Log de erro"""
        print(f"❌ {msg}")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extrai texto de TODAS as páginas do PDF
        
        ESTRATÉGIA CORRETA: Parâmetros estão distribuídos em TODAS as páginas.
        Checkboxes e valores textuais aparecem ao longo de todo o documento.
        Extração híbrida: PyPDF2 (texto) + OCR (checkboxes) posteriormente.
        """
        try:
            reader = PdfReader(str(pdf_path))
            parts = []
            
            # CORRIGIDO: Processar TODAS as páginas (parâmetros em todo o documento)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
            
            return "\n".join(parts)
        except Exception as e:
            self.log_error(f"Erro ao extrair PDF {pdf_path.name}: {e}")
            return ""
    
    def parse_text_to_dataframe(self, text: str, source_format: str) -> Tuple[pd.DataFrame, str]:
        """
        Converte texto em DataFrame padronizado (Code, Description, Value)
        
        Returns:
            Tupla (DataFrame, formato_detectado)
        """
        rows = []
        detected_format = "unknown"
        
        # Detectar formato do relay
        lowered = text.lower()
        if "micom s1 agile" in lowered or "micom p24" in lowered:
            detected_format = "micom"
        elif "easergy studio" in lowered or "easergy p2" in lowered:
            detected_format = "easergy" 
        elif "[sepam_" in lowered or "=" in text and "[" in text:
            detected_format = "sepam_s40"
        elif "generic" in source_format or "txt" in source_format:
            detected_format = "structured_text"
        
        # Variável para track de seção SepaM
        current_section = "general"
        
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            # SepaM .S40 format: [seção] e key=value
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]  # Remove [ ]
                continue
            elif '=' in line and detected_format == "sepam_s40":
                key, value = line.split('=', 1)
                # ✅ CORREÇÃO: Usar apenas o key sem prefixo de seção
                code = key.strip()
                rows.append({
                    "Code": code,
                    "Description": key.strip(),
                    "Value": value.strip()
                })
                continue
            
            # Tentar patterns MiCOM primeiro
            m = self.re_micom.match(line)
            if m:
                code, desc, val = m.groups()
                rows.append({
                    "Code": code.strip(),
                    "Description": desc.strip(), 
                    "Value": val.strip()
                })
                if detected_format == "unknown":
                    detected_format = "micom"
                continue
            
            # Patterns Easergy
            m = self.re_easergy_equals.match(line)
            if m:
                code, desc, val = m.groups()
                rows.append({
                    "Code": code.strip(),
                    "Description": desc.strip(),
                    "Value": val.strip()
                })
                if detected_format == "unknown":
                    detected_format = "easergy"
                continue
                
            m = self.re_easergy_colon.match(line)
            if m:
                code, desc, val = m.groups()
                rows.append({
                    "Code": code.strip(),
                    "Description": desc.strip(),
                    "Value": val.strip()
                })
                if detected_format == "unknown":
                    detected_format = "easergy"
                continue
            
            # Pattern genérico (3 campos separados por :)
            m = self.re_structured.match(line)
            if m:
                code, desc, val = m.groups()
                rows.append({
                    "Code": code.strip(),
                    "Description": desc.strip(),
                    "Value": val.strip()
                })
                if detected_format == "unknown":
                    detected_format = "structured_text"
        
        df = pd.DataFrame(rows)
        
        # Garantir colunas padronizadas
        for col in ["Code", "Description", "Value"]:
            if col not in df.columns:
                df[col] = ""
        
        return df[["Code", "Description", "Value"]], detected_format
    
    def convert_pdf_to_csv(self, pdf_path: Path) -> Optional[Path]:
        """Converte PDF para CSV padronizado usando método apropriado (checkbox ou texto)"""
        self.log_info(f"Convertendo PDF: {pdf_path.name}")
        
        # Identificar modelo do relé
        relay_model = self._identify_relay_model(pdf_path.name)
        
        if relay_model and relay_model in self.relay_config.get('models', {}):
            model_config = self.relay_config['models'][relay_model]
            detection_method = model_config.get('detection_method', 'text')
            
            # Se usa checkboxes, usar PreciseParameterExtractor
            if detection_method == 'checkbox':
                self.log_info(f"  Modelo {relay_model} detectado - usando extração visual de checkboxes")
                try:
                    df = self.precise_extractor.extract_from_pdf(pdf_path)
                    
                    if df is None or df.empty:
                        self.log_warning(f"PDF {pdf_path.name} não gerou dados válidos (checkboxes)")
                        return None
                    
                    # Garantir colunas padrão
                    for col in ["Code", "Description", "Value", "is_active"]:
                        if col not in df.columns:
                            df[col] = "" if col != "is_active" else False
                    
                    # Salvar CSV com coluna is_active
                    output_path = OUTPUT_CSV_DIR / f"{pdf_path.stem}_active_setup.csv"
                    df.to_csv(output_path, index=False, encoding='utf-8')
                    
                    self.log_success(f"PDF convertido (checkboxes): {pdf_path.name} → {output_path.name} ({len(df)} linhas)")
                    return output_path
                    
                except Exception as e:
                    self.log_error(f"Erro ao usar PreciseParameterExtractor em {pdf_path.name}: {e}")
                    self.log_warning("  Tentando fallback para extração de texto...")
        
        # Fallback ou método padrão: extração de texto
        text = self.extract_text_from_pdf(pdf_path)
        if not text.strip():
            self.log_warning(f"PDF {pdf_path.name} sem texto extraível")
            return None
        
        # Fazer parse
        df, detected_format = self.parse_text_to_dataframe(text, "pdf")
        
        if df.empty:
            self.log_warning(f"Nenhum dado estruturado encontrado em {pdf_path.name}")
            return None
        
        # CORREÇÃO CRÍTICA: Limpar valores 'None', 'nan' antes de salvar
        df = df.replace(['None', 'nan', 'NaN', 'NAN'], '')
        df = df.fillna('')
        
        # Salvar CSV
        output_path = OUTPUT_CSV_DIR / f"{pdf_path.stem}_params.csv"
        df.to_csv(output_path, index=False, encoding='utf-8', na_rep="")  # ✅ CORREÇÃO: Evitar conversão None→"nan"
        
        self.log_success(f"PDF convertido: {pdf_path.name} → {output_path.name} ({len(df)} linhas, {detected_format})")
        return output_path
    
    def convert_txt_to_csv(self, txt_path: Path) -> Optional[Path]:
        """Converte TXT para CSV padronizado"""
        self.log_info(f"Convertendo TXT: {txt_path.name}")
        
        try:
            # Tentar diferentes encodings
            text = None
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(txt_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if text is None:
                self.log_error(f"Não foi possível ler {txt_path.name} com encodings suportados")
                return None
            
            # Parse
            df, detected_format = self.parse_text_to_dataframe(text, "txt")
            
            if df.empty:
                self.log_warning(f"Nenhum dado estruturado em {txt_path.name}")
                return None
            
            # CORREÇÃO CRÍTICA: Limpar valores 'None', 'nan' antes de salvar
            df = df.replace(['None', 'nan', 'NaN', 'NAN'], '')
            df = df.fillna('')
            
            # Salvar CSV
            output_path = OUTPUT_CSV_DIR / f"{txt_path.stem}_params.csv"
            df.to_csv(output_path, index=False, encoding='utf-8', na_rep="")  # ✅ CORREÇÃO: Evitar conversão None→"nan"
            
            self.log_success(f"TXT convertido: {txt_path.name} → {output_path.name} ({len(df)} linhas, {detected_format})")
            return output_path
            
        except Exception as e:
            self.log_error(f"Erro ao converter TXT {txt_path.name}: {e}")
            return None
    
    def convert_xlsx_to_csv(self, xlsx_path: Path) -> Optional[Path]:
        """Converte XLSX para CSV padronizado"""
        self.log_info(f"Convertendo XLSX: {xlsx_path.name}")
        
        try:
            # Ler Excel (tentar múltiplas sheets se necessário)
            df = None
            try:
                xls = pd.ExcelFile(xlsx_path)
                
                # Procurar sheet com mais dados
                best_df = None
                max_rows = 0
                
                for sheet_name in xls.sheet_names:
                    temp_df = pd.read_excel(xlsx_path, sheet_name=sheet_name, dtype=str)
                    if len(temp_df) > max_rows and len(temp_df.columns) >= 3:
                        best_df = temp_df
                        max_rows = len(temp_df)
                
                df = best_df if best_df is not None else pd.read_excel(xlsx_path, dtype=str)
                
            except Exception:
                df = pd.read_excel(xlsx_path, dtype=str)
            
            if df is None or df.empty:
                self.log_warning(f"XLSX {xlsx_path.name} vazio ou ilegível")
                return None
            
            # Mapear colunas para formato padrão
            column_mapping = self._map_columns_to_standard(df.columns)
            df = df.rename(columns=column_mapping)
            
            # Garantir colunas padrão
            for col in ["Code", "Description", "Value"]:
                if col not in df.columns:
                    df[col] = ""
            
            # Limpar dados
            df = df[["Code", "Description", "Value"]].fillna("")
            
            # CORREÇÃO CRÍTICA: Substituir valores 'None' e 'nan' (string) por vazios
            df = df.replace(['None', 'nan', 'NaN', 'NAN'], '')
            
            df = df[df["Code"].astype(str).str.strip() != ""]  # Remover linhas sem código
            
            if df.empty:
                self.log_warning(f"Nenhum dado válido em {xlsx_path.name}")
                return None
            
            # Salvar CSV
            output_path = OUTPUT_CSV_DIR / f"{xlsx_path.stem}_params.csv"
            df.to_csv(output_path, index=False, encoding='utf-8', na_rep="")  # ✅ CORREÇÃO: Evitar conversão None→"nan"
            
            self.log_success(f"XLSX convertido: {xlsx_path.name} → {output_path.name} ({len(df)} linhas)")
            return output_path
            
        except Exception as e:
            self.log_error(f"Erro ao converter XLSX {xlsx_path.name}: {e}")
            return None
    
    def convert_csv_to_standardized_csv(self, csv_path: Path) -> Optional[Path]:
        """Converte CSV para CSV padronizado (normalização)"""
        self.log_info(f"Padronizando CSV: {csv_path.name}")
        
        try:
            # Tentar diferentes separadores
            df = None
            for sep in [',', ';', '\t', '|']:
                try:
                    temp_df = pd.read_csv(csv_path, sep=sep, dtype=str, encoding='utf-8')
                    if len(temp_df.columns) >= 3:
                        df = temp_df
                        break
                except:
                    continue
            
            if df is None:
                # Fallback para separador padrão
                df = pd.read_csv(csv_path, dtype=str, encoding='utf-8')
            
            if df.empty:
                self.log_warning(f"CSV {csv_path.name} vazio")
                return None
            
            # Mapear colunas
            column_mapping = self._map_columns_to_standard(df.columns)
            df = df.rename(columns=column_mapping)
            
            # Garantir colunas padrão
            for col in ["Code", "Description", "Value"]:
                if col not in df.columns:
                    df[col] = ""
            
            # Limpar dados
            df = df[["Code", "Description", "Value"]].fillna("")
            # CORREÇÃO CRÍTICA: Limpar valores 'None', 'nan' antes de salvar
            df = df.replace(['None', 'nan', 'NaN', 'NAN'], '')
            df = df[df["Code"].astype(str).str.strip() != ""]
            
            if df.empty:
                self.log_warning(f"Nenhum dado válido em {csv_path.name}")
                return None
            
            # Salvar CSV padronizado
            output_path = OUTPUT_CSV_DIR / f"{csv_path.stem}_params.csv"
            df.to_csv(output_path, index=False, encoding='utf-8', na_rep="")  # ✅ CORREÇÃO: Evitar conversão None→"nan"
            
            self.log_success(f"CSV padronizado: {csv_path.name} → {output_path.name} ({len(df)} linhas)")
            return output_path
            
        except Exception as e:
            self.log_error(f"Erro ao padronizar CSV {csv_path.name}: {e}")
            return None
    
    def _map_columns_to_standard(self, columns: List[str]) -> Dict[str, str]:
        """Mapeia colunas encontradas para formato padrão (Code, Description, Value)"""
        mapping = {}
        
        for col in columns:
            col_lower = str(col).lower().strip()
            
            # Mapear para Code
            if any(term in col_lower for term in ['code', 'código', 'cod', 'id', 'ref']):
                mapping[col] = 'Code'
            
            # Mapear para Description  
            elif any(term in col_lower for term in ['desc', 'description', 'descrição', 'name', 'nome', 'parameter']):
                mapping[col] = 'Description'
            
            # Mapear para Value
            elif any(term in col_lower for term in ['value', 'valor', 'val', 'setting', 'config', 'data']):
                mapping[col] = 'Value'
        
        return mapping
    
    def convert_all_formats(self) -> Dict[str, Any]:
        """
        Converte todos os formatos encontrados em inputs/ para CSV padronizado
        
        Returns:
            Dicionário com estatísticas do processamento
        """
        # Buscar arquivos em cada formato
        formatos = {
            'pdf': list(INPUT_PDF_DIR.glob("*.pdf")),
            'txt': list(INPUT_TXT_DIR.glob("*.txt")) + list(INPUT_TXT_DIR.glob("*.S40")),
            'xlsx': list(INPUT_XLSX_DIR.glob("*.xlsx")) + list(INPUT_XLSX_DIR.glob("*.xls")),
            'csv': list(INPUT_CSV_DIR.glob("*.csv"))
        }
        
        # Estatísticas
        total_encontrados = sum(len(files) for files in formatos.values())
        total_convertidos = 0
        
        self.stats['formatos_encontrados'] = {fmt: len(files) for fmt, files in formatos.items()}
        
        if total_encontrados == 0:
            self.log_warning("Nenhum arquivo encontrado em inputs/")
            return self.stats
        
        print(f"\n🔍 Arquivos encontrados: {self.stats['formatos_encontrados']}")
        print(f"📋 Total: {total_encontrados} arquivo(s)\n")
        
        # Converter PDFs
        for pdf_path in formatos['pdf']:
            output_path = self.convert_pdf_to_csv(pdf_path)
            if output_path:
                self.stats['arquivos_processados'].append({
                    'entrada': str(pdf_path),
                    'saida': str(output_path),
                    'formato': 'pdf'
                })
                total_convertidos += 1
            else:
                self.stats['arquivos_ignorados'].append(str(pdf_path))
        
        # Converter TXTs
        for txt_path in formatos['txt']:
            output_path = self.convert_txt_to_csv(txt_path)
            if output_path:
                self.stats['arquivos_processados'].append({
                    'entrada': str(txt_path),
                    'saida': str(output_path),
                    'formato': 'txt'
                })
                total_convertidos += 1
            else:
                self.stats['arquivos_ignorados'].append(str(txt_path))
        
        # Converter XLSXs
        for xlsx_path in formatos['xlsx']:
            output_path = self.convert_xlsx_to_csv(xlsx_path)
            if output_path:
                self.stats['arquivos_processados'].append({
                    'entrada': str(xlsx_path),
                    'saida': str(output_path),
                    'formato': 'xlsx'
                })
                total_convertidos += 1
            else:
                self.stats['arquivos_ignorados'].append(str(xlsx_path))
        
        # Padronizar CSVs
        for csv_path in formatos['csv']:
            output_path = self.convert_csv_to_standardized_csv(csv_path)
            if output_path:
                self.stats['arquivos_processados'].append({
                    'entrada': str(csv_path),
                    'saida': str(output_path),
                    'formato': 'csv'
                })
                total_convertidos += 1
            else:
                self.stats['arquivos_ignorados'].append(str(csv_path))
        
        # Finalizar estatísticas
        self.stats.update({
            'fim': datetime.now().isoformat(),
            'total_encontrados': total_encontrados,
            'total_convertidos': total_convertidos,
            'total_ignorados': len(self.stats['arquivos_ignorados']),
            'total_erros': len(self.stats['erros'])
        })
        
        return self.stats
    
    def mostrar_resumo(self):
        """Mostra resumo da conversão"""
        print("\n" + "="*60)
        print("📊 RESUMO DA CONVERSÃO UNIVERSAL")
        print("="*60)
        
        print(f"📁 Formatos encontrados: {self.stats['formatos_encontrados']}")
        print(f"✅ Convertidos: {self.stats.get('total_convertidos', 0)}")
        print(f"⏭️  Ignorados: {self.stats.get('total_ignorados', 0)}")
        print(f"❌ Erros: {self.stats.get('total_erros', 0)}")
        
        if self.stats['arquivos_processados']:
            print(f"\n📋 Arquivos convertidos:")
            for item in self.stats['arquivos_processados']:
                entrada = Path(item['entrada']).name
                saida = Path(item['saida']).name
                formato = item['formato'].upper()
                print(f"  • {formato}: {entrada} → {saida}")
        
        if self.stats['arquivos_ignorados']:
            print(f"\n⚠️  Arquivos ignorados:")
            for arquivo in self.stats['arquivos_ignorados']:
                print(f"  • {Path(arquivo).name}")
        
        if self.stats['erros']:
            print(f"\n❌ Erros:")
            for erro in self.stats['erros']:
                print(f"  • {erro}")
        
        print(f"\n📂 Saídas em: {OUTPUT_CSV_DIR.relative_to(PROJECT_ROOT)}")
        print("="*60)


def build_argparser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos"""
    parser = argparse.ArgumentParser(
        description="Conversor Universal - Todos os formatos para CSV padronizado",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ARQUITETURA UNIFICADA:
inputs/{pdf,txt,xlsx,csv} → [CONVERSOR UNIVERSAL] → outputs/csv/ → [PIPELINE ÚNICO]

Exemplos de uso:

  # Converter todos os formatos encontrados
  python src/universal_format_converter.py
  
  # Modo verbose
  python src/universal_format_converter.py --verbose

Resultado:
  • Todos os formatos convertidos para CSV padronizado (Code, Description, Value)
  • Pipeline único a partir de outputs/csv/
  • Manutenção simplificada
  • Análise comparativa facilitada
        """
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Output detalhado'
    )
    
    return parser


def main() -> int:
    """Função principal"""
    args = build_argparser().parse_args()
    
    try:
        # Criar conversor
        converter = UniversalFormatConverter(verbose=args.verbose)
        
        # Executar conversão
        stats = converter.convert_all_formats()
        
        # Mostrar resumo
        converter.mostrar_resumo()
        
        # Salvar relatório
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        relatorio_path = OUTPUT_LOGS_DIR / f"universal_conversion_{timestamp}.json"
        
        import json
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Relatório salvo: {relatorio_path.relative_to(PROJECT_ROOT)}")
        
        # Código de retorno
        if stats.get('total_erros', 0) > 0:
            return 1
        elif stats.get('total_convertidos', 0) == 0:
            return 2  # Nenhum arquivo convertido
        else:
            return 0  # Sucesso
        
    except KeyboardInterrupt:
        print("\n⏹️  Conversão interrompida pelo usuário")
        return 130
        
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
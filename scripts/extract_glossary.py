"""Extrator de Glossário de Parâmetros de Relés.

Este script lê o arquivo Excel 'inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx',
extrai os parâmetros de configuração de cada modelo de relé (Micon, SEPAM),
normaliza os códigos e nomes, e gera arquivos estruturados (JSON e CSV) para
posterior importação no banco de dados.

Arquitetura:
    - Lê todas as planilhas (sheets) do workbook Excel
    - Normaliza códigos de parâmetros (trim, uppercase)
    - Extrai código, nome, unidade, valor exemplo e associa ao modelo
    - Gera dois outputs:
        1. glossary_mapping.json (estrutura hierárquica por modelo)
        2. glossary_mapping.csv (formato flat para import SQL)

Outputs:
    - inputs/glossario/glossary_mapping.json
    - inputs/glossario/glossary_mapping.csv

Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 1.0.0
Safety-Critical: Yes
Principles: CAUSA RAIZ, ROBUSTEZ, ZERO MOCK/FAKE
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Configuração de caminhos
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_FILE = PROJECT_ROOT / "inputs" / "glossario" / "Dados_Glossario_Micon_Sepam.xlsx"
OUTPUT_JSON = PROJECT_ROOT / "inputs" / "glossario" / "glossary_mapping.json"
OUTPUT_CSV = PROJECT_ROOT / "inputs" / "glossario" / "glossary_mapping.csv"


class GlossaryExtractor:
    """Extrator de parâmetros do glossário Excel.
    
    Attributes:
        glossary_path (Path): Caminho do arquivo Excel de entrada.
        mapping (Dict): Estrutura hierárquica modelo -> parâmetros.
        flat_records (List[Dict]): Lista flat de registros para CSV.
    """

    def __init__(self, glossary_path: Path):
        """Inicializa o extrator.
        
        Args:
            glossary_path: Path para o arquivo Excel do glossário.
            
        Raises:
            FileNotFoundError: Se o arquivo não existir.
        """
        if not glossary_path.exists():
            raise FileNotFoundError(f"Arquivo de glossário não encontrado: {glossary_path}")
        
        self.glossary_path = glossary_path
        self.mapping: Dict[str, List[Dict[str, Any]]] = {}
        self.flat_records: List[Dict[str, str]] = []

    def extract(self) -> None:
        """Extrai todos os parâmetros de todas as planilhas do Excel.
        
        Processa cada sheet, identifica modelo pelo nome da sheet,
        extrai códigos e valores de parâmetros, normaliza e armazena.
        """
        print(f"[INFO] Lendo arquivo: {self.glossary_path}")
        
        # Ler todas as sheets
        excel_file = pd.ExcelFile(self.glossary_path)
        print(f"[INFO] Encontradas {len(excel_file.sheet_names)} planilhas: {excel_file.sheet_names}")
        
        for sheet_name in excel_file.sheet_names:
            print(f"[INFO] Processando planilha: {sheet_name}")
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
            
            # Detectar modelo pelo nome da sheet
            model = self._detect_model(sheet_name)
            
            # Extrair parâmetros
            parameters = self._extract_parameters_from_sheet(df, model, sheet_name)
            
            if model not in self.mapping:
                self.mapping[model] = []
            
            self.mapping[model].extend(parameters)
            print(f"[INFO]   Extraídos {len(parameters)} parâmetros do modelo {model}")
        
        # Gerar flat records para CSV
        self._generate_flat_records()
        
        print(f"[INFO] Extração concluída: {len(self.flat_records)} registros no total")

    def _detect_model(self, sheet_name: str) -> str:
        """Detecta o modelo de relé pelo nome da planilha.
        
        Args:
            sheet_name: Nome da planilha Excel.
            
        Returns:
            Nome do modelo normalizado (MICON, SEPAM, etc).
        """
        sheet_upper = sheet_name.upper()
        
        if "MICON" in sheet_upper:
            return "MICON"
        elif "SEPAM" in sheet_upper:
            return "SEPAM"
        elif "P14" in sheet_upper:
            return "MICON_P14X"
        elif "P12" in sheet_upper:
            return "MICON_P12X"
        elif "S20" in sheet_upper:
            return "SEPAM_S20"
        elif "S40" in sheet_upper:
            return "SEPAM_S40"
        elif "S80" in sheet_upper:
            return "SEPAM_S80"
        else:
            # Fallback: usar o próprio nome da sheet
            return sheet_name.strip().replace(" ", "_").upper()

    def _extract_parameters_from_sheet(
        self, df: pd.DataFrame, model: str, sheet_name: str
    ) -> List[Dict[str, Any]]:
        """Extrai parâmetros de uma planilha específica.
        
        Args:
            df: DataFrame com o conteúdo da planilha.
            model: Nome do modelo detectado.
            sheet_name: Nome original da planilha.
            
        Returns:
            Lista de dicionários com parâmetros extraídos.
        """
        parameters = []
        
        # Estratégia: varrer todas as linhas e detectar padrões de código/valor
        for idx, row in df.iterrows():
            # Converter linha para string e buscar padrões
            row_text = " ".join([str(cell) for cell in row if pd.notna(cell)])
            
            # Padrão 1: Código: Nome (ex: "010A: Reference")
            # Padrão 2: Código = Valor (ex: "0211: I>> =: 8.0In")
            # Padrão 3: key=value SEPAM (ex: "Inom=5A")
            
            # Regex para detectar código numérico/alfanumérico seguido de descrição
            pattern_code = r"([0-9A-F]{4,})\s*[:\-]\s*(.+?)(?:\s*[=:]\s*(.+))?$"
            match = re.search(pattern_code, row_text)
            
            if match:
                code = match.group(1).strip()
                name = match.group(2).strip() if match.group(2) else ""
                value_example = match.group(3).strip() if match.group(3) else ""
                
                # Extrair unidade se presente no nome ou valor
                unit = self._extract_unit(name + " " + value_example)
                
                param = {
                    "code": code,
                    "name": name,
                    "unit": unit,
                    "value_example": value_example,
                    "model": model,
                    "sheet": sheet_name
                }
                parameters.append(param)
                continue
            
            # Padrão SEPAM key=value
            pattern_sepam = r"([A-Za-z0-9_]+)\s*=\s*(.+)"
            match_sepam = re.search(pattern_sepam, row_text)
            
            if match_sepam:
                key = match_sepam.group(1).strip()
                value = match_sepam.group(2).strip()
                
                # Ignorar valores numéricos puros (são linhas de índice)
                if key and not key.isdigit():
                    unit = self._extract_unit(value)
                    
                    param = {
                        "code": key.upper(),
                        "name": key,
                        "unit": unit,
                        "value_example": value,
                        "model": model,
                        "sheet": sheet_name
                    }
                    parameters.append(param)
        
        return parameters

    def _extract_unit(self, text: str) -> str:
        """Extrai unidade de medida de uma string.
        
        Args:
            text: Texto contendo possível unidade.
            
        Returns:
            Unidade detectada ou string vazia.
        """
        # Unidades comuns: A, V, Hz, s, ms, In, Vn, kV, MVA, etc
        units_pattern = r"\b(A|V|Hz|s|ms|In|Vn|kV|MVA|MW|Var|deg|°|%|Ω|ohm)\b"
        match = re.search(units_pattern, text, re.IGNORECASE)
        
        if match:
            return match.group(1)
        
        return ""

    def _generate_flat_records(self) -> None:
        """Gera lista flat de registros para export CSV."""
        for model, params in self.mapping.items():
            for param in params:
                self.flat_records.append({
                    "model": model,
                    "code": param["code"],
                    "name": param["name"],
                    "unit": param["unit"],
                    "value_example": param["value_example"],
                    "sheet": param["sheet"]
                })

    def save_json(self, output_path: Path) -> None:
        """Salva mapping hierárquico em JSON.
        
        Args:
            output_path: Path do arquivo JSON de saída.
        """
        print(f"[INFO] Salvando JSON em: {output_path}")
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] JSON salvo com sucesso")

    def save_csv(self, output_path: Path) -> None:
        """Salva registros flat em CSV.
        
        Args:
            output_path: Path do arquivo CSV de saída.
        """
        print(f"[INFO] Salvando CSV em: {output_path}")
        
        df = pd.DataFrame(self.flat_records)
        df.to_csv(output_path, index=False, encoding="utf-8")
        
        print(f"[OK] CSV salvo com sucesso: {len(df)} registros")


def main() -> int:
    """Função principal de execução.
    
    Returns:
        Exit code (0 = sucesso, 1 = erro).
    """
    try:
        print("=" * 80)
        print("EXTRATOR DE GLOSSÁRIO DE PARÂMETROS DE RELÉS")
        print("=" * 80)
        
        # Validar existência do arquivo
        if not GLOSSARY_FILE.exists():
            print(f"[ERRO] Arquivo não encontrado: {GLOSSARY_FILE}")
            return 1
        
        # Criar extrator e processar
        extractor = GlossaryExtractor(GLOSSARY_FILE)
        extractor.extract()
        
        # Salvar outputs
        extractor.save_json(OUTPUT_JSON)
        extractor.save_csv(OUTPUT_CSV)
        
        print("=" * 80)
        print("[SUCESSO] Extração concluída!")
        print(f"  JSON: {OUTPUT_JSON}")
        print(f"  CSV:  {OUTPUT_CSV}")
        print("=" * 80)
        
        return 0
    
    except Exception as e:
        print(f"[ERRO FATAL] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

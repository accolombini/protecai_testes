#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — Extrator de parâmetros de proteção a partir de relatórios PDF (MiCOM S1 Agile e Easergy Studio)

- Lê PDFs de relatórios de configuração (tela1.pdf, tela3.pdf, etc.)
- Detecta o formato (MiCOM S1 Agile ou Easergy Studio) automaticamente
- Faz o parsing para (Code, Description, Value)
- Exporta para Excel (uma planilha por arquivo)
- Pode também exportar CSV

Requisitos:
  pip install PyPDF2 pandas xlsxwriter

Executar:
    python src/app.py --inputs tela1.pdf tela3.pdf
    python -m src.app --inputs input_pdfs/*.pdf => É preciso ter o __init__.py em src/


Uso (exemplos):
  python app.py --inputs tela1.pdf tela3.pdf --xlsx saida.xlsx
  python app.py --inputs tela1.pdf --csv micom.csv
  python app.py --inputs tela1.pdf tela3.pdf  # gera arquivos padrão por arquivo
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from PyPDF2 import PdfReader

# ---------------------------
# Pastas padrão do projeto
# ---------------------------

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]          # src/ -> raiz do projeto
INPUT_DIR = PROJECT_ROOT / "input_pdfs"
OUT_EXCEL_DIR = PROJECT_ROOT / "outputs" / "excel"
OUT_CSV_DIR = PROJECT_ROOT / "outputs" / "csv"

# garantir que as saídas existam
OUT_EXCEL_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------
# Extração de texto do PDF
# ---------------------------

def extract_text_pypdf2(pdf_path: Path) -> str:
    """Extrai texto de todas as páginas com PyPDF2."""
    reader = PdfReader(str(pdf_path))
    parts: List[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


# ---------------------------
# Parsers (MiCOM / Easergy)
# ---------------------------

# MiCOM S1 Agile: linhas do tipo "0A.01: Main VT Primary: 13.80 kV"
RE_MICOM = re.compile(r"^([0-9A-F]{2}\.[0-9A-F]{2}):\s*([^:]+):\s*(.*)$")

# Easergy Studio: linhas do tipo "0202: Iteta> =: 0.64In"
RE_EASERGY = re.compile(r"^([0-9A-F]{4}):\s*([^=:]+)=:\s*(.*)$")


def parse_micom(text: str) -> pd.DataFrame:
    """Parser para MiCOM S1 Agile: retorna DataFrame (Code, Description, Value)."""
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        m = RE_MICOM.match(line)
        if m:
            code, desc, val = m.groups()
            rows.append({"Code": code, "Description": desc.strip(), "Value": val.strip()})
    return pd.DataFrame(rows)


def parse_easergy(text: str) -> pd.DataFrame:
    """Parser para Easergy Studio: retorna DataFrame (Code, Description, Value)."""
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        m = RE_EASERGY.match(line)
        if m:
            code, desc, val = m.groups()
            rows.append({"Code": code, "Description": desc.strip(), "Value": val.strip()})
    return pd.DataFrame(rows)


# ---------------------------
# Heurística de detecção
# ---------------------------

@dataclass
class ParseResult:
    df: pd.DataFrame
    detected: str  # "micom" | "easergy" | "unknown"


def detect_and_parse(text: str) -> ParseResult:
    """
    Detecta o tipo de relatório e faz o parsing.
    Heurísticas:
      - Presença de marca "MiCOM S1 Agile" => micom
      - Presença de "Easergy Studio" => easergy
      - Caso ambíguo: testa os dois regex e escolhe o que extraiu mais linhas
    """
    lowered = text.lower()
    if "micom s1 agile" in lowered:
        df = parse_micom(text)
        return ParseResult(df=df, detected="micom")
    if "easergy studio" in lowered:
        df = parse_easergy(text)
        return ParseResult(df=df, detected="easergy")

    # fallback: testar ambos
    micom_df = parse_micom(text)
    easergy_df = parse_easergy(text)
    if len(micom_df) >= len(easergy_df) and len(micom_df) > 0:
        return ParseResult(df=micom_df, detected="micom")
    if len(easergy_df) > 0:
        return ParseResult(df=easergy_df, detected="easergy")
    return ParseResult(df=pd.DataFrame(columns=["Code", "Description", "Value"]), detected="unknown")


# ---------------------------
# I/O Helpers
# ---------------------------

def default_output_names(pdf_path: Path) -> Tuple[Path, Path]:
    """
    Gera nomes padrão nas pastas de saída oficiais:
      outputs/excel/<stem>_params.xlsx
      outputs/csv/<stem>_params.csv
      Observação: quando você passa --xlsx (arquivo único consolidado) ou --csv (para 1 PDF), 
      esses caminhos continuam valendo como override — ou seja, salvam exatamente onde você indicar.
    """
    xlsx = OUT_EXCEL_DIR / f"{pdf_path.stem}_params.xlsx"
    csv = OUT_CSV_DIR / f"{pdf_path.stem}_params.csv"
    return xlsx, csv


def write_outputs(
    df: pd.DataFrame,
    pdf_path: Path,
    xlsx_path: Optional[Path],
    csv_path: Optional[Path],
    sheet_name: Optional[str] = None,
) -> Tuple[Path, Path]:
    """
    Escreve Excel e/ou CSV.
    - Se xlsx_path/csv_path forem None, usa nomes padrão ao lado do PDF.
    - Retorna caminhos efetivamente escritos.
    """
    # nomes padrão se não forem fornecidos
    default_xlsx, default_csv = default_output_names(pdf_path)
    out_xlsx = xlsx_path or default_xlsx
    out_csv = csv_path or default_csv

    # Excel
    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name or "parameters")

    # CSV
    df.to_csv(out_csv, index=False)

    return out_xlsx, out_csv


# ---------------------------
# CLI
# ---------------------------

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Extrai parâmetros de relatórios PDF (MiCOM S1 Agile / Easergy Studio) e exporta para Excel/CSV."
    )
    p.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="Lista de arquivos PDF de entrada (ex.: tela1.pdf tela3.pdf).",
    )
    p.add_argument(
        "--xlsx",
        type=str,
        default=None,
        help="Caminho do Excel de saída único (se fornecer vários PDFs, cria uma aba por arquivo).",
    )
    p.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Caminho do CSV único de saída (apenas quando há um único PDF).",
    )
    p.add_argument(
        "--sheet-prefix",
        type=str,
        default="Sheet",
        help="Prefixo para nomes de abas quando usar --xlsx único (default: Sheet).",
    )
    return p


def main() -> None:
    args = build_argparser().parse_args()

    pdf_paths = []
    for raw in args.inputs:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            cand = (Path.cwd() / raw)
            if not cand.exists():
                cand = INPUT_DIR / raw           # cai para input_pdfs/<arquivo>
            p = cand
        p = p.resolve()
        pdf_paths.append(p)

    for p in pdf_paths:
        if not p.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {p}")

    # Caso 1: Usuário forneceu um XLSX único para consolidar tudo
    if args.xlsx:
        out_xlsx = Path(args.xlsx).expanduser().resolve()
        # Se também passou --csv, só permitimos se houver 1 PDF (CSV único)
        if args.csv and len(pdf_paths) != 1:
            raise ValueError("--csv só é permitido junto com --xlsx quando houver APENAS 1 PDF de entrada.")

        writer = pd.ExcelWriter(out_xlsx, engine="xlsxwriter")
        consolidated_rows = []  # opcional: consolidar em uma tabela única

        try:
            for idx, pdf in enumerate(pdf_paths, start=1):
                text = extract_text_pypdf2(pdf)
                res = detect_and_parse(text)
                sheet_name = f"{args.sheet_prefix}{idx}"
                # Tentar nome mais informativo e curto (<= 31 chars no Excel)
                informative = (pdf.stem[:20] + f"_{res.detected}")[:31]
                sheet_name = informative or sheet_name

                # escreve aba
                res.df.to_excel(writer, index=False, sheet_name=sheet_name)

                # acumula metadados (opcional)
                if not res.df.empty:
                    tmp = res.df.copy()
                    tmp.insert(0, "SourcePDF", str(pdf.name))
                    tmp.insert(1, "Detected", res.detected)
                    consolidated_rows.append(tmp)
                print(f"[OK] {pdf.name}: {len(res.df)} linhas ({res.detected}).")

            # Se também pediu CSV (e há 1 PDF), escrever CSV único
            if args.csv and len(pdf_paths) == 1 and consolidated_rows:
                all_df = consolidated_rows[0]
                out_csv = Path(args.csv).expanduser().resolve()
                all_df.to_csv(out_csv, index=False)
                print(f"[OK] CSV salvo em: {out_csv}")

        finally:
            writer.close()

        print(f"[OK] Excel consolidado salvo em: {out_xlsx}")
        return

    # Caso 2: Sem XLSX único → gerar saídas por arquivo individualmente
    if len(pdf_paths) > 1 and args.csv:
        raise ValueError("--csv único só faz sentido quando há 1 PDF de entrada ou quando usa --xlsx único.")

    for pdf in pdf_paths:
        text = extract_text_pypdf2(pdf)
        res = detect_and_parse(text)
        xlsx_out, csv_out = write_outputs(
            df=res.df,
            pdf_path=pdf,
            xlsx_path=None,   # usa nome padrão baseado no PDF
            csv_path=None,    # idem
            sheet_name=res.detected or "parameters",
        )
        print(f"[OK] {pdf.name}: {len(res.df)} linhas ({res.detected}).")
        print(f"     Excel: {xlsx_out}")
        print(f"     CSV  : {csv_out}")


def run():
    main()

if __name__ == "__main__":
    run()

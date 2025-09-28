#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_units.py — Varre outputs/excel e cria versões limpas em outputs/atrib_limpOS
Regra: só separa quando for exatamente 'numero + unidade'; demais casos ficam como texto.

Requisitos:
  pip install openpyxl

Uso:
  python -m src.utils.split_units
  # ou
  python src/utils/split_units.py
"""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # raiz do repo
INPUT_DIR = ROOT / "outputs" / "excel"
OUTPUT_DIR = ROOT / "outputs" / "atrib_limpOS"  # mantém seu nomeexato do print

pattern = re.compile(r"""
    ^\s*([+-]?\d+(?:[.,]\d+)?)\s*([%A-Za-zµΩ°/]+)\s*$   # numero + unidade (1 token)
""", re.VERBOSE)

def normalize_num(num_str: str) -> float:
    s = str(num_str).strip()
    s = s.replace(" ", "").replace("\u00A0", "").replace("\u202F", "")
    if "," in s and "." in s:
        if s.index(",") < s.index("."):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")

def extract_value_unit(x):
    if pd.isna(x):
        return (pd.NA, pd.NA, x)
    s = str(x).strip()
    m = pattern.match(s)
    if m:
        return (normalize_num(m.group(1)), m.group(2), s)
    return (pd.NA, pd.NA, s)

def process_file(path: Path, out_dir: Path):
    # lê primeira aba (ou adapte para iterar sobre todas)
    df = pd.read_excel(path, sheet_name=0, dtype=str)
    cols = list(df.columns)
    if len(cols) >= 3:
        rename_map = {}
        for i, standard in zip(range(3), ["Code", "Description", "Value"]):
            if df.columns[i] != standard:
                rename_map[df.columns[i]] = standard
        df = df.rename(columns=rename_map)

    value_col = "Value" if "Value" in df.columns else cols[-1]
    vals, units, _ = zip(*df[value_col].map(extract_value_unit))
    df["Valor_Num"] = pd.to_numeric(vals, errors="coerce")
    df["Unidade"] = units

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / path.name.replace(".xlsx", "_clean.xlsx")
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name="clean")
    return out_path

def main():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(INPUT_DIR.glob("*.xlsx"))
    if not files:
        print(f"[aviso] sem .xlsx em {INPUT_DIR}")
        return
    for f in files:
        out = process_file(f, OUTPUT_DIR)
        print(f"[ok] {f.name} -> {out.name}")

if __name__ == "__main__":
    main()

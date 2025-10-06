# 🛡️ PROTECAI_TESTES

Sistema completo para **extração, normalização e armazenamento de parâmetros de proteção elétrica** a partir de relatórios PDF (MiCOM S1 Agile / Easergy Studio).

## 🌟 Funcionalidades

✅ **Extração de PDFs**: Lê configurações de relés e extrai parâmetros estruturados  
✅ **Normalização de Dados**: Processa e limpa dados extraídos com códigos ANSI padronizados  
✅ **Base PostgreSQL**: Armazena dados em estrutura normalizada para análises complexas  
✅ **Docker Compose**: Ambiente completo com PostgreSQL 16 + Adminer para gestão visual  
✅ **Scripts de Importação**: Automatiza inserção de dados na base normalizada  
✅ **Validação de Dados**: Verificações de integridade e relatórios de importação  

---

## 📂 Estrutura de diretórios

```
protecai_testes/
├─ input_pdfs/         # PDFs originais (tela1.pdf, tela3.pdf)
├─ outputs/
│  ├─ excel/           # Arquivos .xlsx extraídos
│  ├─ csv/             # Arquivos .csv extraídos  
│  ├─ norm_csv/        # CSVs normalizados para importação
│  ├─ norm_excel/      # Versões Excel dos dados normalizados
│  ├─ atrib_limpos/    # Arquivos com valores/unidades separados
│  ├─ doc/             # Documentação e códigos normalizados
│  └─ logs/            # Logs de execução e importação
├─ docker/
│  └─ postgres/        # Configuração Docker PostgreSQL + Adminer
│     ├─ docker-compose.yaml
│     ├─ initdb/       # Scripts de inicialização do banco
│     └─ data/         # Dados persistentes PostgreSQL (gitignored)
├─ docs/               # Documentação SQL e modelagem
├─ src/
│  ├─ app.py           # CLI principal: extração de PDFs
│  ├─ normalizador.py  # Normalização com códigos ANSI
│  ├─ importar_dados_normalizado.py    # Importação para PostgreSQL
│  ├─ importar_dados_postgresql.py     # Importação alternativa
│  ├─ validar_dados_importacao.py      # Validação pós-importação
│  ├─ parsers/         # Funções de parsing PDF
│  └─ utils/           # Utilitários diversos
├─ tests/              # Testes automatizados
├─ README.md
└─ requirements.txt
```

---

## ⚙️ Preparando o ambiente

### 1. Criar e ativar o ambiente virtual
No macOS (já usando o `virtualenvwrapper`):
```bash
mkvirtualenv -p python3.13 protecai_testes
workon protecai_testes
```

### 2. Instalar dependências
```bash
pip install -r requirements.txt
pip install pandas openpyxl xlsxwriter   # caso ainda não estejam no requirements
```

---

## 🚀 Uso do `app.py`

Extrai dados dos PDFs e gera arquivos `.csv` e/ou `.xlsx` em `outputs/`.

### Exemplos:

```bash
# Extrair de vários PDFs e salvar em um único XLSX
python src/app.py --inputs input_pdfs/tela1.pdf input_pdfs/tela3.pdf --xlsx outputs/excel/saida.xlsx

# Extrair de um único PDF e salvar em CSV
python src/app.py --inputs input_pdfs/tela1.pdf --csv outputs/csv/micom.csv

# Extrair de vários PDFs gerando um arquivo por PDF (XLSX/CSV padrão)
python src/app.py --inputs input_pdfs/tela1.pdf input_pdfs/tela3.pdf
```

- **Entradas:** arquivos PDF na pasta `input_pdfs/`.
- **Saída:** CSV/XLSX conforme parâmetros (`--csv`, `--xlsx`).

---

## 🧹 Uso do `split_units.py`

Processa **todos** os arquivos `.xlsx` em `outputs/excel/`, detecta valores no formato **“número + unidade”** e adiciona colunas:

- `Valor_Num` → número convertido para `float`
- `Unidade` → unidade de medida
- Mantém os campos **textuais** (ex.: `2 VT + Residual`, `Group 1`, `Select via Menu`) sem alteração.

### Executar:

```bash
python -m src.utils.split_units
```

- Saída será criada em `outputs/atrib_limpOS/` com o sufixo `_clean.xlsx`.

---

## 🔄 Fluxo de trabalho completo

1. Coloque seus PDFs em `input_pdfs/`.
2. Rode o `app.py` para gerar arquivos em `outputs/excel/` e/ou `outputs/csv/`.
3. Rode o `split_units.py` para criar versões limpas com valores e unidades separados em `outputs/atrib_limpOS/`.

---

## 🧪 Testes

Execute todos os testes com:

```bash
pytest
```

(Os testes devem estar em `tests/` e podem validar parsing e exportação.)

---

## 📝 Logs

Durante a execução, logs podem ser gravados em `outputs/logs/` (dependendo da configuração do `app.py`).

---

## ⚡️ Notas importantes

- O `split_units.py` **não** altera os arquivos originais — cria cópias limpas.  
- Apenas **valores numéricos simples com unidade única** são separados.  
- Campos textuais complexos (ex.: `2 VT + Residual`, `Select via Menu`) permanecem intactos.  
- Ajuste a regex em `split_units.py` caso surjam formatos não previstos de unidade.

---

## 🏗️ Próximos passos

- Integrar `split_units.py` como opção interna do `app.py` (ex.: `--clean`).  
- Expandir testes automatizados para validar a separação de unidades.

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

## 🐳 Docker + PostgreSQL (Recomendado)

### 1. Subir o ambiente Docker

```bash
# Navegar para o diretório do Docker
cd docker/postgres

# Subir PostgreSQL + Adminer
docker-compose up -d

# Verificar se os containers estão rodando
docker-compose ps
```

**Serviços disponíveis:**
- **PostgreSQL 16**: `localhost:5432`
- **Adminer** (interface web): http://localhost:8080

### 2. Acessar o banco PostgreSQL

**Via psql (linha de comando):**
```bash
# Entrar no container PostgreSQL
docker exec -it postgres-protecai psql -U protecai -d protecai_db

# Ou diretamente do host (se tiver psql instalado)
psql -h localhost -p 5432 -U protecai -d protecai_db
```

**Via Adminer (interface web):**
1. Acesse: http://localhost:8080
2. **Sistema**: PostgreSQL
3. **Servidor**: postgres-protecai
4. **Usuário**: protecai
5. **Senha**: protecai_password
6. **Base de dados**: protecai_db

### 3. Parar o ambiente Docker

```bash
# Parar containers (mantém dados)
docker-compose stop

# Parar e remover containers (mantém dados persistentes)
docker-compose down

# Parar e remover TUDO (incluindo dados - ⚠️ CUIDADO!)
docker-compose down -v
```

---

## ⚙️ Preparando o ambiente Python

### 1. Criar ambiente virtual
```bash
# Com virtualenvwrapper (macOS)
mkvirtualenv -p python3.13 protecai_testes
workon protecai_testes

# Ou com venv padrão
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 2. Instalar dependências
```bash
pip install -r requirements.txt
```

---

## 🚀 Fluxo de trabalho completo

### 1. Extração de PDFs → CSV/Excel

```bash
# Extrair dados dos PDFs para formato tabular
python src/app.py --inputs input_pdfs/tela1.pdf input_pdfs/tela3.pdf --xlsx outputs/excel/dados.xlsx

# Ou para CSV
python src/app.py --inputs input_pdfs/tela1.pdf input_pdfs/tela3.pdf --csv outputs/csv/dados.csv
```

### 2. Normalização com códigos ANSI

```bash
# Processa arquivos CSV/Excel e aplica normalização ANSI
python src/normalizador.py

# Gera arquivos em outputs/norm_csv/ e outputs/norm_excel/
```

### 3. Importação para PostgreSQL

**Importante**: Certifique-se que o Docker está rodando primeiro!

```bash
# Importar dados normalizados para PostgreSQL
python src/importar_dados_normalizado.py

# Verifica log de importação
cat outputs/logs/relatorio_importacao.json
```

### 4. Validar importação

```bash
# Executar validações pós-importação
python src/validar_dados_importacao.py
```

---

## 📊 Explorando os dados no PostgreSQL

### Estrutura das tabelas

```sql
-- Verificar estrutura do schema
\dt protec_ai.*

-- Tabelas principais:
-- • fabricantes (6 registros: Schneider, ABB, GE, etc.)
-- • tipos_token (11 tipos: ANSI, IEEE, IEC, etc.)  
-- • arquivos (arquivos CSV processados)
-- • campos_originais (códigos e descrições originais)
-- • valores_originais (valores extraídos dos PDFs)
-- • tokens_valores (tokens normalizados com confiança)
```

### Consultas úteis

```sql
-- Ver todos os fabricantes
SELECT * FROM protec_ai.fabricantes;

-- Dados completos (via view)
SELECT * FROM protec_ai.vw_dados_completos LIMIT 10;

-- Códigos ANSI encontrados
SELECT * FROM protec_ai.vw_codigos_ansi;

-- Campos por fabricante
SELECT * FROM protec_ai.vw_campos_por_fabricante;

-- Estatísticas de importação
SELECT 
    COUNT(*) as total_campos,
    COUNT(DISTINCT arquivo_id) as arquivos_processados
FROM protec_ai.campos_originais;
```

### Views disponíveis

1. **`vw_dados_completos`**: Visão consolidada de todos os dados
2. **`vw_codigos_ansi`**: Apenas registros com códigos ANSI válidos  
3. **`vw_campos_por_fabricante`**: Agrupamento por fabricante

---

## 🔧 Scripts utilitários

### Limpeza de valores/unidades
```bash
# Separar valores numéricos das unidades
python -m src.utils.split_units

# Saída em outputs/atrib_limpos/ com sufixo _clean.xlsx
```

### Geração de documentação
```bash
# Gerar documentação dos códigos normalizados  
python -m src.utils.generate_docx_documentation

# Saída em outputs/doc/
```

---

## 🧪 Testes e validação

```bash
# Executar testes automatizados
pytest tests/

# Verificar logs de importação
ls -la outputs/logs/

# Validar dados no PostgreSQL
python src/validar_dados_importacao.py
```

---

## 📝 Logs e relatórios

### Locais importantes:
- **`outputs/logs/relatorio_importacao.json`**: Status da última importação
- **`outputs/logs/importacao_normalizada.log`**: Log detalhado do processo
- **`outputs/doc/`**: Documentação gerada automaticamente

### Exemplo de relatório de importação:
```json
{
  "arquivos_processados": 2,
  "fabricantes_inseridos": 6,
  "tipos_token_inseridos": 11,
  "campos_inseridos": 486,
  "valores_inseridos": 332,
  "tokens_inseridos": 332,
  "erros": [],
  "duracao_segundos": 1.1
}
```

---

## 🔍 Troubleshooting

### Docker não sobe
```bash
# Verificar se as portas estão livres
lsof -i :5432  # PostgreSQL
lsof -i :8080  # Adminer

# Recriar containers
docker-compose down
docker-compose up -d --force-recreate
```

### Erro de conexão PostgreSQL
```bash
# Verificar se o container está rodando
docker-compose ps

# Ver logs do PostgreSQL
docker-compose logs postgres-protecai

# Testar conexão
docker exec -it postgres-protecai psql -U protecai -d protecai_db -c "SELECT version();"
```

### Erro na importação
```bash
# Verificar log detalhado
cat outputs/logs/relatorio_importacao.json

# Verificar estrutura do banco
docker exec -it postgres-protecai psql -U protecai -d protecai_db -c "\dt protec_ai.*"
```

---

## 🚀 Próximos passos

- **API REST**: Desenvolver API para consultar dados normalizados
- **Dashboard**: Interface web para visualização dos dados
- **ML Pipeline**: Algoritmos de análise de padrões nos parâmetros  
- **Exportação avançada**: Relatórios customizados em múltiplos formatos
- **Integração CI/CD**: Automatizar testes e deployments

---

## 📄 Licença

Este projeto é destinado para uso interno da Petrobras no contexto de proteção elétrica.
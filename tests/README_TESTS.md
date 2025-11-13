# 🧪 Guia de Testes - ProtecAI

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Estrutura dos Testes](#estrutura-dos-testes)
3. [Como Executar](#como-executar)
4. [Descrição dos Testes](#descrição-dos-testes)
5. [Configuração](#configuração)
6. [Boas Práticas](#boas-práticas)

---

## 🎯 Visão Geral

Suite de testes completa para validar o pipeline de processamento de dados de relés de proteção:

- ✅ **Extração de Glossário**: Validação da leitura de Excel e exportação JSON/CSV
- ✅ **Geração de SQL**: Validação da geração de scripts de população do banco
- ✅ **Geração de Relatórios**: Validação dos 4 formatos de export (JSON/CSV/XLSX/PDF)
- ✅ **Integração End-to-End**: Validação do pipeline completo

---

## 📁 Estrutura dos Testes

```
tests/
├── conftest.py                      # Configurações compartilhadas e fixtures
├── test_glossary_extraction.py     # Testes de extração do glossário
├── test_sql_generation.py          # Testes de geração de SQL
├── test_report_generation.py       # Testes de geração de relatórios
├── test_integration_pipeline.py    # Testes de integração completos
└── README_TESTS.md                 # Este arquivo
```

---

## 🚀 Como Executar

### Pré-requisitos

```bash
# Instalar dependências de teste
pip install pytest pytest-mock pytest-cov openpyxl reportlab pandas psycopg2-binary
```

### Executar Todos os Testes

```bash
# Executar todos os testes
pytest tests/ -v

# Com cobertura de código
pytest tests/ --cov=scripts --cov=api/services --cov-report=html

# Apenas testes unitários (rápidos)
pytest tests/ -v -m unit

# Apenas testes de integração
pytest tests/ -v -m integration
```

### Executar Testes Específicos

```bash
# Apenas testes de glossário
pytest tests/test_glossary_extraction.py -v

# Apenas testes de SQL
pytest tests/test_sql_generation.py -v

# Apenas testes de relatórios
pytest tests/test_report_generation.py -v

# Apenas testes de integração
pytest tests/test_integration_pipeline.py -v

# Executar teste específico
pytest tests/test_glossary_extraction.py::TestNormalizeCode::test_normalize_basic_code -v
```

### Opções Úteis

```bash
# Mostrar print statements
pytest tests/ -v -s

# Parar no primeiro erro
pytest tests/ -v -x

# Executar apenas testes que falharam na última vez
pytest tests/ --lf

# Modo verbose com traceback curto
pytest tests/ -v --tb=short

# Executar em paralelo (requer pytest-xdist)
pytest tests/ -n auto
```

---

## 📊 Descrição dos Testes

### 1️⃣ test_glossary_extraction.py

**Objetivo**: Validar extração de dados do glossário Excel

**Classes de Teste**:
- `TestNormalizeCode`: Normalização de códigos de parâmetros
- `TestReadGlossarySheet`: Leitura de planilhas Excel
- `TestExportToJson`: Exportação para formato JSON
- `TestExportToCsv`: Exportação para formato CSV
- `TestIntegrationGlossaryExtraction`: Workflow completo de extração
- `TestEdgeCases`: Casos extremos (caracteres especiais, unicode, etc.)

**Cobertura**:
- ✅ Leitura de Excel com diferentes estruturas
- ✅ Normalização de códigos
- ✅ Exportação JSON/CSV
- ✅ Tratamento de dados vazios
- ✅ Caracteres especiais e unicode
- ✅ Preservação de dados

**Exemplo**:
```bash
pytest tests/test_glossary_extraction.py -v
```

---

### 2️⃣ test_sql_generation.py

**Objetivo**: Validar geração de scripts SQL e CSV para popular banco de dados

**Classes de Teste**:
- `TestExtractFunctionFromName`: Extração de códigos ANSI (50, 27, 81, etc.)
- `TestCategorizeParameter`: Categorização de parâmetros (protection, control, etc.)
- `TestGenerateSqlProtectionFunctions`: Geração de SQL para funções
- `TestGenerateSqlRelaySettings`: Geração de SQL para configurações
- `TestGenerateCsvFunctions`: Geração de CSV
- `TestIntegrationSqlGeneration`: Workflow completo SQL

**Cobertura**:
- ✅ Extração de funções ANSI (50, 50N, 51, 27, 59, 81, 87)
- ✅ Categorização correta (protection, electrical, control, monitoring)
- ✅ Geração de SQL válido
- ✅ Geração de CSV
- ✅ Eliminação de duplicatas
- ✅ Preservação de unidades

**Exemplo**:
```bash
pytest tests/test_sql_generation.py::TestExtractFunctionFromName -v
```

---

### 3️⃣ test_report_generation.py

**Objetivo**: Validar geração de relatórios de configuração em múltiplos formatos

**Classes de Teste**:
- `TestRelayConfigReportService`: Serviço principal de relatórios
- `TestReportGenerationCSV`: Geração de relatórios CSV
- `TestReportGenerationXLSX`: Geração de relatórios Excel
- `TestReportGenerationPDF`: Geração de relatórios PDF
- `TestEdgeCases`: Casos extremos (equipamento não encontrado, sem dados, etc.)
- `TestTokenization`: Tokenização de valores

**Cobertura**:
- ✅ Geração de relatórios JSON
- ✅ Geração de relatórios CSV (parseável)
- ✅ Geração de relatórios XLSX (múltiplas sheets)
- ✅ Geração de relatórios PDF (válido)
- ✅ Filtro include_disabled
- ✅ Tratamento de equipamento não encontrado
- ✅ Tokenização de valores

**Exemplo**:
```bash
pytest tests/test_report_generation.py::TestReportGenerationXLSX -v
```

---

### 4️⃣ test_integration_pipeline.py

**Objetivo**: Validar pipeline completo end-to-end

**Classes de Teste**:
- `TestEndToEndPipeline`: Pipeline completo sem DB
- `TestPipelineDataIntegrity`: Integridade de dados ao longo do pipeline
- `TestPipelineErrorHandling`: Tratamento de erros
- `TestPipelinePerformance`: Testes de desempenho
- `TestPipelineValidation`: Validação de dados

**Cobertura**:
- ✅ Workflow: Extração → SQL → Validação
- ✅ Preservação de dados através do pipeline
- ✅ Tratamento de caracteres especiais
- ✅ Tratamento de erros (arquivo não encontrado, JSON inválido)
- ✅ Performance (500+ parâmetros em <5s)
- ✅ Precisão de extração de códigos ANSI
- ✅ Preservação de unidades

**Exemplo**:
```bash
pytest tests/test_integration_pipeline.py::TestEndToEndPipeline -v
```

---

## ⚙️ Configuração

### conftest.py

Arquivo central de configuração com:

**Fixtures de Configuração**:
- `project_root`: Diretório raiz do projeto
- `test_data_dir`: Diretório de dados de teste
- `temp_output_dir`: Diretório temporário para outputs

**Fixtures de Banco de Dados**:
- `test_db_config`: Configuração de DB de teste
- `db_session`: Sessão com rollback automático
- `clean_db_session`: Sessão que limpa tabelas antes do teste

**Fixtures de Dados**:
- `sample_glossary_data`: Dados de glossário de exemplo
- `sample_protection_functions`: Funções de proteção de exemplo
- `sample_relay_settings`: Configurações de exemplo
- `sample_equipment_info`: Informações de equipamento

**Fixtures Utilitárias**:
- `create_temp_excel`: Factory para criar Excel temporário
- `create_temp_json`: Factory para criar JSON temporário
- `assert_sql_valid`: Validador de sintaxe SQL

**Marcadores**:
- `@pytest.mark.unit`: Testes unitários rápidos
- `@pytest.mark.integration`: Testes de integração
- `@pytest.mark.requires_db`: Testes que precisam de DB
- `@pytest.mark.slow`: Testes lentos

---

## 🎯 Boas Práticas

### Organizando Testes

```python
# ✅ BOM: Testes organizados por classe
class TestFunctionality:
    def test_basic_case(self):
        pass
    
    def test_edge_case(self):
        pass

# ❌ RUIM: Testes desorganizados
def test_something_1():
    pass
def test_something_2():
    pass
```

### Usando Fixtures

```python
# ✅ BOM: Reutilizar fixtures
def test_with_fixture(sample_glossary_data):
    result = process(sample_glossary_data)
    assert result is not None

# ❌ RUIM: Criar dados em cada teste
def test_without_fixture():
    data = {'codigo': 'P001', ...}  # Repetitivo
    result = process(data)
```

### Nomes Descritivos

```python
# ✅ BOM: Nome descritivo
def test_extract_function_50_from_parameter_name():
    pass

# ❌ RUIM: Nome vago
def test_extract():
    pass
```

### Asserções Claras

```python
# ✅ BOM: Asserção clara
assert len(results) == 5, f"Esperado 5 resultados, obteve {len(results)}"

# ❌ RUIM: Asserção sem contexto
assert len(results) == 5
```

### Isolamento de Testes

```python
# ✅ BOM: Teste isolado (usa tmp_path)
def test_file_creation(tmp_path):
    file = tmp_path / "test.json"
    create_file(file)
    assert file.exists()

# ❌ RUIM: Teste que afeta filesystem global
def test_file_creation():
    create_file("test.json")  # Fica no filesystem
```

---

## 📈 Cobertura de Código

Para gerar relatório de cobertura:

```bash
# Gerar cobertura HTML
pytest tests/ --cov=scripts --cov=api/services --cov-report=html

# Abrir relatório
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Meta de Cobertura**: Mínimo 80% para código crítico

---

## 🐛 Debugging de Testes

### Ver Output Completo

```bash
pytest tests/test_glossary_extraction.py -v -s
```

### Ver Traceback Completo

```bash
pytest tests/test_glossary_extraction.py -v --tb=long
```

### Debugar com PDB

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    result = my_function()
```

### Ver Warnings

```bash
pytest tests/ -v -W all
```

---

## 📝 Checklist de Testes

Antes de fazer commit:

- [ ] Todos os testes passam: `pytest tests/ -v`
- [ ] Cobertura adequada: `pytest tests/ --cov --cov-report=term-missing`
- [ ] Sem warnings: `pytest tests/ -W error`
- [ ] Testes de integração OK: `pytest tests/ -m integration`
- [ ] Documentação atualizada

---

## 🆘 Troubleshooting

### Erro: "ModuleNotFoundError"

```bash
# Solução: Instalar dependências
pip install -r requirements.txt
pip install pytest pytest-mock pytest-cov
```

### Erro: "Database connection failed"

```bash
# Solução: Configurar variáveis de ambiente
export TEST_DB_HOST=localhost
export TEST_DB_NAME=protecai_test
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=postgres
```

### Erro: "Permission denied" ao criar arquivos

```bash
# Solução: Usar tmp_path fixture (pytest gerencia automaticamente)
def test_file(tmp_path):
    file = tmp_path / "test.txt"  # Diretório temporário gerenciado pelo pytest
```

---

## 📚 Recursos Adicionais

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-mock Documentation](https://pytest-mock.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

---

**Última atualização**: 2025-11-03

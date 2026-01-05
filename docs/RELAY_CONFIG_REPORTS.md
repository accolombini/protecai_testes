# Relatórios de Configuração de Relés - Documentação Completa

## 📋 Visão Geral

Sistema completo para geração de relatórios de configuração (setup) de relés de proteção elétrica, consolidando dados do glossário MICON/SEPAM e configurações armazenadas no banco de dados PostgreSQL.

## 🎯 Funcionalidades Implementadas

### 1. API REST Endpoints

#### **GET** `/api/relay-config/report/{equipment_id}`
Retorna relatório JSON completo com:
- Informações do equipamento (tag, fabricante, modelo, serial)
- Funções de proteção configuradas
- Parâmetros/ajustes de cada função
- Configurações gerais
- Sumário estatístico

**Parâmetros de query:**
- `include_disabled` (boolean): Incluir funções/parâmetros desabilitados (default: false)

**Resposta:**
```json
{
  "equipment": {
    "id": 1,
    "equipment_tag": "52-MF-02A",
    "manufacturer_name": "Schneider Electric",
    "model_name": "P220",
    "serial_number": "SN123456",
    "voltage_class": "13.8 kV",
    "phase_ct_primary": 1500,
    "phase_ct_secondary": 5
  },
  "protection_functions": [
    {
      "function_code": "50",
      "function_name": "Instantaneous Overcurrent",
      "is_enabled": true,
      "is_primary": true,
      "settings": [
        {
          "parameter_name": "I>",
          "parameter_code": "0201",
          "set_value": 0.63,
          "set_value_text": "0.63In",
          "unit_of_measure": "In",
          "setting_group": "GROUP_1",
          "is_enabled": true
        }
      ],
      "settings_count": 12
    }
  ],
  "general_settings": [
    {
      "parameter_name": "Frequency",
      "parameter_code": "0104",
      "set_value": 60,
      "unit_of_measure": "Hz"
    }
  ],
  "summary": {
    "total_functions": 5,
    "enabled_functions": 4,
    "total_settings": 32,
    "report_generated_at": "2025-11-03T12:00:00"
  }
}
```

#### **GET** `/api/relay-config/export/{equipment_id}`
Exporta relatório em formato CSV, XLSX ou PDF para download.

**Parâmetros de query:**
- `format` (string): csv | xlsx | pdf (obrigatório)
- `include_disabled` (boolean): Incluir desabilitados (default: false)

**Resposta:**
- Header: `Content-Disposition: attachment; filename="CONFIG_52MF02A_20251103_120000.{ext}"`
- Body: Arquivo binário para download

**Exemplo de uso (curl):**
```bash
# Download CSV
curl -O http://localhost:8000/api/relay-config/export/1?format=csv

# Download PDF
curl -O http://localhost:8000/api/relay-config/export/1?format=pdf

# Download XLSX com funções desabilitadas
curl -O "http://localhost:8000/api/relay-config/export/1?format=xlsx&include_disabled=true"
```

#### **GET** `/api/relay-config/equipment/list`
Lista equipamentos disponíveis para geração de relatório.

**Parâmetros de query:**
- `manufacturer` (string): Filtro por fabricante (opcional)
- `model` (string): Filtro por modelo (opcional)
- `status` (string): Filtro por status (opcional)
- `limit` (int): Limite de resultados (default: 100, max: 1000)

**Resposta:**
```json
{
  "total": 50,
  "equipment": [
    {
      "id": 1,
      "equipment_tag": "52-MF-02A",
      "manufacturer_name": "Schneider Electric",
      "model_name": "P220",
      "status": "active",
      "settings_count": 32,
      "functions_count": 5,
      "has_settings": true,
      "has_functions": true
    }
  ],
  "filters_applied": {
    "manufacturer": "Schneider",
    "model": null,
    "status": null
  }
}
```

#### **GET** `/api/relay-config/health`
Verifica saúde do serviço e dependências disponíveis.

**Resposta:**
```json
{
  "status": "healthy",
  "service": "Relay Configuration Reports",
  "capabilities": {
    "json": true,
    "csv": true,
    "xlsx": true,
    "pdf": true
  },
  "dependencies": {
    "openpyxl": true,
    "reportlab": true
  }
}
```

### 2. Script Standalone

**Arquivo:** `scripts/generate_relay_config_report.py`

Gera relatórios sem necessidade de rodar a API FastAPI.

**Uso:**

```bash
# Listar equipamentos disponíveis
python scripts/generate_relay_config_report.py --list

# Listar equipamentos Schneider
python scripts/generate_relay_config_report.py --list --manufacturer Schneider

# Gerar relatório JSON no stdout
python scripts/generate_relay_config_report.py --equipment-id 1 --format json

# Gerar CSV e salvar em arquivo
python scripts/generate_relay_config_report.py --equipment-id 1 --format csv --output outputs/reports/

# Gerar PDF com funções desabilitadas
python scripts/generate_relay_config_report.py --equipment-id 1 --format pdf --include-disabled --output outputs/reports/

# Gerar XLSX
python scripts/generate_relay_config_report.py --equipment-id 1 --format xlsx --output outputs/reports/
```

**Opções:**
- `--list`: Lista equipamentos disponíveis
- `--equipment-id ID`: ID do equipamento (obrigatório)
- `--format {json,csv,xlsx,pdf}`: Formato do relatório (default: json)
- `--include-disabled`: Incluir funções/parâmetros desabilitados
- `--output DIR`: Diretório de saída (obrigatório para CSV/XLSX/PDF)
- `--manufacturer NOME`: Filtro por fabricante (usado com --list)
- `--model NOME`: Filtro por modelo (usado com --list)

## 📂 Estrutura de Arquivos

```
protecai_testes/
├── api/
│   ├── services/
│   │   └── relay_config_report_service.py  # ✅ Serviço de geração
│   └── routers/
│       └── relay_config_reports.py          # ✅ Endpoints API
├── scripts/
│   └── generate_relay_config_report.py      # ✅ Script standalone
├── outputs/
│   └── reports/                              # Relatórios gerados
│       ├── CONFIG_52MF02A_20251103_120000.csv
│       ├── CONFIG_52MF02A_20251103_120001.xlsx
│       └── CONFIG_52MF02A_20251103_120002.pdf
└── docs/
    └── RELAY_CONFIG_REPORTS.md               # Esta documentação
```

## 🔧 Configuração

### Dependências Python

**Obrigatórias:**
```txt
fastapi>=0.104.1
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
```

**Opcionais (para XLSX/PDF):**
```txt
openpyxl>=3.1.0     # Para exportação XLSX
reportlab>=4.0.0    # Para exportação PDF
```

**Instalação:**
```bash
# Obrigatórias
pip install fastapi sqlalchemy psycopg2-binary

# Opcionais
pip install openpyxl reportlab
```

### Banco de Dados

**Pré-requisitos:**
- PostgreSQL rodando
- Database `protecai_db` criado
- Schema `protec_ai` criado
- Tabelas populadas:
  - `relay_equipment`
  - `relay_models`
  - `manufacturers`
  - `protection_functions`
  - `relay_settings`
  - `equipment_protection_functions`
  - `electrical_configuration`

**Configuração (editar se necessário):**

Em `scripts/generate_relay_config_report.py` e `api/core/database.py`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}
```

## 🚀 Execução

### Modo API (Recomendado para Produção)

```bash
# Iniciar API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Acessar documentação interativa
open http://localhost:8000/docs

# Testar endpoint
curl http://localhost:8000/api/relay-config/health
```

### Modo Script (Para Automação/Batch)

```bash
# Gerar relatório específico
python scripts/generate_relay_config_report.py \
    --equipment-id 1 \
    --format pdf \
    --output outputs/reports/

# Gerar múltiplos relatórios (bash loop)
for id in {1..10}; do
    python scripts/generate_relay_config_report.py \
        --equipment-id $id \
        --format csv \
        --output outputs/reports/
done
```

## 📊 Formatos de Saída

### JSON
- **Uso:** APIs, processamento programático
- **Estrutura:** Hierárquica completa
- **Tamanho:** ~5-20 KB por equipamento
- **Encoding:** UTF-8

### CSV
- **Uso:** Excel, análise em planilhas
- **Estrutura:** Tabular simplificada
- **Tamanho:** ~2-10 KB por equipamento
- **Encoding:** UTF-8
- **Delimitador:** vírgula `,`
- **Quote:** aspas duplas `"`

**Estrutura:**
```csv
RELATÓRIO DE CONFIGURAÇÃO DE RELÉ

Tag,52-MF-02A
Fabricante,Schneider Electric
Modelo,P220
Serial,SN123456

FUNÇÕES DE PROTEÇÃO E CONFIGURAÇÕES

Função: 50 - Instantaneous Overcurrent,,Habilitada: True
Parâmetro,Código,Valor,Unidade,Grupo
I>,0201,0.63In,In,GROUP_1
...
```

### XLSX (Excel)
- **Uso:** Relatórios formais, apresentações
- **Estrutura:** Planilha formatada
- **Tamanho:** ~10-50 KB por equipamento
- **Features:**
  - Cabeçalhos formatados (bold, cores)
  - Células mescladas
  - Larguras de coluna ajustadas
  - Bordas e grid

### PDF
- **Uso:** Documentação oficial, arquivo
- **Estrutura:** Documento paginado formatado
- **Tamanho:** ~50-200 KB por equipamento
- **Features:**
  - Título centralizado
  - Tabelas com bordas
  - Quebras de página automáticas
  - Layout A4

## 🔍 Queries SQL Utilizadas

### Informações do Equipamento
```sql
SELECT 
    e.id, e.equipment_tag, e.plant_reference, e.bay_position,
    e.serial_number, e.software_version, e.description,
    e.frequency, e.status,
    m.name as model_name, m.model_type, m.voltage_class,
    mf.name as manufacturer_name,
    ec.phase_ct_primary, ec.phase_ct_secondary,
    ec.neutral_ct_primary, ec.neutral_ct_secondary,
    ec.vt_primary, ec.vt_secondary
FROM protec_ai.relay_equipment e
LEFT JOIN protec_ai.relay_models m ON e.model_id = m.id
LEFT JOIN protec_ai.manufacturers mf ON m.manufacturer_id = mf.id
LEFT JOIN protec_ai.electrical_configuration ec ON e.id = ec.equipment_id
WHERE e.id = :equipment_id
```

### Funções de Proteção
```sql
SELECT 
    pf.id, pf.function_code, pf.function_name,
    pf.function_description, pf.ansi_ieee_standard,
    pf.is_primary, epf.is_enabled, epf.priority
FROM protec_ai.protection_functions pf
LEFT JOIN protec_ai.equipment_protection_functions epf 
    ON pf.id = epf.function_id 
    AND epf.equipment_id = :equipment_id
WHERE epf.equipment_id = :equipment_id
ORDER BY pf.function_code, pf.function_name
```

### Configurações do Relé
```sql
SELECT 
    rs.id, rs.parameter_name, rs.parameter_code,
    rs.set_value, rs.set_value_text, rs.unit_of_measure,
    rs.setting_group, rs.is_enabled,
    pf.function_code, pf.function_name
FROM protec_ai.relay_settings rs
LEFT JOIN protec_ai.protection_functions pf ON rs.function_id = pf.id
WHERE rs.equipment_id = :equipment_id
  AND rs.function_id = :function_id
ORDER BY rs.parameter_code
```

## ⚠️ Considerações Importantes

### Segurança
- **API**: Endpoints não possuem autenticação (adicionar antes de produção)
- **Database**: Credenciais hardcoded (mover para variáveis de ambiente)
- **Acesso**: Sem controle de permissões (implementar RBAC se necessário)

### Performance
- **Queries**: Otimizadas com LEFT JOINs e indexes
- **Cache**: Não implementado (considerar Redis para alta carga)
- **Paginação**: Lista de equipamentos limitada a 1000 (ajustar conforme necessidade)

### Limitações
- **PDF/XLSX**: Requerem bibliotecas opcionais (openpyxl, reportlab)
- **Tamanho**: PDFs podem ser grandes para equipamentos com muitas funções (>100 settings)
- **Encoding**: UTF-8 obrigatório (problemas com caracteres especiais em CSV legado)

### Manutenção
- **Logs**: Gerados em `outputs/logs/` (rotacionar periodicamente)
- **Relatórios**: Salvos em `outputs/reports/` (limpar antigos)
- **Banco**: Backup regular antes de modificar schemas

## 📝 Exemplos Práticos

### Exemplo 1: Gerar relatório para análise rápida
```bash
# JSON no terminal (pipe para jq para pretty-print)
python scripts/generate_relay_config_report.py --equipment-id 1 --format json | jq .
```

### Exemplo 2: Exportar todos os equipamentos Schneider
```bash
# Listar IDs
python scripts/generate_relay_config_report.py --list --manufacturer Schneider

# Gerar PDFs em loop
for id in 1 2 3 4 5; do
    python scripts/generate_relay_config_report.py \
        --equipment-id $id \
        --format pdf \
        --output outputs/reports/schneider/
done
```

### Exemplo 3: Integração com API externa
```python
import requests

# Obter lista de equipamentos
response = requests.get('http://localhost:8000/api/relay-config/equipment/list')
equipment_list = response.json()['equipment']

# Gerar relatório para cada um
for eq in equipment_list:
    response = requests.get(
        f"http://localhost:8000/api/relay-config/report/{eq['id']}"
    )
    report = response.json()
    
    # Processar relatório...
    print(f"Equipamento {eq['equipment_tag']}: {report['summary']['total_settings']} settings")
```

## 🧪 Testes

### Teste Manual (API)
```bash
# 1. Iniciar API
uvicorn api.main:app --reload

# 2. Health check
curl http://localhost:8000/api/relay-config/health

# 3. Listar equipamentos
curl http://localhost:8000/api/relay-config/equipment/list

# 4. Gerar relatório JSON
curl http://localhost:8000/api/relay-config/report/1 | jq .

# 5. Download PDF
curl -O http://localhost:8000/api/relay-config/export/1?format=pdf
```

### Teste Manual (Script)
```bash
# 1. Listar equipamentos
python scripts/generate_relay_config_report.py --list

# 2. Gerar JSON
python scripts/generate_relay_config_report.py --equipment-id 1 --format json

# 3. Gerar CSV
python scripts/generate_relay_config_report.py --equipment-id 1 --format csv --output /tmp/

# 4. Verificar arquivo gerado
ls -lh /tmp/CONFIG_*
```

## 📚 Referências

- **Schema DB**: `scripts/database_cleanup_and_structure.sql`
- **Glossário**: `inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx`
- **Pipeline Importação**: `docs/PIPELINE_IMPORTACAO_GLOSSARIO.md`
- **API Main**: `api/main.py`
- **FastAPI Docs**: `http://localhost:8000/docs` (quando API rodando)

---

**Autor:** ProtecAI Engineering Team  
**Data:** 2025-11-03  
**Versão:** 1.0.0

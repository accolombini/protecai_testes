# ProtecAI - Sistema de Proteção Elétrica Industrial

**Sistema enterprise-grade para extração, normalização e análise de parâmetros de proteção elétrica de subestações industriais.**

---

## 📋 Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Funcionalidades](#funcionalidades)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Uso](#uso)
- [API REST](#api-rest)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Banco de Dados](#banco-de-dados)
- [Desenvolvimento](#desenvolvimento)
- [Padrões de Qualidade](#padrões-de-qualidade)
- [Licença](#licença)

---

## 🎯 Visão Geral

ProtecAI é um sistema robusto desenvolvido para o setor de engenharia de proteção elétrica da Petrobras, capaz de processar automaticamente configurações de relés de proteção de **qualquer fabricante** (Schneider Electric, General Electric, ABB, Siemens, SEL, etc.) e gerar relatórios consolidados para análise técnica.

### Princípios Fundamentais

- **ROBUSTEZ**: Sistema crítico para operação de subestações elétricas
- **FLEXIBILIDADE**: Adapta-se automaticamente a novos fabricantes/modelos
- **DADOS REAIS**: Zero tolerância a dados fictícios (mock/fake)
- **CAUSA RAIZ**: Problemas sempre corrigidos na origem, não sintomas
- **SEGURANÇA**: Vidas dependem da precisão dos dados de proteção

---

## �️ Arquitetura do Sistema

```
┌─────────────────┐
│   Arquivos      │  PDF, TXT, S40, XLSX, CSV
│   de Entrada    │  (Múltiplos fabricantes)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Conversor      │  Universal Format Converter
│  Universal      │  Detecção automática de formato
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CSV            │  Formato padronizado:
│  Padronizado    │  Code | Description | Value
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │  Banco normalizado (3NF)
│  Database       │  protec_ai schema
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  REST API       │  FastAPI + SQLAlchemy
│  (FastAPI)      │  18+ endpoints
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Frontend       │  React + TypeScript
│  (React)        │  Dashboards e relatórios
└─────────────────┘
```

### Componentes Principais

1. **Universal Format Converter**: Converte qualquer formato para CSV padronizado
2. **Relay Processor**: Detecta fabricante, extrai metadados, importa para DB
3. **PostgreSQL Database**: Armazena dados normalizados (3NF)
4. **REST API**: Expõe dados via FastAPI (JSON, CSV, XLSX, PDF)
5. **Frontend**: Interface React para visualização e geração de relatórios

---

## ✨ Funcionalidades

### Processamento de Dados

- ✅ **Extração Universal**: PDF (PyPDF2), TXT, S40/S41/S80 (Schneider), XLSX, CSV
- ✅ **Detecção Automática**: Identifica fabricante através de regex patterns
- ✅ **Normalização ANSI/IEEE**: Padronização com códigos internacionais
- ✅ **Consolidação**: Elimina duplicatas e variações de nomes
- ✅ **Rastreabilidade**: Logs detalhados de todas as operações

### Relatórios e Análises

- ✅ **Metadados Dinâmicos**: Fabricantes, modelos, bays, status extraídos do DB
- ✅ **Filtros Avançados**: Combinação de múltiplos critérios
- ✅ **Exportação Multi-formato**: CSV, XLSX, PDF com headers descritivos
- ✅ **Nomes Inteligentes**: `REL_SCHN-P220_20251102_150530.csv`
- ✅ **Performance Otimizada**: Queries com indexes, ~18ms para 50 equipamentos

### Integração e Extensibilidade

- ✅ **REST API Completa**: 18+ endpoints documentados (OpenAPI/Swagger)
- ✅ **Banco Normalizado**: Schema 3NF com relacionamentos corretos
- ✅ **Docker Compose**: PostgreSQL 16 + Adminer containerizados
- ✅ **Extensível**: Novos fabricantes sem modificação de código  

---

## � Requisitos

### Software

- **Python**: 3.12+
- **PostgreSQL**: 16+ (via Docker)
- **Docker**: 20+ e Docker Compose
- **Node.js**: 18+ (para frontend)

### Bibliotecas Python

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.10
pydantic==2.5.1
pandas==2.3.2
openpyxl==3.1.5
reportlab==4.0.7
PyPDF2==3.0.1
python-docx==1.2.0
```

Ver `requirements.txt` para lista completa.

---

## 🚀 Instalação

### 1. Clone o Repositório

```bash
git clone https://github.com/accolombini/protecai_testes.git
cd protecai_testes
```

### 2. Configure Ambiente Virtual Python

```bash
# Criar ambiente virtual
python3 -m venv protecai_testes

# Ativar (Linux/macOS)
source protecai_testes/bin/activate

# Ativar (Windows)
protecai_testes\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configurar PostgreSQL (Docker)

```bash
# Navegar para diretório Docker
cd docker/postgres

# Verificar arquivo .env (criado automaticamente)
cat .env

# Subir containers
docker compose up -d

# Verificar status
docker compose ps
```

**Serviços Disponíveis:**
- PostgreSQL: `localhost:5432`
- Adminer (UI): http://localhost:8080

**Credenciais Padrão:**
- Usuário: `protecai`
- Senha: `protecai`
- Database: `protecai_db`

### 4. Inicializar Banco de Dados

```bash
# Voltar para raiz do projeto
cd ../..

# Criar schema protec_ai e tabelas (automático no primeiro uso)
# ou execute manualmente:
PGPASSWORD=protecai psql -h localhost -U protecai -d protecai_db -f docs/SCHEMA_CONFIGURACOES_RELES_CORRETO.sql
```

---

## � Uso

### Processamento de Arquivos

#### Fluxo Completo (Recomendado)

```bash
# 1. Converter todos os formatos para CSV padronizado
python src/universal_format_converter.py

# 2. Pipeline completo: conversão + normalização + importação
python src/pipeline_completo.py

# 3. Verificar logs
cat outputs/logs/relatorio_importacao.json
```

#### Processamento Específico

```bash
# Apenas extração de PDFs
python src/app.py

# Apenas normalização ANSI
python src/normalizador.py

# Apenas importação para PostgreSQL
python src/importar_dados_normalizado.py
```

### API REST

#### Iniciar Servidor

```bash
cd api/
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Acessos:**
- API: http://localhost:8000
- Documentação: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

#### Endpoints Principais

```bash
# Metadados para filtros
curl http://localhost:8000/api/v1/reports/metadata

# Exportar relatório CSV
curl "http://localhost:8000/api/v1/reports/export/csv?status=ACTIVE" \
  -o relatorio.csv

# Exportar relatório PDF
curl "http://localhost:8000/api/v1/reports/export/pdf?manufacturer=Schneider" \
  -o relatorio.pdf
```

### Frontend

```bash
cd frontend/protecai-frontend
npm install
npm run dev
```

Acesse: http://localhost:5173

---

## 🌐 API REST

### Endpoints de Relatórios

| Método | Endpoint | Descrição | Performance |
|--------|----------|-----------|-------------|
| GET | `/api/v1/reports/metadata` | Metadados dinâmicos | ~18ms |
| POST | `/api/v1/reports/preview` | Preview com paginação | ~18ms |
| GET | `/api/v1/reports/export/csv` | Exportar CSV | ~16ms |
| GET | `/api/v1/reports/export/xlsx` | Exportar Excel | ~564ms |
| GET | `/api/v1/reports/export/pdf` | Exportar PDF | ~27ms |

### Exemplo de Resposta - Metadata

```json
{
  "manufacturers": [
    {
      "code": "GE",
      "name": "General Electric",
      "count": 8
    },
    {
      "code": "SE",
      "name": "Schneider Electric",
      "count": 42
    }
  ],
  "models": [
    {
      "code": "P220",
      "name": "P220",
      "manufacturer_code": "SE",
      "count": 20
    }
  ],
  "bays": [
    {
      "name": "52-MP-08B",
      "count": 1
    }
  ],
  "statuses": [
    {
      "code": "ACTIVE",
      "label": "Ativo",
      "count": 50
    }
  ]
}
```

---

## � Estrutura de Diretórios

```
protecai_testes/
├── api/                      # REST API (FastAPI)
│   ├── main.py              # Application principal
│   ├── core/                # Configurações
│   ├── models/              # SQLAlchemy models
│   ├── routers/             # Endpoints REST
│   ├── schemas/             # Pydantic schemas
│   └── services/            # Business logic
│
├── inputs/                   # Arquivos de entrada
│   ├── pdf/                 # PDFs de relés
│   ├── txt/                 # Arquivos texto
│   ├── xlsx/                # Planilhas Excel
│   └── csv/                 # CSVs externos
│
├── outputs/                  # Arquivos gerados
│   ├── csv/                 # CSVs convertidos
│   ├── norm_csv/            # CSVs normalizados
│   ├── excel/               # Excel exportados
│   ├── reports/             # Relatórios gerados
│   └── logs/                # Logs de processamento
│
├── scripts/                  # Scripts de processamento
│   ├── universal_robust_relay_processor.py
│   ├── test_sepam_voltage_fix.py
│   └── ...
│
├── src/                      # Core processing engines
│   ├── app.py               # Extração de PDFs
│   ├── universal_format_converter.py
│   ├── normalizador.py      # Normalização ANSI
│   └── pipeline_completo.py # Pipeline unificado
│
├── tests/                    # Testes automatizados
├── docker/                   # Docker configs
│   └── postgres/            # PostgreSQL setup
│
├── frontend/                 # Interface React
│   └── protecai-frontend/
│
├── requirements.txt          # Dependências Python
├── docker-compose.yml        # Orquestração Docker
└── README.md                 # Esta documentação
```

---

## �️ Banco de Dados

### Schema `protec_ai`

**Tabelas Principais:**

```sql
-- Fabricantes de relés
fabricantes (
    id SERIAL PRIMARY KEY,
    codigo_fabricante VARCHAR(50),
    nome_completo VARCHAR(200),
    pais_origem VARCHAR(100)
)

-- Modelos de relés
relay_models (
    id SERIAL PRIMARY KEY,
    model_code VARCHAR(100),
    manufacturer_id INTEGER REFERENCES fabricantes(id),
    model_name VARCHAR(200),
    voltage_class VARCHAR(50),
    technology VARCHAR(50)
)

-- Equipamentos instalados
relay_equipment (
    id SERIAL PRIMARY KEY,
    equipment_tag VARCHAR(100) UNIQUE,
    relay_model_id INTEGER REFERENCES relay_models(id),
    serial_number VARCHAR(100),
    bay_name VARCHAR(100),
    status VARCHAR(20),
    installation_date DATE
)

-- Barramentos (bays)
bays (
    id SERIAL PRIMARY KEY,
    bay_code VARCHAR(50) UNIQUE,
    voltage_level VARCHAR(20),
    bay_type VARCHAR(50)
)
```

### Consultas Úteis

```sql
-- Ver todos equipamentos
SELECT * FROM protec_ai.relay_equipment;

-- Equipamentos por fabricante
SELECT f.nome_completo, COUNT(*) as total
FROM protec_ai.relay_equipment re
JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
GROUP BY f.nome_completo;

-- Modelos mais utilizados
SELECT rm.model_name, COUNT(*) as total
FROM protec_ai.relay_equipment re
JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
GROUP BY rm.model_name
ORDER BY total DESC;
```

---

## �️ Desenvolvimento

### Executar Testes

```bash
# Todos os testes
pytest tests/

# Teste específico
pytest tests/test_ml_gateway_api_complete.py -v

# Com cobertura
pytest --cov=api tests/
```

### Formatação de Código

```bash
# Black (formatter)
black api/ src/ scripts/

# isort (imports)
isort api/ src/ scripts/

# flake8 (linting)
flake8 api/ src/ scripts/
```

### Debug

```bash
# Logs detalhados
tail -f outputs/logs/universal_relay_processing.log

# Verificar conexão PostgreSQL
docker exec -it postgres-protecai psql -U protecai -d protecai_db

# Ver containers
docker compose ps
docker compose logs postgres-protecai
```

---

## ✅ Padrões de Qualidade

### Princípios de Código

- **Docstrings**: Google Style em todas as funções públicas
- **Type Hints**: Python 3.12+ type annotations
- **Error Handling**: Try/except com logging detalhado
- **Logging**: Estruturado (timestamp, level, message)
- **Commits**: Conventional Commits (feat:, fix:, docs:, etc.)

### Dados Reais Validados

- **50 equipamentos** catalogados
- **2 fabricantes**: General Electric (8), Schneider Electric (42)
- **6 modelos** reais: P143, P241, P122, P220, P922, SEPAM S40
- **43 barramentos** (bays) distintos
- **Zero mock/fake data**: 100% dados reais da Petrobras

### Performance

- Metadata endpoint: ~18ms
- Export CSV: ~16ms
- Export XLSX: ~564ms
- Export PDF: ~27ms
- Processamento: 7,000+ dispositivos/segundo

---

## 📄 Licença

Projeto proprietário desenvolvido para Petrobras.  
**Uso restrito:** Engenharia de Proteção Elétrica.

---

## � Equipe

**Desenvolvimento:** ProtecAI Engineering Team  
**Cliente:** Petrobras - Engenharia de Proteção  
**Data:** Outubro/Novembro 2025  
**Versão:** 1.0.0

---

## 🆘 Suporte

Para questões técnicas ou reportar problemas:

1. Verifique logs em `outputs/logs/`
2. Consulte documentação da API: http://localhost:8000/docs
3. Revise STATUS.md para estado atual do projeto

---

**⚡ Sistema Crítico - Vidas Dependem da Precisão dos Dados ⚡**
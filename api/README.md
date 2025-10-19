# ProtecAI API 🔧

**Sistema Integrado de Proteção de Relés - API REST**

## 🎯 Visão Geral

A **ProtecAI API** é uma API REST robusta que revoluciona a engenharia de proteção através da integração de múltiplas tecnologias:

- 📊 **PostgreSQL**: Histórico e configurações reais
- 🎯 **ETAP Simulador**: Validação de seletividade (preparatória)
- 🤖 **ML Reinforcement Learning**: Otimização contínua (preparatória)
- 👷 **Interface Única**: Hub para engenheiros de proteção

## 🚀 Funcionalidades Principais

### ✅ **Implementadas (TODO #7)**
- **Equipments**: CRUD completo de equipamentos
- **Compare**: Comparação inteligente de configurações
- **Import**: Controle de importação de dados
- **Validation**: Validação de configurações

### 🚧 **Preparatórias (TODO #8 e #9)**
- **ETAP**: Interface com simulador
- **ML**: Otimização via aprendizado por reforço

## 📋 Endpoints Principais

### 🔧 Equipamentos
```
GET    /api/v1/equipments          # Listar equipamentos
GET    /api/v1/equipments/{id}     # Obter equipamento
POST   /api/v1/equipments          # Criar equipamento
PUT    /api/v1/equipments/{id}     # Atualizar equipamento
DELETE /api/v1/equipments/{id}     # Excluir equipamento
```

### 🔬 Comparação
```
POST   /api/v1/compare             # Comparar equipamentos
GET    /api/v1/compare/reports/{id} # Obter relatório
GET    /api/v1/compare/history/{id} # Histórico de comparações
POST   /api/v1/compare/batch       # Comparação em lote
```

### 📥 Importação
```
POST   /api/v1/import              # Importar dados
POST   /api/v1/import/upload       # Upload e importação
GET    /api/v1/import/status       # Status de importações
```

### ✅ Validação
```
POST   /api/v1/validation          # Validar configuração
GET    /api/v1/validation/rules    # Regras de validação
POST   /api/v1/validation/custom   # Validação customizada
```

### 🎯 ETAP (Preparatório)
```
POST   /api/v1/etap/simulate       # Simular seletividade
GET    /api/v1/etap/status/{id}    # Status da simulação
GET    /api/v1/etap/connection     # Verificar conexão
```

### 🤖 ML (Preparatório)
```
POST   /api/v1/ml/optimize         # Otimizar configuração
GET    /api/v1/ml/status/{id}      # Status da otimização
GET    /api/v1/ml/models           # Modelos disponíveis
POST   /api/v1/ml/feedback         # Fornecer feedback
```

## 🛠️ Instalação e Execução

### Pré-requisitos
- Python 3.11+
- PostgreSQL 16
- Docker (opcional)

### 1. Ambiente Virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r api/requirements.txt
```

### 2. Banco de Dados
```bash
# Iniciar PostgreSQL (Docker)
cd docker/postgres
docker-compose up -d

# Executar schema
psql -h localhost -U protecai -d protecai_db -f docs/SCHEMA_CONFIGURACOES_RELES_CORRETO.sql
```

### 3. Executar API
```bash
# Desenvolvimento
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Produção com Docker
docker-compose up --build
```

### 4. Acessar Documentação
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🐳 Docker

### Construir e Executar
```bash
# API + PostgreSQL + Adminer
cd api
docker-compose up --build

# Apenas API
docker build -t protecai-api .
docker run -p 8000:8000 protecai-api
```

### Serviços
- **API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Adminer**: http://localhost:8080

## 📊 Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI                              │
├─────────────────────────────────────────────────────────┤
│  Routers  │  Services  │  Schemas  │  Core             │
├─────────────────────────────────────────────────────────┤
│                 PostgreSQL                              │
│              (relay_configs schema)                     │
├─────────────────────────────────────────────────────────┤
│  ETAP Integration  │  ML Module  │  Validation Engine  │
│   (preparatório)   │ (preparatório) │   (implementado)   │
└─────────────────────────────────────────────────────────┘
```

## 🔗 Integração com Sistema Existente

A API integra perfeitamente com os componentes existentes:

- **relay_configuration_comparator.py**: Core de comparação
- **importar_configuracoes_reles.py**: Sistema de importação
- **file_registry_manager.py**: Controle de arquivos
- **Schema PostgreSQL**: Base de dados estruturada

## 📈 Casos de Uso

### 1. Comparação de Relés
```python
# POST /api/v1/compare
{
  "equipment_1_id": 3,
  "equipment_2_id": 4,
  "comparison_type": "full",
  "include_details": true
}
```

### 2. Importação de Dados
```python
# POST /api/v1/import
{
  "file_path": "inputs/pdf/new_relay_config.pdf",
  "file_type": "pdf",
  "force_reimport": false
}
```

### 3. Validação de Configuração
```python
# POST /api/v1/validation
{
  "equipment_ids": [3, 4],
  "validation_type": "full"
}
```

## 🔒 Segurança

- Validação de entrada com Pydantic
- Sanitização de queries SQL
- Rate limiting (planejado)
- Autenticação JWT (planejada)

## 📝 Logs

Logs estruturados em diferentes níveis:
- **INFO**: Operações normais
- **WARNING**: Situações de atenção
- **ERROR**: Erros de sistema
- **DEBUG**: Informações detalhadas

## 🧪 Testes

```bash
# Executar testes
pytest

# Com coverage
pytest --cov=api

# Testes específicos
pytest tests/test_comparison.py
```

## 🚀 Roadmap

### TODO #8 - ETAP Integration
- Conectores reais com ETAP
- Simulação de seletividade
- Análise de coordenação

### TODO #9 - ML Module  
- Algoritmos de Reinforcement Learning
- Otimização automática
- Aprendizado contínuo

### TODO #10 - Frontend
- Interface web React/Vue.js
- Dashboard interativo
- Relatórios visuais

## 📞 Contato

**ProtecAI Team**  
Email: protecai@petrobras.com.br  
Projeto: Revolução na Engenharia de Proteção

---

*API desenvolvida com ❤️ para transformar a engenharia de proteção industrial*
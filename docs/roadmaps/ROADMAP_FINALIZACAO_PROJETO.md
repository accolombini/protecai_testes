# 🗺️ ROADMAP DE FINALIZAÇÃO DO PROJETO - ProtecAI
## Data: 06 de Novembro de 2025

---

## 🎯 OBJETIVO FINAL

**Entregar sistema completo e funcional:**
- ✅ Pipeline de extração automática (50 relés → 500 relés)
- ✅ Banco de dados atualizado e validado
- ✅ Frontend integrado com upload e visualização
- ✅ Relatórios funcionais (PDF, Excel, CSV)
- ✅ Sistema pronto para produção

---

## 📋 FASES DO PROJETO (ORDEM DE EXECUÇÃO)

---

### 🔴 **FASE 1: AUDITORIA E ATUALIZAÇÃO DO BANCO DE DADOS**
**Status:** 🟡 EM ANDAMENTO  
**Prioridade:** CRÍTICA  
**Tempo estimado:** 1-2 horas  
**Responsável:** Próxima ação

#### **Tarefa 1.1: Auditar Banco vs Pipeline** ⏳
**Status:** PENDENTE  
**Arquivo:** `scripts/audit_database_vs_pipeline.py`  
**Descrição:** Comparar dados do banco com CSVs normalizados

**Ações:**
- [ ] Conectar ao PostgreSQL
- [ ] Contar parâmetros no banco (relay_settings)
- [ ] Contar parâmetros nos CSVs (outputs/norm_csv/)
- [ ] Comparar contagens por equipamento
- [ ] Identificar divergências
- [ ] Gerar relatório JSON em `outputs/reports/database_audit.json`

**Queries SQL:**
```sql
-- Total no banco
SELECT COUNT(*) FROM protec_ai.relay_settings;

-- Distribuição por equipamento
SELECT equipment_id, COUNT(*) as params 
FROM protec_ai.relay_settings 
GROUP BY equipment_id 
ORDER BY params DESC;

-- Última importação
SELECT MAX(created_at) FROM protec_ai.relay_settings;
```

**Output esperado:**
```json
{
  "database": {
    "total_params": 14314,
    "total_equipment": 50,
    "last_import": "2025-11-06T10:00:00"
  },
  "pipeline": {
    "total_params": XXXXX,
    "total_equipment": 50
  },
  "divergences": {
    "missing_params": XXXX,
    "extra_params": XXXX,
    "equipment_with_issues": [...]
  }
}
```

---

#### **Tarefa 1.2: Limpar Banco (se necessário)** ⏳
**Status:** PENDENTE (depende de 1.1)  
**Script:** SQL manual

**Ações:**
- [ ] Backup do banco atual
- [ ] DELETE FROM protec_ai.relay_settings;
- [ ] Verificar integridade (foreign keys)
- [ ] Confirmar limpeza

**SQL:**
```sql
-- Backup (dump antes de limpar)
pg_dump -U protecai -d protecai_db -t protec_ai.relay_settings > backup_relay_settings_20251106.sql

-- Limpar
DELETE FROM protec_ai.relay_settings;

-- Verificar
SELECT COUNT(*) FROM protec_ai.relay_settings; -- Deve retornar 0
```

---

#### **Tarefa 1.3: Re-importar Dados Normalizados** ⏳
**Status:** PENDENTE (depende de 1.2)  
**Arquivo:** `scripts/reimport_normalized_data.py`  
**Descrição:** Importar os 50 CSVs normalizados para o banco

**Ações:**
- [ ] Ler cada CSV de `outputs/norm_csv/`
- [ ] Mapear equipamento (via equipment_tag)
- [ ] Inserir em relay_settings
  - parameter_code → Code
  - parameter_name → Description
  - set_value → Value
  - unit_of_measure → unit
- [ ] Validar inserção (count)
- [ ] Gerar log de importação

**Estrutura CSV → Banco:**
```
CSV:                      BANCO:
Code         →           parameter_code
Description  →           parameter_name
Value        →           set_value
unit         →           unit_of_measure
```

**Output esperado:**
```
✅ 50/50 CSVs importados
✅ XXXXX parâmetros inseridos
✅ 0 erros
📄 Log: outputs/logs/reimport_20251106_HHMMSS.log
```

---

#### **Tarefa 1.4: Validar Importação** ⏳
**Status:** PENDENTE (depende de 1.3)  
**Script:** SQL de validação

**Ações:**
- [ ] Contar total de parâmetros
- [ ] Verificar distribuição por equipamento
- [ ] Validar campos obrigatórios preenchidos
- [ ] Comparar com expectativa (outputs/norm_csv/)

**SQL de validação:**
```sql
-- Total importado
SELECT COUNT(*) as total FROM protec_ai.relay_settings;

-- Por equipamento
SELECT 
  re.equipment_tag,
  COUNT(rs.id) as params
FROM protec_ai.relay_settings rs
JOIN protec_ai.relay_equipment re ON rs.equipment_id = re.id
GROUP BY re.equipment_tag
ORDER BY params DESC;

-- Campos vazios (não deveria ter)
SELECT COUNT(*) FROM protec_ai.relay_settings 
WHERE parameter_code IS NULL OR parameter_name IS NULL;
```

---

### 🔴 **FASE 2: CORRIGIR GERAÇÃO DE RELATÓRIOS**
**Status:** 🔴 NÃO INICIADO  
**Prioridade:** CRÍTICA  
**Tempo estimado:** 1-2 horas  
**Responsável:** Após conclusão Fase 1

#### **Tarefa 2.1: Testar Relatórios Atuais** ⏳
**Status:** PENDENTE  
**Descrição:** Validar endpoints de relatórios

**Ações:**
- [ ] Iniciar backend (`uvicorn api.main:app`)
- [ ] Testar GET `/api/v1/reports/metadata`
- [ ] Testar POST `/api/v1/reports/preview`
- [ ] Testar GET `/api/v1/reports/export/pdf?equipment_id=1`
- [ ] Testar GET `/api/v1/reports/export/xlsx?equipment_id=1`
- [ ] Testar GET `/api/v1/reports/export/csv?equipment_id=1`
- [ ] Documentar erros encontrados

**Comandos de teste:**
```bash
# Metadata
curl http://localhost:8000/api/v1/reports/metadata

# Preview
curl -X POST http://localhost:8000/api/v1/reports/preview \
  -H "Content-Type: application/json" \
  -d '{"equipment_ids": [1]}'

# Export PDF
curl http://localhost:8000/api/v1/reports/export/pdf?equipment_id=1 \
  --output test_report.pdf

# Export Excel
curl http://localhost:8000/api/v1/reports/export/xlsx?equipment_id=1 \
  --output test_report.xlsx

# Export CSV
curl http://localhost:8000/api/v1/reports/export/csv?equipment_id=1 \
  --output test_report.csv
```

**Erros esperados:**
```
❌ Dados vazios no relatório
❌ Formatação quebrada
❌ Erro 500 (query SQL inválida)
❌ Headers incorretos
```

---

#### **Tarefa 2.2: Corrigir Queries de Relatórios** ⏳
**Status:** PENDENTE (depende de 2.1)  
**Arquivo:** `api/services/report_service.py`  
**Descrição:** Corrigir queries SQL para incluir dados normalizados

**Ações:**
- [ ] Revisar query atual
- [ ] Adicionar colunas: parameter_code, unit_of_measure
- [ ] Testar query manualmente no PostgreSQL
- [ ] Atualizar service
- [ ] Re-testar endpoints

**Query corrigida (exemplo):**
```python
# ANTES (possivelmente incorreta)
query = """
SELECT parameter_name, set_value 
FROM protec_ai.relay_settings 
WHERE equipment_id = %s
"""

# DEPOIS (corrigida)
query = """
SELECT 
  parameter_code,
  parameter_name,
  set_value,
  unit_of_measure,
  category
FROM protec_ai.relay_settings 
WHERE equipment_id = %s
ORDER BY parameter_code
"""
```

---

#### **Tarefa 2.3: Corrigir Formatação de Relatórios** ⏳
**Status:** PENDENTE (depende de 2.2)  
**Arquivos:** 
- `api/services/report_service.py` (geração)
- `api/routers/reports.py` (endpoints)

**Ações:**
- [ ] **PDF:** Validar formatação (reportlab)
  - Headers com logo/título
  - Tabela de parâmetros
  - Footer com data/página
- [ ] **Excel:** Validar formatação (openpyxl)
  - Planilha com abas (por categoria?)
  - Headers em negrito
  - Auto-width de colunas
- [ ] **CSV:** Validar encoding (UTF-8)
  - Delimitador correto (;)
  - Quote fields

**Exemplo de melhoria PDF:**
```python
# Adicionar headers
pdf.setFont("Helvetica-Bold", 16)
pdf.drawString(100, 800, f"Relatório de Configuração - {equipment_tag}")

# Tabela de parâmetros
data = [["Código", "Descrição", "Valor", "Unidade"]]
for param in params:
    data.append([
        param.parameter_code,
        param.parameter_name,
        param.set_value,
        param.unit_of_measure
    ])
```

---

#### **Tarefa 2.4: Testar Relatórios Corrigidos** ⏳
**Status:** PENDENTE (depende de 2.3)

**Ações:**
- [ ] Re-executar testes de 2.1
- [ ] Validar conteúdo dos arquivos gerados
- [ ] Verificar formatação visual
- [ ] Confirmar dados corretos
- [ ] Testar com múltiplos equipamentos

**Critérios de sucesso:**
```
✅ PDF gerado com dados corretos
✅ Excel gerado com formatação adequada
✅ CSV gerado com encoding UTF-8
✅ Todos os campos preenchidos
✅ Dados batem com banco
```

---

### 🟡 **FASE 3: INTEGRAR FRONTEND COM PIPELINE**
**Status:** 🔴 NÃO INICIADO  
**Prioridade:** IMPORTANTE  
**Tempo estimado:** 2-3 horas  
**Responsável:** Após conclusão Fase 2

#### **Tarefa 3.1: Criar Upload de Relés no Frontend** ⏳
**Status:** PENDENTE  
**Arquivo:** `frontend/protecai-frontend/src/components/RelayUpload.tsx`  
**Descrição:** Componente React para upload de PDF/S40

**Ações:**
- [ ] Criar componente RelayUpload.tsx
- [ ] Input type="file" (aceitar .pdf, .S40, .s40)
- [ ] Botão "Processar Relé"
- [ ] Loading state durante processamento
- [ ] Exibir resultado (parâmetros extraídos)
- [ ] Mensagens de erro apropriadas

**Estrutura do componente:**
```typescript
interface RelayUploadProps {}

const RelayUpload: React.FC<RelayUploadProps> = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProcessResult | null>(null);

  const handleUpload = async () => {
    // POST /api/relays/process
  };

  return (
    <div>
      <input type="file" accept=".pdf,.S40,.s40" onChange={...} />
      <button onClick={handleUpload}>Processar Relé</button>
      {loading && <Spinner />}
      {result && <ResultTable data={result} />}
    </div>
  );
};
```

---

#### **Tarefa 3.2: Criar Endpoint de Processamento** ⏳
**Status:** PENDENTE  
**Arquivo:** `api/routers/relays.py`  
**Descrição:** Endpoint POST /api/relays/process

**Ações:**
- [ ] Criar rota POST /relays/process
- [ ] Receber arquivo (multipart/form-data)
- [ ] Salvar em inputs/pdf/ ou inputs/txt/
- [ ] Executar CompletePipelineProcessor
- [ ] Importar dados para banco
- [ ] Retornar resumo JSON

**Estrutura do endpoint:**
```python
@router.post("/process")
async def process_relay_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Processa arquivo de relé e importa para banco
    
    Returns:
        {
          "status": "success",
          "equipment_tag": "REL-P220-XXX",
          "params_extracted": 150,
          "params_imported": 150,
          "output_files": {
            "csv": "outputs/csv/XXX.csv",
            "excel": "outputs/excel/XXX.xlsx",
            "norm_csv": "outputs/norm_csv/XXX.csv",
            "norm_excel": "outputs/norm_excel/XXX.xlsx"
          }
        }
    """
    # 1. Salvar arquivo
    # 2. Processar pipeline
    # 3. Importar para banco
    # 4. Retornar resumo
```

---

#### **Tarefa 3.3: Criar Visualização de Dados Normalizados** ⏳
**Status:** PENDENTE  
**Arquivo:** `frontend/protecai-frontend/src/components/RelayNormalizedView.tsx`  
**Descrição:** Tabela com dados normalizados

**Ações:**
- [ ] Criar componente RelayNormalizedView.tsx
- [ ] Tabela com colunas: Code, Description, Value, Unit, Category
- [ ] Filtros por categoria
- [ ] Ordenação por código
- [ ] Paginação
- [ ] Botões de export (PDF/Excel/CSV)

**Estrutura:**
```typescript
interface NormalizedData {
  code: string;
  description: string;
  value: string;
  unit: string;
  category: string;
}

const RelayNormalizedView: React.FC<{equipmentId: number}> = ({equipmentId}) => {
  const [data, setData] = useState<NormalizedData[]>([]);
  const [filter, setFilter] = useState<string>("all");

  // Fetch data from /api/relays/{equipmentId}/settings

  return (
    <div>
      <FilterBar onChange={setFilter} />
      <Table data={filteredData} columns={columns} />
      <ExportButtons equipmentId={equipmentId} />
    </div>
  );
};
```

---

#### **Tarefa 3.4: Integrar com Menu Principal** ⏳
**Status:** PENDENTE  
**Descrição:** Adicionar links no menu

**Ações:**
- [ ] Adicionar menu "Upload de Relé"
- [ ] Adicionar menu "Visualizar Dados Normalizados"
- [ ] Atualizar rotas no React Router

---

### 🟢 **FASE 4: TESTES E VALIDAÇÃO FINAL**
**Status:** 🔴 NÃO INICIADO  
**Prioridade:** ESSENCIAL  
**Tempo estimado:** 1 hora  
**Responsável:** Após conclusão Fase 3

#### **Tarefa 4.1: Testes End-to-End** ⏳
**Status:** PENDENTE  
**Descrição:** Validar fluxo completo

**Ações:**
- [ ] **Teste 1:** Upload de novo relé via frontend
  - Escolher arquivo PDF
  - Clicar "Processar"
  - Aguardar processamento
  - Verificar resultado exibido
- [ ] **Teste 2:** Dados no banco
  - Query: SELECT * FROM relay_settings WHERE equipment_tag = 'XXX'
  - Confirmar dados corretos
- [ ] **Teste 3:** Relatórios
  - Gerar PDF do novo relé
  - Gerar Excel
  - Gerar CSV
  - Validar conteúdo
- [ ] **Teste 4:** Visualização
  - Abrir "Visualizar Dados Normalizados"
  - Filtrar por categoria
  - Exportar dados

**Critérios de sucesso:**
```
✅ Upload funciona sem erros
✅ Pipeline processa automaticamente
✅ Dados aparecem no banco
✅ Relatórios geram corretamente
✅ Frontend exibe dados corretos
```

---

#### **Tarefa 4.2: Testes de Regressão** ⏳
**Status:** PENDENTE  
**Descrição:** Garantir que não quebramos nada

**Ações:**
- [ ] Testar 50 equipamentos existentes
- [ ] Confirmar que frontend carrega dados
- [ ] Confirmar que relatórios antigos geram
- [ ] Confirmar que queries continuam funcionando

---

#### **Tarefa 4.3: Testes de Performance** ⏳
**Status:** PENDENTE (opcional)  
**Descrição:** Validar performance

**Ações:**
- [ ] Processar arquivo grande (SEPAM 1131 params)
- [ ] Medir tempo de processamento
- [ ] Medir tempo de importação
- [ ] Validar memória (não deve ultrapassar)

---

### 🟢 **FASE 5: DOCUMENTAÇÃO E ENTREGA**
**Status:** 🔴 NÃO INICIADO  
**Prioridade:** FINAL  
**Tempo estimado:** 30 minutos  
**Responsável:** Após conclusão Fase 4

#### **Tarefa 5.1: Criar README de Outputs** ⏳
**Status:** PENDENTE  
**Arquivo:** `outputs/README.md`

**Ações:**
- [ ] Documentar estrutura de cada output
- [ ] Explicar formato de cada arquivo
- [ ] Dar exemplos de uso

---

#### **Tarefa 5.2: Backup Completo** ⏳
**Status:** PENDENTE

**Ações:**
- [ ] Criar tar.gz de outputs/
- [ ] Backup do banco (pg_dump)
- [ ] Salvar em local seguro

---

#### **Tarefa 5.3: Atualizar STATUS.md** ⏳
**Status:** PENDENTE

**Ações:**
- [ ] Consolidar todos os STATUS*.md
- [ ] Atualizar com conquistas finais
- [ ] Documentar próximos passos (500 relés)

---

## 📊 MÉTRICAS DE SUCESSO

### **Banco de Dados:**
- [ ] Dados importados = Dados nos CSVs normalizados
- [ ] 50 equipamentos com parâmetros completos
- [ ] 0 erros de integridade

### **Relatórios:**
- [ ] PDF gerado com dados corretos
- [ ] Excel formatado adequadamente
- [ ] CSV com encoding UTF-8
- [ ] Tempo de geração < 5s

### **Frontend:**
- [ ] Upload de relés funcional
- [ ] Pipeline executada automaticamente
- [ ] Dados exibidos corretamente
- [ ] Export PDF/Excel/CSV funcional

### **Sistema Completo:**
- [ ] 100% dos testes passando
- [ ] 0 erros em produção
- [ ] Documentação completa
- [ ] Backup realizado

---

## ⚠️ RISCOS E MITIGAÇÕES

### **Risco 1: Banco muito grande após re-importação**
**Mitigação:** Validar contagem antes, fazer backup

### **Risco 2: Relatórios com performance ruim**
**Mitigação:** Adicionar paginação, índices no banco

### **Risco 3: Upload de arquivo muito grande**
**Mitigação:** Limitar tamanho (max 50MB), processar em background

---

## 🎯 PRÓXIMA AÇÃO IMEDIATA

**FASE 1 - Tarefa 1.1:** Criar e executar `scripts/audit_database_vs_pipeline.py`

**Comando:**
```bash
cd /Users/accol/Library/Mobile\ Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes
workon protecai_testes
python scripts/audit_database_vs_pipeline.py
```

**Resultado esperado:**
- Relatório JSON em `outputs/reports/database_audit.json`
- Identificação de divergências
- Decisão: Limpar e re-importar ou não

---

## 📅 TIMELINE ESTIMADO

| Fase | Tempo | Conclusão Esperada |
|------|-------|-------------------|
| Fase 1 | 1-2h | Hoje (06/11 - tarde) |
| Fase 2 | 1-2h | Hoje (06/11 - noite) ou Amanhã |
| Fase 3 | 2-3h | Amanhã (07/11) |
| Fase 4 | 1h | Amanhã (07/11) |
| Fase 5 | 30min | Amanhã (07/11) |

**Total:** 5.5 - 8.5 horas de trabalho

---

## ✅ CHECKLIST DE CONTROLE

### Fase 1: Banco de Dados
- [ ] 1.1 Auditoria executada
- [ ] 1.2 Banco limpo (se necessário)
- [ ] 1.3 Dados re-importados
- [ ] 1.4 Validação concluída

### Fase 2: Relatórios
- [ ] 2.1 Testes realizados
- [ ] 2.2 Queries corrigidas
- [ ] 2.3 Formatação corrigida
- [ ] 2.4 Re-testes aprovados

### Fase 3: Frontend
- [ ] 3.1 Upload criado
- [ ] 3.2 Endpoint criado
- [ ] 3.3 Visualização criada
- [ ] 3.4 Menu atualizado

### Fase 4: Validação
- [ ] 4.1 E2E testado
- [ ] 4.2 Regressão testada
- [ ] 4.3 Performance validada

### Fase 5: Entrega
- [ ] 5.1 README criado
- [ ] 5.2 Backup realizado
- [ ] 5.3 STATUS atualizado

---

**Última atualização:** 06/11/2025 - 15:00  
**Status geral:** FASE 1 EM ANDAMENTO  
**Próxima revisão:** Após conclusão de cada fase

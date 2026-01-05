# 🚨 CORREÇÃO URGENTE - Schema Incorreto no Backend

**Data**: 16 de novembro de 2025  
**Prioridade**: CRÍTICA  
**Status**: EM ANDAMENTO

---

## ❌ Problema Identificado

O trabalho de hoje (nomenclatura Bay→Barra) focou em **schema `relay_configs`**, mas o **schema de produção é `protec_ai`**!

### Evidências:
- ✅ Pipeline usa `protec_ai` (CORRETO)
- ✅ Importação PostgreSQL usa `protec_ai` (CORRETO)
- ❌ Backend/API usa `relay_configs` (ERRADO - 51 referências)
- ❌ Alterações de hoje foram em queries para `relay_configs` (ERRADO)
- ❌ Frontend conecta a endpoints que apontam para schema errado

---

## 📊 Estado Atual do Banco

```sql
-- Schema protec_ai (CORRETO - EM USO)
relay_equipment: 50 registros ✅ com barra_nome
relay_settings: 236.716 registros ✅
protection_functions: 31 registros ✅
relay_trip_configuration: 0 registros ❌ (vazio)
equipment_protection_functions: 0 registros ❌ (vazio)

-- Schema relay_configs (ERRADO - DESATUALIZADO)
Provavelmente contém dados antigos/obsoletos
```

---

## 🎯 Plano de Correção (5 Etapas)

### ETAPA 1: Correção Massiva do Backend ✅ URGENTE
**Arquivos afetados**: 51 referências em `api/`

**Ação**:
```bash
# Substituir relay_configs → protec_ai em todos os models
find api/ -name "*.py" -exec sed -i '' 's/relay_configs\./protec_ai./g' {} \;

# Arquivos críticos:
- api/models/equipment_models.py (10+ refs)
- api/models/etap_models.py (7+ refs)
- api/services/*.py (queries SQL)
- api/routers/*.py (endpoints)
```

**Validação**:
```bash
# Verificar que não sobrou nenhuma referência
grep -r "relay_configs\." api/ --include="*.py" | wc -l
# Esperado: 0
```

---

### ETAPA 2: Reverter Alterações de Hoje em relay_configs
**Problema**: Alteramos `relay_configs.equipments` mas os dados estão em `protec_ai.relay_equipment`

**Ação**:
1. Verificar se `protec_ai.relay_equipment` já tem `barra_nome` ✅ (TEM!)
2. Verificar se falta alguma coluna nova (subestacao_codigo, etc.)
3. Se faltar, adicionar em `protec_ai.relay_equipment`

**SQL de verificação**:
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_schema = 'protec_ai' AND table_name = 'relay_equipment'
ORDER BY column_name;
```

---

### ETAPA 3: Executar Script de Extração no Schema Correto
**Arquivo**: `scripts/extract_barra_petrobas.py`

**Problema**: Script roda mas não especifica schema

**Ação**:
1. Modificar script para usar `protec_ai.relay_equipment`
2. Re-executar extração
3. Validar que os 50 registros foram atualizados

**Comando**:
```bash
python scripts/extract_barra_petrobas.py
```

---

### ETAPA 4: Popular Tabelas de TRIP (NOVO)
**Tabelas vazias que precisam ser populadas**:

1. **`protec_ai.relay_trip_configuration`** (0 → ~150-300 registros esperados)
   - Extrair configurações de TRIP dos PDFs
   - Parser por modelo: P122, P143, P241, P220, P922, SEPAM
   
2. **`protec_ai.equipment_protection_functions`** (0 → ~150-200 registros esperados)
   - Relacionar equipamentos com funções de proteção ativas
   - Baseado em detecção de funções nos PDFs

**Scripts a criar/executar**:
- `scripts/extract_trip_all_models.py` (NOVO)
- `scripts/populate_equipment_functions.py` (NOVO)

---

### ETAPA 5: Atualizar Outputs CSV/Excel
**Diretórios afetados**:
- `outputs/csv/`
- `outputs/excel/`
- `outputs/norm_csv/`
- `outputs/norm_excel/`

**Problema**: Arquivos podem ter coluna "bay" em vez de "barra"

**Ação**:
1. Re-executar pipeline completo
2. Validar que CSVs têm coluna "barra_nome"
3. Validar que Excel tem coluna "Barra"

**Comando**:
```bash
python src/pipeline_completo.py --verbose
```

---

## 🔧 Comandos de Execução

### 1. Backup antes das mudanças
```bash
# Backup do código
git add -A
git commit -m "backup: antes correção schema"

# Backup do banco
docker exec postgres-protecai pg_dump -U protecai -d protecai_db -n protec_ai > backup_protec_ai_$(date +%Y%m%d).sql
```

### 2. Correção massiva backend
```bash
# Substituir relay_configs → protec_ai
find api/ -name "*.py" -type f -exec sed -i '' 's/relay_configs\./protec_ai./g' {} \;

# Verificar
grep -r "relay_configs\." api/ --include="*.py"
```

### 3. Verificar schema protec_ai
```bash
docker exec -it postgres-protecai psql -U protecai -d protecai_db -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'protec_ai' AND table_name = 'relay_equipment'
ORDER BY ordinal_position;"
```

### 4. Re-executar extração
```bash
python scripts/extract_barra_petrobas.py
```

### 5. Re-executar pipeline
```bash
python src/pipeline_completo.py --verbose
```

### 6. Testar relatórios
```bash
./tests/test_all_reports_comprehensive.sh
```

---

## ✅ Checklist de Validação

### Backend
- [ ] 0 referências a `relay_configs` em `api/`
- [ ] Todos os models usam `protec_ai`
- [ ] Todos os services usam `protec_ai`
- [ ] Todos os routers usam `protec_ai`
- [ ] Backend reiniciado sem erros

### Banco de Dados
- [ ] `protec_ai.relay_equipment` tem `barra_nome` (50/50)
- [ ] `protec_ai.relay_equipment` tem 5 colunas novas
- [ ] `protec_ai.relay_trip_configuration` populada (>0)
- [ ] `protec_ai.equipment_protection_functions` populada (>0)

### Outputs
- [ ] `outputs/csv/` tem coluna "barra_nome"
- [ ] `outputs/excel/` tem coluna "Barra"
- [ ] `outputs/norm_csv/` tem coluna "barra_nome"
- [ ] `outputs/norm_excel/` tem coluna "Barra"

### Relatórios
- [ ] 33/33 relatórios gerados com sucesso
- [ ] 11/11 PDFs sem "Bay" hardcoded
- [ ] PDFs mostram dados do schema `protec_ai`

### Frontend
- [ ] Dashboard mostra dados corretos
- [ ] Número de registros atualizado (se TRIP populado)
- [ ] Todas as telas funcionando

---

## 📝 Próximos Passos APÓS Correção

1. **Implementar extração de TRIP** (prioridade ALTA)
   - Criar parsers por modelo
   - Popular `relay_trip_configuration`
   - Popular `equipment_protection_functions`

2. **Normalização 3FN** (revisar)
   - Validar se todas as tabelas estão em 3FN
   - Documentar relacionamentos
   - Criar diagrama ER atualizado

3. **Testes de integração**
   - Teste end-to-end completo
   - Validação de todos os endpoints
   - Performance testing

4. **Documentação**
   - Atualizar documentação do schema
   - Atualizar guia de desenvolvimento
   - Criar diagrama de arquitetura

---

## ⚠️ Riscos

1. **Downtime**: Mudança de schema requer restart do backend
2. **Dados inconsistentes**: Se houver dados em `relay_configs`, podem ser perdidos
3. **Testes**: Podem falhar até correção completa
4. **Frontend**: Pode mostrar erros temporários

**Mitigação**: Fazer em horário de baixo uso, com backup completo

---

## 📞 Contato para Dúvidas

- Verificar: `RETOMADA_RAPIDA_2025-11-16.md`
- Verificar: `STATUS_SESSAO_2025-11-16_NOMENCLATURA_BARRA.md`
- Verificar: Lição de Casa (credenciais e estrutura)

---

**Criado por**: GitHub Copilot (Claude Sonnet 4.5)  
**Última atualização**: 16/11/2025 16:30

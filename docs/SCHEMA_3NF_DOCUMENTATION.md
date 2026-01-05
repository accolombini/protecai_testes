# Schema PostgreSQL 3FN - ProtecAI

## 📋 Visão Geral

Schema relacional normalizado (3FN) para armazenar configurações de relés de proteção extraídas de PDFs e arquivos SEPAM.

**Arquivo SQL**: `schema_3nf_protecai.sql`  
**Data de Criação**: 2025-11-10  
**Dados Processados**: 50 arquivos, 14,196 parâmetros ativos

---

## 🏗️ Estrutura das Tabelas

### 1. `relay_types` - Tipos de Relés
**Propósito**: Catálogo de tipos de relés suportados

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | Chave primária |
| `type_name` | VARCHAR(50) | Nome do tipo (SEPAM, EASERGY_P122, MICOM_P143, etc.) |
| `manufacturer` | VARCHAR(100) | Fabricante (Schneider Electric, GE) |
| `description` | TEXT | Descrição detalhada |

**Dados Iniciais**: 7 tipos (SEPAM, EASERGY_P122/P220/P922, MICOM_P143/P241, UNKNOWN)

---

### 2. `units` - Unidades de Medida
**Propósito**: Catálogo de unidades extraídas dos valores

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | Chave primária |
| `unit_symbol` | VARCHAR(20) | Símbolo (Hz, A, V, ms, °C, etc.) |
| `unit_name` | VARCHAR(100) | Nome completo (Hertz, Ampere, Volt) |
| `unit_category` | VARCHAR(50) | Categoria (frequency, current, voltage, time) |

**Dados Iniciais**: 12 unidades comuns (Hz, A, V, kV, ms, s, Ω, W, kW, °C, %, deg)

---

### 3. `equipments` - Equipamentos
**Propósito**: Equipamentos individuais com metadados completos

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | Chave primária |
| `relay_type_id` | INTEGER | FK para `relay_types` |
| `source_file` | VARCHAR(255) | Nome do arquivo de origem |
| `extraction_date` | TIMESTAMP | Data de extração |
| **Metadados PDF** | | |
| `code_0079` | TEXT | Description |
| `code_0081` | TEXT | Serial Number |
| `code_010a` | TEXT | Reference |
| `code_0005` | TEXT | Software Version |
| `code_0104` | TEXT | Additional metadata |
| **Metadados SEPAM** | | |
| `sepam_repere` | VARCHAR(100) | Equipment ID |
| `sepam_modele` | VARCHAR(100) | Model |
| `sepam_mes` | VARCHAR(100) | Measurement type |
| `sepam_gamme` | VARCHAR(100) | Product line |
| `sepam_typemat` | VARCHAR(100) | Material type |

**Constraint**: `UNIQUE(source_file, extraction_date)`

---

### 4. `parameters` - Catálogo de Parâmetros
**Propósito**: Códigos e descrições de parâmetros

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | Chave primária |
| `parameter_code` | VARCHAR(50) | Código do parâmetro (0150, frequence_reseau, etc.) |
| `parameter_description` | TEXT | Descrição legível |
| `is_metadata` | BOOLEAN | TRUE se for metadado (0079, 0081, SEPAM_*) |

**Constraint**: `UNIQUE(parameter_code)`

---

### 5. `parameter_values` - Valores dos Parâmetros
**Propósito**: Relação N:M entre equipamentos e parâmetros com valores

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | Chave primária |
| `equipment_id` | INTEGER | FK para `equipments` (CASCADE) |
| `parameter_id` | INTEGER | FK para `parameters` (CASCADE) |
| `unit_id` | INTEGER | FK para `units` (opcional) |
| `parameter_value` | TEXT | Valor atomizado |
| `value_type` | VARCHAR(20) | null, numeric, boolean, text |
| `is_active` | BOOLEAN | Parâmetro ativo no setup? |
| **Multipart** | | |
| `is_multipart` | BOOLEAN | Faz parte de grupo multipart? |
| `multipart_base` | VARCHAR(100) | Nome base (ex: "LED 5") |
| `multipart_part` | INTEGER | Número da parte (1, 2, 3, 4) |

**Constraint**: `UNIQUE(equipment_id, parameter_id, multipart_part)`

---

### 6. `multipart_groups` - Grupos Multipart
**Propósito**: Agrupar parâmetros multipart

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | Chave primária |
| `equipment_id` | INTEGER | FK para `equipments` (CASCADE) |
| `multipart_base` | VARCHAR(100) | Nome base do grupo |
| `total_parts` | INTEGER | Quantidade de partes |

**Constraint**: `UNIQUE(equipment_id, multipart_base)`

---

## 🔍 Views Úteis

### `v_active_parameters`
Parâmetros ativos com informações completas (JOIN de todas as tabelas)

**Colunas**:
- `equipment_id`, `source_file`, `relay_type`
- `sepam_repere`, `serial_number`
- `parameter_code`, `parameter_description`
- `parameter_value`, `unit_symbol`, `value_type`
- `is_multipart`, `multipart_base`, `multipart_part`

**Uso**:
```sql
-- Listar todos os parâmetros ativos de um equipamento
SELECT * FROM v_active_parameters 
WHERE source_file = 'P122 52-MF-02A_2021-03-08';

-- Parâmetros ativos por tipo de relé
SELECT relay_type, COUNT(*) 
FROM v_active_parameters 
GROUP BY relay_type;
```

---

### `v_multipart_groups`
Grupos multipart completos com arrays de valores

**Colunas**:
- `source_file`, `multipart_base`, `total_parts`
- `parts_found` (quantidade encontrada)
- `parts_array` (array de números de partes)
- `values_array` (array de valores)

**Uso**:
```sql
-- Ver todos os grupos LED de um equipamento
SELECT * FROM v_multipart_groups 
WHERE source_file LIKE '%P122%' 
AND multipart_base LIKE 'LED%';
```

---

### `v_relay_statistics`
Estatísticas agregadas por tipo de relé

**Colunas**:
- `relay_type`, `total_equipments`
- `unique_parameters`, `total_parameter_values`
- `active_parameters`, `multipart_parameters`
- `avg_active_percentage`

**Uso**:
```sql
-- Estatísticas gerais do banco
SELECT * FROM v_relay_statistics;

-- Tipo de relé com mais parâmetros ativos
SELECT relay_type, active_parameters 
FROM v_relay_statistics 
ORDER BY active_parameters DESC 
LIMIT 1;
```

---

### `v_equipment_metadata`
Metadados completos dos equipamentos

**Colunas**:
- `equipment_id`, `source_file`, `relay_type`
- Todos os metadados SEPAM (`sepam_*`)
- Todos os metadados PDF (`description`, `serial_number`, `reference`, etc.)
- `extraction_date`

**Uso**:
```sql
-- Listar todos os SEPAMs
SELECT * FROM v_equipment_metadata 
WHERE relay_type = 'SEPAM';

-- Buscar por número de série
SELECT * FROM v_equipment_metadata 
WHERE serial_number = 'NS08170043';
```

---

## 📊 Índices Criados

### Equipments
- `idx_equipments_relay_type` (relay_type_id)
- `idx_equipments_source_file` (source_file)
- `idx_equipments_sepam_repere` (sepam_repere)
- `idx_equipments_code_0081` (code_0081)

### Parameters
- `idx_parameters_code` (parameter_code)
- `idx_parameters_metadata` (is_metadata)

### Parameter Values
- `idx_parameter_values_equipment` (equipment_id)
- `idx_parameter_values_parameter` (parameter_id)
- `idx_parameter_values_is_active` (is_active)
- `idx_parameter_values_is_multipart` (is_multipart)
- `idx_parameter_values_multipart_base` (multipart_base)
- `idx_parameter_values_value_type` (value_type)

### Multipart Groups
- `idx_multipart_groups_equipment` (equipment_id)
- `idx_multipart_groups_base` (multipart_base)

---

## 🔄 Triggers Automáticos

### `update_updated_at_column()`
Atualiza automaticamente a coluna `updated_at` ao modificar registros

**Aplica-se a**:
- `relay_types`
- `equipments`
- `parameters`
- `parameter_values`

---

## 📦 Dados Iniciais (Seed Data)

### Relay Types Pré-cadastrados
- SEPAM (Schneider Electric)
- EASERGY_P122, P220, P922 (Schneider Electric)
- MICOM_P143, P241 (GE Grid Solutions)
- UNKNOWN (tipo não identificado)

### Units Pré-cadastradas
- **Frequência**: Hz
- **Corrente**: A
- **Tensão**: V, kV
- **Tempo**: ms, s
- **Resistência**: Ω
- **Potência**: W, kW
- **Temperatura**: °C
- **Outros**: %, deg

---

## 🎯 Normalização 3FN

### 1ª Forma Normal (1FN)
✅ Todos os atributos são atômicos
- Valores separados das unidades (tabela `units`)
- Multipart expandidos em linhas individuais
- Sem arrays ou valores compostos

### 2ª Forma Normal (2FN)
✅ Sem dependências parciais
- `parameters` separado de `parameter_values`
- `equipments` com metadados isolados
- Chaves compostas apenas onde necessário

### 3ª Forma Normal (3FN)
✅ Sem dependências transitivas
- `relay_types` não depende de `equipments`
- `units` independente de `parameter_values`
- Catálogos (`parameters`, `relay_types`, `units`) isolados

---

## 📈 Capacidade Esperada

Com base nos dados processados:

- **50 equipamentos** → Tabela `equipments`
- **~300 parâmetros únicos** → Tabela `parameters`
- **14,196 valores ativos** → Tabela `parameter_values`
- **~100 grupos multipart** → Tabela `multipart_groups`
- **12+ unidades** → Tabela `units`
- **7 tipos de relés** → Tabela `relay_types`

**Total estimado**: ~15,000 registros principais

---

## 🚀 Próximos Passos

1. **Criar banco de dados**:
   ```bash
   createdb protecai_db
   ```

2. **Executar schema**:
   ```bash
   psql -d protecai_db -f docs/schema_3nf_protecai.sql
   ```

3. **Verificar criação**:
   ```sql
   \dt  -- Listar tabelas
   \dv  -- Listar views
   SELECT * FROM relay_types;
   ```

4. **Importar dados** (PASSO 4):
   - Usar script Python para ler CSVs normalizados
   - Popular tabelas respeitando ordem de dependências
   - Validar integridade referencial

---

## 📝 Observações

- **DELETE CASCADE**: Ao remover um equipamento, seus parâmetros são removidos automaticamente
- **Timestamps**: Todas as tabelas principais têm `created_at` e `updated_at`
- **UUIDs**: Extensão habilitada para uso futuro
- **Performance**: Índices criados para consultas comuns (active params, multipart, metadata)

---

## 🔗 Relacionamentos

```
relay_types (1) ──────┐
                      │
                      ↓ (N)
                  equipments (1) ──────┐
                      ↑                │
                      │                │
                      │                ↓ (N)
                      │           parameter_values (N) ────→ units (1)
                      │                ↑
                      │                │ (N)
                      │                │
                      └────────→ multipart_groups (N)
                                       
parameters (1) ──────→ parameter_values (N)
```

**Relacionamentos**:
1. `equipments` N:1 `relay_types`
2. `parameter_values` N:1 `equipments` (CASCADE)
3. `parameter_values` N:1 `parameters` (CASCADE)
4. `parameter_values` N:1 `units`
5. `multipart_groups` N:1 `equipments` (CASCADE)

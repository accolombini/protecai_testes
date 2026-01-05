# Pipeline de Importação e População - Glossário de Relés

## 📋 Visão Geral

Este documento descreve o pipeline completo de extração, população e importação de dados de configuração de relés de proteção a partir do glossário MICON/SEPAM.

## 🔄 Fluxo do Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ 1. EXTRAÇÃO DO GLOSSÁRIO                                    │
│    scripts/extract_glossary.py                              │
│    └─> inputs/glossario/glossary_mapping.json/csv          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. GERAÇÃO DE SQL/CSV PARA POPULAÇÃO                        │
│    scripts/generate_db_population_from_glossary.py          │
│    └─> outputs/sql/populate_*.sql                          │
│    └─> outputs/csv/protection_functions.csv                │
│    └─> outputs/csv/relay_settings.csv                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. POPULAÇÃO DO BANCO DE DADOS                              │
│    scripts/populate_db_from_glossary.py                     │
│    └─> protec_ai.protection_functions (30 funções)         │
│    └─> protec_ai.relay_settings (369 parâmetros)           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. IMPORTAÇÃO DE DADOS ORIGINAIS (PIPELINE ESTENDIDO)       │
│    src/enhanced_import_pipeline.py                          │
│    └─> protec_ai.campos_originais                          │
│    └─> protec_ai.valores_originais                         │
│    └─> protec_ai.tokens_valores                            │
└─────────────────────────────────────────────────────────────┘
```

## 📂 Estrutura de Arquivos

```
protecai_testes/
├── inputs/glossario/
│   ├── Dados_Glossario_Micon_Sepam.xlsx       # Entrada: Glossário Excel
│   ├── glossary_mapping.json                  # Saída: Mapeamento JSON
│   └── glossary_mapping.csv                   # Saída: Mapeamento CSV
├── outputs/
│   ├── sql/
│   │   ├── populate_protection_functions.sql  # SQL: Funções de proteção
│   │   └── populate_relay_settings.sql        # SQL: Configurações
│   ├── csv/
│   │   ├── protection_functions.csv           # CSV: Funções
│   │   └── relay_settings.csv                 # CSV: Configurações
│   └── logs/
│       └── populate_db_audit.log              # Log de auditoria
├── scripts/
│   ├── extract_glossary.py                    # Passo 1: Extração
│   ├── generate_db_population_from_glossary.py # Passo 2: Geração SQL
│   └── populate_db_from_glossary.py           # Passo 3: População DB
└── src/
    └── enhanced_import_pipeline.py            # Passo 4: Pipeline estendido
```

## 🚀 Execução

### Passo 1: Extrair Glossário

```bash
python scripts/extract_glossary.py
```

**Saída:**
- `inputs/glossario/glossary_mapping.json` (404 registros)
- `inputs/glossario/glossary_mapping.csv` (404 linhas)

**Estatísticas:**
- MICON P122: 64 parâmetros
- MICON P220: 58 parâmetros  
- MICON P922: 96 parâmetros
- SEPAM S40: 176 parâmetros

### Passo 2: Gerar SQL/CSV para População

```bash
python scripts/generate_db_population_from_glossary.py
```

**Saída:**
- `outputs/sql/populate_protection_functions.sql` (30 funções)
- `outputs/sql/populate_relay_settings.sql` (369 parâmetros)
- `outputs/csv/protection_functions.csv`
- `outputs/csv/relay_settings.csv`

**Funções ANSI Mapeadas:**
- ANSI 50: Sobrecorrente (I>, I>>, I>>>)
- ANSI 50N: Terra (Ie>, Ie>>, Ie>>>)
- ANSI 46: Sequência negativa (I2>, I2>>)
- ANSI 37: Subcorrente (I<)
- ANSI 47: Tensão sequência negativa (V2>)
- ANSI 59/27: Proteção de tensão (V1<, U>, etc.)

### Passo 3: Popular Banco de Dados

**Pré-requisitos:**
- PostgreSQL rodando
- Database `protecai_db` criado
- Schema `protec_ai` existente
- Tabelas criadas (via `scripts/database_cleanup_and_structure.sql`)

**Configuração do Banco (editar se necessário):**
```python
# Em scripts/populate_db_from_glossary.py
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}
```

**Executar:**
```bash
python scripts/populate_db_from_glossary.py
```

**Verificação:**
```sql
-- Verificar funções inseridas
SELECT COUNT(*) FROM protec_ai.protection_functions;
-- Esperado: 30

-- Ver amostra
SELECT function_code, function_name, is_primary 
FROM protec_ai.protection_functions 
ORDER BY function_code 
LIMIT 10;
```

**Nota sobre `relay_settings`:**  
Por padrão, o script **não** popula `relay_settings` pois os registros têm `equipment_id` NULL (template). Para popular:
1. Descomente as linhas no script, ou
2. Execute o SQL manualmente após cadastrar equipamentos

### Passo 4: Pipeline Estendido (Integração)

O módulo `src/enhanced_import_pipeline.py` estende o pipeline existente para persistir dados originais.

**Uso em código existente:**

```python
from enhanced_import_pipeline import ImportPipelineExtension

# Configuração
DB_CONFIG = { ... }
pipeline_ext = ImportPipelineExtension(DB_CONFIG)
pipeline_ext.conectar()

# Após processar arquivo e inserir equipment:
for param in parsed_parameters:
    pipeline_ext.persist_parsed_parameter(
        equipment_id=equipment_id,
        param_name=param['name'],
        param_value=param['value'],
        param_code=param.get('code'),
        line_number=param.get('line', 0),
        unit=param.get('unit')
    )

# Para funções de proteção:
for func in protection_functions:
    pipeline_ext.persist_protection_function_params(
        equipment_id=equipment_id,
        function_name=func['name'],
        function_params=func['params']
    )

pipeline_ext.desconectar()
```

**Tabelas populadas:**
- `protec_ai.campos_originais` - Campos extraídos dos arquivos
- `protec_ai.valores_originais` - Valores brutos + parseados
- `protec_ai.tokens_valores` - Tokens individuais (números, unidades, keywords)

## 📊 Estrutura dos Dados

### `protection_functions`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | SERIAL | ID único |
| function_code | VARCHAR(10) | Código ANSI (50, 51, 67, etc.) |
| function_name | VARCHAR(200) | Nome da função |
| function_description | TEXT | Descrição detalhada |
| ansi_ieee_standard | VARCHAR(50) | Padrão ANSI |
| is_primary | BOOLEAN | Proteção primária? |
| is_backup | BOOLEAN | Proteção backup? |

**Exemplo:**
```sql
INSERT INTO protec_ai.protection_functions 
(function_code, function_name, function_description, ansi_ieee_standard, is_primary)
VALUES 
('50', 'Instantaneous Overcurrent', 'Protection function I>', 'ANSI 50', true);
```

### `relay_settings`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | SERIAL | ID único |
| equipment_id | INTEGER | FK para relay_equipment (NULL em template) |
| function_id | INTEGER | FK para protection_functions |
| parameter_name | VARCHAR(100) | Nome do parâmetro |
| parameter_code | VARCHAR(50) | Código do parâmetro (ex: 0201) |
| set_value | DECIMAL(15,6) | Valor numérico |
| set_value_text | VARCHAR(200) | Valor texto |
| unit_of_measure | VARCHAR(20) | Unidade (A, V, s, Hz, etc.) |
| setting_group | VARCHAR(20) | Grupo de settings (GROUP_1, etc.) |
| is_enabled | BOOLEAN | Parâmetro ativo? |

**Exemplo:**
```sql
INSERT INTO protec_ai.relay_settings 
(equipment_id, parameter_name, parameter_code, set_value, set_value_text, unit_of_measure)
VALUES 
(NULL, 'I>', '0201', 0.63, '0.63In', 'In');
```

### `campos_originais` / `valores_originais` / `tokens_valores`

Estrutura normalizada 3NF para rastreabilidade completa dos dados originais extraídos.

## 🔍 Queries Úteis

### Listar todas as funções de proteção
```sql
SELECT 
    function_code,
    function_name,
    CASE WHEN is_primary THEN '⭐ PRIMARY' ELSE '  BACKUP' END as type
FROM protec_ai.protection_functions
ORDER BY function_code;
```

### Parâmetros por categoria
```sql
SELECT 
    category,
    COUNT(*) as total,
    STRING_AGG(DISTINCT parameter_name, ', ' ORDER BY parameter_name) as params
FROM (
    SELECT 
        CASE 
            WHEN parameter_name LIKE '%CT%' THEN 'INSTRUMENTATION'
            WHEN parameter_name LIKE 'I>%' OR parameter_name LIKE 'Ie>%' THEN 'OVERCURRENT'
            WHEN parameter_name LIKE '%Delay%' OR parameter_name LIKE 't%' THEN 'TIMING'
            ELSE 'OTHER'
        END as category,
        parameter_name
    FROM protec_ai.relay_settings
) categorized
GROUP BY category
ORDER BY total DESC;
```

### Ver dados originais de um equipamento
```sql
SELECT 
    co.nome_campo,
    vo.valor_texto,
    vo.valor_numerico,
    vo.unidade,
    STRING_AGG(tv.token, ' | ') as tokens
FROM protec_ai.campos_originais co
JOIN protec_ai.valores_originais vo ON vo.campo_id = co.id
LEFT JOIN protec_ai.tokens_valores tv ON tv.valor_id = vo.id
WHERE co.equipment_id = 1
GROUP BY co.id, co.nome_campo, vo.valor_texto, vo.valor_numerico, vo.unidade
ORDER BY co.linha_arquivo;
```

## ⚠️ Notas Importantes

1. **Dados Template**: O SQL de `relay_settings` insere registros com `equipment_id = NULL`. Vincule a equipamentos reais após cadastro.

2. **Transações**: Os scripts usam transações. Se falhar, é feito rollback automático.

3. **Idempotência**: Re-executar scripts pode causar duplicatas. Use `DELETE` ou `TRUNCATE` antes se necessário:
   ```sql
   TRUNCATE protec_ai.protection_functions CASCADE;
   ```

4. **Performance**: Para grandes volumes, use `COPY` em vez de `INSERT` individual:
   ```bash
   psql -U protecai -d protecai_db -c "\COPY protec_ai.protection_functions FROM 'outputs/csv/protection_functions.csv' CSV HEADER"
   ```

## 📝 Logs e Auditoria

Todos os scripts geram logs em `outputs/logs/`:
- `populate_db_audit.log` - Log completo de população
- Timestamps, estatísticas antes/depois, erros

## 🧪 Testes

Para validar a população:

```bash
# Contar registros
psql -U protecai -d protecai_db -c "
    SELECT 'protection_functions' as table, COUNT(*) FROM protec_ai.protection_functions
    UNION ALL
    SELECT 'relay_settings', COUNT(*) FROM protec_ai.relay_settings;
"

# Verificar integridade
python -m pytest tests/test_db_population.py -v
```

## 📚 Referências

- **Glossário Original**: `inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx`
- **Schema DB**: `scripts/database_cleanup_and_structure.sql`
- **Pipeline Processamento**: `src/enhanced_multi_format_processor.py`
- **Importação Configs**: `src/importar_configuracoes_reles.py`

---

**Autor:** ProtecAI Engineering Team  
**Data:** 2025-11-03  
**Versão:** 1.0.0

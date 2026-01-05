# 📋 PLANO DE CORREÇÃO - BARRA + TRIP
**Data:** 16 de novembro de 2025 (Domingo)  
**Status:** Pausa para almoço - Retomar às 14h  
**Projeto:** ProtecAI - Sistema de Proteção Elétrica Petrobras

---

## ✅ CONTEXTO E DECISÕES APROVADAS

### **1. Nomenclatura ABNT/Petrobras**
- ✅ **"Bay" → "Barra"** em TODO o sistema (código, banco, interface)
- ✅ **Renomear colunas do banco** (não manter inglês)
- ✅ **Adicionar novos campos** necessários ao schema

### **2. Extração de Barra (Nomenclatura Petrobras Validada)**

**Padrão Confirmado:**
```
P122_204-PN-06_LADO_A_2014-08-01
│    │   │  │   │      └─ Data parametrização
│    │   │  │   └─ Lado da barra (A/B, PATIO, REATOR)
│    │   │  └─ Alimentador (06, 2C, 02AC)
│    │   └─ BARRA (PN, MF, MP, MK) ← ESTE É O CAMPO PRINCIPAL
│    └─ Subestação (204, 52, 223)
└─ Modelo (P122, P143, P220, P241, P922)
```

**Regex Validado:**
```regex
-([A-Z]{2,3})-  → Extrai BARRA
```

**Exemplos Validados:**
- `P122_204-PN-06_LADO_A_2014-08-01` → Barra: **PN**
- `P143_204-MF-2C_2018-06-13` → Barra: **MF**
- `P922 52-MF-02AC` → Barra: **MF**

### **3. TRIP/Disparo**
- ✅ **Todos os 50 relés** + futuros precisam
- ✅ **Termo brasileiro:** TRIP ou Disparo
- ✅ **Dados nos arquivos:** inputs/pdf + inputs/txt (S40)
- ✅ **6 modelos mapeados:** P122, P143, P220, P241, P922, SEPAM

### **4. Estratégia Aprovada**
1. Criar estrutura de tabelas (hoje - 15 min)
2. Corrigir Barra/Bay + Relatórios (pós-almoço - 3h)
3. Extração TRIP (próxima sessão - 1-2 dias)

---

## 📊 MODELOS DE RELÉ MAPEADOS

| Modelo | Aplicação | TRIP Pattern | Funções Únicas |
|--------|-----------|--------------|----------------|
| **P122** | Sobrecorrente/Terra | 0180: Trip Commands (checkbox) | tI>, tIe>, tI>>, Thermal Teta |
| **P143** | Feeder Management | 0C.XX: Digital Inputs | V<2 Trip, Relay Labels |
| **P220** | Generator Protection | 01D0/01D1: Trip RLY Settings | THERM OVERLOAD, EXCES LONG START, LOCKED ROTOR |
| **P241** | Line Differential | 30.06: Thermal Trip + 0C.XX | Thermal constants (T1, T2, Tr) |
| **P922** | Voltage/Frequency | 01D0/01D1: Trip Part 1/2 + Latch | tU<, tVo>, tf1-6 |
| **SEPAM** | Multi-function (S40) | commande_disjoncteur (INI) | [ProtectionXXX] sections |

---

## 🎯 TODAS AS CORREÇÕES NECESSÁRIAS

### **FASE 1: BANCO DE DADOS (40 min)**

#### **1.1 Renomear Colunas**
```sql
-- Renomear bay_name → barra_nome
ALTER TABLE protec_ai.relay_equipment 
  RENAME COLUMN bay_name TO barra_nome;

-- Renomear tabela bays → barras
ALTER TABLE protec_ai.bays RENAME TO barras;

-- Atualizar comentários
COMMENT ON COLUMN protec_ai.relay_equipment.barra_nome IS 
  'Barra/Painel onde o relé está instalado (ex: PN, MF, MP, MK)';
```

#### **1.2 Adicionar Novos Campos**
```sql
ALTER TABLE protec_ai.relay_equipment 
  ADD COLUMN IF NOT EXISTS subestacao_codigo VARCHAR(10),
  ADD COLUMN IF NOT EXISTS alimentador_numero VARCHAR(10),
  ADD COLUMN IF NOT EXISTS lado_barra VARCHAR(20),
  ADD COLUMN IF NOT EXISTS data_parametrizacao DATE,
  ADD COLUMN IF NOT EXISTS codigo_ansi_equipamento VARCHAR(10);

COMMENT ON COLUMN protec_ai.relay_equipment.subestacao_codigo IS 
  'Código da subestação (204, 52, 223)';
COMMENT ON COLUMN protec_ai.relay_equipment.alimentador_numero IS 
  'Número do alimentador/bay (06, 2C, 02AC)';
COMMENT ON COLUMN protec_ai.relay_equipment.lado_barra IS 
  'Lado da barra dupla (LADO_A, LADO_B, L_PATIO, L_REATOR)';
COMMENT ON COLUMN protec_ai.relay_equipment.codigo_ansi_equipamento IS 
  'Código ANSI do equipamento (52=disjuntor)';
```

#### **1.3 Criar Tabela de TRIP**
```sql
CREATE TABLE protec_ai.relay_trip_configuration (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES protec_ai.relay_equipment(id) ON DELETE CASCADE,
    
    -- Identificação
    trip_type VARCHAR(50) NOT NULL,
    trip_group VARCHAR(20),
    
    -- Função
    function_code VARCHAR(50) NOT NULL,
    function_description TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Configuração
    parameter_code VARCHAR(50) NOT NULL,
    output_relays JSONB,
    
    -- Latch
    has_latch BOOLEAN DEFAULT FALSE,
    latch_parameter_code VARCHAR(50),
    
    -- Térmico
    thermal_ith_current DECIMAL(10,2),
    thermal_k_coefficient INTEGER,
    thermal_const_t1 DECIMAL(10,2),
    thermal_const_t2 DECIMAL(10,2),
    cooling_const_tr DECIMAL(10,2),
    
    -- Metadados
    relay_model VARCHAR(20) NOT NULL,
    extraction_method VARCHAR(50),
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trip_equipment ON protec_ai.relay_trip_configuration(equipment_id);
CREATE INDEX idx_trip_type ON protec_ai.relay_trip_configuration(trip_type);
CREATE INDEX idx_trip_enabled ON protec_ai.relay_trip_configuration(is_enabled) 
  WHERE is_enabled = TRUE;
CREATE INDEX idx_trip_model ON protec_ai.relay_trip_configuration(relay_model);

COMMENT ON TABLE protec_ai.relay_trip_configuration IS 
  'Configurações de TRIP/Disparo dos relés (todos os modelos: P122, P143, P220, P241, P922, SEPAM)';
```

---

### **FASE 2: PIPELINE DE DADOS (1h 30min)**

#### **2.1 Script de Extração**
**Arquivo:** `scripts/extract_barra_petrobras.py`

**Função Principal:**
```python
def extrair_dados_equipment_tag(equipment_tag: str) -> dict:
    """
    Extrai dados do equipment_tag seguindo nomenclatura Petrobras.
    
    Returns:
        dict com: modelo, subestacao, barra, alimentador, lado, data, codigo_ansi
    """
    # Padrão A: P122_204-PN-06_LADO_A_2014-08-01
    # Padrão B: P922 52-MF-02AC (com espaço + ANSI)
```

#### **2.2 Popular Dados**
```python
# Para cada equipment_tag:
# 1. Extrair campos
# 2. UPDATE protec_ai.relay_equipment SET 
#      barra_nome = 'PN',
#      subestacao_codigo = '204',
#      alimentador_numero = '06',
#      lado_barra = 'LADO_A',
#      data_parametrizacao = '2014-08-01'
```

---

### **FASE 3: BACKEND (1h)**

#### **3.1 Traduzir Strings (report_service.py)**
```python
# Buscar e substituir em strings de usuário:
"Bay" → "Barra"
"bay" → "barra"
"Barramento" → "Barra"
"Circuit Breaker Bay" → "Barra do Disjuntor"

# Manter nomes técnicos em inglês (variáveis):
bay_name → OK
get_bay_data() → OK
```

#### **3.2 Atualizar Queries SQL**
```python
# api/services/report_service.py - linha ~539
base_query = """
    SELECT 
        re.id,
        re.equipment_tag,
        re.barra_nome,          -- RENOMEADO
        re.subestacao_codigo,   -- NOVO
        re.alimentador_numero,  -- NOVO
        ...
    FROM protec_ai.relay_equipment re
    ...
"""
```

#### **3.3 Schemas Pydantic (schemas/reports.py)**
```python
class EquipmentSchema(BaseModel):
    barra_nome: Optional[str] = Field(None, description="Barra (PN, MF, MP)")
    subestacao_codigo: Optional[str] = Field(None, description="Subestação")
```

---

### **FASE 4: FRONTEND (30min)**

#### **4.1 Traduzir Interface (Reports.tsx)**
```typescript
// Linha 586: Cabeçalho da tabela
<th>Barra</th>  // era "Bay"

// Linha 798: Dropdown de filtro
<label>Barra</label>  // era "Barramento"

// metadata.bays → metadata.barras
{metadata.barras.map(b => ...)}
```

#### **4.2 Tipos TypeScript**
```typescript
interface Equipment {
  barra_nome: string;        // RENOMEADO
  subestacao_codigo: string; // NOVO
}
```

---

### **FASE 5: RELATÓRIOS (30min)**

#### **5.1 Colunas PDF/XLSX/CSV**
```python
# Headers dos relatórios:
headers = ['Tag', 'Modelo', 'Código', 'Fabricante', 'Barra', 'Status']
#                                                     ^^^^^^
# Trocar de "Bay" para "Barra"
```

#### **5.2 Verificar _header_footer()**
```python
# api/services/report_service.py - linhas 787-865
# JÁ IMPLEMENTADO com PETROBRAS
# Apenas verificar se não há menção a "Bay" nas strings
```

---

### **FASE 6: EXTRAÇÃO TRIP (Próxima Sessão - 1-2 dias)**

#### **6.1 Parsers por Modelo**
- `scripts/extract_trip_p122.py` - Checkbox Trip Commands
- `scripts/extract_trip_p143.py` - Digital Inputs
- `scripts/extract_trip_p220.py` - THERM OVERLOAD, LOCKED ROTOR
- `scripts/extract_trip_p241.py` - Thermal constants
- `scripts/extract_trip_p922.py` - Voltage/Frequency
- `scripts/extract_trip_sepam.py` - S40 INI format

#### **6.2 Popular Tabela**
```python
# INSERT INTO relay_trip_configuration (
#   equipment_id, trip_type, function_code, is_enabled, ...
# ) VALUES ...
```

---

## 📊 CHECKLIST DE EXECUÇÃO

| # | Tarefa | Arquivo | Tempo | Status |
|---|--------|---------|-------|--------|
| **PRÉ-ALMOÇO (15 min)** |
| 1 | Criar este documento | PLANO_CORRECAO_BARRA_TRIP_2025-11-16.md | 5min | ✅ |
| 2 | Criar tabelas SQL | migration_barra_trip.sql | 10min | ⏳ |
| **PÓS-ALMOÇO (3h)** |
| 3 | Script extração Barra | extract_barra_petrobras.py | 1h | ⏳ |
| 4 | Popular barra_nome | Script + UPDATE | 30min | ⏳ |
| 5 | Traduzir Backend | report_service.py, reports.py | 1h | ⏳ |
| 6 | Traduzir Frontend | Reports.tsx | 30min | ⏳ |
| 7 | Atualizar Relatórios | Headers PDF/XLSX/CSV | 20min | ⏳ |
| 8 | Testar Completo | Gerar todos relatórios | 30min | ⏳ |
| **PRÓXIMA SESSÃO** |
| 9 | Extração TRIP | 6 parsers + pipeline | 1-2 dias | ⏳ |

---

## 🚀 PRÓXIMOS PASSOS (Pós-Almoço)

1. **Executar migration SQL** (criar tabelas)
2. **Criar script de extração** de Barra
3. **Popular banco** com dados corretos
4. **Traduzir código** Backend + Frontend
5. **Testar relatórios** (verificar se Barra aparece corretamente)
6. **Validar com usuário** antes de avançar para TRIP

---

## 📝 NOTAS IMPORTANTES

### **Problema Original Descoberto:**
- ❌ `bay_name` no banco está **VAZIO** (0 de 50 registros)
- ✅ Relatório PDF mostra valores porque **extrai do equipment_tag**
- 🚨 **GRAVE:** Dados estavam sendo "inventados" em tempo real

### **Solução:**
1. Extrair corretamente do `equipment_tag`
2. Popular `barra_nome` no banco
3. Garantir que código use dados reais (não parsing runtime)

### **Validação:**
```sql
-- Antes: 0 registros com barra_nome
SELECT COUNT(*) FROM protec_ai.relay_equipment WHERE barra_nome IS NOT NULL;
-- Resultado: 0

-- Depois: 50 registros com barra_nome
-- Esperado: 50
```

---

## 🎯 ENTREGAS DO DIA

**Até 18h (final do domingo):**
- ✅ Tabelas criadas (TRIP + campos novos)
- ✅ Barra extraída e populada (50 equipamentos)
- ✅ Código traduzido (Bay → Barra)
- ✅ Relatórios funcionando com dados corretos

**Segunda-feira (sessão dedicada):**
- ⏳ Extração completa de TRIP (6 modelos)
- ⏳ Popular `relay_trip_configuration`
- ⏳ Relatório de TRIP/Disparo

---

**FIM DO DOCUMENTO - Bom almoço! 🍽️**  
**Retomar: ~14h | Duração estimada: 3h**

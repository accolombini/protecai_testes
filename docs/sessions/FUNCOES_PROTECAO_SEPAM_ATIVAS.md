# Funções de Proteção Ativas - SEPAM S40

**Data:** 13 de novembro de 2025  
**Fonte:** Arquivos `.S40` em `inputs/txt/`

## Resumo Executivo

- **Total de relés SEPAM analisados:** 3
- **Funções de proteção únicas encontradas:** 4
- **Status:** Baseado no campo `activite_X=1` nas seções `[ProtectionXXX]`

---

## Detalhamento por Equipamento

### 00-MF-12 (2016-03-31)

**Total de seções Protection:** 9  
**Funções ATIVAS:** 4

| Função ANSI | Seção no .S40 | Grupos Ativos | Descrição |
|-------------|---------------|---------------|-----------|
| **59N** | Protection59N | 0 | Sobretensão de Neutro |
| **27/27S** | Protection2727S | 0, 1 | Subtensão |
| **50/51N** | Protection50_51N | 0, 1, 2, 3 | Sobrecorrente de Terra (Inst + Temp) |
| **50/51** | Protection50_51 | 0, 1, 2, 3 | Sobrecorrente de Fase (Inst + Temp) |

---

### 00-MF-14 (2016-03-31)

**Total de seções Protection:** 9  
**Funções ATIVAS:** 3

| Função ANSI | Seção no .S40 | Grupos Ativos | Descrição |
|-------------|---------------|---------------|-----------|
| **59N** | Protection59N | 0 | Sobretensão de Neutro |
| **50/51N** | Protection50_51N | 0, 1, 2, 3 | Sobrecorrente de Terra (Inst + Temp) |
| **50/51** | Protection50_51 | 0, 1, 2, 3 | Sobrecorrente de Fase (Inst + Temp) |

---

### 00-MF-24 (2024-09-10)

**Total de seções Protection:** 9  
**Funções ATIVAS:** 3

| Função ANSI | Seção no .S40 | Grupos Ativos | Descrição |
|-------------|---------------|---------------|-----------|
| **59N** | Protection59N | 0 | Sobretensão de Neutro |
| **50/51N** | Protection50_51N | 0, 1, 2, 3 | Sobrecorrente de Terra (Inst + Temp) |
| **50/51** | Protection50_51 | 0, 1, 2, 3 | Sobrecorrente de Fase (Inst + Temp) |

---

## Funções ANSI Consolidadas

### Funções Encontradas

1. **50/51** - Sobrecorrente de Fase (Instantânea + Temporizada)
   - Presente em: 00-MF-12, 00-MF-14, 00-MF-24
   - Grupos configurados: 0, 1, 2, 3 (4 ajustes diferentes)

2. **50/51N** - Sobrecorrente de Terra (Instantânea + Temporizada)
   - Presente em: 00-MF-12, 00-MF-14, 00-MF-24
   - Grupos configurados: 0, 1, 2, 3 (4 ajustes diferentes)

3. **59N** - Sobretensão de Neutro
   - Presente em: 00-MF-12, 00-MF-14, 00-MF-24
   - Grupos configurados: 0 (1 ajuste)

4. **27/27S** - Subtensão
   - Presente em: 00-MF-12
   - Grupos configurados: 0, 1 (2 ajustes)

---

## Observações Técnicas

### Estrutura dos Arquivos SEPAM .S40

Os arquivos SEPAM seguem o formato INI com seções `[ProtectionXXX]`. Cada função de proteção pode ter múltiplos grupos de ajustes (0, 1, 2, 3, etc.), identificados pelo sufixo `_X` nos parâmetros.

**Exemplo:**
```ini
[Protection50_51N]
activite_3=1              ← Grupo 3 ATIVO
courant_seuil_3_1=200    ← Parâmetro do grupo 3
activite_2=1              ← Grupo 2 ATIVO
courant_seuil_2_1=3000   ← Parâmetro do grupo 2
activite_1=0              ← Grupo 1 INATIVO
activite_0=0              ← Grupo 0 INATIVO
```

### Critério de Ativação

Uma função de proteção é considerada **ATIVA** quando possui **pelo menos um grupo com `activite_X=1`**.

### Próximos Passos

1. ✅ **CONCLUÍDO:** Corrigir `detect_active_setup_sepam()` para ler campos `activite_X`
2. ✅ **CONCLUÍDO:** Criar script `list_sepam_active_functions.py` 
3. ⏳ **PENDENTE:** Re-processar todos os 50 arquivos com lógica corrigida
4. ⏳ **PENDENTE:** Re-importar dados para o banco PostgreSQL
5. ⏳ **PENDENTE:** Validar estatísticas no dashboard

---

**Gerado por:** `scripts/list_sepam_active_functions.py`  
**Comando:** `python scripts/list_sepam_active_functions.py`

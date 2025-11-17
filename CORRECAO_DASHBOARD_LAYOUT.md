# 🎯 CORREÇÃO URGENTE - Dashboard Layout

**Data:** 16/11/2025  
**Prioridade:** CRÍTICA  
**Arquivo:** `frontend/protecai-frontend/src/components/MainDashboard.tsx`

---

## 🚨 PROBLEMAS IDENTIFICADOS:

### 1. **Card "Registros DB" está errado**
- **Atual:** 470 registros (ERRADO)
- **Deveria:** 236,716 settings do protec_ai
- **Linha ~394-402**

```tsx
// ❌ ATUAL (ERRADO):
<p className="text-orange-200 text-sm font-medium">Registros DB</p>
<p className="text-3xl font-bold text-white">{systemStats.postgresRecords}</p>
<p className="text-orange-200 text-sm mt-2">PostgreSQL 16 - Dados Reais</p>

// ✅ CORRIGIR PARA:
<p className="text-orange-200 text-sm font-medium">Settings (protec_ai)</p>
<p className="text-3xl font-bold text-white">{technicalData.totalSettings.toLocaleString()}</p>
<p className="text-orange-200 text-sm mt-2">relay_settings • Schema PIPELINE</p>
```

---

### 2. **Schema PIPELINE mostra 0 dados**
- **Linha ~408-430:** technicalData está com valores zerados
- **Causa:** API não está sendo chamada corretamente

```tsx
// VERIFICAR linha ~190-195:
setTechnicalData({
  totalEquipments: data.summary?.total_equipments || 0,  // ← Pode estar retornando undefined
  totalSettings: data.summary?.total_settings || 0,
  activeSettings: data.summary?.active_settings || 0,
  protectionFunctions: 158,
  activeFunctions: data.summary?.active_functions_count || 23
});
```

**SOLUÇÃO:**
1. Verificar se endpoint `/api/v1/imports/statistics` retorna `summary` correto
2. Adicionar console.log para debug:

```tsx
console.log('📊 Summary data:', data.summary);
console.log('📊 TechnicalData atualizado:', {
  totalEquipments: data.summary?.total_equipments,
  totalSettings: data.summary?.total_settings
});
```

---

### 3. **Layout confuso - não deixa claro separação dos 3 schemas**

#### **PROPOSTA NOVA ESTRUTURA:**

```tsx
{/* 🔵 SCHEMA PRINCIPAL - PIPELINE (protec_ai) */}
<div className="bg-linear-to-r from-blue-900 to-blue-800 rounded-lg p-6 border-2 border-blue-500 shadow-lg">
  <div className="flex items-center justify-between mb-4">
    <div className="flex items-center gap-3">
      <ServerIcon className="h-8 w-8 text-blue-300" />
      <div>
        <h2 className="text-2xl font-bold text-white">SCHEMA PIPELINE (protec_ai)</h2>
        <p className="text-blue-200 text-sm">Time Dados • Schema de Produção • NOSSO</p>
      </div>
    </div>
    <div className="bg-green-500 text-white px-4 py-2 rounded-full font-semibold">
      ✅ OPERACIONAL
    </div>
  </div>
  
  {/* Grid com 4 métricas principais */}
  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
    <div className="bg-blue-800/50 rounded-lg p-4">
      <p className="text-blue-200 text-xs">Equipamentos</p>
      <p className="text-3xl font-bold">{technicalData.totalEquipments}</p>
      <p className="text-blue-300 text-xs">relés</p>
    </div>
    <div className="bg-blue-800/50 rounded-lg p-4">
      <p className="text-blue-200 text-xs">Settings</p>
      <p className="text-3xl font-bold">{technicalData.totalSettings.toLocaleString()}</p>
      <p className="text-blue-300 text-xs">configs</p>
    </div>
    <div className="bg-blue-800/50 rounded-lg p-4">
      <p className="text-blue-200 text-xs">Funções Ativas</p>
      <p className="text-3xl font-bold">{technicalData.activeFunctions}</p>
      <p className="text-blue-300 text-xs">de {technicalData.protectionFunctions}</p>
    </div>
    <div className="bg-blue-800/50 rounded-lg p-4">
      <p className="text-blue-200 text-xs">APIs</p>
      <p className="text-3xl font-bold">{onlineAPIs}/{apiStatuses.length}</p>
      <p className="text-blue-300 text-xs">online</p>
    </div>
  </div>
</div>

{/* 🟢 🟣 SCHEMAS AUXILIARES - ETAP E ML */}
<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
  {/* ETAP */}
  <div className="bg-gray-800 rounded-lg p-6 border border-green-600">
    <h3 className="text-xl font-semibold text-green-400">Schema ETAP</h3>
    <p className="text-gray-400 text-sm mb-4">(relay_configs) • Time ETAP</p>
    <div className="space-y-3">
      <div className="flex justify-between">
        <span>Estrutura:</span>
        <span className="text-green-400">✅ Preparada</span>
      </div>
      <div className="flex justify-between">
        <span>Status:</span>
        <span className="text-blue-400">Vazio (Aguardando Time ETAP)</span>
      </div>
      <div className="bg-green-900/30 border border-green-700 rounded p-3 mt-4">
        <p className="text-green-300 text-xs text-center">
          🎯 Pronto para simulações ETAP
        </p>
      </div>
    </div>
  </div>

  {/* ML */}
  <div className="bg-gray-800 rounded-lg p-6 border border-purple-600">
    <h3 className="text-xl font-semibold text-purple-400">Schema ML</h3>
    <p className="text-gray-400 text-sm mb-4">(ml_gateway) • Time ML</p>
    <div className="space-y-3">
      <div className="flex justify-between">
        <span>Estrutura:</span>
        <span className="text-green-400">✅ Preparada</span>
      </div>
      <div className="flex justify-between">
        <span>Status:</span>
        <span className="text-blue-400">Vazio (Aguardando Time ML)</span>
      </div>
      <div className="bg-purple-900/30 border border-purple-700 rounded p-3 mt-4">
        <p className="text-purple-300 text-xs text-center">
          🤖 Pronto para modelos preditivos
        </p>
      </div>
    </div>
  </div>
</div>
```

---

## ✅ BENEFÍCIOS DO NOVO LAYOUT:

1. **Hierarquia Visual Clara:**
   - Schema PIPELINE (nosso) em DESTAQUE (azul, maior, topo)
   - Schemas auxiliares (ETAP, ML) em segundo plano (menores, embaixo)

2. **Separação de Responsabilidades:**
   - Cada card diz "Time X"
   - Fica claro quem é dono de qual schema

3. **Métricas Relevantes:**
   - protec_ai: 50 relés, 236K settings, 23/158 funções
   - ETAP/ML: Status de preparação, não métricas (pois estão vazios)

4. **Escalabilidade:**
   - Quando ETAP/ML popularem, fácil adicionar métricas nos cards deles
   - Layout suporta crescimento futuro

---

## 📋 CHECKLIST DE CORREÇÃO:

- [ ] Corrigir card "Registros DB" para mostrar 236,716 (protec_ai)
- [ ] Adicionar console.log para debugar API statistics
- [ ] Implementar novo layout com hierarquia visual
- [ ] Testar no navegador e verificar valores reais
- [ ] Fazer commit: `fix: dashboard layout hierárquico 3 schemas + dados protec_ai corretos`

---

## 🎯 RESULTADO ESPERADO:

```
┌────────────────────────────────────────────────────────────┐
│  🔵 SCHEMA PIPELINE (protec_ai) - TIME DADOS              │
│  ✅ OPERACIONAL                                            │
├────────────────────────────────────────────────────────────┤
│  [50 relés] [236K settings] [23/158 funções] [10/10 APIs] │
└────────────────────────────────────────────────────────────┘

┌─────────────────────────┬──────────────────────────────────┐
│ 🟢 Schema ETAP          │ 🟣 Schema ML                     │
│ (relay_configs)         │ (ml_gateway)                     │
│ Time ETAP               │ Time ML                          │
│ ✅ Preparado            │ ✅ Preparado                     │
│ Vazio (Aguardando)      │ Vazio (Aguardando)               │
└─────────────────────────┴──────────────────────────────────┘
```

---

**IMPORTANTE:** Este é o padrão que deve ser mantido sempre. O schema **protec_ai é NOSSO** e deve ter destaque visual no dashboard!

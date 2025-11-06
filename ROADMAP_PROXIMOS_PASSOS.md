# 🚀 ROADMAP - PRÓXIMOS PASSOS PROTECAI

**Data**: 03 de Novembro de 2025  
**Status Atual**: ✅ Backend + Testes (53/53 passing)  
**Próximo Foco**: 🎨 Frontend + Integração Completa

---

## 📊 **STATUS DO PROJETO**

### ✅ **COMPLETADO (100%)**

#### **Backend Core**
- ✅ Extração de Glossário (Excel → JSON/CSV)
- ✅ Geração SQL para popular DB (protection_functions, relay_settings)
- ✅ Pipeline de importação atualizado
- ✅ Endpoints API de relatórios (/api/relay-config/*)
- ✅ Geração multi-formato (JSON/CSV/XLSX/PDF)

#### **Testes**
- ✅ 17 testes - Extração de Glossário
- ✅ 20 testes - Geração SQL/CSV
- ✅ 16 testes - Robustez Multi-Fabricante
- ✅ **TOTAL: 53 testes passando (100%)**

---

## 🎯 **FASE 6 - VISUALIZAÇÃO FRONTEND (PRÓXIMA)**

### **OBJETIVO**: Usuário final consegue **VER e USAR** as configurações dos relés

### **6.1 - CRUD Completo de Configurações (Backend)** 🔴 **CRÍTICO** ⚠️ **ESQUECEMOS!**

**Descrição**: Implementar endpoints de CREATE, UPDATE, DELETE para configurações de relés

**Localização**: `api/routers/relay_config_reports.py` (expandir) + `api/services/relay_config_crud_service.py` (novo)

**Situação Atual**: ✅ Temos apenas READ (visualizar). ❌ Falta CUD (criar, editar, deletar)!

#### **Endpoints a Implementar**

```python
# ============================================================
# CREATE - Criar nova configuração manual
# ============================================================
POST /api/relay-config/settings
Body: {
  "equipment_id": 1,
  "function_code": "50",
  "parameter_code": "0201",
  "parameter_name": "I>",
  "set_value": 5.5,
  "unit_of_measure": "A",
  "is_enabled": true
}

# ============================================================
# UPDATE - Atualizar configuração existente
# ============================================================
PUT /api/relay-config/settings/{setting_id}
Body: {
  "set_value": 6.0,
  "is_enabled": false,
  "notes": "Ajustado para novo critério"
}

PATCH /api/relay-config/settings/bulk
Body: {
  "equipment_id": 1,
  "updates": [
    {"setting_id": 10, "set_value": 5.5},
    {"setting_id": 11, "set_value": 10.0}
  ]
}

# ============================================================
# DELETE - Excluir configuração
# ============================================================
DELETE /api/relay-config/settings/{setting_id}
  ?soft_delete=true  # Marca como deletado sem remover fisicamente

DELETE /api/relay-config/equipment/{equipment_id}
  ?cascade=true      # Remove equipamento + todas as configs
  ?soft_delete=true  # Marca como inativo

# ============================================================
# DISABLE/ENABLE - Desabilitar/Habilitar função
# ============================================================
PATCH /api/relay-config/settings/{setting_id}/toggle
Body: {
  "is_enabled": false
}
```

#### **Service a Criar**

**Arquivo**: `api/services/relay_config_crud_service.py`

```python
class RelayConfigCRUDService:
    """
    Serviço para operações CRUD em configurações de relés.
    
    RESPONSABILIDADES:
    - Validar integridade dos dados antes de persistir
    - Garantir audit trail (quem mudou, quando, de onde)
    - Validar regras de negócio (ex: setpoint dentro de limites)
    - Soft delete com possibilidade de rollback
    """
    
    def create_setting(self, data: RelaySettingCreate) -> RelaySettingResponse:
        """Cria nova configuração validando constraints"""
        
    def update_setting(self, setting_id: int, data: RelaySettingUpdate) -> RelaySettingResponse:
        """Atualiza configuração existente com histórico"""
        
    def delete_setting(self, setting_id: int, soft: bool = True) -> dict:
        """Remove ou desativa configuração"""
        
    def bulk_update_settings(self, equipment_id: int, updates: List[dict]) -> dict:
        """Atualiza múltiplas configurações de uma vez (transação)"""
        
    def delete_equipment_with_cascade(self, equipment_id: int, soft: bool = True) -> dict:
        """Remove equipamento e todas as suas configurações"""
```

#### **Schemas Pydantic a Criar**

**Arquivo**: `api/schemas/relay_config_schemas.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class RelaySettingCreate(BaseModel):
    """Schema para criação de nova configuração"""
    equipment_id: int
    function_code: str = Field(..., min_length=1, max_length=10)
    parameter_code: str = Field(..., min_length=1, max_length=20)
    parameter_name: str = Field(..., min_length=1, max_length=100)
    set_value: float
    unit_of_measure: Optional[str] = None
    min_limit: Optional[float] = None
    max_limit: Optional[float] = None
    is_enabled: bool = True
    notes: Optional[str] = None
    
    @validator('set_value')
    def validate_set_value(cls, v, values):
        """Valida se setpoint está dentro dos limites"""
        min_val = values.get('min_limit')
        max_val = values.get('max_limit')
        if min_val is not None and v < min_val:
            raise ValueError(f'set_value {v} abaixo do limite mínimo {min_val}')
        if max_val is not None and v > max_val:
            raise ValueError(f'set_value {v} acima do limite máximo {max_val}')
        return v

class RelaySettingUpdate(BaseModel):
    """Schema para atualização de configuração"""
    set_value: Optional[float] = None
    is_enabled: Optional[bool] = None
    notes: Optional[str] = None
    modified_by: Optional[str] = None  # Usuário que fez a mudança

class RelaySettingResponse(BaseModel):
    """Schema de resposta com audit trail"""
    id: int
    equipment_id: int
    parameter_name: str
    set_value: float
    unit_of_measure: Optional[str]
    is_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]
    modified_by: Optional[str]
    
    class Config:
        from_attributes = True

class BulkUpdateRequest(BaseModel):
    """Schema para atualização em lote"""
    equipment_id: int
    updates: List[dict]
    modified_by: Optional[str] = None
```

#### **Critérios de Aceitação (Backend)**

- [ ] POST /api/relay-config/settings cria nova configuração
- [ ] PUT /api/relay-config/settings/{id} atualiza configuração existente
- [ ] DELETE /api/relay-config/settings/{id} faz soft delete por padrão
- [ ] DELETE com ?soft_delete=false faz hard delete (físico)
- [ ] PATCH /bulk atualiza múltiplas configs em transação única
- [ ] Validação de limites (min/max) antes de persistir
- [ ] Audit trail registra quem/quando modificou
- [ ] Rollback automático em caso de erro em bulk update
- [ ] Testes unitários para todos os endpoints CRUD

---

### **6.2 - Tela de Configuração de Relés no Frontend** 🔴 **CRÍTICO**

**Descrição**: Criar interface para **VISUALIZAR, EDITAR E EXCLUIR** configurações dos relés

**Localização**: `frontend/protecai-frontend/src/pages/RelayConfiguration.tsx`

**Funcionalidades Essenciais**:

#### **Componentes a Criar**

```typescript
// 1. Página Principal
RelayConfigurationPage.tsx
├── RelayListPanel.tsx           // Lista de equipamentos
│   ├── FilterBar.tsx             // Filtros (fabricante, modelo, subestação)
│   ├── EquipmentCard.tsx         // Card de cada equipamento
│   └── DeleteEquipmentModal.tsx  // ⚠️ NOVO: Confirmar exclusão de relé
│
├── ConfigurationDetailPanel.tsx  // Detalhes da configuração
│   ├── EquipmentHeader.tsx       // Cabeçalho (nome, modelo, SE)
│   │   └── EditEquipmentButton   // ⚠️ NOVO: Botão para editar info básica
│   ├── ProtectionFunctionsTab.tsx // Tab de funções de proteção
│   │   ├── FunctionRow.tsx       // ⚠️ NOVO: Linha editável
│   │   └── InlineEditor.tsx      // ⚠️ NOVO: Editor inline de valores
│   ├── SettingsTab.tsx           // Tab de settings/parâmetros
│   │   ├── SettingRow.tsx        // ⚠️ NOVO: Linha editável
│   │   ├── BulkEditModal.tsx     // ⚠️ NOVO: Edição em lote
│   │   └── DeleteSettingButton   // ⚠️ NOVO: Excluir configuração
│   └── ExportActions.tsx         // Botões de export (PDF, Excel, CSV)
│
├── ComparisonModal.tsx           // Modal para comparar 2+ relés
└── EditSettingModal.tsx          // ⚠️ NOVO: Modal para editar configuração
```

#### **APIs a Consumir**

```typescript
// services/relayConfigService.ts

// ============================================================
// READ - Visualizar
// ============================================================
// 1. Listar equipamentos disponíveis
GET /api/relay-config/equipment/list
  ?manufacturer=MICON
  &model=P122
  &substation=SE-NORTE

// 2. Buscar configuração de um relé
GET /api/relay-config/report/{equipment_id}
  ?include_disabled=false

// 3. Exportar relatório
GET /api/relay-config/export/{equipment_id}
  ?format=pdf|xlsx|csv

// ============================================================
// CREATE - Criar nova configuração ⚠️ NOVO
// ============================================================
POST /api/relay-config/settings
Body: {
  equipment_id: 1,
  function_code: "50",
  parameter_code: "0201",
  parameter_name: "I>",
  set_value: 5.5,
  unit_of_measure: "A",
  is_enabled: true
}

// ============================================================
// UPDATE - Editar configuração existente ⚠️ NOVO
// ============================================================
PUT /api/relay-config/settings/{setting_id}
Body: {
  set_value: 6.0,
  is_enabled: false,
  notes: "Ajustado conforme estudo de coordenação"
}

// Edição em lote
PATCH /api/relay-config/settings/bulk
Body: {
  equipment_id: 1,
  updates: [
    {setting_id: 10, set_value: 5.5},
    {setting_id: 11, set_value: 10.0}
  ]
}

// ============================================================
// DELETE - Excluir configuração/equipamento ⚠️ NOVO
// ============================================================
DELETE /api/relay-config/settings/{setting_id}
  ?soft_delete=true  // Soft delete por padrão

DELETE /api/relay-config/equipment/{equipment_id}
  ?cascade=true      // Remove todas as configs também
  ?soft_delete=true
```

#### **Layout Sugerido (com CRUD)**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CONFIGURAÇÃO DE RELÉS DE PROTEÇÃO                        [👤 Admin] [⚙️]  │
├─────────────────┬───────────────────────────────────────────────────────────┤
│                 │                                                             │
│  FILTROS        │  EQUIPAMENTO: REL-001            [✏️ Editar] [🗑️ Excluir] │
│  ─────────      │  Modelo: MICON P122 | SE: NORTE | Bay: L1                 │
│                 │                                                             │
│  Fabricante:    │  ┌──────────────────────────────────────────────────────┐ │
│  [ MICON ▼ ]    │  │ Funções de Proteção │ Parâmetros │ Histórico        │ │
│                 │  ├──────────────────────────────────────────────────────┤ │
│  Modelo:        │  │ ✓ 50  - Sobrecorrente Inst.           [✏️] [➕] [🗑️]│ │
│  [ P122  ▼ ]    │  │   ├─ I>    = [5.5] A     [💾Salvar]  [Min: 1.0]     │ │
│                 │  │   ├─ I>>   = [10.0] A    [Min: 5.0]  [Max: 20.0]    │ │
│  Subestação:    │  │   └─ I>>>  = [20.0] A    [Max: 50.0]                │ │
│  [ NORTE ▼ ]    │  │                                                       │ │
│                 │  │ ✓ 50N - Sobrecorrente Terra                   [✏️]   │ │
│  [Buscar]       │  │   └─ Ie>   = [2.0] A                                 │ │
│                 │  │                                                       │ │
│  EQUIPAMENTOS   │  │ ✓ 27  - Subtensão                             [✏️]   │ │
│  ─────────────  │  │   └─ V<    = [0.85] pu                               │ │
│                 │  │                                                       │ │
│  ⚡ REL-001  ✅ │  │ ✓ 59  - Sobretensão                           [✏️]   │ │
│  ⚡ REL-002  ✅ │  │   └─ V>    = [1.15] pu                               │ │
│  ⚡ REL-003  ⚠️ │  │                                                       │ │
│  ⚡ REL-004  ❌ │  │ ⚠️ Alterações não salvas! [💾 Salvar Tudo] [↩️ Cancelar]│
│                 │  └──────────────────────────────────────────────────────┘ │
│  [+ Novo Relé]  │                                                             │
│                 │  [📄 PDF] [📊 Excel] [📋 CSV] [⚖️ Comparar] [✏️ Ed. Lote]  │
└─────────────────┴───────────────────────────────────────────────────────────┘

LEGENDA DE STATUS:
✅ = Configurado e ativo
⚠️ = Com pendências ou alertas
❌ = Inativo ou com erros
```

#### **Estados da UI**

```typescript
interface RelayConfigState {
  // Visualização
  selectedEquipmentId: number | null;
  configurationData: RelayConfiguration | null;
  isLoading: boolean;
  filters: {
    manufacturer: string;
    model: string;
    substation: string;
  };
  comparisonMode: boolean;
  selectedForComparison: number[];
  
  // ⚠️ NOVO: Edição
  editMode: boolean;
  editingSettingId: number | null;
  unsavedChanges: Map<number, SettingUpdate>;  // settingId → novos valores
  validationErrors: Map<number, string>;        // settingId → mensagem de erro
  
  // ⚠️ NOVO: Exclusão
  confirmDeleteModal: {
    isOpen: boolean;
    type: 'setting' | 'equipment';
    targetId: number | null;
    targetName: string;
  };
  
  // ⚠️ NOVO: Bulk Edit
  bulkEditMode: boolean;
  selectedSettingsForBulk: Set<number>;
}

interface SettingUpdate {
  settingId: number;
  originalValue: number;
  newValue: number;
  isDirty: boolean;
  isValid: boolean;
  validationMessage?: string;
}
```

#### **Requisitos Técnicos**

- [ ] React 18+ com TypeScript
- [ ] React Query para cache de dados
- [ ] TailwindCSS para estilização
- [ ] React Icons para ícones
- [ ] Axios para chamadas API
- [ ] React Table para tabelas de parâmetros
- [ ] jsPDF ou html2canvas para export PDF client-side

#### **Critérios de Aceitação (Frontend)**

##### **Visualização (já planejado)**
- [ ] Usuário consegue filtrar equipamentos por fabricante/modelo/SE
- [ ] Usuário visualiza todas as funções de proteção de um relé
- [ ] Usuário visualiza todos os parâmetros configurados
- [ ] Usuário exporta configuração em PDF/Excel/CSV
- [ ] Usuário compara configuração de 2 ou mais relés lado a lado
- [ ] Interface responsiva (desktop/tablet)
- [ ] Loading states e error handling adequados

##### **Edição (NOVO)** ⚠️
- [ ] Usuário clica em ✏️ ao lado de um parâmetro e entra em modo de edição
- [ ] Modo de edição mostra input editável + botões Salvar/Cancelar
- [ ] Validação client-side: valor dentro de min/max permitido
- [ ] Indicador visual de "alterações não salvas" (badge amarelo ⚠️)
- [ ] Botão "Salvar Tudo" envia múltiplas alterações em transação única
- [ ] Botão "Cancelar" reverte todas as mudanças não salvas
- [ ] Confirmação antes de sair da página com alterações pendentes
- [ ] Toast/notification de sucesso após salvar: "3 configurações atualizadas ✅"
- [ ] Toast/notification de erro com detalhes: "Falha: I> fora dos limites (1.0 - 20.0)"
- [ ] Histórico de alterações visível (quem alterou, quando, valor anterior)

##### **Edição em Lote (NOVO)** ⚠️
- [ ] Usuário seleciona múltiplos parâmetros com checkbox
- [ ] Botão "Editar em Lote" abre modal com lista de selecionados
- [ ] Modal permite editar todos os valores de uma vez
- [ ] Aplicação em transação única (tudo ou nada)
- [ ] Rollback automático se um item falhar validação

##### **Exclusão (NOVO)** ⚠️
- [ ] Botão 🗑️ ao lado de cada configuração
- [ ] Modal de confirmação: "Tem certeza que deseja excluir I> = 5.5A?"
- [ ] Opção de soft delete (padrão) vs hard delete
- [ ] Botão "Excluir Relé" remove equipamento completo
- [ ] Confirmação extra ao excluir equipamento: "Isso removerá 32 configurações!"
- [ ] Toast de sucesso: "Configuração removida ✅"
- [ ] Possibilidade de desfazer (undo) nos primeiros 10 segundos
- [ ] Exclusões registradas em log de auditoria

##### **Controle de Acesso (NOVO)** ⚠️
- [ ] Usuário com role "Viewer" só vê dados (READ)
- [ ] Usuário com role "Editor" pode editar/excluir
- [ ] Usuário com role "Admin" pode excluir equipamentos
- [ ] Botões de edição/exclusão desabilitados para Viewers
- [ ] Mensagem clara: "Você não tem permissão para editar"

---

### **6.3 - Testes E2E da Funcionalidade** 🟡 **ALTA**

**Arquivo**: `frontend/protecai-frontend/cypress/e2e/relay-configuration.cy.ts`

```typescript
describe('Relay Configuration Module', () => {
  
  // ========================================
  // TESTES DE VISUALIZAÇÃO (READ)
  // ========================================
  it('should load equipment list', () => {
    cy.visit('/relay-configuration')
    cy.get('[data-testid="equipment-list"]').should('exist')
    cy.get('[data-testid="equipment-card"]').should('have.length.gt', 0)
  })

  it('should display relay configuration details', () => {
    cy.visit('/relay-configuration')
    cy.get('[data-testid="equipment-card"]').first().click()
    cy.get('[data-testid="config-detail-panel"]').should('be.visible')
    cy.get('[data-testid="protection-function"]').should('have.length.gt', 0)
  })

  it('should export configuration as PDF', () => {
    cy.visit('/relay-configuration/1')
    cy.get('[data-testid="export-pdf-btn"]').click()
    cy.wait('@exportPDF')
    // Validar download
  })

  it('should filter equipment by manufacturer', () => {
    cy.visit('/relay-configuration')
    cy.get('[data-testid="filter-manufacturer"]').select('MICON')
    cy.get('[data-testid="equipment-card"]').should('have.length.gt', 0)
    cy.get('[data-testid="equipment-card"]').each(($el) => {
      cy.wrap($el).should('contain', 'MICON')
    })
  })
  
  // ========================================
  // TESTES DE EDIÇÃO (UPDATE) ⚠️ NOVO
  // ========================================
  it('should edit a setting value inline', () => {
    cy.visit('/relay-configuration/1')
    
    // Clicar em editar
    cy.get('[data-testid="setting-row-10"]')
      .find('[data-testid="edit-button"]')
      .click()
    
    // Input de edição deve aparecer
    cy.get('[data-testid="setting-input-10"]').should('be.visible')
    
    // Alterar valor
    cy.get('[data-testid="setting-input-10"]')
      .clear()
      .type('6.5')
    
    // Salvar
    cy.get('[data-testid="save-button-10"]').click()
    
    // Verificar chamada à API
    cy.wait('@updateSetting').its('request.body').should('deep.include', {
      set_value: 6.5
    })
    
    // Verificar toast de sucesso
    cy.get('[data-testid="toast-success"]')
      .should('be.visible')
      .and('contain', 'Configuração atualizada')
  })
  
  it('should show validation error for value out of range', () => {
    cy.visit('/relay-configuration/1')
    
    cy.get('[data-testid="setting-row-10"]')
      .find('[data-testid="edit-button"]')
      .click()
    
    // Tentar valor fora do range
    cy.get('[data-testid="setting-input-10"]')
      .clear()
      .type('999')  // Acima do máximo permitido
    
    cy.get('[data-testid="save-button-10"]').click()
    
    // Deve mostrar erro de validação
    cy.get('[data-testid="validation-error-10"]')
      .should('be.visible')
      .and('contain', 'fora dos limites')
  })
  
  it('should handle bulk edit of multiple settings', () => {
    cy.visit('/relay-configuration/1')
    
    // Selecionar múltiplos settings
    cy.get('[data-testid="checkbox-setting-10"]').check()
    cy.get('[data-testid="checkbox-setting-11"]').check()
    cy.get('[data-testid="checkbox-setting-12"]').check()
    
    // Abrir modal de bulk edit
    cy.get('[data-testid="bulk-edit-button"]').click()
    cy.get('[data-testid="bulk-edit-modal"]').should('be.visible')
    
    // Editar valores
    cy.get('[data-testid="bulk-input-10"]').clear().type('5.5')
    cy.get('[data-testid="bulk-input-11"]').clear().type('10.0')
    cy.get('[data-testid="bulk-input-12"]').clear().type('15.0')
    
    // Salvar tudo
    cy.get('[data-testid="bulk-save-button"]').click()
    
    // Verificar transação única
    cy.wait('@bulkUpdate').its('request.body.updates')
      .should('have.length', 3)
    
    cy.get('[data-testid="toast-success"]')
      .should('contain', '3 configurações atualizadas')
  })
  
  it('should warn before leaving page with unsaved changes', () => {
    cy.visit('/relay-configuration/1')
    
    // Fazer alteração sem salvar
    cy.get('[data-testid="setting-row-10"]')
      .find('[data-testid="edit-button"]')
      .click()
    cy.get('[data-testid="setting-input-10"]').clear().type('7.0')
    
    // Badge de alterações pendentes
    cy.get('[data-testid="unsaved-badge"]').should('be.visible')
    
    // Tentar navegar para outro equipamento
    cy.get('[data-testid="equipment-card"]').eq(1).click()
    
    // Deve mostrar confirmação
    cy.get('[data-testid="confirm-navigation-modal"]')
      .should('be.visible')
      .and('contain', 'alterações não salvas')
  })
  
  // ========================================
  // TESTES DE EXCLUSÃO (DELETE) ⚠️ NOVO
  // ========================================
  it('should delete a setting with confirmation', () => {
    cy.visit('/relay-configuration/1')
    
    // Clicar em excluir
    cy.get('[data-testid="setting-row-10"]')
      .find('[data-testid="delete-button"]')
      .click()
    
    // Modal de confirmação
    cy.get('[data-testid="confirm-delete-modal"]')
      .should('be.visible')
      .and('contain', 'Tem certeza')
    
    // Confirmar
    cy.get('[data-testid="confirm-delete-button"]').click()
    
    // Verificar chamada à API
    cy.wait('@deleteSetting')
    
    // Setting deve sumir da lista
    cy.get('[data-testid="setting-row-10"]').should('not.exist')
    
    // Toast de sucesso
    cy.get('[data-testid="toast-success"]')
      .should('contain', 'Configuração removida')
  })
  
  it('should delete equipment with cascade warning', () => {
    cy.visit('/relay-configuration/1')
    
    // Clicar em excluir equipamento
    cy.get('[data-testid="delete-equipment-button"]').click()
    
    // Modal deve avisar sobre cascade
    cy.get('[data-testid="confirm-delete-modal"]')
      .should('be.visible')
      .and('contain', 'removerá')
      .and('contain', 'configurações')
    
    // Confirmar
    cy.get('[data-testid="confirm-delete-button"]').click()
    
    // Verificar chamada à API com cascade
    cy.wait('@deleteEquipment').its('request.url')
      .should('include', 'cascade=true')
    
    // Redirect para lista
    cy.url().should('eq', '/relay-configuration')
    
    // Equipamento não deve mais aparecer
    cy.get('[data-testid="equipment-card-1"]').should('not.exist')
  })
  
  it('should allow undo after delete', () => {
    cy.visit('/relay-configuration/1')
    
    cy.get('[data-testid="setting-row-10"]')
      .find('[data-testid="delete-button"]')
      .click()
    cy.get('[data-testid="confirm-delete-button"]').click()
    
    // Toast com botão de undo
    cy.get('[data-testid="toast-undo-button"]')
      .should('be.visible')
      .click()
    
    // Verificar chamada de restore
    cy.wait('@restoreSetting')
    
    // Setting volta a aparecer
    cy.get('[data-testid="setting-row-10"]').should('exist')
  })
  
  // ========================================
  // TESTES DE CONTROLE DE ACESSO ⚠️ NOVO
  // ========================================
  it('should hide edit/delete buttons for viewer role', () => {
    // Login como viewer
    cy.login('viewer@example.com', 'password')
    cy.visit('/relay-configuration/1')
    
    // Botões de edição não devem existir
    cy.get('[data-testid="edit-button"]').should('not.exist')
    cy.get('[data-testid="delete-button"]').should('not.exist')
    cy.get('[data-testid="bulk-edit-button"]').should('not.exist')
    
    // Apenas botões de export
    cy.get('[data-testid="export-pdf-btn"]').should('exist')
  })
  
  it('should show edit/delete buttons for editor role', () => {
    cy.login('editor@example.com', 'password')
    cy.visit('/relay-configuration/1')
    
    // Botões de edição devem existir
    cy.get('[data-testid="edit-button"]').should('exist')
    cy.get('[data-testid="delete-button"]').should('exist')
  })
})
```

---

## 📋 **FASE 7 - TESTES BACKEND RESTANTES**

### **7.1 - Testes de Relatórios** 🟡 **ALTA**

**Arquivo**: `tests/test_report_generation.py` (já criado, executar)

```bash
pytest tests/test_report_generation.py -v
```

**Validações**:
- [ ] Relatório JSON tem estrutura correta
- [ ] CSV tem todas as colunas esperadas
- [ ] XLSX tem sheet names corretos
- [ ] PDF é gerado e tem conteúdo válido

### **7.2 - Teste de Integração E2E** 🟡 **ALTA**

**Arquivo**: `tests/test_integration_pipeline.py` (já criado, executar)

```bash
pytest tests/test_integration_pipeline.py -v
```

**Validações**:
- [ ] Excel → Glossário → SQL → DB → Relatório (fluxo completo)
- [ ] Dados persistem corretamente no banco
- [ ] Relatórios refletem dados do banco

---

## 🗄️ **FASE 8 - POPULAÇÃO DO BANCO DE DADOS REAL**

### **8.1 - Executar Scripts SQL Gerados**

```bash
# 1. Popular funções de proteção
psql -U postgres -d protecai_db -f outputs/sql/populate_protection_functions.sql

# 2. Popular relay settings (ajustar equipment_id antes!)
# ATENÇÃO: Editar SQL para vincular a equipamentos reais
psql -U postgres -d protecai_db -f outputs/sql/populate_relay_settings.sql

# 3. Validar dados inseridos
psql -U postgres -d protecai_db -c "
SELECT COUNT(*) FROM protec_ai.protection_functions;
SELECT COUNT(*) FROM protec_ai.relay_settings;
"
```

### **8.2 - Criar Script de Migração Seguro**

**Arquivo**: `scripts/migrate_glossary_to_db.py`

```python
"""
Script seguro de migração do glossário para o banco de dados.
Inclui validação, rollback automático em caso de erro.
"""
```

---

## 🎨 **FASE 9 - MELHORIAS DE UX/UI**

### **9.1 - Dashboard de Configurações**

- [ ] Gráfico de funções mais usadas
- [ ] Comparativo de setpoints entre equipamentos similares
- [ ] Alertas de configurações fora do padrão
- [ ] Histórico de alterações de configuração

### **9.2 - Funcionalidades Avançadas**

- [ ] Busca textual nas configurações
- [ ] Tags e categorização customizada
- [ ] Exportação em lote (múltiplos equipamentos)
- [ ] Templates de configuração padrão

---

## 🔐 **FASE 10 - SEGURANÇA E AUDITORIA**

### **10.1 - Controle de Acesso**

- [ ] Roles: Visualizador vs Editor
- [ ] Log de quem visualizou configurações
- [ ] Proteção contra SQL injection (já validado nos testes)

### **10.2 - Auditoria**

- [ ] Registro de todas as exportações
- [ ] Tracking de mudanças em configurações
- [ ] Relatório de acessos

---

## 📊 **PRIORIZAÇÃO (MoSCoW)**

### **MUST HAVE** 🔴 (Fazer Agora)
1. **✅ CRUD Backend - Endpoints de CREATE/UPDATE/DELETE** (Fase 6.1) ⚠️ **ESQUECEMOS!**
2. **Tela Frontend de Configuração com Edição/Exclusão** (Fase 6.2)
3. **Integração Frontend ↔ Backend CRUD** (Fase 6.2)
4. **População do DB com dados reais** (Fase 8.1)

### **SHOULD HAVE** 🟡 (Próxima Sprint)
5. Testes E2E Frontend incluindo CRUD (Fase 6.3)
6. Testes de Relatórios Backend (Fase 7.1)
7. Teste Integração Completa (Fase 7.2)
8. Controle de Acesso (Viewer vs Editor) (Fase 10.1)

### **COULD HAVE** 🟢 (Backlog)
9. Dashboard de Configurações (Fase 9.1)
10. Funcionalidades Avançadas (Fase 9.2)
11. Histórico de Alterações com Timeline (Fase 9.1)

### **WON'T HAVE NOW** ⚪ (Futuro)
12. Auditoria Completa (Fase 10.2)
13. Notificações em Tempo Real (WebSockets)
14. Versionamento de Configurações

---

## 🚀 **PLANO DE AÇÃO IMEDIATO (Esta Semana)**

### **Dia 1: Backend CRUD** ⚠️ **CRÍTICO - ESQUECEMOS!**
```bash
# Criar novos arquivos
touch api/services/relay_config_crud_service.py
touch api/schemas/relay_config_schemas.py
touch tests/test_relay_config_crud.py

# Implementar
# 1. RelayConfigCRUDService com métodos create/update/delete
# 2. Schemas Pydantic com validações (min/max limits)
# 3. Endpoints POST/PUT/DELETE em relay_config_reports.py
# 4. Testes unitários (pytest)

# Validar
pytest tests/test_relay_config_crud.py -v
```

### **Dia 2: Testes Backend CRUD**
```bash
# Criar testes robustos
# - Validação de limites (min/max)
# - Soft delete vs hard delete
# - Bulk update com rollback em erro
# - Audit trail (created_at, updated_at, modified_by)

# Executar todos os testes
pytest tests/ -v
```

### **Dia 3-4: Setup e Implementar Frontend**
```bash
cd frontend/protecai-frontend

# Criar estrutura de pastas
mkdir -p src/pages/RelayConfiguration
mkdir -p src/components/RelayConfiguration
mkdir -p src/services
mkdir -p src/types

# Instalar dependências
npm install react-query axios react-table
npm install react-hook-form yup  # Validação de formulários
npm install react-hot-toast       # Notificações
npm install -D @types/react-table

# Implementar componentes
# - RelayConfigurationPage.tsx (página principal)
# - InlineEditor.tsx (edição inline de valores)
# - EditSettingModal.tsx (modal de edição)
# - DeleteConfirmModal.tsx (confirmação de exclusão)
# - BulkEditModal.tsx (edição em lote)
# - relayConfigService.ts (API calls CRUD completos)
```

### **Dia 5: Integração e Testes E2E**
```bash
# Conectar com backend real
# - Testar fluxo READ
# - Testar fluxo CREATE (criar nova configuração manual)
# - Testar fluxo UPDATE (editar inline + bulk edit)
# - Testar fluxo DELETE (soft delete + hard delete)

# Testes E2E com Cypress
npm run cypress:open

# Ajustes de UI/UX
# - Loading states
# - Error handling
# - Toast notifications
# - Validação client-side
```

---

## ✅ **DEFINIÇÃO DE PRONTO (DoD)**

Uma funcionalidade está **PRONTA** quando:

- [x] Código implementado e revisado
- [x] Testes unitários passando (se backend)
- [x] Testes E2E passando (se frontend)
- [x] Documentação atualizada
- [x] Validado em ambiente de desenvolvimento
- [x] Aprovado pelo usuário final (você!)

---

## 📝 **NOTAS IMPORTANTES**

### **Sobre População do Banco**
⚠️ **ATENÇÃO**: O SQL de `relay_settings` tem `equipment_id = NULL`. Antes de executar:
1. Identificar equipamentos reais no banco
2. Criar mapeamento: código_glossário → equipment_id
3. Atualizar SQL ou fazer UPDATE posterior

### **Sobre Export de Relatórios**
💡 **TIP**: Considere fazer export PDF **client-side** no frontend para melhor performance:
- Usa `jsPDF` ou `html2canvas`
- Não sobrecarrega backend
- Usuário tem feedback visual imediato

---

## 🎯 **OBJETIVO FINAL**

Entregar uma **aplicação completa** onde:

✅ Usuário acessa `http://localhost:5173/relay-configuration`  
✅ Vê lista de todos os relés com filtros  
✅ Clica em um relé e visualiza toda a configuração  
✅ **EDITA configurações inline com validação em tempo real** ⚠️ **NOVO**  
✅ **Edita múltiplas configurações de uma vez (bulk edit)** ⚠️ **NOVO**  
✅ **Exclui configurações específicas ou equipamento completo** ⚠️ **NOVO**  
✅ **Confirmação antes de exclusões com opção de undo** ⚠️ **NOVO**  
✅ **Controle de acesso: Viewer (só lê) vs Editor (edita/exclui)** ⚠️ **NOVO**  
✅ Exporta para PDF/Excel/CSV  
✅ Compara configurações de múltiplos relés  
✅ **Sistema registra audit trail de todas as alterações** ⚠️ **NOVO**  
✅ **Sistema é ROBUSTO, CONFIÁVEL e PRODUTIVO**  

---

## ⚠️ **ALERTA: FUNCIONALIDADE ESQUECIDA INCLUÍDA!**

**O QUE FOI ADICIONADO:**

1. **Backend CRUD Completo** (Fase 6.1)
   - POST /api/relay-config/settings (criar configuração)
   - PUT /api/relay-config/settings/{id} (editar configuração)
   - DELETE /api/relay-config/settings/{id} (excluir configuração)
   - PATCH /api/relay-config/settings/bulk (edição em lote)
   - DELETE /api/relay-config/equipment/{id} (excluir equipamento)

2. **Frontend com Edição/Exclusão** (Fase 6.2)
   - Edição inline de valores
   - Modal de edição completa
   - Bulk edit (múltiplas configurações)
   - Confirmação de exclusão
   - Indicador de alterações não salvas
   - Toast notifications
   - Validação client-side

3. **Testes E2E CRUD** (Fase 6.3)
   - 15+ cenários de teste incluindo edição/exclusão
   - Validação de limites (min/max)
   - Confirmações e undo
   - Controle de acesso por role

4. **Controle de Acesso** (Fase 10.1 promovida para SHOULD HAVE)
   - Viewer: apenas leitura
   - Editor: edição e exclusão
   - Admin: todas as operações

---

**Próxima Ação Sugerida**: Começar pela **Fase 6.1 - Backend CRUD** (DIA 1) 🎨

---

## 📚 **LIÇÕES APRENDIDAS**

### **1. Importância de Pensar no CRUD Completo Desde o Início**

❌ **ERRO COMETIDO**: Implementamos apenas READ (visualização) sem pensar em CREATE, UPDATE, DELETE.

✅ **CORREÇÃO**: Sempre pensar no **CRUD completo** ao planejar funcionalidades:
- **C**reate: Como usuário cria novo registro?
- **R**ead: Como usuário visualiza dados?
- **U**pdate: Como usuário edita dados existentes?
- **D**elete: Como usuário remove dados?

### **2. Frontend Sem Backend CRUD = Sistema Incompleto**

Uma tela bonita de visualização **NÃO É SUFICIENTE** se o usuário não consegue:
- Corrigir erros de importação
- Ajustar valores manualmente
- Remover dados incorretos

### **3. Checklist de Funcionalidade Completa**

Ao implementar qualquer funcionalidade, validar:
- [ ] Backend tem endpoints CRUD completos?
- [ ] Frontend tem UI para todas as operações?
- [ ] Validações estão tanto no cliente quanto no servidor?
- [ ] Há controle de acesso (quem pode fazer o quê)?
- [ ] Há audit trail (quem fez, quando, o quê)?
- [ ] Há testes E2E para todos os fluxos?
- [ ] Há confirmações para ações destrutivas (delete)?
- [ ] Há possibilidade de desfazer (undo)?

### **4. Perguntas a Fazer Sempre**

Ao revisar um plano:
1. "E se o usuário quiser **editar** isso?"
2. "E se o usuário quiser **excluir** isso?"
3. "E se o usuário errar e quiser **desfazer**?"
4. "Quem pode fazer essa operação? (**controle de acesso**)"
5. "Como vamos **auditar** essa mudança?"

---

**Autor**: ProtecAI Engineering Team  
**Última Atualização**: 2025-11-03  
**Revisão**: Incluído CRUD completo após identificação da lacuna

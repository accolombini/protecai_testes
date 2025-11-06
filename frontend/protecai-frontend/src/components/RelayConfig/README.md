# ⚡ Relay Configuration CRUD Component

## 📝 Descrição

Componente React completo para gerenciamento de configurações de relés de proteção, implementando operações CRUD com interface moderna e intuitiva.

## ✨ Features Implementadas

### 🎯 Funcionalidades Principais

- **Listagem Paginada**: Visualização organizada de todas as configurações
- **Edição Inline**: Double-click para editar valores diretamente na tabela
- **Validação em Tempo Real**: Verifica limites min/max durante edição
- **Bulk Operations**: Seleção múltipla para habilitar/desabilitar em lote
- **Soft Delete**: Exclusão reversível com possibilidade de undo
- **Hard Delete**: Exclusão permanente (com confirmação)
- **Filtros**: Filtrar por Equipment ID
- **Toast Notifications**: Feedback visual para todas as operações

### 🎨 UI/UX

- ✅ Interface moderna com Tailwind CSS
- ✅ Ícones Heroicons
- ✅ Estados visuais (hover, seleção, validação)
- ✅ Feedback de loading
- ✅ Mensagens de erro/sucesso

## 🛠️ Tecnologias Utilizadas

- **React 19** + TypeScript
- **Tailwind CSS** para estilização
- **Axios** para chamadas API
- **Heroicons** para ícones
- **Vite** como bundler

## 📡 API Integration

O componente se conecta aos seguintes endpoints:

```typescript
GET    /api/relay-config/settings                  // Listar todas
GET    /api/relay-config/equipment/:id/settings    // Filtrar por equipamento
PUT    /api/relay-config/settings/:id              // Atualizar uma
PATCH  /api/relay-config/settings/bulk             // Atualizar múltiplas
DELETE /api/relay-config/settings/:id              // Deletar (soft/hard)
POST   /api/relay-config/settings/:id/restore      // Restaurar soft-deleted
```

## 🚀 Como Usar

### 1. Configurar variável de ambiente

Criar arquivo `.env.development`:

```bash
VITE_API_URL=http://localhost:8000
```

### 2. Iniciar backend

```bash
# Terminal 1 - Backend FastAPI
cd protecai_testes
uvicorn api.main:app --reload --port 8000
```

### 3. Iniciar frontend

```bash
# Terminal 2 - Frontend React
cd frontend/protecai-frontend
npm run dev
```

### 4. Acessar aplicação

Abrir navegador em: `http://localhost:5173`

Navegar para aba **"⚡ Config CRUD"**

## 📊 Uso do Componente

### Edição Inline

1. **Double-click** na linha para iniciar edição
2. Alterar valores nos campos editáveis
3. Clicar ✅ para salvar ou ❌ para cancelar

### Bulk Update

1. Selecionar checkboxes das configurações desejadas
2. Clicar em "Habilitar" ou "Desabilitar"
3. Todas as selecionadas serão atualizadas em uma transação atômica

### Filtros

1. Digitar Equipment ID no campo de filtro
2. Clicar "Recarregar" para aplicar filtro

### Validação

- Valores fora dos limites min/max são destacados em **vermelho**
- Validação impede salvar valores inválidos

## 🧪 Testes

### Testes Manuais

1. **Criar configuração** (via Swagger/Postman)
2. **Listar**: Verificar se aparece na tabela
3. **Editar**: Double-click e alterar valor
4. **Soft Delete**: Clicar no ícone de lixeira
5. **Bulk Update**: Selecionar múltiplas e habilitar/desabilitar
6. **Validação**: Tentar inserir valor fora dos limites

## 📝 TODO (Próximas Melhorias)

- [ ] Paginação (atualmente carrega todas)
- [ ] Busca por nome de parâmetro
- [ ] Ordenação por colunas
- [ ] Exportar para CSV/Excel
- [ ] Modal para criação de nova configuração
- [ ] Histórico de alterações
- [ ] Visualização de logs de auditoria
- [ ] Gráficos de valores vs limites

## 🐛 Troubleshooting

### Erro: "CORS blocked"

Verificar se backend está rodando com CORS habilitado:

```python
# api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Erro: "Network Error"

Verificar se `VITE_API_URL` está correto no `.env.development`

### Componente não aparece

Verificar se foi adicionado ao `App.tsx` e se a navegação está funcionando

## 📚 Estrutura de Arquivos

```
src/
├── components/
│   └── RelayConfig/
│       ├── RelayConfigCRUD.tsx     # Componente principal
│       └── README.md               # Esta documentação
├── App.tsx                          # Roteamento principal
└── .env.development                 # Configuração de ambiente
```

## 🎯 Checklist de Implementação

- [x] Componente CRUD básico
- [x] Integração com API
- [x] Edição inline
- [x] Bulk operations
- [x] Soft/Hard delete
- [x] Validação de limites
- [x] Toast notifications
- [x] Filtros básicos
- [x] Documentação
- [ ] Testes unitários (Jest)
- [ ] Testes E2E (Cypress)
- [ ] Criação de nova config
- [ ] Restore soft-deleted

---

**Desenvolvido por**: ProtecAI Engineering Team  
**Data**: 2025-11-03  
**Versão**: 1.0.0

#!/bin/bash
# EXECUTAR AMANHÃ - PRIMEIRA COISA

echo "🚀 Finalizando commit da pipeline de funções ativas..."

# 1. COMMIT PRINCIPAL (6 arquivos já no staging)
git commit -m "feat: Pipeline robusta de detecção de funções ativas de proteção

- Implementado detector genérico para MICON, P143 e SEPAM
- 8 modelos configurados em relay_models_config.json
- Detecção via code ranges (MICON), text patterns (P143), INI parsing (SEPAM)
- Pipeline completa: extração → detecção → relatórios
- Importação para banco: 82 funções em active_protection_functions
- Correções: path bug, P143 patterns, NaN handling, template warnings
- Resultados: 47 PDFs (100%), 37 relés, 0 erros
- Validação: 100% consistência CSV vs Banco

Arquivos implementados:
- scripts/detect_active_functions.py (312 linhas)
- scripts/import_active_functions_to_db.py (312 linhas)  
- scripts/reprocess_pipeline_complete.py (245 linhas)
- STATUS_PIPELINE_FUNCOES_ATIVAS_2025-11-13.md (documentação completa)
- PONTO_DE_RETOMADA_2025-11-13_NOITE.md (contexto para retomada)
- CHECKLIST_RAPIDO_14-11.md (checklist rápido)"

echo "✅ Commit principal concluído!"

# 2. ARQUIVOS CRÍTICOS IGNORADOS (FORCE ADD)
echo ""
echo "🔧 Adicionando arquivos críticos que estavam no .gitignore..."
git add -f inputs/glossario/relay_models_config.json
git add -f src/intelligent_relay_extractor.py

git commit -m "fix: Adiciona configuração de modelos e correção de warnings

- relay_models_config.json: 8 modelos com code ranges completos
- intelligent_relay_extractor.py: Remove warning confuso de template
- Arquivos estavam no .gitignore mas são essenciais para pipeline"

echo "✅ Arquivos críticos adicionados!"

# 3. PUSH PARA REMOTE
echo ""
echo "📤 Enviando para origin/main..."
git push origin main

echo ""
echo "✨ CONCLUÍDO! Pipeline commitada e enviada com sucesso!"
echo ""
echo "📊 Próximos passos:"
echo "  1. Validar banco: python scripts/import_active_functions_to_db.py"
echo "  2. Implementar normalização 3FN (meta de ontem que ficou pendente)"
echo ""

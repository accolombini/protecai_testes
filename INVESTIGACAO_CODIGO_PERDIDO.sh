#!/bin/bash
# ====================================================================
# INVESTIGAÇÃO FORENSE - CÓDIGO PERDIDO QUE FUNCIONAVA
# ====================================================================
# 
# SITUAÇÃO: 176 funções ativas no banco foram geradas por código ANTIGO
#           que foi PERDIDO/SUBSTITUÍDO pela pipeline atual
#
# OBJETIVO: Encontrar o código original que FUNCIONAVA
# ====================================================================

echo "🔍 INVESTIGAÇÃO FORENSE - CÓDIGO PERDIDO"
echo "========================================"
echo ""

# ========================
# 1. GIT HISTORY
# ========================
echo "📜 1. INVESTIGANDO GIT HISTORY"
echo "-----------------------------"
echo ""

echo "1.1 Últimos 50 commits:"
git log --oneline --graph --decorate -50

echo ""
echo "1.2 Commits relacionados a 'extract', 'checkbox', 'function':"
git log --all --grep="extract" --grep="checkbox" --grep="function" --oneline | head -20

echo ""
echo "1.3 Commits que modificaram precise_parameter_extractor.py:"
git log --oneline -- src/precise_parameter_extractor.py | head -20

echo ""
echo "1.4 Commits que modificaram universal_checkbox_detector.py:"
git log --oneline -- scripts/universal_checkbox_detector.py | head -20

echo ""
read -p "⏸️  Pressione ENTER para continuar..."

# ========================
# 2. BUSCAR ARQUIVOS BACKUP
# ========================
echo ""
echo "📁 2. BUSCANDO ARQUIVOS DE BACKUP"
echo "-----------------------------"
echo ""

echo "2.1 Arquivos com 'backup' no nome:"
find . -type f -name "*backup*" ! -path "./node_modules/*" ! -path "./.git/*" 2>/dev/null

echo ""
echo "2.2 Arquivos com extensão .bak, .old:"
find . -type f \( -name "*.bak" -o -name "*.old" \) ! -path "./node_modules/*" ! -path "./.git/*" 2>/dev/null

echo ""
echo "2.3 Pastas com backup no nome:"
find . -type d -name "*backup*" ! -path "./node_modules/*" ! -path "./.git/*" 2>/dev/null

echo ""
read -p "⏸️  Pressione ENTER para continuar..."

# ========================
# 3. BUSCAR SCRIPTS RELACIONADOS
# ========================
echo ""
echo "🔎 3. BUSCANDO SCRIPTS RELACIONADOS"
echo "-----------------------------"
echo ""

echo "3.1 Todos os scripts Python em scripts/:"
ls -lht scripts/*.py 2>/dev/null | head -20

echo ""
echo "3.2 Scripts com 'extract' no nome:"
find scripts/ -type f -name "*extract*.py" 2>/dev/null

echo ""
echo "3.3 Scripts com 'checkbox' no nome:"
find scripts/ -type f -name "*checkbox*.py" 2>/dev/null

echo ""
echo "3.4 Scripts com 'import' no nome:"
find scripts/ -type f -name "*import*.py" 2>/dev/null

echo ""
read -p "⏸️  Pressione ENTER para continuar..."

# ========================
# 4. ANALISAR BANCO DE DADOS
# ========================
echo ""
echo "🗄️  4. ANALISANDO BANCO DE DADOS"
echo "-----------------------------"
echo ""

echo "4.1 Total de funções ativas:"
psql -U postgres -d protecai_testes -c "
    SELECT COUNT(*) as funcoes_ativas 
    FROM relay_parameters 
    WHERE value IS NOT NULL AND value != '';
" 2>/dev/null

echo ""
echo "4.2 Data da última importação:"
psql -U postgres -d protecai_testes -c "
    SELECT 
        MAX(created_at) as ultima_importacao,
        COUNT(*) as total_registros
    FROM relay_parameters;
" 2>/dev/null

echo ""
echo "4.3 Primeiros 5 relés com funções ativas:"
psql -U postgres -d protecai_testes -c "
    SELECT 
        relay_id,
        COUNT(*) as parametros,
        COUNT(CASE WHEN value IS NOT NULL AND value != '' THEN 1 END) as com_valor
    FROM relay_parameters
    GROUP BY relay_id
    HAVING COUNT(CASE WHEN value IS NOT NULL AND value != '' THEN 1 END) > 0
    LIMIT 5;
" 2>/dev/null

echo ""
read -p "⏸️  Pressione ENTER para continuar..."

# ========================
# 5. VERIFICAR DOCUMENTAÇÃO
# ========================
echo ""
echo "📚 5. VERIFICANDO DOCUMENTAÇÃO"
echo "-----------------------------"
echo ""

echo "5.1 Documentos de status/retomada:"
ls -lht *STATUS*.md *RETOMADA*.md *PONTO*.md 2>/dev/null | head -10

echo ""
echo "5.2 Grep por 'universal_checkbox_detector' nos docs:"
grep -l "universal_checkbox_detector" *.md 2>/dev/null

echo ""
echo "5.3 Grep por '176' (funções ativas) nos docs:"
grep -l "176" *.md 2>/dev/null

echo ""
read -p "⏸️  Pressione ENTER para continuar..."

# ========================
# 6. COMPARAR CÓDIGOS
# ========================
echo ""
echo "🔬 6. COMPARANDO CÓDIGOS"
echo "-----------------------------"
echo ""

echo "6.1 Tamanho dos arquivos principais:"
echo "  precise_parameter_extractor.py:"
wc -l src/precise_parameter_extractor.py 2>/dev/null
echo "  universal_checkbox_detector.py:"
wc -l scripts/universal_checkbox_detector.py 2>/dev/null

echo ""
echo "6.2 Métodos em precise_parameter_extractor.py:"
grep -n "def " src/precise_parameter_extractor.py 2>/dev/null | head -20

echo ""
echo "6.3 Métodos em universal_checkbox_detector.py:"
grep -n "def " scripts/universal_checkbox_detector.py 2>/dev/null | head -20

echo ""
read -p "⏸️  Pressione ENTER para continuar..."

# ========================
# 7. VERIFICAR COMMITS ESPECÍFICOS
# ========================
echo ""
echo "🕐 7. COMMITS EM DATAS CRÍTICAS"
echo "-----------------------------"
echo ""

echo "7.1 Commits entre 01/11 e 08/11 (quando funcionava):"
git log --since="2025-11-01" --until="2025-11-09" --oneline --all

echo ""
echo "7.2 Commits entre 09/11 e 16/11 (quando quebrou):"
git log --since="2025-11-09" --until="2025-11-17" --oneline --all

echo ""
read -p "⏸️  Pressione ENTER para continuar..."

# ========================
# 8. BRANCHES E STASHES
# ========================
echo ""
echo "🌿 8. VERIFICANDO BRANCHES E STASHES"
echo "-----------------------------"
echo ""

echo "8.1 Todas as branches:"
git branch -a

echo ""
echo "8.2 Stashes (código temporário salvo):"
git stash list

echo ""
echo "8.3 Tags (versões marcadas):"
git tag -l

echo ""
read -p "⏸️  Pressione ENTER para continuar..."

# ========================
# 9. OUTPUTS E RESULTADOS
# ========================
echo ""
echo "📤 9. VERIFICANDO OUTPUTS GERADOS"
echo "-----------------------------"
echo ""

echo "9.1 Últimos arquivos modificados em outputs/:"
find outputs/ -type f -mtime -30 -exec ls -lht {} + 2>/dev/null | head -20

echo ""
echo "9.2 CSVs gerados recentemente:"
find outputs/ -type f -name "*.csv" -mtime -30 2>/dev/null | head -10

echo ""
echo "9.3 Checkboxes debug outputs:"
ls -lht outputs/checkbox_debug/ 2>/dev/null | head -10

echo ""
read -p "⏸️  Pressione ENTER para continuar..."

# ========================
# 10. RESUMO E RECOMENDAÇÕES
# ========================
echo ""
echo "📊 10. RESUMO DA INVESTIGAÇÃO"
echo "=============================="
echo ""

echo "✅ ARQUIVOS ENCONTRADOS:"
echo "  - universal_checkbox_detector.py (667 linhas) - VALIDADO 100%"
echo "  - precise_parameter_extractor.py (545 linhas) - ATUAL (quebrado)"
echo ""

echo "❓ PERGUNTAS CRÍTICAS:"
echo "  1. universal_checkbox_detector.py É o código que gerou os 176?"
echo "  2. Existe outro script mais antigo que foi deletado?"
echo "  3. Os commits de 08/11 têm o código funcionando?"
echo ""

echo "🎯 PRÓXIMOS PASSOS:"
echo "  1. Testar universal_checkbox_detector.py:"
echo "     python scripts/universal_checkbox_detector.py 'inputs/pdf/P122_204-PN-06_LADO_A_2014-08-01.pdf' 1"
echo ""
echo "  2. Se funcionar (detectar ~20-40 checkboxes):"
echo "     → ESTE é o código correto"
echo "     → Copiar para precise_parameter_extractor.py"
echo ""
echo "  3. Se NÃO funcionar:"
echo "     → Procurar em commits anteriores:"
echo "     → git show <commit_hash>:scripts/nome_arquivo.py"
echo ""
echo "  4. Verificar data da última importação no banco:"
echo "     → Se foi antes de 09/11, procurar código de 01-08/11"
echo ""

echo "🔧 COMANDOS ÚTEIS PARA INVESTIGAR:"
echo "  # Ver conteúdo de arquivo em commit específico:"
echo "  git show <hash>:src/precise_parameter_extractor.py"
echo ""
echo "  # Listar arquivos em commit específico:"
echo "  git ls-tree -r <hash> --name-only"
echo ""
echo "  # Ver diff entre dois commits:"
echo "  git diff <hash1> <hash2> -- src/precise_parameter_extractor.py"
echo ""
echo "  # Recuperar arquivo de commit antigo:"
echo "  git checkout <hash> -- src/precise_parameter_extractor.py"
echo ""

echo "======================================"
echo "✅ Investigação completa!"
echo "📋 Analise os resultados acima"
echo "🎯 Teste universal_checkbox_detector.py primeiro"
echo "======================================"

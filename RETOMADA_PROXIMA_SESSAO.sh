#!/bin/bash
# 🚀 SCRIPT DE RETOMADA - PROTECAI
# Executar este script para iniciar a próxima sessão de trabalho
# Data: 15 de Novembro de 2025
# Missão: Sistema de Relatórios

echo "========================================================================"
echo "🚀 PROTECAI - RETOMADA DE SESSÃO"
echo "========================================================================"
echo ""
echo "📅 Última sessão: 14/11/2025 - Detecção IEC Completa"
echo "🎯 Status: 50/50 relés mapeados, 176 funções ativas"
echo "⏭️  Próxima missão: SISTEMA DE RELATÓRIOS"
echo ""
echo "========================================================================"

# 1. VERIFICAR AMBIENTE
echo ""
echo "1️⃣  VERIFICANDO AMBIENTE..."
echo "----------------------------------------"

# Verificar diretório
if [ ! -d "/Users/accol/Library/Mobile Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes" ]; then
    echo "❌ Diretório do projeto não encontrado!"
    exit 1
fi

cd "/Users/accol/Library/Mobile Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes"
echo "✅ Diretório: $(pwd)"

# Verificar virtualenv
if [ ! -d "/Volumes/Mac_XIV/virtualenvs/protecai_testes" ]; then
    echo "❌ Virtualenv não encontrado!"
    exit 1
fi

echo "✅ Virtualenv: /Volumes/Mac_XIV/virtualenvs/protecai_testes"

# 2. ATIVAR VIRTUALENV
echo ""
echo "2️⃣  ATIVANDO VIRTUALENV..."
echo "----------------------------------------"
source /Volumes/Mac_XIV/virtualenvs/protecai_testes/bin/activate
echo "✅ Virtualenv ativado: $VIRTUAL_ENV"

# 3. VERIFICAR POSTGRESQL
echo ""
echo "3️⃣  VERIFICANDO POSTGRESQL..."
echo "----------------------------------------"

# Verificar se PostgreSQL está rodando
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "⚠️  PostgreSQL não está rodando. Iniciando..."
    brew services start postgresql@16
    sleep 3
    
    if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo "❌ Erro ao iniciar PostgreSQL!"
        exit 1
    fi
fi

echo "✅ PostgreSQL está rodando"

# 4. VALIDAR BANCO DE DADOS
echo ""
echo "4️⃣  VALIDANDO BANCO DE DADOS..."
echo "----------------------------------------"

python3 << 'PYTHON_VALIDATION'
import psycopg2
import sys

try:
    conn = psycopg2.connect(
        host='localhost',
        database='protecai_db',
        user='protecai',
        password='protecai'
    )
    cur = conn.cursor()
    
    # Verificar relés
    cur.execute('SELECT COUNT(*) FROM protec_ai.relay_equipment')
    relay_count = cur.fetchone()[0]
    print(f"✅ Relés no banco: {relay_count}")
    
    # Verificar configurações
    cur.execute('SELECT COUNT(*) FROM protec_ai.relay_settings')
    settings_count = cur.fetchone()[0]
    print(f"✅ Configurações: {settings_count:,}")
    
    # Verificar funções ativas
    cur.execute('SELECT COUNT(*) FROM active_protection_functions')
    functions_count = cur.fetchone()[0]
    print(f"✅ Funções ativas: {functions_count}")
    
    # Verificar relés com funções
    cur.execute('SELECT COUNT(DISTINCT relay_file) FROM active_protection_functions')
    relays_with_functions = cur.fetchone()[0]
    print(f"✅ Relés com funções: {relays_with_functions}/50")
    
    conn.close()
    
    # Validar resultados esperados
    if relay_count != 50:
        print(f"❌ ERRO: Esperado 50 relés, encontrado {relay_count}")
        sys.exit(1)
    
    if functions_count < 170:
        print(f"⚠️  AVISO: Funções abaixo do esperado ({functions_count} < 170)")
    
    if relays_with_functions != 50:
        print(f"❌ ERRO: Nem todos os relés têm funções ({relays_with_functions}/50)")
        sys.exit(1)
    
    print("\n🎉 BANCO DE DADOS VALIDADO COM SUCESSO!")
    
except Exception as e:
    print(f"❌ Erro ao validar banco: {e}")
    sys.exit(1)
PYTHON_VALIDATION

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ERRO NA VALIDAÇÃO DO BANCO DE DADOS!"
    exit 1
fi

# 5. VERIFICAR ARQUIVOS CRÍTICOS
echo ""
echo "5️⃣  VERIFICANDO ARQUIVOS CRÍTICOS..."
echo "----------------------------------------"

critical_files=(
    "scripts/normalize_to_3nf.py"
    "scripts/detect_iec_functions.py"
    "scripts/import_normalized_data_to_db.py"
    "api/main.py"
    "api/routers/active_functions.py"
    "frontend/protecai-frontend/src/components/ActiveFunctions.tsx"
)

for file in "${critical_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Arquivo não encontrado: $file"
        exit 1
    fi
done

echo "✅ Todos os arquivos críticos encontrados"

# 6. VERIFICAR CSVs NORMALIZADOS
echo ""
echo "6️⃣  VERIFICANDO CSVs NORMALIZADOS..."
echo "----------------------------------------"

csv_count=$(ls -1 outputs/norm_csv/*_normalized.csv 2>/dev/null | wc -l)
if [ $csv_count -lt 50 ]; then
    echo "⚠️  CSVs normalizados incompletos: $csv_count/50"
else
    echo "✅ CSVs normalizados: $csv_count"
fi

# 7. STATUS FINAL
echo ""
echo "========================================================================"
echo "✅ SISTEMA PRONTO PARA TRABALHO!"
echo "========================================================================"
echo ""
echo "📊 RESUMO DO SISTEMA:"
echo "  • 50 relés processados"
echo "  • 236.716 configurações importadas"
echo "  • 176 funções de proteção ativas"
echo "  • 14 códigos ANSI únicos"
echo "  • 9 modelos de relés"
echo ""
echo "🎯 PRÓXIMA MISSÃO: SISTEMA DE RELATÓRIOS"
echo ""
echo "📝 OBJETIVOS:"
echo "  1. Relatório de Configuração por Relé (PDF)"
echo "  2. Relatório Comparativo entre Relés"
echo "  3. Relatório de Auditoria e Conformidade"
echo "  4. Exportação para ETAP (.dta)"
echo ""
echo "========================================================================"
echo ""
echo "🚀 PARA INICIAR OS SERVIÇOS:"
echo ""
echo "Terminal 1 - Backend API:"
echo "  cd api && uvicorn main:app --reload --port 8000"
echo ""
echo "Terminal 2 - Frontend React:"
echo "  cd frontend/protecai-frontend && npm start"
echo ""
echo "Terminal 3 - Desenvolvimento:"
echo "  # Use este terminal para scripts e comandos"
echo ""
echo "========================================================================"
echo ""
echo "📚 DOCUMENTAÇÃO:"
echo "  • STATUS_SESSAO_2025-11-14_DETECCAO_IEC.md"
echo "  • Logs: outputs/logs/"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Dashboard: http://localhost:3000"
echo ""
echo "========================================================================"
echo "✅ RETOMADA CONCLUÍDA - BOA SESSÃO!"
echo "========================================================================"

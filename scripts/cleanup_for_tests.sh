#!/bin/bash
# =====================================================
# ProtecAI System - Script de Limpeza Completa
# =====================================================
# OBJETIVO: Resetar sistema para novos testes mantendo arquivos base
# EXECUÇÃO: ./scripts/cleanup_for_tests.sh
# CUIDADO: Remove dados processados e registros do banco

echo "🧹 ProtecAI - Iniciando Limpeza Completa do Sistema"
echo "⚠️  ATENÇÃO: Este script remove dados processados e registros do banco"
echo ""

# Definir caminhos base
BASE_DIR="/Users/accol/Library/Mobile Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes"
INPUTS_DIR="$BASE_DIR/inputs"
OUTPUTS_DIR="$BASE_DIR/outputs"
REGISTRY_FILE="$INPUTS_DIR/registry/processed_files.json"

echo "📁 Base Directory: $BASE_DIR"
echo ""

# 1. LIMPAR REGISTRY DE ARQUIVOS PROCESSADOS
echo "1️⃣ Limpando Registry de Arquivos Processados..."
if [ -f "$REGISTRY_FILE" ]; then
    echo "   ✅ Backup do registry atual: processed_files_backup_$(date +%Y%m%d_%H%M%S).json"
    cp "$REGISTRY_FILE" "$INPUTS_DIR/registry/processed_files_backup_$(date +%Y%m%d_%H%M%S).json"
    
    echo "   🗑️  Resetando processed_files.json"
    echo "{}" > "$REGISTRY_FILE"
    echo "   ✅ Registry limpo: $REGISTRY_FILE"
else
    echo "   ⚠️  Registry não encontrado, criando novo"
    mkdir -p "$INPUTS_DIR/registry"
    echo "{}" > "$REGISTRY_FILE"
fi
echo ""

# 2. LIMPAR OUTPUTS GERADOS
echo "2️⃣ Limpando Outputs Processados..."
if [ -d "$OUTPUTS_DIR" ]; then
    # Backup de logs importantes
    if [ -d "$OUTPUTS_DIR/logs" ]; then
        echo "   📋 Backup de logs: logs_backup_$(date +%Y%m%d_%H%M%S)/"
        cp -r "$OUTPUTS_DIR/logs" "$OUTPUTS_DIR/logs_backup_$(date +%Y%m%d_%H%M%S)/"
    fi
    
    # Limpar CSVs processados
    if [ -d "$OUTPUTS_DIR/csv" ]; then
        echo "   🗑️  Removendo CSVs processados"
        rm -f "$OUTPUTS_DIR/csv"/*.csv
        echo "   ✅ CSVs removidos: $OUTPUTS_DIR/csv/"
    fi
    
    # Limpar Excel processados
    if [ -d "$OUTPUTS_DIR/excel" ]; then
        echo "   🗑️  Removendo Excel processados"
        rm -f "$OUTPUTS_DIR/excel"/*.xlsx
        echo "   ✅ Excel removidos: $OUTPUTS_DIR/excel/"
    fi
    
    # Limpar outros outputs
    if [ -d "$OUTPUTS_DIR/norm_csv" ]; then
        echo "   🗑️  Removendo CSVs normalizados"
        rm -f "$OUTPUTS_DIR/norm_csv"/*.csv
        echo "   ✅ CSVs normalizados removidos"
    fi
    
    if [ -d "$OUTPUTS_DIR/norm_excel" ]; then
        echo "   🗑️  Removendo Excel normalizados"
        rm -f "$OUTPUTS_DIR/norm_excel"/*.xlsx
        echo "   ✅ Excel normalizados removidos"
    fi
else
    echo "   ⚠️  Diretório outputs não encontrado"
fi
echo ""

# 3. LIMPAR BANCO POSTGRESQL (Configurações de Relés)
echo "3️⃣ Limpando Banco PostgreSQL..."
echo "   🔗 Conectando ao PostgreSQL local..."

# Comando SQL para limpar tabelas de configurações (preservar ML Gateway)
SQL_CLEANUP="
-- Backup timestamp
SELECT 'CLEANUP STARTED AT: ' || NOW() as cleanup_start;

-- Limpar tabelas de configurações de relés (manter ML Gateway)
DELETE FROM io_configurations WHERE equipment_id IN (SELECT id FROM equipments);
DELETE FROM protection_functions WHERE equipment_id IN (SELECT id FROM equipments);
DELETE FROM electrical_configurations WHERE equipment_id IN (SELECT id FROM equipments);
DELETE FROM equipments;

-- Verificar limpeza
SELECT 'EQUIPMENTS REMAINING: ' || COUNT(*) FROM equipments;
SELECT 'ELECTRICAL_CONFIGS REMAINING: ' || COUNT(*) FROM electrical_configurations;
SELECT 'PROTECTION_FUNCTIONS REMAINING: ' || COUNT(*) FROM protection_functions;
SELECT 'IO_CONFIGURATIONS REMAINING: ' || COUNT(*) FROM io_configurations;

-- ML Gateway preservado
SELECT 'ML_JOBS PRESERVED: ' || COUNT(*) FROM ml_gateway.ml_jobs;
SELECT 'ML_DATA_SOURCES PRESERVED: ' || COUNT(*) FROM ml_gateway.ml_data_sources;

SELECT 'CLEANUP COMPLETED AT: ' || NOW() as cleanup_end;
"

# Executar limpeza do banco
if command -v psql &> /dev/null; then
    echo "   🗑️  Executando limpeza das tabelas de configurações..."
    echo "$SQL_CLEANUP" | psql -h localhost -d protecai_db -U postgres 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ Banco PostgreSQL limpo com sucesso"
    else
        echo "   ⚠️  Erro na limpeza do banco - verifique conexão PostgreSQL"
    fi
else
    echo "   ⚠️  psql não encontrado - pule limpeza do banco manualmente"
fi
echo ""

# 4. VERIFICAR ARQUIVOS BASE MANTIDOS
echo "4️⃣ Verificando Arquivos Base Mantidos..."
echo "   📁 Arquivos em inputs/pdf/:"
ls -la "$INPUTS_DIR/pdf/" 2>/dev/null || echo "   ⚠️  Diretório pdf não encontrado"
echo "   📁 Arquivos em inputs/csv/:"
ls -la "$INPUTS_DIR/csv/" 2>/dev/null || echo "   ⚠️  Diretório csv não encontrado"
echo "   📁 Arquivos em inputs/xlsx/:"
ls -la "$INPUTS_DIR/xlsx/" 2>/dev/null || echo "   ⚠️  Diretório xlsx não encontrado"
echo ""

# 5. RESUMO DA LIMPEZA
echo "✅ LIMPEZA COMPLETA FINALIZADA!"
echo ""
echo "📋 RESUMO:"
echo "   ✅ Registry resetado (backup criado)"
echo "   ✅ Outputs processados removidos (logs preservados)"
echo "   ✅ Banco PostgreSQL limpo (ML Gateway preservado)"
echo "   ✅ Arquivos base mantidos em /inputs/"
echo ""
echo "🎯 SISTEMA PRONTO PARA NOVOS TESTES!"
echo "   - TELA1.pdf e TELA3.pdf prontos para reprocessamento"
echo "   - Upload frontend pode processar arquivos novamente"
echo "   - Pipeline completo disponível para execução"
echo ""
echo "🚀 PRÓXIMOS PASSOS:"
echo "   1. Testar upload via frontend (localhost:5174)"
echo "   2. Verificar processamento real dos arquivos"
echo "   3. Validar gravação no PostgreSQL"
echo ""
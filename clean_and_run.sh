#!/bin/bash
# SCRIPT DE LIMPEZA E EXECUÇÃO COMPLETA DA PIPELINE
# ==================================================

set -e  # Parar em caso de erro

echo "========================================================================"
echo "🧹 LIMPEZA COMPLETA - BANCO DE DADOS E OUTPUTS"
echo "========================================================================"

# 1. Limpar banco de dados
echo ""
echo "🗄️  Limpando banco de dados PostgreSQL..."
docker exec postgres-protecai psql -U protecai -d protecai_db -c "
  -- Desabilitar foreign key checks temporariamente
  SET session_replication_role = 'replica';
  
  -- Limpar tabelas principais na ordem correta
  TRUNCATE TABLE protec_ai.relay_settings RESTART IDENTITY CASCADE;
  TRUNCATE TABLE protec_ai.active_protection_functions RESTART IDENTITY CASCADE;
  TRUNCATE TABLE protec_ai.relay_equipment RESTART IDENTITY CASCADE;
  TRUNCATE TABLE protec_ai.relay_models RESTART IDENTITY CASCADE;
  TRUNCATE TABLE protec_ai.fabricantes RESTART IDENTITY CASCADE;
  TRUNCATE TABLE protec_ai.units RESTART IDENTITY CASCADE;
  TRUNCATE TABLE protec_ai.protection_functions RESTART IDENTITY CASCADE;
  
  -- Re-habilitar foreign key checks
  SET session_replication_role = 'origin';
"
echo "✅ Banco de dados limpo!"

# 2. Limpar pastas de output
echo ""
echo "📁 Limpando pastas de output..."

# Limpar CSV
if [ -d "outputs/csv" ]; then
    rm -f outputs/csv/*.csv
    echo "   ✓ outputs/csv/ limpa"
fi

# Limpar Excel
if [ -d "outputs/excel" ]; then
    rm -f outputs/excel/*.xlsx
    echo "   ✓ outputs/excel/ limpa"
fi

# Limpar norm_csv
if [ -d "outputs/norm_csv" ]; then
    rm -f outputs/norm_csv/*.csv
    echo "   ✓ outputs/norm_csv/ limpa"
fi

# Limpar norm_excel
if [ -d "outputs/norm_excel" ]; then
    rm -f outputs/norm_excel/*.xlsx
    echo "   ✓ outputs/norm_excel/ limpa"
fi

# Limpar audit
if [ -d "outputs/audit" ]; then
    rm -f outputs/audit/*
    echo "   ✓ outputs/audit/ limpa"
fi

# Limpar atrib_limpos
if [ -d "outputs/atrib_limpos" ]; then
    rm -f outputs/atrib_limpos/*
    echo "   ✓ outputs/atrib_limpos/ limpa"
fi

# Limpar checkbox_analysis
if [ -d "outputs/checkbox_analysis" ]; then
    rm -f outputs/checkbox_analysis/*
    echo "   ✓ outputs/checkbox_analysis/ limpa"
fi

echo ""
echo "========================================================================"
echo "🚀 EXECUTANDO PIPELINE COMPLETA"
echo "========================================================================"
echo ""

# 3. Executar pipeline completa
source /Volumes/Mac_XIV/virtualenvs/protecai_testes/bin/activate
python run_complete_pipeline.py

echo ""
echo "========================================================================"
echo "✅ PROCESSO COMPLETO FINALIZADO!"
echo "========================================================================"

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
docker exec postgres-protecai psql -U protecai -d protecai_db -c \
  "TRUNCATE TABLE protec_ai.equipments, protec_ai.parameters, protec_ai.parameter_values RESTART IDENTITY CASCADE;"
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

#!/bin/bash
# ========================================================================
# Script de Validação COMPLETA - 11 Relatórios × 3 Formatos = 33 testes
# Data: 2025-11-16
# Objetivo: Validar nomenclatura "Bay" → "Barra" em TODOS os relatórios
# ========================================================================

set -euo pipefail

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Contadores
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Diretório de output
OUTPUT_DIR="/tmp/test_reports_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}  TESTE COMPLETO DE RELATÓRIOS - ProtecAI PETROBRAS${NC}"
echo -e "${BLUE}  11 Tipos de Relatórios × 3 Formatos = 33 Arquivos${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""
echo -e "${YELLOW}📁 Diretório de output: $OUTPUT_DIR${NC}"
echo ""

# Função para testar um relatório
test_report() {
    local TIPO="$1"
    local FORMATO="$2"
    local URL="$3"
    local DESCRICAO="$4"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    local FILENAME="${OUTPUT_DIR}/${TIPO}_${FORMATO}.${FORMATO}"
    local FORMATO_UPPER=$(echo "$FORMATO" | tr '[:lower:]' '[:upper:]')
    
    echo -ne "${BLUE}[${TOTAL_TESTS}/33]${NC} Testando ${DESCRICAO} (${FORMATO_UPPER})... "
    
    # Fazer requisição
    if curl -s -f "$URL" -o "$FILENAME" 2>/dev/null; then
        # Verificar se arquivo foi criado
        if [ -f "$FILENAME" ]; then
            local FILE_SIZE=$(stat -f%z "$FILENAME" 2>/dev/null || stat -c%s "$FILENAME" 2>/dev/null || echo "0")
            
            if [ "$FILE_SIZE" -gt 100 ]; then
                # Arquivo válido (> 100 bytes)
                local FILE_TYPE=$(file -b "$FILENAME" | cut -d',' -f1)
                
                # Validação específica por formato
                case "$FORMATO" in
                    pdf)
                        if echo "$FILE_TYPE" | grep -q "PDF"; then
                            echo -e "${GREEN}✅ OK${NC} (${FILE_SIZE} bytes, $FILE_TYPE)"
                            PASSED_TESTS=$((PASSED_TESTS + 1))
                            return 0
                        else
                            echo -e "${RED}❌ FALHOU${NC} (não é PDF válido: $FILE_TYPE)"
                            FAILED_TESTS=$((FAILED_TESTS + 1))
                            return 1
                        fi
                        ;;
                    xlsx)
                        if echo "$FILE_TYPE" | grep -qE "Microsoft Excel|Zip archive"; then
                            echo -e "${GREEN}✅ OK${NC} (${FILE_SIZE} bytes)"
                            PASSED_TESTS=$((PASSED_TESTS + 1))
                            return 0
                        else
                            echo -e "${RED}❌ FALHOU${NC} (não é XLSX válido: $FILE_TYPE)"
                            FAILED_TESTS=$((FAILED_TESTS + 1))
                            return 1
                        fi
                        ;;
                    csv)
                        if echo "$FILE_TYPE" | grep -qE "CSV|ASCII text|UTF-8"; then
                            echo -e "${GREEN}✅ OK${NC} (${FILE_SIZE} bytes)"
                            PASSED_TESTS=$((PASSED_TESTS + 1))
                            return 0
                        else
                            echo -e "${RED}❌ FALHOU${NC} (não é CSV válido: $FILE_TYPE)"
                            FAILED_TESTS=$((FAILED_TESTS + 1))
                            return 1
                        fi
                        ;;
                esac
            else
                echo -e "${RED}❌ FALHOU${NC} (arquivo muito pequeno: ${FILE_SIZE} bytes)"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                return 1
            fi
        else
            echo -e "${RED}❌ FALHOU${NC} (arquivo não criado)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    else
        echo -e "${RED}❌ FALHOU${NC} (erro HTTP ou timeout)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  PARTE 1: RELATÓRIOS BÁSICOS (5 tipos × 3 formatos = 15 testes)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. OVERVIEW (Visão Geral) - sem parâmetros
BASE_URL="http://localhost:8000/api/v1/reports/export"
test_report "01_overview" "pdf" "${BASE_URL}/pdf" "Visão Geral"
test_report "01_overview" "xlsx" "${BASE_URL}/xlsx" "Visão Geral"
test_report "01_overview" "csv" "${BASE_URL}/csv" "Visão Geral"

# 2. ALL RELAYS (Todos os Relés) - tenta buscar todos
test_report "02_all_relays" "pdf" "${BASE_URL}/pdf" "Todos os Relés"
test_report "02_all_relays" "xlsx" "${BASE_URL}/xlsx" "Todos os Relés"
test_report "02_all_relays" "csv" "${BASE_URL}/csv" "Todos os Relés"

# 3. BY MANUFACTURER (Por Fabricante) - filtro: manufacturer=Schneider
test_report "03_by_manufacturer" "pdf" "${BASE_URL}/pdf?manufacturer=Schneider" "Por Fabricante (Schneider)"
test_report "03_by_manufacturer" "xlsx" "${BASE_URL}/xlsx?manufacturer=Schneider" "Por Fabricante (Schneider)"
test_report "03_by_manufacturer" "csv" "${BASE_URL}/csv?manufacturer=Schneider" "Por Fabricante (Schneider)"

# 4. BY STATUS (Por Status) - filtro: status=ACTIVE
test_report "04_by_status" "pdf" "${BASE_URL}/pdf?status=ACTIVE" "Por Status (Ativo)"
test_report "04_by_status" "xlsx" "${BASE_URL}/xlsx?status=ACTIVE" "Por Status (Ativo)"
test_report "04_by_status" "csv" "${BASE_URL}/csv?status=ACTIVE" "Por Status (Ativo)"

# 5. CUSTOM (Personalizado) - filtros combinados
test_report "05_custom" "pdf" "${BASE_URL}/pdf?manufacturer=Schneider&status=ACTIVE" "Personalizado (Multi-filtro)"
test_report "05_custom" "xlsx" "${BASE_URL}/xlsx?manufacturer=Schneider&status=ACTIVE" "Personalizado (Multi-filtro)"
test_report "05_custom" "csv" "${BASE_URL}/csv?manufacturer=Schneider&status=ACTIVE" "Personalizado (Multi-filtro)"

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  PARTE 2: RELATÓRIOS TÉCNICOS (6 tipos × 3 formatos = 18 testes)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 6. PROTECTION FUNCTIONS (Funções de Proteção)
BASE_URL_TECH="http://localhost:8000/api/v1/reports"
test_report "06_protection" "pdf" "${BASE_URL_TECH}/protection-functions/export/pdf" "Funções de Proteção"
test_report "06_protection" "xlsx" "${BASE_URL_TECH}/protection-functions/export/xlsx" "Funções de Proteção"
test_report "06_protection" "csv" "${BASE_URL_TECH}/protection-functions/export/csv" "Funções de Proteção"

# 7. SETPOINTS (Setpoints Críticos)
test_report "07_setpoints" "pdf" "${BASE_URL_TECH}/setpoints/export/pdf" "Setpoints Críticos"
test_report "07_setpoints" "xlsx" "${BASE_URL_TECH}/setpoints/export/xlsx" "Setpoints Críticos"
test_report "07_setpoints" "csv" "${BASE_URL_TECH}/setpoints/export/csv" "Setpoints Críticos"

# 8. COORDINATION (Coordenação)
test_report "08_coordination" "pdf" "${BASE_URL_TECH}/coordination/export/pdf" "Coordenação"
test_report "08_coordination" "xlsx" "${BASE_URL_TECH}/coordination/export/xlsx" "Coordenação"
test_report "08_coordination" "csv" "${BASE_URL_TECH}/coordination/export/csv" "Coordenação"

# 9. BY BAY (Por Barra/Subestação) ← CRÍTICO para validar "Barra"
test_report "09_by_bay" "pdf" "${BASE_URL_TECH}/by-bay/export/pdf" "Por Barra/Subestação"
test_report "09_by_bay" "xlsx" "${BASE_URL_TECH}/by-bay/export/xlsx" "Por Barra/Subestação"
test_report "09_by_bay" "csv" "${BASE_URL_TECH}/by-bay/export/csv" "Por Barra/Subestação"

# 10. MAINTENANCE (Manutenção)
test_report "10_maintenance" "pdf" "${BASE_URL_TECH}/maintenance/export/pdf" "Manutenção"
test_report "10_maintenance" "xlsx" "${BASE_URL_TECH}/maintenance/export/xlsx" "Manutenção"
test_report "10_maintenance" "csv" "${BASE_URL_TECH}/maintenance/export/csv" "Manutenção"

# 11. EXECUTIVE (Executivo)
test_report "11_executive" "pdf" "${BASE_URL_TECH}/executive/export/pdf" "Executivo"
test_report "11_executive" "xlsx" "${BASE_URL_TECH}/executive/export/xlsx" "Executivo"
test_report "11_executive" "csv" "${BASE_URL_TECH}/executive/export/csv" "Executivo"

# ========================================================================
# PARTE 3: VALIDAÇÃO DE CONTEÚDO PDF - Buscar "Bay" hardcoded
# ========================================================================
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  PARTE 3: VALIDAÇÃO DE CONTEÚDO PDF (11 PDFs)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

PDF_WITH_BAY=()
PDF_VALIDATED=0

for pdf_file in "$OUTPUT_DIR"/*_pdf.pdf; do
    if [ -f "$pdf_file" ]; then
        BASENAME=$(basename "$pdf_file")
        echo -ne "🔍 Validando $BASENAME... "
        
        # Extrair texto e buscar "Bay" (case-insensitive, excluindo "Bay/Barra" que é aceitável)
        if pdftotext "$pdf_file" - 2>/dev/null | grep -iE "\bBay\b" | grep -v "Bay/Barra" >/dev/null 2>&1; then
            echo -e "${RED}❌ ENCONTROU 'Bay' hardcoded${NC}"
            PDF_WITH_BAY+=("$BASENAME")
        else
            echo -e "${GREEN}✅ OK - Apenas 'Barra'${NC}"
            PDF_VALIDATED=$((PDF_VALIDATED + 1))
        fi
    fi
done

# ========================================================================
# RESUMO FINAL
# ========================================================================
echo ""
echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}  RESUMO DA VALIDAÇÃO${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""
echo -e "Total de testes executados: ${BLUE}${TOTAL_TESTS}/33${NC}"
echo -e "Testes bem-sucedidos:       ${GREEN}${PASSED_TESTS}${NC}"
echo -e "Testes falhados:            ${RED}${FAILED_TESTS}${NC}"
echo ""
echo -e "PDFs validados (conteúdo):  ${GREEN}${PDF_VALIDATED}/11${NC}"

if [ ${#PDF_WITH_BAY[@]} -gt 0 ]; then
    echo -e "PDFs com 'Bay' hardcoded:   ${RED}${#PDF_WITH_BAY[@]}${NC}"
    echo ""
    echo -e "${RED}⚠️  ATENÇÃO: Encontrado 'Bay' hardcoded nos seguintes PDFs:${NC}"
    for pdf in "${PDF_WITH_BAY[@]}"; do
        echo -e "   ${RED}→${NC} $pdf"
    done
else
    echo -e "PDFs com 'Bay' hardcoded:   ${GREEN}0${NC}"
fi

echo ""
echo -e "${BLUE}========================================================================${NC}"

if [ $FAILED_TESTS -eq 0 ] && [ ${#PDF_WITH_BAY[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ VALIDAÇÃO 100% COMPLETA - Todos os relatórios OK!${NC}"
    EXIT_CODE=0
else
    echo -e "${RED}❌ VALIDAÇÃO INCOMPLETA - Verificar erros acima${NC}"
    EXIT_CODE=1
fi

echo -e "${BLUE}========================================================================${NC}"
echo ""
echo -e "📁 Arquivos salvos em: ${YELLOW}${OUTPUT_DIR}${NC}"
echo ""

exit $EXIT_CODE

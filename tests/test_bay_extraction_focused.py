#!/usr/bin/env python3
"""
🔬 TESTE FOCADO - Validação de Extração de Bay Name
====================================================

Testa a correção do regex para extração de bay_name dos arquivos problemáticos
que retornavam "Unknown" (20% dos dados).

OBJETIVO: Validar correção antes de reprocessar todos os 50 equipamentos.

Arquivo alvo: P122_204-MF-2B1_2014-07-28_params.csv
Problema: bay_name = "Unknown" (deveria ser "204-MF-2B1")
"""

import re
import sys
from pathlib import Path

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def extract_bay_old_regex(filename: str) -> str:
    """Regex ANTIGO que causava Unknown"""
    bay_match = re.search(r'(\d{2,3}-[A-Z]{2}-\d{2}[A-Z]?)', filename)
    return bay_match.group(1) if bay_match else "Unknown"

def extract_bay_new_regex(filename: str) -> str:
    """Regex NOVO corrigido"""
    bay_match = re.search(r'(\d{2,3}-[A-Z]{2,3}-[A-Z0-9]{1,4})', filename)
    return bay_match.group(1) if bay_match else "Unknown"

def main():
    print_header("🔬 TESTE DE VALIDAÇÃO - BAY NAME EXTRACTION")
    
    # Casos de teste (arquivos reais com Unknown)
    test_cases = [
        "P122_204-MF-2B1_2014-07-28_params.csv",
        "P122_204-PN-04_2014-08-02_params.csv",
        "P122_204-PN-05_2014-08-09_params.csv",
        "P122_204-PN-06_LADO_A_2014-08-01_params.csv",
        "P122_204-PN-06_LADO_B_2014-08-09_params.csv",
        "P122_52-MF-02A_2021-03-08_params.csv",
        "P122_52-MF-03A1_2021-03-11_params.csv",
        "00-MF-12_2016-03-31_params.csv",
        "00-MF-14_2016-03-31_params.csv",
        "00-MF-24_2024-09-10_params.csv",
    ]
    
    print(f"{Colors.BOLD}Testando {len(test_cases)} arquivos que retornavam 'Unknown'...{Colors.END}\n")
    
    passed = 0
    failed = 0
    
    for i, filename in enumerate(test_cases, 1):
        print(f"{Colors.BOLD}[{i}/{len(test_cases)}] {filename}{Colors.END}")
        
        old_result = extract_bay_old_regex(filename)
        new_result = extract_bay_new_regex(filename)
        
        print(f"  📊 Regex ANTIGO: {Colors.RED if old_result == 'Unknown' else Colors.GREEN}{old_result}{Colors.END}")
        print(f"  📊 Regex NOVO:   {Colors.GREEN if new_result != 'Unknown' else Colors.RED}{new_result}{Colors.END}")
        
        if new_result != "Unknown" and old_result == "Unknown":
            print_success(f"CORRIGIDO! {old_result} → {new_result}")
            passed += 1
        elif new_result == "Unknown":
            print_error(f"AINDA COM PROBLEMA! Permanece: {new_result}")
            failed += 1
        else:
            print_warning(f"Já estava OK: {new_result}")
            passed += 1
        
        print()
    
    # Resumo final
    print_header("📊 RESUMO DOS TESTES")
    print(f"Total testado: {len(test_cases)}")
    print(f"{Colors.GREEN}✅ Passed: {passed}{Colors.END}")
    print(f"{Colors.RED}❌ Failed: {failed}{Colors.END}")
    
    success_rate = (passed / len(test_cases)) * 100
    print(f"\n{Colors.BOLD}Taxa de sucesso: {success_rate:.1f}%{Colors.END}")
    
    if failed == 0:
        print_success("\n🎉 TODOS OS TESTES PASSARAM! Regex corrigido com sucesso!")
        print_success("✅ Pode prosseguir com o reprocessamento dos dados.")
        return 0
    else:
        print_error(f"\n⚠️  {failed} teste(s) ainda com problema(s)!")
        print_error("❌ NÃO reprocessar dados ainda. Corrija o regex primeiro.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

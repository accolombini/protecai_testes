#!/usr/bin/env python3
"""
Script para corrigir enums ML nos services
"""

import re
import os

def fix_enums_in_file(file_path):
    """Corrige enums em um arquivo específico"""
    if not os.path.exists(file_path):
        print(f"Arquivo não encontrado: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substituições
    original_content = content
    
    # JobStatus -> MLJobStatus
    content = re.sub(r'\bJobStatus\.', 'MLJobStatus.', content)
    content = re.sub(r'\bJobStatus\(', 'MLJobStatus(', content)
    
    # AnalysisType -> MLAnalysisType
    content = re.sub(r'\bAnalysisType\(', 'MLAnalysisType(', content)
    
    # ResultType -> MLResultType (se existir)
    content = re.sub(r'\bResultType\.', 'MLResultType.', content)
    content = re.sub(r'\bResultType\(', 'MLResultType(', content)
    
    # RecommendationType -> MLRecommendationType
    content = re.sub(r'\bRecommendationType\.', 'MLRecommendationType.', content)
    content = re.sub(r'\bRecommendationType\(', 'MLRecommendationType(', content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Corrigido: {file_path}")
    else:
        print(f"ℹ️  Sem alterações: {file_path}")

def main():
    """Corrige todos os arquivos ML services"""
    base_path = "/Users/accol/Library/Mobile Documents/com~apple~CloudDocs/UNIVERSIDADES/UFF/PROJETOS/PETROBRAS/PETRO_ProtecAI/protecai_testes"
    
    files_to_fix = [
        f"{base_path}/api/services/ml_integration_service.py",
        f"{base_path}/api/services/ml_data_service.py", 
        f"{base_path}/api/services/ml_results_service.py",
        f"{base_path}/api/routers/ml_gateway.py"
    ]
    
    print("🔧 Iniciando correção de enums ML...")
    
    for file_path in files_to_fix:
        fix_enums_in_file(file_path)
    
    print("🎉 Correção concluída!")

if __name__ == "__main__":
    main()
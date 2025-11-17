#!/usr/bin/env python3
"""
Detector GENÉRICO e ROBUSTO de funções de proteção ativas.
Funciona para QUALQUER modelo de relé seguindo relay_models_config.json.

Autor: Sistema ProtecAI
Data: 2025-11-13
"""

import json
import pandas as pd
import configparser
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

CONFIG_PATH = Path(__file__).parent.parent / "inputs" / "glossario" / "relay_models_config.json"


def load_relay_config() -> Dict:
    """Carrega configuração dos modelos de relés."""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def identify_relay_model(file_path: Path, config: Dict) -> Optional[str]:
    """
    Identifica o modelo do relé baseado no nome do arquivo.
    
    Args:
        file_path: Caminho do arquivo
        config: Configuração dos modelos
        
    Returns:
        Nome do modelo ou None se não identificado
    """
    filename = file_path.stem.upper()
    
    # Mapeamento de padrões de identificação (ordem importa - mais específico primeiro)
    patterns = {
        'MICON_P122_205': ['P122_205', 'P122-205', 'P_122_205'],
        'MICON_P122_52': ['P122_52', 'P122-52', 'P_122_52', 'P122 52', 'P_122 52'],
        'MICON_P122_204': ['P122_204', 'P122-204', 'P_122_204'],
        'MICON_P143': ['P143', 'P_143'],
        'MICON_P220': ['P220', 'P_220'],
        'MICON_P922': ['P922', 'P_922', 'P922S'],
        'MICON_P241': ['P241', 'P_241'],
        'SEPAM_S40': ['.S40', 'MF-']  # SEPAM por último para evitar falsos positivos
    }
    
    # Verifica extensão e nome
    file_ext = file_path.suffix.upper()
    
    # Prioridade para extensão .S40 (SEPAM)
    if file_ext == '.S40':
        return 'SEPAM_S40' if 'SEPAM_S40' in config['models'] else None
    
    # Para outros casos, busca padrões no nome
    for model_name, model_patterns in patterns.items():
        if model_name == 'SEPAM_S40':  # Já tratado acima
            continue
        for pattern in model_patterns:
            if pattern in filename:
                # Valida se o modelo existe na configuração
                if model_name in config['models']:
                    return model_name
    
    return None


def detect_micon_functions(csv_path: Path, model_config: Dict) -> Set[str]:
    """
    Detecta funções ativas em relés MICON Easergy.
    
    Para Easergy, a presença de campos "Function X>" no CSV indica que
    a função está HABILITADA, independente do valor estar vazio.
    
    Args:
        csv_path: Caminho do CSV com parâmetros
        model_config: Configuração específica do modelo
        
    Returns:
        Set com códigos ANSI das funções ativas
    """
    active_functions = set()
    
    # Carrega CSV de parâmetros
    df = pd.read_csv(csv_path)
    
    # Normaliza nomes de colunas
    df.columns = df.columns.str.lower()
    
    # Identifica colunas
    code_col = 'code' if 'code' in df.columns else 'param_code'
    desc_col = 'description' if 'description' in df.columns else 'param_description'
    
    if code_col not in df.columns:
        return active_functions
    
    # Para cada função configurada no modelo
    for function, func_config in model_config['functions'].items():
        code_range = func_config['code_range']
        start_code = code_range[0]
        end_code = code_range[1]
        
        # Procura por qualquer parâmetro neste range de código
        # Se existe ao menos um campo "Function X>" neste range, a função está ativa
        for _, row in df.iterrows():
            param_code = str(row[code_col]).upper().strip()
            
            # Extrai código hex
            code_match = re.search(r'\b([0-9A-F]{4})\b', param_code)
            if not code_match:
                continue
            
            code_value = code_match.group(1)
            
            # Verifica se está no range desta função
            if start_code <= code_value <= end_code:
                # Para Easergy, verifica se é um campo "Function"
                if desc_col in df.columns:
                    description = str(row[desc_col]).lower()
                    if 'function' in description:
                        # Encontrou campo de função neste range, marca como ativa
                        active_functions.add(function)
                        break
                else:
                    # Fallback: qualquer código no range indica função ativa
                    active_functions.add(function)
                    break
    
    return active_functions


def detect_p143_functions(pdf_path: Path, model_config: Dict) -> Set[str]:
    """
    Detecta funções ativas em relés MICON P143.
    No P143, padrão é: "35.23: I>1 Function:" seguido de valor na próxima linha.
    - Se valor = "Disabled" → função INATIVA
    - Se valor = qualquer outro (DT, IEC E Inverse, etc.) → função ATIVA
    
    Args:
        pdf_path: Caminho do arquivo PDF
        model_config: Configuração específica do modelo
        
    Returns:
        Set com códigos ANSI das funções ativas
    """
    active_functions = set()
    
    # Extrai texto do PDF
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text = ''
        for page in doc:
            text += page.get_text()
        doc.close()
        
        lines = text.split('\n')
        
        # Para cada função, busca seu padrão de ativação
        for function, func_config in model_config['functions'].items():
            activation_field = func_config.get('activation_field') or func_config.get('activation_pattern')
            
            if not activation_field:
                continue
            
            # Padrões a buscar: "I>1 Function:", "I>2 Function:", "IN1>1 Function:", etc.
            patterns_to_search = [
                f'{activation_field}1 Function:',
                f'{activation_field}2 Function:',
                f'{activation_field}1>1 Function:',
                f'{activation_field}1>2 Function:'
            ]
            
            # Procura qualquer um dos padrões
            for pattern in patterns_to_search:
                for i, line in enumerate(lines):
                    if pattern in line:
                        # Verifica próxima linha para valor
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            # Se não está vazio e não é "Disabled"
                            if next_line and next_line.lower() not in ['disabled', 'none', 'off', 'not used', '-', '']:
                                active_functions.add(function)
                                break
                if function in active_functions:
                    break  # Já encontrou esta função, não precisa testar outros padrões
    except Exception:
        # Erro ao ler PDF, retorna vazio
        pass
    
    return active_functions


def detect_sepam_functions(s40_path: Path, model_config: Dict) -> Set[str]:
    """
    Detecta funções ativas em relés SEPAM usando activite_X=1 nas seções.
    
    Args:
        s40_path: Caminho do arquivo .S40
        model_config: Configuração específica do modelo
        
    Returns:
        Set com códigos ANSI das funções ativas
    """
    active_functions = set()
    
    # Lê arquivo .S40 (formato INI) - tenta vários encodings
    config_parser = configparser.ConfigParser()
    for encoding in ['latin-1', 'cp1252', 'utf-8', 'iso-8859-1']:
        try:
            config_parser.read(s40_path, encoding=encoding)
            break
        except (UnicodeDecodeError, Exception):
            continue
    
    # Para cada função configurada, verifica sua seção
    for function, func_config in model_config['functions'].items():
        section_name = func_config['section']
        
        if not config_parser.has_section(section_name):
            continue
        
        # Verifica se existe algum activite_X=1 na seção
        section_items = dict(config_parser.items(section_name))
        
        for key, value in section_items.items():
            if key.startswith('activite_') and value == '1':
                active_functions.add(function)
                break
    
    return active_functions


def detect_active_functions(file_path: Path) -> Dict[str, any]:
    """
    Função PRINCIPAL: detecta funções ativas de forma genérica.
    
    Args:
        file_path: Caminho do arquivo do relé
        
    Returns:
        Dict com informações da detecção:
        {
            'relay_file': str,
            'model': str,
            'detection_method': str,
            'active_functions': List[str],
            'total_functions': int,
            'success': bool,
            'error': str (opcional)
        }
    """
    result = {
        'relay_file': file_path.name,
        'model': None,
        'detection_method': None,
        'active_functions': [],
        'total_functions': 0,
        'success': False
    }
    
    try:
        # Carrega configuração
        config = load_relay_config()
        
        # Identifica modelo
        model_name = identify_relay_model(file_path, config)
        if not model_name:
            result['error'] = 'Modelo não identificado'
            return result
        
        result['model'] = model_name
        model_config = config['models'][model_name]
        result['detection_method'] = model_config['detection_method']
        result['total_functions'] = len(model_config['functions'])
        
        # Aplica estratégia de detecção baseada no método
        active_funcs = set()
        
        if model_config['detection_method'] == 'checkbox':
            # MICON com checkboxes - usa CSV de parâmetros
            project_base = Path(__file__).parent.parent
            csv_path = project_base / 'outputs' / 'csv' / f"{file_path.stem}_params.csv"
            
            if csv_path.exists():
                active_funcs = detect_micon_functions(csv_path, model_config)
            else:
                result['error'] = f'CSV não encontrado: {csv_path.name}'
                return result
                
        elif model_config['detection_method'] == 'function_field':
            # P143 com Function X>: Yes
            active_funcs = detect_p143_functions(file_path, model_config)
            
        elif model_config['detection_method'] == 'activite_field':
            # SEPAM com activite_X=1
            active_funcs = detect_sepam_functions(file_path, model_config)
        
        else:
            result['error'] = f'Método de detecção desconhecido: {model_config["detection_method"]}'
            return result
        
        result['active_functions'] = sorted(list(active_funcs))
        result['success'] = True
        
    except Exception as e:
        result['error'] = str(e)
        result['success'] = False
    
    return result


def main():
    """Testa o detector em arquivos de exemplo."""
    
    print("=" * 80)
    print("DETECTOR GENÉRICO DE FUNÇÕES DE PROTEÇÃO")
    print("=" * 80)
    print()
    
    base_path = Path(__file__).parent.parent
    
    # Testa SEPAM
    print("📁 Testando SEPAM S40...")
    sepam_files = list((base_path / "inputs" / "txt").glob("*.S40"))
    
    for sepam_file in sepam_files[:3]:  # Primeiros 3
        result = detect_active_functions(sepam_file)
        print(f"\n  Arquivo: {result['relay_file']}")
        print(f"  Modelo: {result['model']}")
        print(f"  Método: {result['detection_method']}")
        if result['success']:
            print(f"  Funções ativas: {', '.join(result['active_functions'])}")
            print(f"  Total: {len(result['active_functions'])}/{result['total_functions']}")
        else:
            print(f"  ❌ Erro: {result.get('error')}")
    
    # Testa MICON (precisa de CSVs processados)
    print("\n" + "=" * 80)
    print("📁 Testando MICON (via CSV)...")
    pdf_files = list((base_path / "inputs" / "pdf").glob("*.pdf"))
    
    for pdf_file in pdf_files[:3]:  # Primeiros 3
        result = detect_active_functions(pdf_file)
        print(f"\n  Arquivo: {result['relay_file']}")
        print(f"  Modelo: {result['model']}")
        print(f"  Método: {result['detection_method']}")
        if result['success']:
            print(f"  Funções ativas: {', '.join(result['active_functions'])}")
            print(f"  Total: {len(result['active_functions'])}/{result['total_functions']}")
        else:
            print(f"  ⚠️  {result.get('error')}")
    
    # Testa P143
    print("\n" + "=" * 80)
    print("📁 Testando MICON P143 (via TXT)...")
    p143_files = [f for f in (base_path / "inputs" / "registry").glob("*.txt") 
                  if 'P143' in f.stem.upper()]
    
    for p143_file in p143_files[:3]:  # Primeiros 3
        result = detect_active_functions(p143_file)
        print(f"\n  Arquivo: {result['relay_file']}")
        print(f"  Modelo: {result['model']}")
        print(f"  Método: {result['detection_method']}")
        if result['success']:
            print(f"  Funções ativas: {', '.join(result['active_functions'])}")
            print(f"  Total: {len(result['active_functions'])}/{result['total_functions']}")
        else:
            print(f"  ⚠️  {result.get('error')}")
    
    print("\n" + "=" * 80)
    print("✅ Testes concluídos!")
    print("=" * 80)


if __name__ == "__main__":
    main()

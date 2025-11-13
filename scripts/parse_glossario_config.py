#!/usr/bin/env python3
"""
Parser do Glossário - Extrai regras de detecção de funções ativas

Lê inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx e gera um arquivo
de configuração JSON com as regras de cada modelo de relé.

Estrutura da configuração:
{
    "MICON_P122": {
        "detection_method": "checkbox",
        "source_format": "pdf",
        "functions": {
            "50/51": {
                "code_ranges": [("0200", "0229")],
                "description": "Sobrecorrente de Fase"
            }
        }
    },
    "MICON_P143": {
        "detection_method": "function_field",
        "source_format": "text",
        "activation_pattern": "Function {X}>:\\s*(Yes|No)",
        "functions": {
            "50/51": {
                "activation_field": "Function I>",
                "code_ranges": [("0200", "0229")]
            }
        }
    },
    "SEPAM_S40": {
        "detection_method": "activite_field",
        "source_format": "ini",
        "activation_pattern": "activite_\\d+=([01])",
        "functions": {
            "50/51": {
                "section": "Protection50_51"
            }
        }
    }
}
"""

import pandas as pd
from pathlib import Path
import json
from typing import Dict, Any

def parse_glossario() -> Dict[str, Any]:
    """
    Lê o glossário Excel e extrai configuração estruturada
    """
    glossario_path = Path('inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx')
    
    if not glossario_path.exists():
        raise FileNotFoundError(f"Glossário não encontrado: {glossario_path}")
    
    # Ler todas as abas
    excel_file = pd.ExcelFile(glossario_path)
    
    config = {
        "models": {},
        "metadata": {
            "source": str(glossario_path),
            "version": "1.0",
            "description": "Configuração automática extraída do glossário"
        }
    }
    
    # Mapear abas para modelos
    sheet_to_model = {
        'MICON P122_52': 'MICON_P122_52',
        'MICON P122_205': 'MICON_P122_205',
        'MICON P220': 'MICON_P220',
        'MICON P922': 'MICON_P922',
        'MICON P241': 'MICON_P241',
        'MICON P143': 'MICON_P143',
        'SEPAM S40': 'SEPAM_S40'
    }
    
    for sheet_name, model_name in sheet_to_model.items():
        if sheet_name not in excel_file.sheet_names:
            print(f"⚠️  Aba '{sheet_name}' não encontrada, pulando...")
            continue
        
        df = pd.read_excel(glossario_path, sheet_name=sheet_name)
        
        # Detectar tipo de modelo baseado no nome
        if 'P143' in model_name:
            model_config = parse_p143_sheet(df, model_name)
        elif 'SEPAM' in model_name:
            model_config = parse_sepam_sheet(df, model_name)
        else:  # P122, P220, P922, P241
            model_config = parse_micon_checkbox_sheet(df, model_name)
        
        config['models'][model_name] = model_config
    
    return config

def parse_micon_checkbox_sheet(df: pd.DataFrame, model_name: str) -> Dict[str, Any]:
    """Parser para MICON com checkboxes (P122, P220, P922, P241)"""
    
    return {
        "detection_method": "checkbox",
        "source_format": "pdf",
        "description": f"Modelo {model_name} - Detecção via checkboxes em PDF",
        "functions": extract_functions_from_codes(df, model_name),
        "code_column": "Código",  # Nome da coluna no glossário
        "description_column": "Descrição"
    }

def parse_p143_sheet(df: pd.DataFrame, model_name: str) -> Dict[str, Any]:
    """Parser para MiCOM P143 - usa Function X>: Yes/No"""
    
    return {
        "detection_method": "function_field",
        "source_format": "text",
        "description": "MiCOM P143 - Detecção via campos 'Function X>:'",
        "activation_pattern": r"Function\s+(\w+)>:\s*(Yes|No)",
        "functions": extract_p143_functions(df),
        "groups": ["GROUP 1", "GROUP 2", "GROUP 3", "GROUP 4"]
    }

def parse_sepam_sheet(df: pd.DataFrame, model_name: str) -> Dict[str, Any]:
    """Parser para SEPAM S40 - usa activite_X=0/1"""
    
    return {
        "detection_method": "activite_field",
        "source_format": "ini",
        "description": "SEPAM S40 - Detecção via campos 'activite_X='",
        "activation_pattern": r"activite_(\d+)=([01])",
        "functions": extract_sepam_functions(df)
    }

def extract_functions_from_codes(df: pd.DataFrame, model_name: str) -> Dict[str, Any]:
    """
    Extrai funções de proteção baseado em ranges de códigos hex
    
    Procura por padrões nas observações (amarelo destacado) e códigos
    """
    functions = {}
    
    # TODO: Implementar leitura das células destacadas em amarelo
    # Por enquanto, retornar estrutura vazia
    # Na próxima iteração, usar openpyxl para ler formatação das células
    
    return functions

def extract_p143_functions(df: pd.DataFrame) -> Dict[str, Any]:
    """Extrai funções do P143 baseado em campos Function X>:"""
    
    # Mapeamento conhecido de campos para funções ANSI
    function_mapping = {
        "I>": {"ansi": "50/51", "description": "Sobrecorrente de Fase"},
        "Ie>": {"ansi": "50N/51N", "description": "Sobrecorrente de Terra"},
        "V<": {"ansi": "27", "description": "Subtensão"},
        "V>": {"ansi": "59", "description": "Sobretensão"},
        "f<": {"ansi": "81U", "description": "Subfrequência"},
        "f>": {"ansi": "81O", "description": "Sobrefrequência"},
        "I2>": {"ansi": "46", "description": "Sequência Negativa"},
    }
    
    functions = {}
    for field, info in function_mapping.items():
        functions[info["ansi"]] = {
            "activation_field": f"Function {field}",
            "description": info["description"]
        }
    
    return functions

def extract_sepam_functions(df: pd.DataFrame) -> Dict[str, Any]:
    """Extrai funções do SEPAM baseado em seções Protection"""
    
    # Mapeamento de seções para funções ANSI
    section_mapping = {
        "Protection27": {"ansi": "27", "description": "Subtensão"},
        "Protection2727S": {"ansi": "27", "description": "Subtensão"},
        "Protection59": {"ansi": "59", "description": "Sobretensão"},
        "Protection59N": {"ansi": "59N", "description": "Sobretensão de Neutro"},
        "Protection50_51": {"ansi": "50/51", "description": "Sobrecorrente de Fase"},
        "Protection50_51N": {"ansi": "50N/51N", "description": "Sobrecorrente de Terra"},
        "Protection46": {"ansi": "46", "description": "Sequência Negativa"},
        "Protection50BF": {"ansi": "50BF", "description": "Breaker Failure"},
    }
    
    functions = {}
    for section, info in section_mapping.items():
        functions[info["ansi"]] = {
            "section": section,
            "description": info["description"]
        }
    
    return functions

def main():
    print("=" * 80)
    print("📖 PARSER DO GLOSSÁRIO - Extraindo Configuração")
    print("=" * 80)
    
    try:
        config = parse_glossario()
        
        # Salvar configuração
        output_path = Path('inputs/glossario/relay_models_config.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Configuração gerada: {output_path}")
        print(f"\n📊 Modelos processados:")
        for model_name, model_config in config['models'].items():
            func_count = len(model_config.get('functions', {}))
            method = model_config.get('detection_method', 'unknown')
            print(f"  • {model_name:20s} → {method:20s} ({func_count} funções)")
        
        print(f"\n💾 Arquivo salvo com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())

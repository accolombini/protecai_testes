#!/usr/bin/env python3
"""
Mapeamento de Códigos de Parâmetros para Funções de Proteção

OBJETIVO: Mapear códigos hexadecimais (MICON) ou nomes (SEPAM) para function_id
baseado no glossário e na estrutura das funções ANSI.

USO:
    from map_parameters_to_functions import get_function_id, get_category
    
    function_id = get_function_id('0201', 'MICON')
    category = get_category('0201')
"""

# Mapeamento baseado no glossário MICON P122_52 e P122_204
# Estrutura: (código_inicial, código_final): (function_code, category)

MICON_CODE_RANGES = {
    # PROTECTION G1
    # [50/51] PHASE OC - Sobrecorrente de Fase
    ('0200', '0229'): ('50/51', 'protection'),
    
    # [50N/51N] E/Gnd - Sobrecorrente de Terra/Neutro
    ('0230', '0259'): ('50N/51N', 'protection'),
    
    # [46] NEG SEQ OC - Desbalanceamento de Corrente (Sequência Negativa)
    ('025C', '0268'): ('46', 'protection'),
    
    # [37] UNDER CURRENT - Subcorrente
    ('025A', '026F'): ('37', 'protection'),
    
    # PROTECTION G2 (códigos 0300-03FF são duplicatas do G1)
    ('0300', '0329'): ('50/51', 'protection'),
    ('0330', '0359'): ('50N/51N', 'protection'),
    ('035C', '0368'): ('46', 'protection'),
    ('035A', '036F'): ('37', 'protection'),
    
    # CT RATIO - Configuração de TC
    ('0120', '0123'): (None, 'configuration'),
    
    # DISPLAY - Configuração de Display
    ('0105', '0109'): (None, 'configuration'),
    
    # OP PARAMETERS - Parâmetros Operacionais
    ('0104', '010A'): (None, 'configuration'),
    
    # CB FAIL - Falha de Disjuntor
    ('018A', '018B'): (None, 'control'),
    ('01A4', '01A6'): (None, 'control'),
    
    # CB SUPERVISION - Supervisão de Disjuntor
    ('019F', '01A3'): (None, 'control'),
}

# Mapeamento MICON P220 (motor protection)
MICON_P220_RANGES = {
    # Phase overcurrent
    ('0210', '0212'): ('50', 'protection'),
    
    # Ground overcurrent
    ('0220', '0225'): ('50N/51N', 'protection'),
    
    # Negative sequence
    ('0230', '0234'): ('46', 'protection'),
    
    # Undercurrent
    ('0250', '0253'): ('37', 'protection'),
    
    # Thermal
    ('0300', '0310'): ('49', 'protection'),
    
    # CT configuration
    ('0120', '0123'): (None, 'configuration'),
}

# Mapeamento MICON P922 (voltage protection)
MICON_P922_RANGES = {
    # Undervoltage
    ('0200', '0222'): ('27', 'protection'),
    
    # Overvoltage  
    ('0230', '0252'): ('59', 'protection'),
    
    # Residual voltage
    ('0260', '0282'): ('59N', 'protection'),
    
    # Frequency
    ('02D0', '02DF'): ('81O/81U', 'protection'),
    
    # VT configuration
    ('0120', '0125'): (None, 'configuration'),
}

# Mapeamento SEPAM (baseado em nomes de parâmetros)
SEPAM_PARAM_PREFIXES = {
    # Características gerais
    'i_nominal': (None, 'configuration'),
    'i_base': (None, 'configuration'),
    'courant_nominal_residuel': (None, 'configuration'),
    'tension_primaire_nominale': (None, 'configuration'),
    'tension_secondaire_nominale': (None, 'configuration'),
    'application': (None, 'configuration'),
    
    # Protection59N - Overvoltage Neutral
    'vs0_': ('59N', 'protection'),
    'tempo_declenchement': (None, 'protection'),  # Generic timing
    
    # Protection - Phase current (detectado por courbe_declenchement + courant_seuil)
    'courant_seuil': ('50/51', 'protection'),
    'courbe_declenchement': ('50/51', 'protection'),
    
    # Frequency
    'frequence_seuil': ('81O/81U', 'protection'),
}


def hex_in_range(code: str, start: str, end: str) -> bool:
    """Verifica se código hexadecimal está dentro do range."""
    try:
        code_int = int(code, 16)
        start_int = int(start, 16)
        end_int = int(end, 16)
        return start_int <= code_int <= end_int
    except ValueError:
        return False


def get_function_code_and_category(param_code: str, model_type: str = 'MICON') -> tuple:
    """
    Retorna (function_code, category) baseado no código do parâmetro.
    
    Args:
        param_code: Código do parâmetro (ex: '0201', 'i_nominal')
        model_type: Tipo do modelo ('MICON', 'SEPAM')
    
    Returns:
        tuple: (function_code, category) onde function_code pode ser None
    """
    if model_type == 'MICON':
        # Tentar P122 primeiro (mais comum)
        for (start, end), (func_code, cat) in MICON_CODE_RANGES.items():
            if hex_in_range(param_code, start, end):
                return (func_code, cat)
        
        # Tentar P220
        for (start, end), (func_code, cat) in MICON_P220_RANGES.items():
            if hex_in_range(param_code, start, end):
                return (func_code, cat)
        
        # Tentar P922
        for (start, end), (func_code, cat) in MICON_P922_RANGES.items():
            if hex_in_range(param_code, start, end):
                return (func_code, cat)
    
    elif model_type == 'SEPAM':
        # Buscar por prefixo do nome do parâmetro
        param_lower = param_code.lower()
        for prefix, (func_code, cat) in SEPAM_PARAM_PREFIXES.items():
            if param_lower.startswith(prefix):
                return (func_code, cat)
    
    # Default: parâmetro não classificado
    return (None, 'other')


def get_function_id(param_code: str, model_type: str, function_map: dict) -> int:
    """
    Retorna o function_id do banco de dados baseado no código.
    
    Args:
        param_code: Código do parâmetro
        model_type: 'MICON' ou 'SEPAM'
        function_map: Dict com mapeamento function_code -> function_id do DB
    
    Returns:
        int: function_id ou None se não encontrado
    """
    function_code, _ = get_function_code_and_category(param_code, model_type)
    
    if function_code is None:
        return None
    
    # Buscar no mapeamento do banco
    return function_map.get(function_code)


def get_category(param_code: str, model_type: str = 'MICON') -> str:
    """
    Retorna a categoria do parâmetro.
    
    Returns:
        str: 'protection', 'configuration', 'control', 'other'
    """
    _, category = get_function_code_and_category(param_code, model_type)
    return category


if __name__ == '__main__':
    # Testes
    test_cases = [
        ('0201', 'MICON'),  # 50/51 - I>
        ('0231', 'MICON'),  # 50N/51N - Ie>
        ('025D', 'MICON'),  # 46 - I2>
        ('0120', 'MICON'),  # Configuration - CT primary
        ('i_nominal', 'SEPAM'),  # Configuration
        ('courant_seuil_1_1', 'SEPAM'),  # 50/51
    ]
    
    print("TESTES DE MAPEAMENTO:")
    print("=" * 80)
    for code, model in test_cases:
        func_code, category = get_function_code_and_category(code, model)
        print(f"{code:20} ({model:6}) -> Function: {func_code or 'None':15} Category: {category}")

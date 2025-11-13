#!/usr/bin/env python3
"""
Teste de extração da PÁGINA 4 do P220 52-MP-04A.pdf
Deve detectar os 7 checkboxes restantes do INPUT 4 (continuação da página 3)
"""

import PyPDF2
import re

def extract_text_from_page(pdf_path, page_num):
    """Extrai texto de uma página específica"""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        if page_num < len(reader.pages):
            page = reader.pages[page_num]
            return page.extract_text()
    return ""

def parse_parameters_from_text(text):
    """
    Parser ROBUSTO para extrair parâmetros e checkboxes do texto.
    Suporta:
    - Múltiplas seções INPUT (pode ter INPUT 3, INPUT 4, etc)
    - Checkboxes que se estendem por múltiplas páginas
    - Mesmo checkbox name em diferentes INPUTs (não são duplicatas!)
    """
    params = []
    checkboxes = []
    lines = text.split('\n')
    
    i = 0
    in_checkbox_section = False
    current_section = ""  # Rastrear qual INPUT está ativo (INPUT 3, INPUT 4, etc)
    
    while i < len(lines):
        line = lines[i].strip()
        
        # ========================================================================
        # RULE 1: Detectar CÓDIGO de parâmetro (NNNN: ou NNAA:)
        # ========================================================================
        code_match = re.match(r'^([0-9A-F]{4}):\s*(.*)$', line, re.IGNORECASE)
        
        if code_match:
            code = code_match.group(1)
            rest_of_line = code_match.group(2).strip()
            
            # Separar descrição e valor da MESMA linha
            description = rest_of_line
            value = ""
            
            # Verificar se valor está NA MESMA LINHA
            # Padrão 1: "DESC ?: YES/NO"
            if '?:' in rest_of_line or '? :' in rest_of_line:
                parts = re.split(r'\?\s*:', rest_of_line)
                description = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ""
            
            # Padrão 2: "DESC =: VALUE" ou "DESC = VALUE"
            elif '=:' in rest_of_line or '=' in rest_of_line:
                separator = '=:' if '=:' in rest_of_line else '='
                parts = rest_of_line.split(separator, 1)
                description = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ""
            
            # Padrão 3: "DESC: VALUE" (sem ? ou =)
            elif ':' in rest_of_line and rest_of_line.count(':') == 1:
                parts = rest_of_line.split(':', 1)
                description = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ""
            
            # Rastrear origem do valor (mesma linha ou próxima)
            value_source = "mesma linha" if value else ""
            
            # Se valor vazio, verificar PRÓXIMA linha
            if not value and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                # Próxima linha é valor SE:
                # - Não começa com código (NNNN:)
                # - Não é seção ([...)
                # - Não é cabeçalho (tudo maiúsculo longo)
                # - Parece um valor (número, unidade, YES/NO)
                is_next_code = re.match(r'^[0-9A-F]{4}:', next_line, re.IGNORECASE)
                is_section = next_line.startswith('[') or (next_line.isupper() and len(next_line) > 10)
                is_value_like = (
                    next_line and
                    (re.match(r'^\d', next_line) or
                     next_line in ['YES', 'NO', 'No'] or
                     any(unit in next_line for unit in ['In', 's', 'Hz', 'mn', 'Ith', 'A', 'V']))
                )
                
                if not is_next_code and not is_section and is_value_like:
                    value = next_line
                    value_source = "linha seguinte"
                    i += 1  # Consumir próxima linha
            
            # Detectar se é seção INPUT (checkbox)
            # SEMPRE reativar se encontrar INPUT (pode ter múltiplos INPUTs)
            if 'INPUT' in description.upper():
                in_checkbox_section = True
                current_section = f"{code}: {description.split('=')[0].strip()}"
                print(f"🔍 DEBUG: Ativando checkbox section para {current_section}")
            # NÃO DESATIVAR! Deixar ativo até encontrar próximo código não-INPUT
            
            params.append({
                'Code': code,
                'Description': description,
                'Value': value,
                'ValueSource': value_source,
                'Type': 'parameter'
            })
            
            i += 1
            continue
        
        # ========================================================================
        # RULE 2: Detectar CHECKBOXES (após INPUT)
        # ========================================================================
        if in_checkbox_section and line:
            print(f"🔍 DEBUG CHECKBOX: linha='{line[:50]}' in_section={in_checkbox_section} (linha {i})")
            
            # Verificar se é um novo código
            is_code = re.match(r'^[0-9A-F]{4}:', line, re.IGNORECASE)
            is_section = line.isupper() and len(line) > 10 and not any(x in line for x in ['EXT', 'SET', 'EMERG'])
            
            print(f"   ↳ is_code={is_code is not None}, is_section={is_section}")
            
            # REGRA ROBUSTA: Parar de coletar checkboxes SOMENTE quando:
            # 1. Encontrar código que NÃO seja INPUT (ex: 0162:, 0170:, etc)
            # 2. OU encontrar seção de cabeçalho longo
            if is_code:
                if 'INPUT' in line:
                    # É outro INPUT! Atualizar contexto e continuar coletando
                    code_match = re.match(r'^([0-9A-F]{4}):\s*(.*)$', line, re.IGNORECASE)
                    if code_match:
                        current_section = f"{code_match.group(1)}: {code_match.group(2).split('=')[0].strip()}"
                        print(f"🔍 DEBUG: Atualizando checkbox section para {current_section}")
                    i += 1
                    continue
                else:
                    # É código diferente de INPUT - parar de coletar checkboxes
                    in_checkbox_section = False
                    print(f"🔍 DEBUG: Desativando checkbox section (código não-INPUT encontrado: {line[:30]})")
                    # NÃO fazer continue - processar este código como parâmetro normal
                    # Voltar para o início do loop para processar como RULE 1
                    continue
            
            # Se encontrou seção nova, desativar
            if is_section:
                in_checkbox_section = False
                print(f"🔍 DEBUG: Desativando checkbox section (seção encontrada: {line[:30]})")
                i += 1
                continue
            
            # FILTRAR: Ignorar valores simples (Yes, No, etc) e marcas de fim
            is_ignored = line in ['YES', 'NO', 'No', 'Yes'] or 'Easergy' in line or 'Studio' in line
            print(f"   ↳ is_ignored={is_ignored} (Easergy={'Easergy' in line}, Studio={'Studio' in line})")
            
            if is_ignored:
                print(f"   ↳ 🛑 IGNORANDO linha: {line}")
                i += 1
                continue
            
            # É um checkbox válido SE:
            # - Tem tamanho razoável (não é cabeçalho longo)
            # - Tem ponto final ou underscore (padrão dos nomes)
            # PERMITIR DUPLICATAS: mesmo checkbox pode aparecer em INPUT 3 e INPUT 4
            is_checkbox_name = (
                len(line) < 30 and
                ('.' in line or '_' in line or line.isupper())
            )
            
            print(f"   ↳ is_checkbox_name={is_checkbox_name}")
            
            if is_checkbox_name:
                # Adicionar contexto do INPUT atual
                input_context = current_section if 'INPUT' in current_section else 'Unknown'
                checkboxes.append({
                    'Code': f'CHK_{len(checkboxes)+1:02d}',
                    'Description': f"{line} ({input_context})",
                    'Value': 'Unchecked',
                    'Type': 'checkbox',
                    'Input_Section': input_context
                })
        
        i += 1
    
    return params, checkboxes

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    pdf_path = "inputs/pdf/P220 52-MP-04A.pdf"
    page_num = 3  # Página 4 (índice 3)
    
    print("=" * 80)
    print(f"📄 Extraindo PÁGINA 4 de: {pdf_path}")
    print("=" * 80)
    
    # Extrair texto
    text = extract_text_from_page(pdf_path, page_num)
    
    if not text:
        print("❌ Erro: não foi possível extrair texto da página")
        exit(1)
    
    # Parser
    params, checkboxes = parse_parameters_from_text(text)
    
    # Exibir resultados
    print("\n" + "=" * 80)
    print(f"📊 PARÂMETROS EXTRAÍDOS DA PÁGINA 4:")
    print("=" * 80)
    for idx, param in enumerate(params, 1):
        value_display = f" = {param['Value']}" if param['Value'] else ""
        source_display = f" [{param['ValueSource']}]" if param['ValueSource'] else ""
        print(f"   {idx:2d}. {param['Code']}: {param['Description']:45s} {value_display}{source_display}")
    
    print("\n" + "=" * 80)
    print(f"☑️  CHECKBOXES DETECTADOS (Continuação de INPUT 4):")
    print("   ⚠️  ATENÇÃO: Extração por TEXTO não detecta se está marcado!")
    print("   ⚠️  Use template matching visual para verificar estado real.")
    print("=" * 80)
    for idx, cb in enumerate(checkboxes, 1):
        print(f"   {idx:2d}. ☐ {cb['Description']} (estado desconhecido)")
    
    print("\n" + "=" * 80)
    print("✅ Extração concluída!")
    print("=" * 80)
    
    print("\n❓ VALIDAÇÃO:")
    print("   Devemos ver os 7 checkboxes restantes do INPUT 4:")
    print("   - VOLT._DIP, DIST TRIG, EXT RESET, EXT 1, EXT 2, EXT 3, EXT 4")
    print("=" * 80)

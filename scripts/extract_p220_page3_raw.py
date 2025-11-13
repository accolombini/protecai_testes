#!/usr/bin/env python3
"""
Extrai TODOS os parâmetros da página 3 do P220 via texto
Objetivo: Validar o que realmente está no PDF
"""

import fitz
from pathlib import Path
import re

def extract_page3_raw_text(pdf_path: Path, page_num: int = 2):
    """Extrai texto bruto da página especificada"""
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]
    text = page.get_text()
    doc.close()
    return text

def parse_parameters_from_text(text: str):
    """
    Parser UNIVERSAL e ROBUSTO - Versão FINAL
    
    Princípios:
    1. Linha com padrão NNNN: ou NNAA: → início de parâmetro
    2. Próxima linha sem código → valor (se parece com valor) ou descrição
    3. Seção INPUT → checkboxes até próximo código
    4. PRESERVAR formatação original do PDF
    5. NÃO presumir formato específico de modelo
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
            # Formato comum: "DESCRIPTION ?: VALUE" ou "DESCRIPTION =: VALUE"
            description = rest_of_line
            value = ""
            
            # Verificar se valor está NA MESMA LINHA
            # Padrão 1: "DESC ?: YES/NO"
            if '?:' in rest_of_line:
                parts = rest_of_line.split('?:', 1)
                description = parts[0].strip() + ' ?'
                value = parts[1].strip() if len(parts) > 1 else ""
            
            # Padrão 2: "DESC =: VALUE"
            elif '=:' in rest_of_line:
                parts = rest_of_line.split('=:', 1)
                description = parts[0].strip() + ' ='
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
            
            # ========================================================================
            # DETECÇÃO GENÉRICA DE CHECKBOX SECTION
            # ========================================================================
            # LÓGICA CORRIGIDA: Detectar checkbox section por PADRÃO, não keyword
            # 
            # Critérios para INICIAR checkbox section:
            # 1. Linha seguinte não tem código (será checkbox)
            # 2. OU descrição sugere lista de opções (INPUT, OUTPUT, Logical, etc)
            # 
            # Heurística: Se após este código vem linha sem código, 
            # pode ser início de checkbox section
            # ========================================================================
            
            # Verificar se próximas linhas são checkboxes (não têm código)
            potential_checkbox_section = False
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Próxima linha parece checkbox se:
                # - NÃO tem código no início
                # - Tem texto significativo
                # - Não é valor simples (YES/NO)
                # - Não é metadata (Easergy, Studio)
                has_code = re.match(r'^[0-9A-F]{4}:', next_line, re.IGNORECASE)
                is_text = len(next_line) > 0 and len(next_line) < 50
                is_not_value = next_line not in ['YES', 'NO', 'Yes', 'No']
                is_not_metadata = not any(x in next_line for x in ['Easergy', 'Studio', 'Page'])
                
                potential_checkbox_section = (
                    not has_code and is_text and is_not_value and is_not_metadata
                )
            
            # Ativar checkbox section se detectado padrão OU se é INPUT/OUTPUT explícito
            if potential_checkbox_section or 'INPUT' in description.upper() or 'OUTPUT' in description.upper():
                in_checkbox_section = True
                current_section = f"{code}: {description}"
                print(f"🔍 DEBUG: Ativando checkbox section para {current_section}")
            else:
                in_checkbox_section = False
            
            params.append({
                'Code': code,
                'Description': description,
                'Value': value,
                'ValueSource': value_source,  # NOVO: rastrear origem
                'Type': 'parameter'
            })
            
            i += 1
            continue
        
        # ========================================================================
        # RULE 2: Detectar CHECKBOXES (detecção genérica por padrão)
        # ========================================================================
        if in_checkbox_section and line:
            print(f"🔍 DEBUG CHECKBOX: linha='{line[:50]}' in_section={in_checkbox_section} (linha {i})")
            
            # Verificar se é um novo código (encerra checkbox section)
            is_code = re.match(r'^[0-9A-F]{4}:', line, re.IGNORECASE)
            is_section = line.isupper() and len(line) > 10 and not any(x in line for x in ['EXT', 'SET', 'EMERG', 'TRIP', 'OUTPUT', 'LOGICAL'])
            
            print(f"   ↳ is_code={is_code is not None}, is_section={is_section}")
            
            # LÓGICA CORRIGIDA: Parar checkbox section SOMENTE quando encontrar novo código
            # (independente se é INPUT ou não)
            if is_code:
                # Verificar se é CONTINUAÇÃO de checkbox section (outro INPUT/OUTPUT)
                # ou se é NOVO parâmetro (encerra checkbox section)
                is_continuation = any(kw in line.upper() for kw in ['INPUT', 'OUTPUT', 'LOGICAL OUTPUT'])
                
                if is_continuation:
                    # Atualizar contexto mas continuar coletando checkboxes
                    code_match = re.match(r'^([0-9A-F]{4}):\s*(.*)$', line, re.IGNORECASE)
                    if code_match:
                        current_section = f"{code_match.group(1)}: {code_match.group(2).split('=')[0].strip()}"
                        print(f"🔍 DEBUG: Atualizando checkbox section para {current_section}")
                    i += 1
                    continue
                else:
                    # É código diferente - encerrar checkbox section
                    in_checkbox_section = False
                    print(f"🔍 DEBUG: Desativando checkbox section (novo código encontrado: {line[:30]})")
                    continue
            
            # Se encontrou seção nova, desativar
            if is_section:
                in_checkbox_section = False
                print(f"🔍 DEBUG: Desativando checkbox section (seção encontrada: {line[:30]})")
                i += 1
                continue
            
            # FILTRAR: Ignorar valores simples, metadata E palavras genéricas de seção
            generic_sections = ['INPUTS', 'OUTPUTS', 'SETTINGS', 'PROTECTION', 'CONFIGURATION']
            is_ignored = (
                line in ['YES', 'NO', 'No', 'Yes'] or 
                'Easergy' in line or 
                'Studio' in line or
                line in generic_sections  # ← NOVO: filtrar palavras de seção
            )
            print(f"   ↳ is_ignored={is_ignored} (Easergy={'Easergy' in line}, Studio={'Studio' in line}, Section={line in generic_sections})")
            
            if is_ignored:
                print(f"   ↳ 🛑 IGNORANDO linha: {line}")
                i += 1
                continue
            
            # ========================================================================
            # DETECÇÃO GENÉRICA DE CHECKBOX
            # ========================================================================
            # É um checkbox válido SE:
            # - Tem tamanho razoável (< 50 chars, não é cabeçalho longo)
            # - Tem padrão de nome de opção:
            #   * Ponto final (EMERG_ST.)
            #   * Underscore (SET_GROUP)
            #   * Palavra "output" (Logical output 2)
            #   * Palavra "input"
            #   * Tudo maiúsculo curto (TRIP, SET GROUP)
            # ========================================================================
            is_checkbox_name = (
                len(line) < 50 and
                (
                    '.' in line or 
                    '_' in line or 
                    'output' in line.lower() or
                    'input' in line.lower() or
                    (line.isupper() and len(line.split()) <= 3)
                )
            )
            
            print(f"   ↳ is_checkbox_name={is_checkbox_name}")
            
            if is_checkbox_name:
                # Adicionar contexto do código/INPUT atual
                input_context = current_section if current_section else 'Unknown'
                checkboxes.append({
                    'Code': f'CHK_{len(checkboxes)+1:02d}',
                    'Description': f"{line} ({input_context})",
                    'Value': 'Unchecked',  # Texto não sabe se está marcado
                    'Type': 'checkbox',
                    'Input_Section': input_context
                })
        
        i += 1
    
    # Combinar parâmetros + checkboxes
    return params + checkboxes

def main():
    pdf_path = Path("inputs/pdf/P220 52-MP-04A.pdf")
    
    print("=" * 80)
    print("📄 EXTRAÇÃO COMPLETA - Página 3 de P220 52-MP-04A.pdf")
    print("=" * 80)
    print()
    
    if not pdf_path.exists():
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    # Extrair texto bruto
    print("🔄 Extraindo texto bruto da página 3...")
    text = extract_page3_raw_text(pdf_path, page_num=2)  # Página 3 = índice 2
    
    print(f"✅ Texto extraído: {len(text)} caracteres")
    print()
    
    # Mostrar texto bruto (primeiros 2000 caracteres)
    print("=" * 80)
    print("📝 TEXTO BRUTO (primeiros 2000 chars):")
    print("=" * 80)
    print(text[:2000])
    print("..." if len(text) > 2000 else "")
    print()
    
    # Parse parâmetros
    print("=" * 80)
    print("🔍 PARSEANDO PARÂMETROS...")
    print("=" * 80)
    
    params = parse_parameters_from_text(text)
    
    print(f"✅ Total extraído: {len(params)} itens")
    print()
    
    # Separar por tipo
    regular_params = [p for p in params if p['Type'] == 'parameter']
    checkbox_params = [p for p in params if p['Type'] == 'checkbox']
    
    print("📊 ESTATÍSTICAS:")
    print(f"   • Parâmetros regulares: {len(regular_params)}")
    print(f"   • Checkboxes: {len(checkbox_params)}")
    print()
    
    # Mostrar parâmetros regulares
    if regular_params:
        print("=" * 80)
        print("📝 PARÂMETROS DE CONFIGURAÇÃO:")
        print("=" * 80)
        for i, p in enumerate(regular_params, 1):
            code = p['Code']
            desc = p['Description']
            value = p['Value'] if p['Value'] else '(vazio)'
            source = f" [{p['ValueSource']}]" if p.get('ValueSource') else ""
            
            # Formato: CÓDIGO: DESCRIÇÃO = VALOR [origem]
            print(f"   {i:2d}. {code}: {desc:40s} = {value}{source}")
        print()
    
    # Mostrar checkboxes
    if checkbox_params:
        print("=" * 80)
        print("☑️  CHECKBOXES DETECTADOS (Seção INPUTS):")
        print("   ⚠️  ATENÇÃO: Extração por TEXTO não detecta se está marcado!")
        print("   ⚠️  Use template matching visual para verificar estado real.")
        print("=" * 80)
        for i, p in enumerate(checkbox_params, 1):
            print(f"   {i:2d}. ☐ {p['Description']} (estado desconhecido)")
        print()
    
    print("=" * 80)
    print("✅ Extração concluída!")
    print("=" * 80)
    print()
    print("❓ VALIDAÇÃO:")
    print("   Compare os resultados acima com a imagem da página 3")
    print("   Verifique se todos os parâmetros estão presentes")
    print("=" * 80)

if __name__ == "__main__":
    main()

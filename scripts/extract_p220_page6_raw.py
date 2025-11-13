"""
Teste de extração RAW - P220 Página 6
Validar lógica ROBUSTA e FLEXÍVEL para múltiplos códigos com checkboxes
"""

import sys
import re
from pathlib import Path

# Adicionar path do projeto
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import PyPDF2
except ImportError:
    print("⚠️  PyPDF2 não encontrado. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
    import PyPDF2


def parse_parameters_from_text(text: str):
    """
    Parser ROBUSTO e FLEXÍVEL para extrair parâmetros e checkboxes
    
    REGRAS:
    1. Código de parâmetro: NNNN: ou NNAA: (ex: 0160:, 017A:)
    2. Checkbox: após INPUT, coletar nomes até próximo código não-INPUT
    3. Multi-linha: se valor vazio, pegar próxima linha
    4. Permitir duplicatas: EMERG_ST. pode aparecer em INPUT 3, 4, 5...
    """
    params = []
    checkboxes = []
    lines = text.split('\n')
    
    i = 0
    in_checkbox_section = False
    current_section = ""  # Rastrear qual INPUT/código está ativo
    
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
            
            # Padrão 2: "DESC =: VALUE" ou "DESC ="
            elif '=:' in rest_of_line or '=' in rest_of_line:
                parts = rest_of_line.split('=', 1)
                description = parts[0].strip()
                value = parts[1].strip().replace(':', '').strip() if len(parts) > 1 else ""
            
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
            
            # Detectar se próxima linha contém checkboxes
            # Olhar adiante para verificar se há checkboxes após este código
            has_checkboxes_next = False
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Verificar se próxima linha parece checkbox
                has_checkboxes_next = (
                    next_line and
                    not re.match(r'^[0-9A-F]{4}:', next_line, re.IGNORECASE) and
                    len(next_line) < 50 and
                    next_line not in ['YES', 'NO', 'No', 'Yes'] and
                    'Easergy' not in next_line and
                    ('.' in next_line or '_' in next_line or 'Logical' in next_line or 'output' in next_line or
                     any(x in next_line for x in ['EMERG', 'SET', 'VOLT', 'DIST', 'EXT', 'RESET', 'TRIP']))
                )
            
            # Ativar seção de checkboxes se detectado padrão
            if has_checkboxes_next:
                in_checkbox_section = True
                current_section = f"{code}: {description}"
                print(f"🔍 DEBUG: Ativando checkbox section para {current_section} (detectou checkboxes na próxima linha)")
            
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
        # RULE 2: Detectar CHECKBOXES (após INPUT ou outros códigos com checkboxes)
        # ========================================================================
        if in_checkbox_section and line:
            print(f"🔍 DEBUG CHECKBOX: linha='{line[:50]}' in_section={in_checkbox_section} (linha {i})")
            
            # Verificar se é um novo código
            is_code = re.match(r'^[0-9A-F]{4}:', line, re.IGNORECASE)
            is_section = line.isupper() and len(line) > 10 and not any(x in line for x in ['EXT', 'SET', 'EMERG', 'LOGICAL', 'OUTPUT', 'VOLT', 'DIST', 'RESET'])
            
            print(f"   ↳ is_code={is_code is not None}, is_section={is_section}")
            
            # REGRA ROBUSTA: Parar de coletar checkboxes SOMENTE quando:
            # 1. Encontrar código que NÃO seja INPUT E NÃO tenha checkboxes
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
                    # NOVO: Verificar se próxima linha é checkbox (ex: "Logical output 2")
                    # Se sim, continuar coletando (códigos 0170, 0171, etc têm checkboxes)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        looks_like_checkbox = (
                            'Logical' in next_line or 
                            'output' in next_line or
                            any(x in next_line for x in ['EMERG', 'SET', 'VOLT', 'DIST', 'EXT', 'RESET'])
                        )
                        if looks_like_checkbox:
                            # Atualizar contexto para o novo código
                            code_match = re.match(r'^([0-9A-F]{4}):\s*(.*)$', line, re.IGNORECASE)
                            if code_match:
                                current_section = f"{code_match.group(1)}: {code_match.group(2)}"
                                print(f"🔍 DEBUG: Atualizando para código com checkboxes: {current_section}")
                            i += 1
                            continue
                    
                    # Não tem checkboxes - parar de coletar
                    in_checkbox_section = False
                    print(f"🔍 DEBUG: Desativando checkbox section (código sem checkboxes: {line[:30]})")
                    continue
            
            # Se encontrou seção nova, desativar
            if is_section:
                in_checkbox_section = False
                print(f"🔍 DEBUG: Desativando checkbox section (seção encontrada: {line[:30]})")
                i += 1
                continue
            
            # FILTRAR: Ignorar valores simples (Yes, No, etc), marcas de fim e seções longas
            is_ignored = (
                line in ['YES', 'NO', 'No', 'Yes'] or 
                'Easergy' in line or 
                'Studio' in line or
                line in ['INPUTS'] or  # Palavra solta "INPUTS"
                (line.isupper() and len(line) > 30)  # Cabeçalhos longos
            )
            print(f"   ↳ is_ignored={is_ignored}")
            
            if is_ignored:
                print(f"   ↳ 🛑 IGNORANDO linha: {line}")
                i += 1
                continue
            
            # É um checkbox válido SE:
            # - Tem tamanho razoável (< 50 chars)
            # - Tem indicadores de checkbox: ponto final, underscore, "Logical", "output", "EXT", etc
            is_checkbox_name = (
                len(line) < 50 and
                ('.' in line or '_' in line or 
                 'Logical' in line or 'output' in line or
                 any(keyword in line for keyword in ['EMERG', 'SET', 'VOLT', 'DIST', 'EXT', 'RESET', 'TRIP']))
            )
            
            print(f"   ↳ is_checkbox_name={is_checkbox_name}")
            
            if is_checkbox_name:
                # Adicionar contexto do código atual
                input_context = current_section if current_section else 'Unknown'
                checkboxes.append({
                    'Code': f'CHK_{len(checkboxes)+1:02d}',
                    'Description': f"{line} ({input_context})",
                    'Value': 'Unchecked',
                    'Type': 'checkbox',
                    'Section': input_context
                })
        
        i += 1
    
    # Combinar parâmetros + checkboxes
    return params, checkboxes


def main():
    """Teste principal - Página 6 do P220"""
    
    pdf_path = project_root / "inputs" / "pdf" / "P220 52-MP-04A.pdf"
    
    if not pdf_path.exists():
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    print(f"📄 Extraindo PÁGINA 6 de: {pdf_path.name}")
    print("=" * 80)
    
    # Extrair texto da página 6 (índice 5)
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        page = reader.pages[5]  # Página 6 (índice 5)
        text = page.extract_text()
    
    print(f"\n📝 TEXTO EXTRAÍDO (primeiras 500 chars):")
    print("-" * 80)
    print(text[:500])
    print("-" * 80)
    
    # Parser robusto
    params, checkboxes = parse_parameters_from_text(text)
    
    print(f"\n✅ Total extraído: {len(params)} parâmetros + {len(checkboxes)} checkboxes")
    
    print("\n" + "=" * 80)
    print("📊 PARÂMETROS EXTRAÍDOS:")
    print("=" * 80)
    for idx, param in enumerate(params, 1):
        value_display = f" = {param['Value']}" if param['Value'] else ""
        source = f" [{param['ValueSource']}]" if param['ValueSource'] else ""
        print(f"{idx:4d}. {param['Code']}: {param['Description']:<40} {value_display}{source}")
    
    print("\n" + "=" * 80)
    print("☑️  CHECKBOXES DETECTADOS:")
    print("   ⚠️  ATENÇÃO: Extração por TEXTO não detecta se está marcado!")
    print("   ⚠️  Use template matching visual para verificar estado real.")
    print("=" * 80)
    
    if checkboxes:
        for idx, cb in enumerate(checkboxes, 1):
            print(f"{idx:4d}. ☐ {cb['Description']} (estado desconhecido)")
    else:
        print("   Nenhum checkbox detectado.")
    
    print("\n" + "=" * 80)
    print("✅ Extração concluída!")
    print("=" * 80)
    
    print("\n❓ VALIDAÇÃO:")
    print("   Compare os resultados acima com a imagem da página 6")
    print("   Esperado: múltiplos códigos (0170-017B) cada um com checkboxes")
    print("=" * 80)


if __name__ == "__main__":
    main()

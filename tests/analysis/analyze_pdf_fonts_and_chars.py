#!/usr/bin/env python3
"""
Analisa fontes e caracteres no PDF para encontrar checkboxes
"""

import fitz  # PyMuPDF
from pathlib import Path

def analyze_fonts_and_chars(pdf_path: Path, page_num: int = 0):
    """Analisa todas as fontes e caracteres da página"""
    
    print(f"\n{'='*80}")
    print(f"🔬 ANÁLISE DE FONTES E CARACTERES: {pdf_path.name}")
    print(f"📄 Página: {page_num + 1}")
    print(f"{'='*80}\n")
    
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # 1. Extrair texto com informações de fonte
    print("📝 EXTRAINDO TEXTO COM INFORMAÇÕES DE FONTE...\n")
    
    text_dict = page.get_text("dict")
    
    char_info = []
    unique_chars = set()
    fonts_used = set()
    
    for block in text_dict["blocks"]:
        if block["type"] == 0:  # Text block
            for line in block["lines"]:
                for span in line["spans"]:
                    font = span["font"]
                    fonts_used.add(font)
                    
                    for char in span["text"]:
                        char_code = ord(char)
                        unique_chars.add(char)
                        
                        # Caracteres suspeitos (checkbox-like)
                        if char_code < 32 or char_code > 126 or char in ['☐', '☒', '☑', '✓', '✗', '×', '■', '□']:
                            char_info.append({
                                'char': char,
                                'code': char_code,
                                'hex': hex(char_code),
                                'font': font,
                                'bbox': span["bbox"]
                            })
    
    # 2. Mostrar fontes usadas
    print(f"🔤 FONTES USADAS ({len(fonts_used)}):")
    print("-" * 80)
    for font in sorted(fonts_used):
        print(f"   • {font}")
    
    # 3. Caracteres especiais
    print(f"\n📋 CARACTERES ESPECIAIS/SUSPEITOS ({len(char_info)}):")
    print("-" * 80)
    
    if char_info:
        for info in char_info[:50]:  # Primeiros 50
            print(f"   '{info['char']}' → U+{info['hex'][2:].upper().zfill(4)} (dec:{info['code']}) | Fonte: {info['font']} | Pos: {info['bbox']}")
    else:
        print("   ❌ Nenhum caractere especial detectado")
    
    # 4. Todos os caracteres únicos
    print(f"\n🔍 TODOS OS CARACTERES ÚNICOS ({len(unique_chars)}):")
    print("-" * 80)
    
    # Agrupar por categoria
    special_unicode = []
    for char in sorted(unique_chars):
        code = ord(char)
        if code < 32:
            special_unicode.append(f"U+{hex(code)[2:].upper().zfill(4)} [Controle]")
        elif code > 126 and code < 256:
            special_unicode.append(f"'{char}' U+{hex(code)[2:].upper().zfill(4)} [Latin-1]")
        elif code >= 256:
            special_unicode.append(f"'{char}' U+{hex(code)[2:].upper().zfill(4)} [Unicode]")
    
    if special_unicode:
        print("   Caracteres especiais:")
        for char in special_unicode[:30]:
            print(f"   • {char}")
    else:
        print("   ❌ Apenas ASCII padrão (32-126)")
    
    # 5. Buscar por padrões de checkbox
    print(f"\n🔍 BUSCANDO PADRÕES DE CHECKBOX...")
    print("-" * 80)
    
    checkbox_patterns = {
        'ZapfDingbats': [0x2610, 0x2611, 0x2612, 0x2713, 0x2717, 0x2718],  # ☐☑☒✓✗✘
        'Wingdings': [0xA8, 0xFE],  # Códigos Wingdings para checkboxes
        'Symbol': [0xD7, 0xF7],  # × ÷
    }
    
    found_checkbox_chars = []
    for char in unique_chars:
        code = ord(char)
        for pattern_name, codes in checkbox_patterns.items():
            if code in codes:
                found_checkbox_chars.append(f"'{char}' U+{hex(code)[2:].upper().zfill(4)} ({pattern_name})")
    
    if found_checkbox_chars:
        print("   ✅ POSSÍVEIS CHECKBOXES ENCONTRADOS:")
        for item in found_checkbox_chars:
            print(f"   • {item}")
    else:
        print("   ❌ Nenhum padrão de checkbox Unicode conhecido detectado")
    
    # 6. Extrair texto raw da região dos checkboxes (LED 5)
    print(f"\n📍 TEXTO RAW DA REGIÃO 'LED 5' (linhas 300-600):")
    print("-" * 80)
    
    text_blocks = page.get_text("text").split('\n')
    led5_start = None
    for i, line in enumerate(text_blocks):
        if 'LED 5' in line or '0150:' in line:
            led5_start = i
            break
    
    if led5_start:
        relevant_lines = text_blocks[led5_start:led5_start+20]
        for line in relevant_lines:
            # Mostrar código de cada caractere
            char_codes = ' '.join([f"U+{hex(ord(c))[2:].upper().zfill(4)}" if ord(c) > 126 else repr(c) for c in line[:50]])
            print(f"   {line[:50]}")
            print(f"      → {char_codes}\n")
    
    doc.close()
    
    print("\n" + "="*80)
    print("✅ Análise concluída!")
    print("="*80)

def main():
    pdf_path = Path("inputs/pdf/P_122 52-MF-03B1_2021-03-17.pdf")
    
    if not pdf_path.exists():
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    analyze_fonts_and_chars(pdf_path, page_num=0)

if __name__ == "__main__":
    main()

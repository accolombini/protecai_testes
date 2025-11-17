#!/usr/bin/env python3
"""Teste simples de busca de palavra com >"""

# Simular resultado do debug
words_list = ['I', 'tI>>']

print("Palavras encontradas:", words_list)
print()

# Lógica atual
for word in words_list:
    if '>' in word:
        print(f"✅ Encontrado: '{word}'")
        break
else:
    print("❌ Nenhuma palavra com > encontrada")

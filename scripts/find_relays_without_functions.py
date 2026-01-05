#!/usr/bin/env python3
"""Script para encontrar relés sem funções de proteção"""
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='protecai_db',
    user='protecai',
    password='protecai'
)
cur = conn.cursor()

# Buscar todos os equipment_tag
cur.execute('SELECT equipment_tag FROM protec_ai.relay_equipment ORDER BY equipment_tag')
all_relays = [row[0] for row in cur.fetchall()]

# Buscar equipment_tag que têm funções ativas (remover extensões .S40, .pdf, etc)
cur.execute('SELECT DISTINCT relay_file FROM active_protection_functions ORDER BY relay_file')
relays_with_functions_raw = [row[0] for row in cur.fetchall()]

# Remover extensões dos nomes
import re
relays_with_functions = []
for relay in relays_with_functions_raw:
    # Remove .S40, .pdf, .txt, etc
    clean_name = re.sub(r'\.(S40|pdf|txt|xlsx)$', '', relay, flags=re.IGNORECASE)
    relays_with_functions.append(clean_name)

# Encontrar diferença
relays_without = [r for r in all_relays if r not in relays_with_functions]

print(f'Total de equipamentos: {len(all_relays)}')
print(f'Com funções ativas: {len(relays_with_functions)}')
print(f'SEM funções ativas: {len(relays_without)}')
print()
print('=' * 60)
print('RELÉS SEM FUNÇÕES DE PROTEÇÃO ATIVAS:')
print('=' * 60)
for i, relay in enumerate(relays_without, 1):
    print(f'{i:2d}. {relay}')

conn.close()

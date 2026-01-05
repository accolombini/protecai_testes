#!/usr/bin/env python3
"""
🔧 CORREÇÃO CRÍTICA: Extrair valores numéricos de set_value_text para set_value

Problema: Script de importação salvou TUDO em set_value_text (campo texto)
Solução: Re-processar 223.540 registros extraindo números para set_value (campo numérico)

Exemplos de conversão:
- "200" → set_value=200, unit=""
- "4160V" → set_value=4160, unit="V"
- "60Hz" → set_value=60, unit="Hz"
- "5.5A" → set_value=5.5, unit="A"
- "True" → set_value=NULL, set_value_text="True"
"""

import psycopg2
import re
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def parse_value(value_str: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Extrai valor numérico e unidade de uma string
    
    Returns:
        (set_value_numeric, set_value_text, unit)
    """
    if not value_str or value_str in ['', 'None', 'nan', 'NaN']:
        return (None, None, None)
    
    value_str = str(value_str).strip()
    
    # Regex para número + unidade opcional
    # Suporta: 200, -5.5, +3.14, 4160V, 60Hz, 5.5A
    match = re.match(r'^([+-]?\d+\.?\d*)\s*([A-Za-z%°]+)?$', value_str)
    
    if match:
        numeric = float(match.group(1))
        unit = match.group(2) if match.group(2) else None
        return (numeric, None, unit)
    else:
        # Não é numérico - manter como texto (True, False, Enable, etc.)
        return (None, value_str, None)


def main():
    logger.info("=" * 80)
    logger.info("🔧 CORREÇÃO: Extrair valores numéricos de set_value_text")
    logger.info("=" * 80)
    
    # Conectar ao banco
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="protecai_db",
            user="protecai",
            password="protecai2024"
        )
        logger.info("✅ Conectado ao PostgreSQL")
    except Exception as e:
        logger.error(f"❌ Erro de conexão: {e}")
        return False
    
    cursor = conn.cursor()
    
    # 1. Contar registros a processar
    cursor.execute("""
        SELECT COUNT(*) 
        FROM protec_ai.relay_settings 
        WHERE set_value IS NULL 
        AND set_value_text IS NOT NULL
        AND set_value_text != ''
    """)
    total = cursor.fetchone()[0]
    logger.info(f"\n📊 Total de registros a processar: {total:,}")
    
    if total == 0:
        logger.info("✅ Todos os registros já estão corretos!")
        conn.close()
        return True
    
    # 2. Processar em batches de 1000
    batch_size = 1000
    processed = 0
    updated_numeric = 0
    kept_text = 0
    
    cursor.execute("""
        SELECT id, set_value_text, unit_of_measure
        FROM protec_ai.relay_settings 
        WHERE set_value IS NULL 
        AND set_value_text IS NOT NULL
        AND set_value_text != ''
        ORDER BY id
    """)
    
    records = cursor.fetchall()
    logger.info(f"\n🔄 Processando {len(records):,} registros...")
    
    for record_id, value_text, current_unit in records:
        # Extrair número + unidade
        set_value, new_text, extracted_unit = parse_value(value_text)
        
        # Determinar unidade final (priorizar extraída)
        final_unit = extracted_unit if extracted_unit else current_unit
        
        if set_value is not None:
            # Valor numérico encontrado
            cursor.execute("""
                UPDATE protec_ai.relay_settings
                SET set_value = %s,
                    set_value_text = NULL,
                    unit_of_measure = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (set_value, final_unit, record_id))
            updated_numeric += 1
        else:
            # Manter como texto (booleanos, enums, etc.)
            cursor.execute("""
                UPDATE protec_ai.relay_settings
                SET set_value_text = %s,
                    unit_of_measure = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (new_text, final_unit, record_id))
            kept_text += 1
        
        processed += 1
        
        # Commit a cada batch
        if processed % batch_size == 0:
            conn.commit()
            percent = (processed / total) * 100
            logger.info(f"  ⏳ Progresso: {processed:,}/{total:,} ({percent:.1f}%)")
    
    # Commit final
    conn.commit()
    
    # 3. Estatísticas finais
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESULTADOS:")
    logger.info(f"  ✅ Total processado: {processed:,}")
    logger.info(f"  🔢 Convertidos para numérico: {updated_numeric:,}")
    logger.info(f"  📝 Mantidos como texto: {kept_text:,}")
    logger.info("=" * 80)
    
    # 4. Verificar resultados
    cursor.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE set_value IS NOT NULL) as com_valor_numerico,
            COUNT(*) FILTER (WHERE set_value_text IS NOT NULL) as com_valor_texto,
            COUNT(*) as total
        FROM protec_ai.relay_settings
        WHERE is_active = true
    """)
    row = cursor.fetchone()
    
    logger.info("\n📈 ESTADO FINAL DO BANCO:")
    logger.info(f"  🔢 Registros com valor numérico: {row[0]:,}")
    logger.info(f"  📝 Registros com valor texto: {row[1]:,}")
    logger.info(f"  📊 Total de registros ativos: {row[2]:,}")
    
    cursor.close()
    conn.close()
    
    logger.info("\n✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

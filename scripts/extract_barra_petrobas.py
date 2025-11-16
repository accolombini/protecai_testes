#!/usr/bin/env python3
"""
Script de Extração - Nomenclatura IEC 81346 / ANSI C37.2
=========================================================

Parser semântico baseado em normas internacionais:
- IEC 81346: Designação hierárquica de equipamentos
- ANSI C37.2: Códigos de função (52=Disjuntor, 53=Seccionadora)
- IEC 61850: Logical Nodes e estrutura de bays

Padrões identificados (50 equipamentos):
1. Formato Completo IEC:     P122_204-PN-06_LADO_A_2014-08-01
2. Formato ANSI com espaço:   P122 52-MF-02A_2021-03-08
3. Formato Zona Especial:     P122_52-Z-08_L_PATIO_2014-08-06
4. Formato Legacy:            00-MF-12_2016-03-31
5. Variações pontuais:        P220-52-MP-08B (hífen no modelo)

Extrai e valida:
- Modelo do relé (P122, P143, P220, P241, P922, SEPAM)
- Código ANSI (52=Disjuntor, 53=Seccionadora, 54=?)
- Subestação (204, 205, 223)
- Barra (MF, PN, MP, MK, TF, Z)
- Bay/Alimentador (06, 2C, 02AC, etc.)
- Lado (LADO_A/B) ou Localização (L_PATIO, L_REATOR)
- Data de parametrização

Data: 16 de novembro de 2025
Autor: GitHub Copilot + Engenharia Petrobras
"""

import re
import psycopg2
from datetime import datetime
from typing import Dict, Optional, Tuple
from enum import Enum
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração do banco
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}


class PadraoNomenclatura(Enum):
    """Tipos de padrão identificados segundo IEC 81346"""
    COMPLETO_IEC = 1      # P122_204-PN-06_LADO_A_2014-08-01
    ANSI_ESPACADO = 2     # P122 52-MF-02A_2021-03-08
    ZONA_ESPECIAL = 3     # P122_52-Z-08_L_PATIO
    LEGACY = 4            # 00-MF-12_2016-03-31
    HIBRIDO = 5           # P220-52-MP-08B (variações)


# Dicionário ANSI C37.2 (IEEE Device Numbers)
CODIGO_ANSI = {
    '27': 'Relé de Subtensão',
    '50': 'Relé de Sobrecorrente Instantâneo',
    '51': 'Relé de Sobrecorrente Temporizado',
    '52': 'Disjuntor',
    '53': 'Relé de Excitação ou Seccionadora',
    '54': 'Transformador de Aterramento',
    '59': 'Relé de Sobretensão',
    '81': 'Relé de Frequência',
    '87': 'Relé Diferencial'
}


def identificar_padrao(equipment_tag: str) -> Tuple[PadraoNomenclatura, str]:
    """
    Identifica qual padrão IEC/ANSI o equipment_tag segue.
    
    Returns:
        (PadraoNomenclatura, descrição)
    """
    if not equipment_tag:
        return (None, "Tag vazia")
    
    # Padrão 4: Legacy (sem modelo de relé)
    if re.match(r'^\d{2}-[A-Z]{2}-\d+', equipment_tag):
        return (PadraoNomenclatura.LEGACY, "Formato Legacy (sem modelo)")
    
    # Padrão 3: Zona Especial (contém -Z-)
    if re.search(r'-Z-\d+', equipment_tag):
        return (PadraoNomenclatura.ZONA_ESPECIAL, "Zona Auxiliar (Pátio/Reator)")
    
    # Padrão 2: ANSI com espaço (ex: P122 52-MF)
    if re.match(r'^[A-Z_]+\d{3,4}[A-Z]?\s+\d{2,3}-', equipment_tag):
        return (PadraoNomenclatura.ANSI_ESPACADO, "ANSI C37.2 com espaço")
    
    # Padrão 5: Híbrido (hífen no modelo: P220-52-MP)
    if re.match(r'^[A-Z]+\d{3,4}-\d{2,3}-', equipment_tag):
        return (PadraoNomenclatura.HIBRIDO, "Formato Híbrido (modelo-ANSI)")
    
    # Padrão 1: Completo IEC 81346 (underscore separando)
    if re.match(r'^[A-Z_]+\d{3,4}[A-Z]?_\d{2,3}-[A-Z]{2,3}-', equipment_tag):
        return (PadraoNomenclatura.COMPLETO_IEC, "IEC 81346 Completo")
    
    return (None, f"Padrão não reconhecido: {equipment_tag[:30]}")


def extrair_dados_equipment_tag(equipment_tag: str) -> Dict[str, Optional[str]]:
    """
    Parser semântico baseado em IEC 81346 + ANSI C37.2.
    
    Identifica o padrão e extrai dados de forma inteligente,
    validando segundo normas internacionais.
    
    Returns:
        dict com: modelo, subestacao, barra, alimentador, lado, data, 
                 codigo_ansi, padrao_identificado, validacao
    """
    resultado = {
        'modelo': None,
        'subestacao': None,
        'barra': None,
        'alimentador': None,
        'lado': None,
        'data': None,
        'codigo_ansi': None,
        'padrao': None,
        'descricao_ansi': None
    }
    
    if not equipment_tag or equipment_tag.strip() == '':
        return resultado
    
    # Identificar padrão
    padrao, desc = identificar_padrao(equipment_tag)
    resultado['padrao'] = padrao.name if padrao else 'DESCONHECIDO'
    
    # ========================================================================
    # EXTRAÇÃO DO MODELO DO RELÉ
    # ========================================================================
    # Aceita: P122, P_122, P122S, P220, SEPAM, etc.
    match_modelo = re.match(r'^([A-Z_]+\d{3,4}[A-Z]?)', equipment_tag)
    if match_modelo:
        resultado['modelo'] = match_modelo.group(1).replace('_', '')
    
    # ========================================================================
    # EXTRAÇÃO BASEADA NO PADRÃO IDENTIFICADO
    # ========================================================================
    
    if padrao == PadraoNomenclatura.LEGACY:
        # Formato: 00-MF-12_2016-03-31
        match = re.match(r'^(\d{2})-([A-Z]{2,3})-([A-Z0-9]+)', equipment_tag)
        if match:
            resultado['codigo_ansi'] = match.group(1)  # 00 como ANSI especial
            resultado['barra'] = match.group(2)
            resultado['alimentador'] = match.group(3)
    
    elif padrao == PadraoNomenclatura.ZONA_ESPECIAL:
        # Formato: P122_52-Z-08_L_PATIO_2014-08-06
        match = re.search(r'(\d{2,3})-Z-([A-Z0-9]+)', equipment_tag)
        if match:
            resultado['codigo_ansi'] = match.group(1)
            resultado['barra'] = 'Z'  # Zona especial
            resultado['alimentador'] = match.group(2)
            resultado['descricao_ansi'] = CODIGO_ANSI.get(match.group(1), 'Desconhecido')
    
    elif padrao == PadraoNomenclatura.ANSI_ESPACADO:
        # Formato: P122 52-MF-02A_2021-03-08
        match = re.search(r'\s+(\d{2,3})-([A-Z]{2,3})-([A-Z0-9]+)', equipment_tag)
        if match:
            resultado['codigo_ansi'] = match.group(1)
            resultado['barra'] = match.group(2)
            resultado['alimentador'] = match.group(3)
            resultado['descricao_ansi'] = CODIGO_ANSI.get(match.group(1), 'Desconhecido')
    
    elif padrao == PadraoNomenclatura.HIBRIDO:
        # Formato: P220-52-MP-08B_2016-03-11
        match = re.search(r'-(\d{2,3})-([A-Z]{2,3})-([A-Z0-9]+)', equipment_tag)
        if match:
            resultado['codigo_ansi'] = match.group(1)
            resultado['barra'] = match.group(2)
            resultado['alimentador'] = match.group(3)
            resultado['descricao_ansi'] = CODIGO_ANSI.get(match.group(1), 'Desconhecido')
    
    elif padrao == PadraoNomenclatura.COMPLETO_IEC:
        # Formato: P122_204-PN-06_LADO_A_2014-08-01
        match = re.search(r'_(\d{2,3})-([A-Z]{2,3})-([A-Z0-9]+)', equipment_tag)
        if match:
            resultado['subestacao'] = match.group(1)
            resultado['barra'] = match.group(2)
            resultado['alimentador'] = match.group(3)
    
    # ========================================================================
    # EXTRAÇÃO DE CAMPOS AUXILIARES (todos os padrões)
    # ========================================================================
    
    # Lado da barra (IEC 61850 Logical Node)
    match_lado = re.search(r'_(LADO[_\s]*[AB]|L[_\s]*(PATIO|REATOR))', equipment_tag, re.IGNORECASE)
    if match_lado:
        resultado['lado'] = match_lado.group(1).replace(' ', '_').upper()
    
    # Data de parametrização
    match_data = re.search(r'(\d{4}-\d{2}-\d{2})', equipment_tag)
    if match_data:
        resultado['data'] = match_data.group(1)
    
    return resultado


def popular_barra_banco():
    """
    Conecta ao banco e popula campos de barra para todos os equipamentos.
    Usa parser semântico baseado em IEC 81346 + ANSI C37.2.
    """
    conn = None
    try:
        # Conectar ao banco
        logger.info("🔌 Conectando ao PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Buscar todos os equipamentos
        logger.info("📊 Buscando equipamentos...")
        cur.execute("""
            SELECT id, equipment_tag 
            FROM protec_ai.relay_equipment 
            ORDER BY id
        """)
        equipamentos = cur.fetchall()
        logger.info(f"✅ Encontrados {len(equipamentos)} equipamentos")
        
        # Estatísticas por padrão
        stats_padrao = {
            'COMPLETO_IEC': 0,
            'ANSI_ESPACADO': 0,
            'ZONA_ESPECIAL': 0,
            'LEGACY': 0,
            'HIBRIDO': 0,
            'DESCONHECIDO': 0
        }
        
        # Processar cada equipamento
        sucesso = 0
        erro = 0
        sem_barra = 0
        
        logger.info("\n" + "="*100)
        logger.info("📋 PROCESSAMENTO POR EQUIPAMENTO (Validação IEC 81346 + ANSI C37.2)")
        logger.info("="*100)
        
        for eq_id, eq_tag in equipamentos:
            try:
                # Extrair dados
                dados = extrair_dados_equipment_tag(eq_tag)
                
                # Atualizar estatísticas
                stats_padrao[dados['padrao']] += 1
                
                if not dados['barra']:
                    logger.warning(f"⚠️  ID {eq_id:2d} ({eq_tag:45s}) → Padrão: {dados['padrao']:15s} | BARRA NÃO IDENTIFICADA")
                    sem_barra += 1
                    continue
                
                # Atualizar banco
                cur.execute("""
                    UPDATE protec_ai.relay_equipment
                    SET 
                        barra_nome = %s,
                        subestacao_codigo = %s,
                        alimentador_numero = %s,
                        lado_barra = %s,
                        data_parametrizacao = %s,
                        codigo_ansi_equipamento = %s
                    WHERE id = %s
                """, (
                    dados['barra'],
                    dados['subestacao'],
                    dados['alimentador'],
                    dados['lado'],
                    dados['data'],
                    dados['codigo_ansi'],
                    eq_id
                ))
                
                # Log detalhado com validação ANSI
                ansi_info = f" | ANSI {dados['codigo_ansi']} ({dados['descricao_ansi']})" if dados['codigo_ansi'] else ""
                logger.info(
                    f"✅ ID {eq_id:2d} | Padrão: {dados['padrao']:15s} | "
                    f"Barra: {dados['barra']:3s} | Sub: {dados['subestacao'] or 'N/A':3s} | "
                    f"Alim: {dados['alimentador']:6s}{ansi_info}"
                )
                sucesso += 1
                
            except Exception as e:
                logger.error(f"❌ Erro no ID {eq_id} ({eq_tag}): {e}")
                erro += 1
        
        # Commit das mudanças
        conn.commit()
        
        # Resumo
        logger.info("\n" + "="*100)
        logger.info("📊 RESUMO DA EXTRAÇÃO (IEC 81346 + ANSI C37.2)")
        logger.info("="*100)
        logger.info(f"✅ Sucesso:            {sucesso:3d} equipamentos")
        logger.info(f"⚠️  Sem barra:          {sem_barra:3d} equipamentos")
        logger.info(f"❌ Erros:              {erro:3d} equipamentos")
        logger.info(f"📦 Total processado:   {len(equipamentos):3d} equipamentos")
        logger.info("="*100)
        
        # Estatísticas por padrão
        logger.info("\n📊 DISTRIBUIÇÃO POR PADRÃO IEC/ANSI:")
        logger.info("-"*100)
        for padrao, count in sorted(stats_padrao.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                pct = (count/len(equipamentos))*100
                logger.info(f"   {padrao:20s}: {count:3d} equipamentos ({pct:5.1f}%)")
        logger.info("-"*100)
        
        # Validação final
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(barra_nome) as com_barra,
                COUNT(subestacao_codigo) as com_sub,
                COUNT(alimentador_numero) as com_alim,
                COUNT(codigo_ansi_equipamento) as com_ansi,
                COUNT(lado_barra) as com_lado
            FROM protec_ai.relay_equipment
        """)
        total, com_barra, com_sub, com_alim, com_ansi, com_lado = cur.fetchone()
        
        logger.info("\n📊 VALIDAÇÃO FINAL NO BANCO:")
        logger.info("-"*100)
        logger.info(f"   Total de equipamentos:      {total:3d}")
        logger.info(f"   Com barra_nome:             {com_barra:3d} ({com_barra/total*100:5.1f}%)")
        logger.info(f"   Com subestacao_codigo:      {com_sub:3d} ({com_sub/total*100:5.1f}%)")
        logger.info(f"   Com alimentador_numero:     {com_alim:3d} ({com_alim/total*100:5.1f}%)")
        logger.info(f"   Com codigo_ansi:            {com_ansi:3d} ({com_ansi/total*100:5.1f}%)")
        logger.info(f"   Com lado_barra:             {com_lado:3d} ({com_lado/total*100:5.1f}%)")
        logger.info("-"*100)
        
        # Validação de códigos ANSI
        cur.execute("""
            SELECT codigo_ansi_equipamento, COUNT(*) as total
            FROM protec_ai.relay_equipment
            WHERE codigo_ansi_equipamento IS NOT NULL
            GROUP BY codigo_ansi_equipamento
            ORDER BY codigo_ansi_equipamento
        """)
        ansi_counts = cur.fetchall()
        
        if ansi_counts:
            logger.info("\n📊 VALIDAÇÃO ANSI C37.2 (Códigos de Função):")
            logger.info("-"*100)
            for codigo, count in ansi_counts:
                descricao = CODIGO_ANSI.get(codigo, 'Código não catalogado')
                logger.info(f"   ANSI {codigo:3s}: {count:3d} equipamentos → {descricao}")
            logger.info("-"*100)
        
        cur.close()
        
    except psycopg2.Error as e:
        logger.error(f"❌ Erro no PostgreSQL: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"❌ Erro geral: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logger.info("\n🔌 Conexão fechada")


def testar_extrator():
    """Testa extração em exemplos reais do banco."""
    exemplos = [
        # Padrão 1: IEC 81346 Completo
        "P122_204-PN-06_LADO_A_2014-08-01",
        "P143_204-MF-2C_2018-06-13",
        
        # Padrão 2: ANSI Espaçado
        "P122 52-MF-02A_2021-03-08",
        "P220 52-MP-01A",
        "P922 52-MF-02AC",
        
        # Padrão 3: Zona Especial
        "P122_52-Z-08_L_PATIO_2014-08-06",
        "P122_52-Z-08_L_REATOR_2014-08-07",
        
        # Padrão 4: Legacy
        "00-MF-12_2016-03-31",
        
        # Padrão 5: Híbrido
        "P220-52-MP-08B_2016-03-11",
        "P_122 52-MF-03B1_2021-03-17"
    ]
    
    print("\n" + "="*100)
    print("🧪 TESTE DE EXTRAÇÃO - Parser Semântico IEC 81346 + ANSI C37.2")
    print("="*100)
    
    for tag in exemplos:
        dados = extrair_dados_equipment_tag(tag)
        padrao, desc = identificar_padrao(tag)
        
        print(f"\n📌 {tag}")
        print(f"   {'Padrão:':<20s} {dados['padrao']} ({desc})")
        print(f"   {'Modelo:':<20s} {dados['modelo']}")
        print(f"   {'Subestação:':<20s} {dados['subestacao']}")
        print(f"   {'Barra:':<20s} {dados['barra']} ← CAMPO PRINCIPAL")
        print(f"   {'Alimentador:':<20s} {dados['alimentador']}")
        print(f"   {'Lado:':<20s} {dados['lado']}")
        print(f"   {'Data:':<20s} {dados['data']}")
        if dados['codigo_ansi']:
            print(f"   {'Código ANSI:':<20s} {dados['codigo_ansi']} ({dados['descricao_ansi']})")


if __name__ == '__main__':
    print("\n" + "="*100)
    print("🚀 EXTRAÇÃO DE BARRA - Parser Semântico IEC 81346 / ANSI C37.2")
    print("="*100)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Normas: IEC 81346 (Hierarquia) + ANSI C37.2 (Funções) + IEC 61850 (Logical Nodes)")
    print("="*100 + "\n")
    
    # Testar primeiro
    testar_extrator()
    
    # Perguntar confirmação
    print("\n" + "="*100)
    resposta = input("🤔 Deseja executar a população do banco? (s/n): ")
    
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        popular_barra_banco()
        print("\n✅ PROCESSO CONCLUÍDO COM SUCESSO!")
    else:
        print("\n❌ Operação cancelada pelo usuário")

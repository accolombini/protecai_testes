#!/usr/bin/env python3
"""
Script de Validação da Importação de Dados
==========================================

Valida e demonstra os dados importados para PostgreSQL,
executando consultas analíticas e gerando relatórios.

Autor: ProtecAI System
Data: 2025-10-05
"""

import pandas as pd
import sys
from pathlib import Path
import json
from datetime import datetime

# Simular consultas PostgreSQL usando pandas para validação
def validar_estrutura_csv():
    """Valida a estrutura dos arquivos CSV normalizados."""
    print("🔍 VALIDAÇÃO DA ESTRUTURA DOS DADOS")
    print("="*50)
    
    csv_dir = Path("outputs/norm_csv")
    arquivos_csv = list(csv_dir.glob("*_normalized.csv"))
    
    if not arquivos_csv:
        print("❌ Nenhum arquivo CSV normalizado encontrado!")
        return False
    
    print(f"📁 Encontrados {len(arquivos_csv)} arquivos CSV:")
    for arquivo in arquivos_csv:
        print(f"   - {arquivo.name}")
    
    # Analisar primeiro arquivo em detalhes
    arquivo_principal = arquivos_csv[0]
    df = pd.read_csv(arquivo_principal)
    
    print(f"\n📊 ANÁLISE DETALHADA: {arquivo_principal.name}")
    print(f"   • Total de registros: {len(df)}")
    print(f"   • Total de colunas: {len(df.columns)}")
    
    # Verificar colunas esperadas
    colunas_esperadas = [
        'arquivo_origem', 'identificador_arquivo', 'fabricante', 'codigo_campo',
        'descricao_campo', 'nome_coluna', 'valor_original', 'eh_atomico',
        'padrao_detectado', 'processado_em', 'num_partes', 'confianca_geral'
    ]
    
    colunas_presentes = [col for col in colunas_esperadas if col in df.columns]
    colunas_ausentes = [col for col in colunas_esperadas if col not in df.columns]
    
    print(f"   • Colunas principais presentes: {len(colunas_presentes)}/{len(colunas_esperadas)}")
    if colunas_ausentes:
        print(f"   ⚠️  Colunas ausentes: {colunas_ausentes}")
    
    # Contar colunas de tokens (parte_1 até parte_7, etc.)
    colunas_tokens = [col for col in df.columns if col.startswith(('parte_', 'tipo_', 'significado_', 'confianca_'))]
    print(f"   • Colunas de tokens: {len(colunas_tokens)}")
    
    return True, df

def analisar_dados_por_fabricante(df):
    """Analisa distribuição de dados por fabricante."""
    print("\n🏭 ANÁLISE POR FABRICANTE")
    print("="*50)
    
    fabricantes = df['fabricante'].value_counts()
    print("Distribuição de registros por fabricante:")
    for fabricante, count in fabricantes.items():
        percentual = (count / len(df)) * 100
        print(f"   • {fabricante.title()}: {count:,} registros ({percentual:.1f}%)")
    
    # Análise de valores multivalorados por fabricante
    print("\nAnálise de valores multivalorados:")
    for fabricante in fabricantes.index:
        fab_data = df[df['fabricante'] == fabricante]
        multivalorados = fab_data[fab_data['eh_atomico'] == False]
        percentual_multi = (len(multivalorados) / len(fab_data)) * 100
        print(f"   • {fabricante.title()}: {len(multivalorados)}/{len(fab_data)} ({percentual_multi:.1f}%) multivalorados")

def analisar_padroes_detectados(df):
    """Analisa padrões detectados pelo parser."""
    print("\n🔍 PADRÕES DETECTADOS")
    print("="*50)
    
    padroes = df['padrao_detectado'].value_counts()
    print("Frequência de padrões detectados:")
    for padrao, count in padroes.items():
        percentual = (count / len(df)) * 100
        print(f"   • {padrao}: {count:,} ocorrências ({percentual:.1f}%)")

def analisar_confianca_processamento(df):
    """Analisa níveis de confiança do processamento."""
    print("\n📈 ANÁLISE DE CONFIANÇA")
    print("="*50)
    
    # Estatísticas de confiança geral
    confianca_stats = df['confianca_geral'].describe()
    print("Estatísticas de confiança geral:")
    print(f"   • Média: {confianca_stats['mean']:.3f}")
    print(f"   • Mediana: {confianca_stats['50%']:.3f}")
    print(f"   • Mínima: {confianca_stats['min']:.3f}")
    print(f"   • Máxima: {confianca_stats['max']:.3f}")
    
    # Distribuição por faixas de confiança
    print("\nDistribuição por faixas de confiança:")
    df['faixa_confianca'] = pd.cut(df['confianca_geral'], 
                                   bins=[0, 0.5, 0.7, 0.9, 1.0], 
                                   labels=['Baixa (0-0.5)', 'Média (0.5-0.7)', 'Alta (0.7-0.9)', 'Muito Alta (0.9-1.0)'])
    
    faixas = df['faixa_confianca'].value_counts()
    for faixa, count in faixas.items():
        percentual = (count / len(df)) * 100
        print(f"   • {faixa}: {count:,} registros ({percentual:.1f}%)")

def analisar_tokens_mais_frequentes(df):
    """Analisa os tokens mais frequentes."""
    print("\n🔤 TOKENS MAIS FREQUENTES")
    print("="*50)
    
    # Coletar todos os tokens das partes 1-7
    todos_tokens = []
    todos_tipos = []
    
    for i in range(1, 8):
        parte_col = f'parte_{i}'
        tipo_col = f'tipo_{i}'
        
        if parte_col in df.columns:
            tokens_validos = df[df[parte_col].notna()][parte_col].astype(str)
            tipos_validos = df[df[tipo_col].notna()][tipo_col].astype(str)
            
            todos_tokens.extend(tokens_validos.tolist())
            todos_tipos.extend(tipos_validos.tolist())
    
    # Top 10 tokens mais frequentes
    if todos_tokens:
        tokens_freq = pd.Series(todos_tokens).value_counts().head(10)
        print("Top 10 tokens mais frequentes:")
        for token, freq in tokens_freq.items():
            print(f"   • '{token}': {freq:,} ocorrências")
    
    # Top 10 tipos de token mais frequentes
    if todos_tipos:
        tipos_freq = pd.Series(todos_tipos).value_counts().head(10)
        print(f"\nTop 10 tipos de token mais frequentes:")
        for tipo, freq in tipos_freq.items():
            print(f"   • {tipo}: {freq:,} ocorrências")

def analisar_codigos_ansi(df):
    """Analisa códigos ANSI específicos."""
    print("\n⚡ CÓDIGOS ANSI DETECTADOS")
    print("="*50)
    
    # Buscar tokens que são códigos ANSI
    codigos_ansi = []
    
    for i in range(1, 8):
        tipo_col = f'tipo_{i}'
        parte_col = f'parte_{i}'
        significado_col = f'significado_{i}'
        
        if tipo_col in df.columns:
            mask_ansi = df[tipo_col] == 'ansi_code'
            ansi_data = df[mask_ansi]
            
            for _, row in ansi_data.iterrows():
                if pd.notna(row[parte_col]):
                    codigos_ansi.append({
                        'codigo': row[parte_col],
                        'significado': row[significado_col] if pd.notna(row[significado_col]) else 'N/A',
                        'fabricante': row['fabricante']
                    })
    
    if codigos_ansi:
        # Converter para DataFrame para análise
        df_ansi = pd.DataFrame(codigos_ansi)
        
        # Códigos ANSI únicos
        codigos_unicos = df_ansi.groupby(['codigo', 'significado']).size().sort_values(ascending=False)
        print("Códigos ANSI detectados (Top 10):")
        for (codigo, significado), freq in codigos_unicos.head(10).items():
            print(f"   • Código {codigo}: {significado} ({freq} ocorrências)")
        
        # Por fabricante
        print(f"\nDistribuição de códigos ANSI por fabricante:")
        por_fabricante = df_ansi.groupby('fabricante')['codigo'].nunique()
        for fabricante, count in por_fabricante.items():
            print(f"   • {fabricante.title()}: {count} códigos ANSI únicos")

def analisar_complexidade_valores(df):
    """Analisa complexidade dos valores (número de partes)."""
    print("\n🧩 COMPLEXIDADE DOS VALORES")
    print("="*50)
    
    complexidade = df['num_partes'].value_counts().sort_index()
    print("Distribuição por número de partes:")
    for partes, count in complexidade.items():
        percentual = (count / len(df)) * 100
        print(f"   • {int(partes)} partes: {count:,} valores ({percentual:.1f}%)")
    
    # Valores mais complexos
    mais_complexos = df[df['num_partes'] >= 5].nlargest(5, 'num_partes')[
        ['fabricante', 'codigo_campo', 'descricao_campo', 'valor_original', 'num_partes', 'confianca_geral']
    ]
    
    if not mais_complexos.empty:
        print(f"\nValores mais complexos (≥5 partes):")
        for _, row in mais_complexos.iterrows():
            print(f"   • {row['valor_original']} ({int(row['num_partes'])} partes, {row['confianca_geral']:.3f} confiança)")
            print(f"     {row['fabricante'].title()} - {row['descricao_campo']}")

def gerar_relatorio_validacao():
    """Gera relatório completo de validação."""
    print("\n📋 RELATÓRIO DE VALIDAÇÃO COMPLETO")
    print("="*60)
    
    # Verificar se os dados existem
    sucesso, df = validar_estrutura_csv()
    if not sucesso:
        return
    
    # Executar todas as análises
    analisar_dados_por_fabricante(df)
    analisar_padroes_detectados(df)
    analisar_confianca_processamento(df)
    analisar_tokens_mais_frequentes(df)
    analisar_codigos_ansi(df)
    analisar_complexidade_valores(df)
    
    # Resumo final
    print(f"\n✅ RESUMO FINAL")
    print("="*50)
    print(f"   • Total de registros analisados: {len(df):,}")
    print(f"   • Valores atômicos: {len(df[df['eh_atomico'] == True]):,}")
    print(f"   • Valores multivalorados: {len(df[df['eh_atomico'] == False]):,}")
    print(f"   • Fabricantes únicos: {df['fabricante'].nunique()}")
    print(f"   • Códigos de campo únicos: {df['codigo_campo'].nunique()}")
    print(f"   • Padrões detectados: {df['padrao_detectado'].nunique()}")
    print(f"   • Confiança média geral: {df['confianca_geral'].mean():.3f}")
    
    print(f"\n🎯 VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
    print(f"   Os dados estão prontos para importação no PostgreSQL.")

def gerar_script_sql_exemplo():
    """Gera script SQL de exemplo para consultas após importação."""
    sql_queries = """
-- =====================================================
-- CONSULTAS DE EXEMPLO APÓS IMPORTAÇÃO
-- =====================================================

-- 1. Estatísticas gerais por fabricante
SELECT 
    f.nome as fabricante,
    COUNT(*) as total_parametros,
    COUNT(CASE WHEN p.eh_atomico = false THEN 1 END) as multivalorados,
    ROUND(AVG(p.confianca_geral), 3) as confianca_media,
    COUNT(DISTINCT p.codigo_campo) as codigos_distintos
FROM parametros_normalizados p
    JOIN fabricantes f ON p.fabricante_id = f.id
GROUP BY f.nome
ORDER BY total_parametros DESC;

-- 2. Códigos ANSI mais frequentes
SELECT 
    tn.valor_token as codigo_ansi,
    tn.significado,
    COUNT(*) as frequencia,
    ROUND(AVG(tn.confianca), 3) as confianca_media
FROM tokens_normalizados tn
    JOIN tipos_token tt ON tn.tipo_token_id = tt.id
WHERE tt.codigo = 'ansi_code'
GROUP BY tn.valor_token, tn.significado
ORDER BY frequencia DESC
LIMIT 10;

-- 3. Parâmetros com maior complexidade
SELECT 
    ao.identificador,
    f.nome as fabricante,
    p.codigo_campo,
    p.descricao_campo,
    p.valor_original,
    p.num_partes,
    p.confianca_geral
FROM parametros_normalizados p
    JOIN arquivos_origem ao ON p.arquivo_origem_id = ao.id
    JOIN fabricantes f ON p.fabricante_id = f.id
WHERE p.num_partes > 3
ORDER BY p.num_partes DESC, p.confianca_geral DESC
LIMIT 20;

-- 4. Modelos de equipamentos Schneider
SELECT 
    p.valor_original as modelo_completo,
    STRING_AGG(
        CONCAT(tt.codigo, ':', tn.valor_token),
        ' | '
        ORDER BY tn.posicao
    ) as componentes
FROM parametros_normalizados p
    JOIN fabricantes f ON p.fabricante_id = f.id
    JOIN tokens_normalizados tn ON p.id = tn.parametro_id
    JOIN tipos_token tt ON tn.tipo_token_id = tt.id
WHERE f.nome = 'schneider' 
    AND p.descricao_campo ILIKE '%model%'
    AND tt.codigo LIKE 'model_%'
GROUP BY p.valor_original
ORDER BY p.valor_original;

-- 5. Análise de confiança por padrão detectado
SELECT 
    pd.codigo as padrao,
    pd.nome,
    COUNT(*) as total_ocorrencias,
    ROUND(AVG(p.confianca_geral), 3) as confianca_media,
    ROUND(MIN(p.confianca_geral), 3) as confianca_minima,
    ROUND(MAX(p.confianca_geral), 3) as confianca_maxima
FROM parametros_normalizados p
    JOIN padroes_detectados pd ON p.padrao_detectado_id = pd.id
GROUP BY pd.codigo, pd.nome
ORDER BY total_ocorrencias DESC;

-- 6. Referências de planta (Plant References)
SELECT 
    ao.identificador as arquivo,
    p.valor_original as referencia_planta,
    STRING_AGG(tn.valor_token, '-' ORDER BY tn.posicao) as componentes_separados
FROM parametros_normalizados p
    JOIN arquivos_origem ao ON p.arquivo_origem_id = ao.id
    JOIN tokens_normalizados tn ON p.id = tn.parametro_id
    JOIN tipos_token tt ON tn.tipo_token_id = tt.id
WHERE p.descricao_campo ILIKE '%plant%reference%'
    AND tt.codigo = 'plant_reference'
GROUP BY ao.identificador, p.valor_original
ORDER BY ao.identificador, p.valor_original;
"""
    
    with open('docs/CONSULTAS_EXEMPLO_POSTGRESQL.sql', 'w', encoding='utf-8') as f:
        f.write(sql_queries)
    
    print(f"\n📄 Script SQL de exemplo salvo em: docs/CONSULTAS_EXEMPLO_POSTGRESQL.sql")

def main():
    """Função principal para validação."""
    print("🚀 INICIANDO VALIDAÇÃO DOS DADOS NORMALIZADOS")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Executar validação completa
        gerar_relatorio_validacao()
        
        # Gerar scripts de exemplo
        gerar_script_sql_exemplo()
        
        print(f"\n🎉 PROCESSO DE VALIDAÇÃO CONCLUÍDO COM SUCESSO!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE VALIDAÇÃO: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
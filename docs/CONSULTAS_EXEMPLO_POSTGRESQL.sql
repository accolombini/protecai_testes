
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

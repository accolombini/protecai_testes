-- =====================================================
-- MODELAGEM DE DADOS NORMALIZADA - ESTRUTURA FINAL
-- Baseado na análise dos dados reais e proposta de normalização
-- Data: 2025-10-05
-- Estrutura: 6 tabelas principais com normalização adequada
-- =====================================================

-- Criar schema para isolamento
CREATE SCHEMA IF NOT EXISTS protec_ai;
SET search_path TO protec_ai;

-- =====================================================
-- TABELAS MESTRES
-- =====================================================

-- Fabricantes/fornecedores de equipamentos de proteção
CREATE TABLE fabricantes (
    id SERIAL PRIMARY KEY,
    codigo_fabricante VARCHAR(50) NOT NULL UNIQUE, -- "schneider", "abb", etc.
    nome_completo VARCHAR(200) NOT NULL, -- "Schneider Electric"
    pais_origem VARCHAR(100),
    certificacoes TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tipos de tokens normalizados
CREATE TABLE tipos_token (
    id SERIAL PRIMARY KEY,
    codigo_tipo VARCHAR(50) NOT NULL UNIQUE, -- "ansi_code", "model_prefix", etc.
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    categoria VARCHAR(50), -- "codigo_ansi", "identificacao", "especificacao_tecnica"
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- TABELAS PRINCIPAIS
-- =====================================================

-- Arquivos processados (origem dos dados)
CREATE TABLE arquivos (
    id SERIAL PRIMARY KEY,
    nome_arquivo VARCHAR(255) NOT NULL, -- "tela1_params_clean.xlsx"
    identificador VARCHAR(50) NOT NULL, -- "tela1", "tela3"
    fabricante_id INTEGER NOT NULL REFERENCES fabricantes(id),
    caminho_completo TEXT,
    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_processamento TIMESTAMP,
    status_processamento VARCHAR(50) DEFAULT 'pendente', -- 'pendente', 'processado', 'erro'
    total_registros INTEGER,
    registros_multivalorados INTEGER,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Garantir unicidade por identificador e fabricante
    CONSTRAINT uk_arquivo_identificador UNIQUE (identificador, fabricante_id)
);

-- Definições dos campos originais (elimina redundância)
CREATE TABLE campos_originais (
    id SERIAL PRIMARY KEY,
    arquivo_id INTEGER NOT NULL REFERENCES arquivos(id),
    codigo_campo VARCHAR(20) NOT NULL, -- "00.04", "00.05", "30.01"
    nome_coluna VARCHAR(100) NOT NULL, -- "Value", "Valor_Num"
    descricao_campo VARCHAR(200) NOT NULL, -- "Description", "Model Number"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Garantir unicidade por arquivo + campo + coluna
    CONSTRAINT uk_campo_arquivo UNIQUE (arquivo_id, codigo_campo, nome_coluna)
);

-- Valores originais processados
CREATE TABLE valores_originais (
    id SERIAL PRIMARY KEY,
    campo_id INTEGER NOT NULL REFERENCES campos_originais(id),
    valor_original TEXT NOT NULL,
    eh_multivalorado BOOLEAN NOT NULL DEFAULT FALSE, -- Invertido: !eh_atomico
    padrao_detectado VARCHAR(50), -- "atomic", "ansi_full", "schneider_model"
    num_partes INTEGER NOT NULL DEFAULT 1,
    confianca_geral DECIMAL(3,3), -- 0.000 a 1.000
    processado_em TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tokens individuais dos valores multivalorados
CREATE TABLE tokens_valores (
    id SERIAL PRIMARY KEY,
    valor_id INTEGER NOT NULL REFERENCES valores_originais(id) ON DELETE CASCADE,
    posicao_token INTEGER NOT NULL CHECK (posicao_token >= 1 AND posicao_token <= 7),
    valor_token VARCHAR(200) NOT NULL,
    tipo_token_id INTEGER REFERENCES tipos_token(id),
    significado TEXT,
    confianca DECIMAL(3,3), -- 0.000 a 1.000
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Garantir ordem dos tokens
    CONSTRAINT uk_token_posicao UNIQUE (valor_id, posicao_token)
);

-- =====================================================
-- VIEWS PARA CONSULTAS FACILITADAS
-- =====================================================

-- View principal reconstituindo a estrutura horizontal
CREATE VIEW vw_dados_completos AS
SELECT 
    a.identificador as arquivo,
    f.codigo_fabricante as fabricante,
    f.nome_completo as fabricante_nome,
    co.codigo_campo,
    co.descricao_campo,
    co.nome_coluna,
    vo.valor_original,
    vo.eh_multivalorado,
    vo.padrao_detectado,
    vo.num_partes,
    vo.confianca_geral,
    vo.processado_em,
    
    -- Reconstituir tokens horizontalmente
    MAX(CASE WHEN tv.posicao_token = 1 THEN tv.valor_token END) as parte_1,
    MAX(CASE WHEN tv.posicao_token = 1 THEN tt.codigo_tipo END) as tipo_1,
    MAX(CASE WHEN tv.posicao_token = 1 THEN tv.significado END) as significado_1,
    MAX(CASE WHEN tv.posicao_token = 1 THEN tv.confianca END) as confianca_1,
    
    MAX(CASE WHEN tv.posicao_token = 2 THEN tv.valor_token END) as parte_2,
    MAX(CASE WHEN tv.posicao_token = 2 THEN tt.codigo_tipo END) as tipo_2,
    MAX(CASE WHEN tv.posicao_token = 2 THEN tv.significado END) as significado_2,
    MAX(CASE WHEN tv.posicao_token = 2 THEN tv.confianca END) as confianca_2,
    
    MAX(CASE WHEN tv.posicao_token = 3 THEN tv.valor_token END) as parte_3,
    MAX(CASE WHEN tv.posicao_token = 3 THEN tt.codigo_tipo END) as tipo_3,
    MAX(CASE WHEN tv.posicao_token = 3 THEN tv.significado END) as significado_3,
    MAX(CASE WHEN tv.posicao_token = 3 THEN tv.confianca END) as confianca_3,
    
    MAX(CASE WHEN tv.posicao_token = 4 THEN tv.valor_token END) as parte_4,
    MAX(CASE WHEN tv.posicao_token = 4 THEN tt.codigo_tipo END) as tipo_4,
    MAX(CASE WHEN tv.posicao_token = 4 THEN tv.significado END) as significado_4,
    MAX(CASE WHEN tv.posicao_token = 4 THEN tv.confianca END) as confianca_4,
    
    MAX(CASE WHEN tv.posicao_token = 5 THEN tv.valor_token END) as parte_5,
    MAX(CASE WHEN tv.posicao_token = 5 THEN tt.codigo_tipo END) as tipo_5,
    MAX(CASE WHEN tv.posicao_token = 5 THEN tv.significado END) as significado_5,
    MAX(CASE WHEN tv.posicao_token = 5 THEN tv.confianca END) as confianca_5,
    
    MAX(CASE WHEN tv.posicao_token = 6 THEN tv.valor_token END) as parte_6,
    MAX(CASE WHEN tv.posicao_token = 6 THEN tt.codigo_tipo END) as tipo_6,
    MAX(CASE WHEN tv.posicao_token = 6 THEN tv.significado END) as significado_6,
    MAX(CASE WHEN tv.posicao_token = 6 THEN tv.confianca END) as confianca_6,
    
    MAX(CASE WHEN tv.posicao_token = 7 THEN tv.valor_token END) as parte_7,
    MAX(CASE WHEN tv.posicao_token = 7 THEN tt.codigo_tipo END) as tipo_7,
    MAX(CASE WHEN tv.posicao_token = 7 THEN tv.significado END) as significado_7,
    MAX(CASE WHEN tv.posicao_token = 7 THEN tv.confianca END) as confianca_7

FROM valores_originais vo
    JOIN campos_originais co ON vo.campo_id = co.id
    JOIN arquivos a ON co.arquivo_id = a.id
    JOIN fabricantes f ON a.fabricante_id = f.id
    LEFT JOIN tokens_valores tv ON vo.id = tv.valor_id
    LEFT JOIN tipos_token tt ON tv.tipo_token_id = tt.id
GROUP BY vo.id, a.identificador, f.codigo_fabricante, f.nome_completo, 
         co.codigo_campo, co.descricao_campo, co.nome_coluna, vo.valor_original,
         vo.eh_multivalorado, vo.padrao_detectado, vo.num_partes, 
         vo.confianca_geral, vo.processado_em
ORDER BY a.identificador, co.codigo_campo, co.nome_coluna;

-- View para análise de códigos ANSI
CREATE VIEW vw_codigos_ansi AS
SELECT 
    a.identificador as arquivo,
    f.codigo_fabricante as fabricante,
    co.codigo_campo,
    co.descricao_campo,
    vo.valor_original,
    tv.valor_token as codigo_ansi,
    tv.significado as significado_ansi,
    tv.confianca
FROM tokens_valores tv
    JOIN tipos_token tt ON tv.tipo_token_id = tt.id
    JOIN valores_originais vo ON tv.valor_id = vo.id
    JOIN campos_originais co ON vo.campo_id = co.id
    JOIN arquivos a ON co.arquivo_id = a.id
    JOIN fabricantes f ON a.fabricante_id = f.id
WHERE tt.codigo_tipo = 'ansi_code'
ORDER BY f.codigo_fabricante, co.codigo_campo, tv.posicao_token;

-- View para análise de campos por fabricante
CREATE VIEW vw_campos_por_fabricante AS
SELECT 
    f.codigo_fabricante as fabricante,
    f.nome_completo as fabricante_nome,
    co.codigo_campo,
    co.descricao_campo,
    COUNT(vo.id) as total_valores,
    COUNT(CASE WHEN vo.eh_multivalorado = true THEN 1 END) as valores_multivalorados,
    ROUND(AVG(vo.confianca_geral), 3) as confianca_media,
    MIN(vo.processado_em) as primeiro_processamento,
    MAX(vo.processado_em) as ultimo_processamento
FROM campos_originais co
    JOIN arquivos a ON co.arquivo_id = a.id
    JOIN fabricantes f ON a.fabricante_id = f.id
    LEFT JOIN valores_originais vo ON co.id = vo.campo_id
GROUP BY f.codigo_fabricante, f.nome_completo, co.codigo_campo, co.descricao_campo
ORDER BY f.codigo_fabricante, co.codigo_campo;

-- =====================================================
-- ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índices nas tabelas principais
CREATE INDEX idx_arquivos_fabricante ON arquivos(fabricante_id);
CREATE INDEX idx_arquivos_identificador ON arquivos(identificador);
CREATE INDEX idx_campos_arquivo ON campos_originais(arquivo_id);
CREATE INDEX idx_campos_codigo ON campos_originais(codigo_campo);
CREATE INDEX idx_valores_campo ON valores_originais(campo_id);
CREATE INDEX idx_valores_padrao ON valores_originais(padrao_detectado);
CREATE INDEX idx_valores_multivalorado ON valores_originais(eh_multivalorado);
CREATE INDEX idx_valores_processado ON valores_originais(processado_em);
CREATE INDEX idx_tokens_valor ON tokens_valores(valor_id);
CREATE INDEX idx_tokens_tipo ON tokens_valores(tipo_token_id);
CREATE INDEX idx_tokens_posicao ON tokens_valores(posicao_token);

-- Índices de texto para busca
CREATE INDEX idx_valores_original_text ON valores_originais USING gin(to_tsvector('portuguese', valor_original));
CREATE INDEX idx_tokens_significado_text ON tokens_valores USING gin(to_tsvector('portuguese', significado));

-- =====================================================
-- TRIGGERS PARA AUDITORIA
-- =====================================================

-- Função para atualizar timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para tabelas com updated_at
CREATE TRIGGER update_fabricantes_modtime 
    BEFORE UPDATE ON fabricantes 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_valores_modtime 
    BEFORE UPDATE ON valores_originais 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- =====================================================
-- INSERÇÃO DE DADOS MESTRES INICIAIS
-- =====================================================

-- Fabricantes conhecidos
INSERT INTO fabricantes (codigo_fabricante, nome_completo, pais_origem, certificacoes) VALUES 
('schneider', 'Schneider Electric', 'França', 'IEC, IEEE, ANSI'),
('abb', 'ABB Group', 'Suíça', 'IEC, IEEE'),
('siemens', 'Siemens AG', 'Alemanha', 'IEC, IEEE, VDE'),
('ge', 'General Electric', 'Estados Unidos', 'IEEE, ANSI, UL'),
('eaton', 'Eaton Corporation', 'Estados Unidos', 'IEEE, ANSI, UL'),
('sel', 'Schweitzer Engineering Laboratories', 'Estados Unidos', 'IEEE, ANSI')
ON CONFLICT (codigo_fabricante) DO NOTHING;

-- Tipos de tokens
INSERT INTO tipos_token (codigo_tipo, nome, descricao, categoria) VALUES 
('atomic', 'Atômico', 'Valor que não requer desmembramento', 'primitivo'),
('ansi_code', 'Código ANSI', 'Código de dispositivo ANSI/IEEE', 'codigo_ansi'),
('protection_type', 'Tipo de Proteção', 'Tipo de função de proteção', 'funcional'),
('sequence_number', 'Número Sequencial', 'Identificador numérico sequencial', 'identificacao'),
('model_prefix', 'Prefixo do Modelo', 'Prefixo identificador do modelo', 'especificacao_tecnica'),
('model_series', 'Série do Modelo', 'Série ou família do produto', 'especificacao_tecnica'),
('model_variant', 'Variante do Modelo', 'Variação específica do modelo', 'especificacao_tecnica'),
('model_suffix', 'Sufixo do Modelo', 'Sufixo do número do modelo', 'especificacao_tecnica'),
('plant_reference', 'Referência da Planta', 'Código de área/equipamento da planta', 'localizacao'),
('revision', 'Revisão', 'Número de revisão do documento/equipamento', 'versionamento'),
('unknown', 'Desconhecido', 'Token não classificado especificamente', 'generico')
ON CONFLICT (codigo_tipo) DO NOTHING;

-- =====================================================
-- COMENTÁRIOS NA ESTRUTURA
-- =====================================================

COMMENT ON SCHEMA protec_ai IS 'Schema para dados de proteção elétrica industrial - Estrutura Normalizada';

COMMENT ON TABLE fabricantes IS 'Fabricantes de equipamentos de proteção elétrica';
COMMENT ON TABLE arquivos IS 'Arquivos Excel processados com dados de parametrização';
COMMENT ON TABLE campos_originais IS 'Definições dos campos originais (elimina redundância)';
COMMENT ON TABLE valores_originais IS 'Valores processados dos parâmetros';
COMMENT ON TABLE tokens_valores IS 'Tokens individuais dos valores multivalorados';
COMMENT ON TABLE tipos_token IS 'Tipos de tokens resultantes da normalização';

COMMENT ON COLUMN fabricantes.codigo_fabricante IS 'Código identificador do fabricante usado nos CSV';
COMMENT ON COLUMN campos_originais.codigo_campo IS 'Código hexadecimal do parâmetro (ex: 00.04, 30.01)';
COMMENT ON COLUMN valores_originais.eh_multivalorado IS 'Indica se o valor foi desmembrado em múltiplos tokens';
COMMENT ON COLUMN valores_originais.confianca_geral IS 'Nível de confiança geral do processamento (0.000-1.000)';
COMMENT ON COLUMN tokens_valores.posicao_token IS 'Posição do token no valor multivalorado (1-7)';
COMMENT ON COLUMN tokens_valores.confianca IS 'Nível de confiança específico do token (0.000-1.000)';

-- =====================================================
-- CONSULTAS DE EXEMPLO
-- =====================================================

/*
-- Estatísticas gerais por fabricante
SELECT 
    f.codigo_fabricante,
    f.nome_completo,
    COUNT(vo.id) as total_valores,
    COUNT(CASE WHEN vo.eh_multivalorado = true THEN 1 END) as multivalorados,
    ROUND(AVG(vo.confianca_geral), 3) as confianca_media,
    COUNT(DISTINCT co.codigo_campo) as codigos_distintos
FROM fabricantes f
    JOIN arquivos a ON f.id = a.fabricante_id
    JOIN campos_originais co ON a.id = co.arquivo_id
    JOIN valores_originais vo ON co.id = vo.campo_id
GROUP BY f.codigo_fabricante, f.nome_completo
ORDER BY total_valores DESC;

-- Códigos ANSI mais frequentes
SELECT 
    tv.valor_token as codigo_ansi,
    tv.significado,
    COUNT(*) as frequencia,
    ROUND(AVG(tv.confianca), 3) as confianca_media
FROM tokens_valores tv
    JOIN tipos_token tt ON tv.tipo_token_id = tt.id
WHERE tt.codigo_tipo = 'ansi_code'
GROUP BY tv.valor_token, tv.significado
ORDER BY frequencia DESC;

-- Campos com maior complexidade (mais tokens)
SELECT 
    a.identificador,
    co.codigo_campo,
    co.descricao_campo,
    vo.valor_original,
    vo.num_partes,
    vo.confianca_geral
FROM valores_originais vo
    JOIN campos_originais co ON vo.campo_id = co.id
    JOIN arquivos a ON co.arquivo_id = a.id
WHERE vo.num_partes > 3
ORDER BY vo.num_partes DESC, vo.confianca_geral DESC;

-- Reconstituir formato original (como CSV)
SELECT * FROM vw_dados_completos 
WHERE arquivo = 'tela1' 
ORDER BY codigo_campo, nome_coluna;
*/
-- =====================================================
-- MODELAGEM DE DADOS REFINADA BASEADA NA ESTRUTURA REAL
-- Baseado na análise do arquivo tela1_params_normalized.csv
-- Data: 2025-10-05
-- =====================================================

-- Criar schema para isolamento
CREATE SCHEMA IF NOT EXISTS protec_ai;
SET search_path TO protec_ai;

-- =====================================================
-- TABELAS PRINCIPAIS (MESTRES)
-- =====================================================

-- Fabricantes/fornecedores de equipamentos de proteção
CREATE TABLE fabricantes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE, -- "schneider", "abb", etc.
    nome_completo VARCHAR(200), -- "Schneider Electric"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Arquivos processados (origem dos dados)
CREATE TABLE arquivos_origem (
    id SERIAL PRIMARY KEY,
    nome_arquivo VARCHAR(255) NOT NULL, -- "tela1_params_clean.xlsx"
    identificador VARCHAR(50) NOT NULL, -- "tela1", "tela3"
    fabricante_id INTEGER REFERENCES fabricantes(id),
    caminho_completo TEXT,
    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_processamento TIMESTAMP,
    status_processamento VARCHAR(50) DEFAULT 'pendente', -- 'pendente', 'processado', 'erro'
    total_registros INTEGER,
    registros_multivalorados INTEGER,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tipos de padrões detectados pelo parser
CREATE TABLE padroes_detectados (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE, -- "ansi_full", "schneider_model", "plant_reference"
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    exemplo VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tipos de tokens normalizados
CREATE TABLE tipos_token (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE, -- "ansi_code", "model_prefix", "sequence_number"
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    categoria VARCHAR(50), -- "codigo_ansi", "identificacao", "especificacao_tecnica"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- TABELA PRINCIPAL DE DADOS NORMALIZADOS
-- =====================================================

-- Registro principal de cada valor processado
CREATE TABLE parametros_normalizados (
    id SERIAL PRIMARY KEY,
    
    -- Identificação da origem
    arquivo_origem_id INTEGER NOT NULL REFERENCES arquivos_origem(id),
    fabricante_id INTEGER NOT NULL REFERENCES fabricantes(id),
    
    -- Identificação do parâmetro
    codigo_campo VARCHAR(20) NOT NULL, -- "00.04", "00.05", "30.01"
    descricao_campo VARCHAR(200) NOT NULL, -- "Description", "Model Number", "Plant Reference"
    nome_coluna VARCHAR(100) NOT NULL, -- "Value", "Valor_Num"
    
    -- Valor original e processamento
    valor_original TEXT NOT NULL,
    eh_atomico BOOLEAN NOT NULL DEFAULT TRUE,
    padrao_detectado_id INTEGER REFERENCES padroes_detectados(id),
    processado_em TIMESTAMP NOT NULL,
    
    -- Informações sobre normalização
    num_partes INTEGER NOT NULL DEFAULT 1,
    confianca_geral DECIMAL(3,3), -- 0.000 a 1.000
    
    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices compostos para performance
    CONSTRAINT uk_parametro_campo UNIQUE (arquivo_origem_id, codigo_campo, nome_coluna, valor_original)
);

-- =====================================================
-- TABELA DE TOKENS NORMALIZADOS
-- =====================================================

-- Partes individuais dos valores multivalorados
CREATE TABLE tokens_normalizados (
    id SERIAL PRIMARY KEY,
    parametro_id INTEGER NOT NULL REFERENCES parametros_normalizados(id) ON DELETE CASCADE,
    
    -- Posição e conteúdo do token
    posicao INTEGER NOT NULL CHECK (posicao >= 1 AND posicao <= 7),
    valor_token VARCHAR(200) NOT NULL,
    
    -- Classificação do token
    tipo_token_id INTEGER REFERENCES tipos_token(id),
    significado TEXT,
    confianca DECIMAL(3,3), -- 0.000 a 1.000
    
    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Garantir ordem dos tokens
    CONSTRAINT uk_token_posicao UNIQUE (parametro_id, posicao)
);

-- =====================================================
-- VIEWS PARA CONSULTAS FACILITADAS
-- =====================================================

-- View principal para análise dos dados
CREATE VIEW vw_parametros_completos AS
SELECT 
    p.id,
    ao.nome_arquivo,
    ao.identificador as arquivo_identificador,
    f.nome as fabricante,
    p.codigo_campo,
    p.descricao_campo,
    p.nome_coluna,
    p.valor_original,
    p.eh_atomico,
    pd.codigo as padrao_detectado,
    p.num_partes,
    p.confianca_geral,
    p.processado_em,
    
    -- Concatenar tokens normalizados
    STRING_AGG(
        CONCAT(tn.posicao, ':', tn.valor_token, ' (', tt.codigo, ')'), 
        ' | ' 
        ORDER BY tn.posicao
    ) as tokens_normalizados
FROM parametros_normalizados p
    LEFT JOIN arquivos_origem ao ON p.arquivo_origem_id = ao.id
    LEFT JOIN fabricantes f ON p.fabricante_id = f.id
    LEFT JOIN padroes_detectados pd ON p.padrao_detectado_id = pd.id
    LEFT JOIN tokens_normalizados tn ON p.id = tn.parametro_id
    LEFT JOIN tipos_token tt ON tn.tipo_token_id = tt.id
GROUP BY p.id, ao.nome_arquivo, ao.identificador, f.nome, p.codigo_campo, 
         p.descricao_campo, p.nome_coluna, p.valor_original, p.eh_atomico, 
         pd.codigo, p.num_partes, p.confianca_geral, p.processado_em;

-- View para análise de códigos ANSI
CREATE VIEW vw_codigos_ansi AS
SELECT 
    p.id,
    ao.identificador as arquivo,
    f.nome as fabricante,
    p.codigo_campo,
    p.descricao_campo,
    p.valor_original,
    tn.valor_token as codigo_ansi,
    tn.significado as significado_ansi,
    tn.confianca
FROM parametros_normalizados p
    JOIN arquivos_origem ao ON p.arquivo_origem_id = ao.id
    JOIN fabricantes f ON p.fabricante_id = f.id
    JOIN tokens_normalizados tn ON p.id = tn.parametro_id
    JOIN tipos_token tt ON tn.tipo_token_id = tt.id
WHERE tt.codigo = 'ansi_code'
ORDER BY f.nome, p.codigo_campo, tn.posicao;

-- View para análise de modelos de equipamentos
CREATE VIEW vw_modelos_equipamentos AS
SELECT 
    ao.identificador as arquivo,
    f.nome as fabricante,
    p.valor_original as modelo_completo,
    STRING_AGG(
        CASE 
            WHEN tt.codigo LIKE 'model_%' THEN CONCAT(tt.codigo, ':', tn.valor_token)
            ELSE NULL 
        END,
        ' | '
        ORDER BY tn.posicao
    ) as componentes_modelo
FROM parametros_normalizados p
    JOIN arquivos_origem ao ON p.arquivo_origem_id = ao.id
    JOIN fabricantes f ON p.fabricante_id = f.id
    JOIN tokens_normalizados tn ON p.id = tn.parametro_id
    JOIN tipos_token tt ON tn.tipo_token_id = tt.id
WHERE p.descricao_campo ILIKE '%model%'
    AND tt.codigo LIKE 'model_%'
GROUP BY ao.identificador, f.nome, p.valor_original
ORDER BY f.nome, p.valor_original;

-- =====================================================
-- ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índices na tabela principal
CREATE INDEX idx_parametros_arquivo ON parametros_normalizados(arquivo_origem_id);
CREATE INDEX idx_parametros_fabricante ON parametros_normalizados(fabricante_id);
CREATE INDEX idx_parametros_codigo_campo ON parametros_normalizados(codigo_campo);
CREATE INDEX idx_parametros_padrao ON parametros_normalizados(padrao_detectado_id);
CREATE INDEX idx_parametros_atomico ON parametros_normalizados(eh_atomico);
CREATE INDEX idx_parametros_processado ON parametros_normalizados(processado_em);

-- Índices na tabela de tokens
CREATE INDEX idx_tokens_parametro ON tokens_normalizados(parametro_id);
CREATE INDEX idx_tokens_tipo ON tokens_normalizados(tipo_token_id);
CREATE INDEX idx_tokens_valor ON tokens_normalizados(valor_token);

-- Índices de texto para busca
CREATE INDEX idx_parametros_valor_original_text ON parametros_normalizados USING gin(to_tsvector('portuguese', valor_original));
CREATE INDEX idx_tokens_significado_text ON tokens_normalizados USING gin(to_tsvector('portuguese', significado));

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

-- Trigger para parametros_normalizados
CREATE TRIGGER update_parametros_modtime 
    BEFORE UPDATE ON parametros_normalizados 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- Trigger para arquivos_origem
CREATE TRIGGER update_arquivos_modtime 
    BEFORE UPDATE ON arquivos_origem 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- =====================================================
-- INSERÇÃO DE DADOS MESTRES INICIAIS
-- =====================================================

-- Fabricantes conhecidos
INSERT INTO fabricantes (nome, nome_completo) VALUES 
('schneider', 'Schneider Electric'),
('abb', 'ABB Group'),
('siemens', 'Siemens AG'),
('ge', 'General Electric'),
('eaton', 'Eaton Corporation'),
('sel', 'Schweitzer Engineering Laboratories')
ON CONFLICT (nome) DO NOTHING;

-- Padrões detectados pelo parser
INSERT INTO padroes_detectados (codigo, nome, descricao, exemplo) VALUES 
('atomic', 'Valor Atômico', 'Valor que não requer desmembramento', 'English'),
('ansi_full', 'Código ANSI Completo', 'Código ANSI com múltiplas partes', '52-MP-20'),
('ansi_simple', 'Código ANSI Simples', 'Código ANSI numérico simples', '52'),
('schneider_model', 'Modelo Schneider', 'Número de modelo Schneider Electric', 'P241311B2M0600J'),
('plant_reference', 'Referência da Planta', 'Código de referência da instalação', '204-MF-02_rev.0'),
('generic_tokens', 'Tokens Genéricos', 'Tokens identificados por padrão genérico', '13.80 kV')
ON CONFLICT (codigo) DO NOTHING;

-- Tipos de tokens
INSERT INTO tipos_token (codigo, nome, descricao, categoria) VALUES 
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
ON CONFLICT (codigo) DO NOTHING;

-- =====================================================
-- COMENTÁRIOS NA ESTRUTURA
-- =====================================================

COMMENT ON SCHEMA protec_ai IS 'Schema para dados de proteção elétrica industrial';

COMMENT ON TABLE fabricantes IS 'Fabricantes de equipamentos de proteção elétrica';
COMMENT ON TABLE arquivos_origem IS 'Arquivos Excel processados com dados de parametrização';
COMMENT ON TABLE padroes_detectados IS 'Padrões de códigos detectados pelo parser';
COMMENT ON TABLE tipos_token IS 'Tipos de tokens resultantes da normalização';
COMMENT ON TABLE parametros_normalizados IS 'Dados principais dos parâmetros normalizados';
COMMENT ON TABLE tokens_normalizados IS 'Tokens individuais dos valores multivalorados';

COMMENT ON COLUMN parametros_normalizados.codigo_campo IS 'Código hexadecimal do parâmetro (ex: 00.04, 30.01)';
COMMENT ON COLUMN parametros_normalizados.confianca_geral IS 'Nível de confiança geral do processamento (0.000-1.000)';
COMMENT ON COLUMN tokens_normalizados.posicao IS 'Posição do token no valor multivalorado (1-7)';
COMMENT ON COLUMN tokens_normalizados.confianca IS 'Nível de confiança específico do token (0.000-1.000)';

-- =====================================================
-- CONSULTAS DE EXEMPLO
-- =====================================================

/*
-- Estatísticas gerais por fabricante
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

-- Códigos ANSI mais frequentes
SELECT 
    tn.valor_token as codigo_ansi,
    tn.significado,
    COUNT(*) as frequencia,
    ROUND(AVG(tn.confianca), 3) as confianca_media
FROM tokens_normalizados tn
    JOIN tipos_token tt ON tn.tipo_token_id = tt.id
WHERE tt.codigo = 'ansi_code'
GROUP BY tn.valor_token, tn.significado
ORDER BY frequencia DESC;

-- Parâmetros com maior complexidade (mais tokens)
SELECT 
    ao.identificador,
    p.codigo_campo,
    p.descricao_campo,
    p.valor_original,
    p.num_partes,
    p.confianca_geral
FROM parametros_normalizados p
    JOIN arquivos_origem ao ON p.arquivo_origem_id = ao.id
WHERE p.num_partes > 3
ORDER BY p.num_partes DESC, p.confianca_geral DESC;
*/
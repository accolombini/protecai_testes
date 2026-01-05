-- ============================================================================
-- SCHEMA NORMALIZADO - TERCEIRA FORMA NORMAL (3FN)
-- Projeto: ProtecAI - Sistema de Gestão de Relés de Proteção PETROBRAS
-- Data: 07/11/2025
-- Autor: Sistema ProtecAI
-- 
-- OBJETIVO: Eliminar dependências transitivas e garantir normalização 3FN
-- ============================================================================

-- ============================================================================
-- TABELA 1: relay_parameters (GLOSSÁRIO - DEFINIÇÕES DE PARÂMETROS)
-- ============================================================================
-- Descrição: Armazena a definição de TODOS os parâmetros possíveis
-- Fonte: inputs/glossario/GLOSSARIO_PARAMETROS_RELES.xlsx (519 parâmetros)
-- Chave Primária: (parameter_code, relay_model_id)
-- ============================================================================

CREATE TABLE IF NOT EXISTS protec_ai.relay_parameters (
    id SERIAL PRIMARY KEY,
    parameter_code VARCHAR(10) NOT NULL,        -- Código do parâmetro (ex: 0123, 0125)
    relay_model_id INTEGER NOT NULL REFERENCES protec_ai.relay_models(id),
    parameter_name TEXT NOT NULL,               -- Nome do parâmetro (ex: CT Primary)
    description TEXT,                           -- Descrição detalhada do glossário
    unit_of_measure VARCHAR(50),                -- Unidade (V, A, Hz, ms, etc)
    category VARCHAR(100),                      -- Categoria (Protection, Control, etc)
    data_type VARCHAR(20),                      -- Tipo: INT, FLOAT, TEXT, BOOLEAN, ENUM
    possible_values TEXT,                       -- Valores possíveis (para ENUMs)
    min_value DECIMAL(15,6),                    -- Valor mínimo permitido
    max_value DECIMAL(15,6),                    -- Valor máximo permitido
    default_value TEXT,                         -- Valor padrão de fábrica
    is_required BOOLEAN DEFAULT FALSE,          -- Parâmetro obrigatório?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT uq_param_model UNIQUE (parameter_code, relay_model_id),
    CONSTRAINT chk_data_type CHECK (data_type IN ('INT', 'FLOAT', 'TEXT', 'BOOLEAN', 'ENUM'))
);

-- Índices para performance
CREATE INDEX idx_relay_parameters_code ON protec_ai.relay_parameters(parameter_code);
CREATE INDEX idx_relay_parameters_model ON protec_ai.relay_parameters(relay_model_id);
CREATE INDEX idx_relay_parameters_category ON protec_ai.relay_parameters(category);

-- ============================================================================
-- TABELA 2: relay_settings (VALORES CONFIGURADOS - INSTÂNCIAS)
-- ============================================================================
-- Descrição: Armazena os valores REAIS configurados em cada equipamento
-- Fonte: inputs/pdf/*.pdf, inputs/txt/*.S40, inputs/txt/*.txt
-- Chave Estrangeira: equipment_id, parameter_id
-- ============================================================================

CREATE TABLE IF NOT EXISTS protec_ai.relay_settings (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES protec_ai.relay_equipment(id) ON DELETE CASCADE,
    parameter_id INTEGER NOT NULL REFERENCES protec_ai.relay_parameters(id),
    
    -- Valores configurados
    set_value TEXT,                             -- Valor numérico/texto configurado
    set_value_text TEXT,                        -- Representação textual (para ENUMs)
    is_active BOOLEAN DEFAULT FALSE,            -- ☑ checkbox marcado = TRUE, ☐ vazio = FALSE
    
    -- Metadados de extração
    extraction_method VARCHAR(50),              -- 'PDF_CHECKBOX', 'PDF_REGEX', 'TXT_PARSER', 'MANUAL'
    confidence_score DECIMAL(3,2),              -- 0.00 a 1.00 (confiança da extração)
    extraction_date TIMESTAMP,                  -- Data/hora da extração
    
    -- Auditoria
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system',
    updated_by VARCHAR(100) DEFAULT 'system',
    
    -- Constraints
    CONSTRAINT uq_equipment_parameter UNIQUE (equipment_id, parameter_id),
    CONSTRAINT chk_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- Índices para performance
CREATE INDEX idx_relay_settings_equipment ON protec_ai.relay_settings(equipment_id);
CREATE INDEX idx_relay_settings_parameter ON protec_ai.relay_settings(parameter_id);
CREATE INDEX idx_relay_settings_active ON protec_ai.relay_settings(is_active);
CREATE INDEX idx_relay_settings_extraction ON protec_ai.relay_settings(extraction_method);

-- ============================================================================
-- TABELA 3: relay_equipment (JÁ EXISTE - APENAS DOCUMENTAÇÃO)
-- ============================================================================
-- Descrição: Equipamentos físicos instalados nas subestações
-- Fonte: Arquivos de entrada (nome do arquivo = equipment_tag)
-- ============================================================================

-- Tabela já existe, apenas documentando estrutura
COMMENT ON TABLE protec_ai.relay_equipment IS 'Equipamentos de proteção instalados (relés)';
COMMENT ON COLUMN protec_ai.relay_equipment.equipment_tag IS 'TAG único do equipamento (ex: 52-MF-01BC)';
COMMENT ON COLUMN protec_ai.relay_equipment.relay_model_id IS 'Modelo do relé (P122, P143, P922, SEPAM, etc)';

-- ============================================================================
-- VIEWS DE CONSULTA (FACILITAR QUERIES)
-- ============================================================================

-- VIEW 1: Parâmetros ativos por equipamento
CREATE OR REPLACE VIEW protec_ai.v_active_settings AS
SELECT 
    e.equipment_tag,
    e.substation_name,
    e.installation_date,
    m.model_name,
    p.parameter_code,
    p.parameter_name,
    s.set_value,
    s.set_value_text,
    p.unit_of_measure,
    p.category,
    s.is_active,
    s.extraction_method,
    s.confidence_score
FROM protec_ai.relay_settings s
INNER JOIN protec_ai.relay_equipment e ON s.equipment_id = e.id
INNER JOIN protec_ai.relay_parameters p ON s.parameter_id = p.id
INNER JOIN protec_ai.relay_models m ON e.relay_model_id = m.id
WHERE s.is_active = TRUE
ORDER BY e.equipment_tag, p.parameter_code;

-- VIEW 2: Todos os parâmetros (ativos + inativos) por equipamento
CREATE OR REPLACE VIEW protec_ai.v_all_settings AS
SELECT 
    e.equipment_tag,
    e.substation_name,
    m.model_name,
    p.parameter_code,
    p.parameter_name,
    s.set_value,
    s.set_value_text,
    p.unit_of_measure,
    p.category,
    s.is_active,
    CASE 
        WHEN s.is_active THEN '☑ ATIVO'
        ELSE '☐ INATIVO'
    END AS status_checkbox
FROM protec_ai.relay_settings s
INNER JOIN protec_ai.relay_equipment e ON s.equipment_id = e.id
INNER JOIN protec_ai.relay_parameters p ON s.parameter_id = p.id
INNER JOIN protec_ai.relay_models m ON e.relay_model_id = m.id
ORDER BY e.equipment_tag, p.parameter_code;

-- VIEW 3: Parâmetros disponíveis por modelo (do glossário)
CREATE OR REPLACE VIEW protec_ai.v_available_parameters AS
SELECT 
    m.model_name,
    p.parameter_code,
    p.parameter_name,
    p.description,
    p.unit_of_measure,
    p.category,
    p.data_type,
    p.min_value,
    p.max_value,
    p.default_value,
    p.is_required
FROM protec_ai.relay_parameters p
INNER JOIN protec_ai.relay_models m ON p.relay_model_id = m.id
ORDER BY m.model_name, p.parameter_code;

-- ============================================================================
-- MIGRAÇÃO DOS DADOS EXISTENTES (PARA EXECUTAR APÓS CRIAR TABELAS)
-- ============================================================================

-- Script de migração será criado separadamente após validação do schema
-- Arquivo: scripts/migrate_to_3fn_schema.py

-- ============================================================================
-- COMENTÁRIOS E DOCUMENTAÇÃO
-- ============================================================================

COMMENT ON TABLE protec_ai.relay_parameters IS 
'Definições de parâmetros do glossário (MASTER DATA - 519 parâmetros)';

COMMENT ON TABLE protec_ai.relay_settings IS 
'Valores configurados em cada equipamento (INSTÂNCIAS - extraídos de PDFs/TXTs)';

COMMENT ON COLUMN protec_ai.relay_settings.is_active IS 
'TRUE = checkbox marcado (☑) no PDF, FALSE = checkbox vazio (☐)';

COMMENT ON COLUMN protec_ai.relay_settings.confidence_score IS 
'Score de confiança da extração: 1.00=manual, 0.90-0.99=alta, 0.70-0.89=média, <0.70=baixa';

COMMENT ON COLUMN protec_ai.relay_settings.extraction_method IS 
'Método de extração: PDF_CHECKBOX (Easergy), PDF_REGEX (MiCOM), TXT_PARSER (SEPAM), MANUAL (entrada manual)';

-- ============================================================================
-- FIM DO SCHEMA 3FN
-- ============================================================================

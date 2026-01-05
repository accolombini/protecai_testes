-- ============================================================================
-- PROTECAI - Schema PostgreSQL 3FN
-- Sistema de Análise de Configurações de Relés de Proteção
-- Data: 2025-11-10
-- ============================================================================

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABELA: relay_types
-- Propósito: Catálogo de tipos de relés (SEPAM, EASERGY P122/P220/P922, MICOM P143/P241)
-- ============================================================================
CREATE TABLE relay_types (
    id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL UNIQUE,  -- Ex: SEPAM, EASERGY_P122, MICOM_P143
    manufacturer VARCHAR(100),               -- Ex: Schneider Electric, GE
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABELA: units
-- Propósito: Unidades de medida extraídas dos valores (Hz, A, V, ms, etc.)
-- ============================================================================
CREATE TABLE units (
    id SERIAL PRIMARY KEY,
    unit_symbol VARCHAR(20) NOT NULL UNIQUE,  -- Ex: Hz, A, V, ms, °C
    unit_name VARCHAR(100),                    -- Ex: Hertz, Ampere, Volt
    unit_category VARCHAR(50),                 -- Ex: frequency, current, voltage, time
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABELA: equipments
-- Propósito: Equipamentos individuais com metadados (serial, modelo, referência, etc.)
-- ============================================================================
CREATE TABLE equipments (
    id SERIAL PRIMARY KEY,
    relay_type_id INTEGER REFERENCES relay_types(id),
    source_file VARCHAR(255) NOT NULL,        -- Nome do arquivo de origem
    extraction_date TIMESTAMP NOT NULL,       -- Data de extração
    
    -- Metadados para PDFs (Easergy, MiCOM)
    code_0079 TEXT,                           -- Description
    code_0081 TEXT,                           -- Serial Number
    code_010a TEXT,                           -- Reference
    code_0005 TEXT,                           -- Software Version
    code_0104 TEXT,                           -- Additional metadata
    
    -- Metadados para SEPAM
    sepam_repere VARCHAR(100),                -- Equipment ID
    sepam_modele VARCHAR(100),                -- Model
    sepam_mes VARCHAR(100),                   -- Measurement type
    sepam_gamme VARCHAR(100),                 -- Product line
    sepam_typemat VARCHAR(100),               -- Material type
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_equipment_source UNIQUE(source_file, extraction_date)
);

-- ============================================================================
-- TABELA: parameters
-- Propósito: Catálogo de códigos de parâmetros e suas descrições
-- ============================================================================
CREATE TABLE parameters (
    id SERIAL PRIMARY KEY,
    parameter_code VARCHAR(50) NOT NULL,      -- Ex: 0150, frequence_reseau
    parameter_description TEXT,               -- Descrição legível
    is_metadata BOOLEAN DEFAULT FALSE,        -- TRUE se for metadado (0079, 0081, SEPAM_*)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_parameter_code UNIQUE(parameter_code)
);

-- ============================================================================
-- TABELA: parameter_values
-- Propósito: Valores dos parâmetros por equipamento (relação N:M entre equipments e parameters)
-- ============================================================================
CREATE TABLE parameter_values (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES equipments(id) ON DELETE CASCADE,
    parameter_id INTEGER NOT NULL REFERENCES parameters(id) ON DELETE CASCADE,
    unit_id INTEGER REFERENCES units(id),
    
    -- Valor atomizado
    parameter_value TEXT,                     -- Valor original ou convertido
    value_type VARCHAR(20),                   -- null, numeric, boolean, text
    
    -- Status de ativação
    is_active BOOLEAN DEFAULT FALSE,          -- Parâmetro ativo no setup?
    
    -- Informações multipart
    is_multipart BOOLEAN DEFAULT FALSE,       -- Faz parte de grupo multipart?
    multipart_base VARCHAR(100),              -- Ex: "LED 5" para "LED 5 part 1"
    multipart_part INTEGER DEFAULT 0,         -- Número da parte (1, 2, 3, 4)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices compostos para consultas rápidas
    CONSTRAINT uq_equipment_parameter UNIQUE(equipment_id, parameter_id, multipart_part)
);

-- ============================================================================
-- TABELA: multipart_groups
-- Propósito: Agrupar parâmetros multipart (ex: LED 5 com parts 1-4)
-- ============================================================================
CREATE TABLE multipart_groups (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES equipments(id) ON DELETE CASCADE,
    multipart_base VARCHAR(100) NOT NULL,     -- Ex: "LED 5"
    total_parts INTEGER NOT NULL,             -- Quantas partes existem
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_equipment_multipart_base UNIQUE(equipment_id, multipart_base)
);

-- ============================================================================
-- ÍNDICES PARA OTIMIZAÇÃO DE CONSULTAS
-- ============================================================================

-- Índices em equipments
CREATE INDEX idx_equipments_relay_type ON equipments(relay_type_id);
CREATE INDEX idx_equipments_source_file ON equipments(source_file);
CREATE INDEX idx_equipments_sepam_repere ON equipments(sepam_repere);
CREATE INDEX idx_equipments_code_0081 ON equipments(code_0081);

-- Índices em parameters
CREATE INDEX idx_parameters_code ON parameters(parameter_code);
CREATE INDEX idx_parameters_metadata ON parameters(is_metadata);

-- Índices em parameter_values
CREATE INDEX idx_parameter_values_equipment ON parameter_values(equipment_id);
CREATE INDEX idx_parameter_values_parameter ON parameter_values(parameter_id);
CREATE INDEX idx_parameter_values_is_active ON parameter_values(is_active);
CREATE INDEX idx_parameter_values_is_multipart ON parameter_values(is_multipart);
CREATE INDEX idx_parameter_values_multipart_base ON parameter_values(multipart_base);
CREATE INDEX idx_parameter_values_value_type ON parameter_values(value_type);

-- Índices em multipart_groups
CREATE INDEX idx_multipart_groups_equipment ON multipart_groups(equipment_id);
CREATE INDEX idx_multipart_groups_base ON multipart_groups(multipart_base);

-- ============================================================================
-- VIEWS ÚTEIS
-- ============================================================================

-- View: Parâmetros ativos por equipamento com informações completas
CREATE OR REPLACE VIEW v_active_parameters AS
SELECT 
    e.id AS equipment_id,
    e.source_file,
    rt.type_name AS relay_type,
    e.sepam_repere,
    e.code_0081 AS serial_number,
    p.parameter_code,
    p.parameter_description,
    pv.parameter_value,
    u.unit_symbol,
    pv.value_type,
    pv.is_multipart,
    pv.multipart_base,
    pv.multipart_part
FROM parameter_values pv
JOIN equipments e ON pv.equipment_id = e.id
JOIN parameters p ON pv.parameter_id = p.id
LEFT JOIN units u ON pv.unit_id = u.id
LEFT JOIN relay_types rt ON e.relay_type_id = rt.id
WHERE pv.is_active = TRUE
ORDER BY e.source_file, p.parameter_code, pv.multipart_part;

-- View: Grupos multipart completos
CREATE OR REPLACE VIEW v_multipart_groups AS
SELECT 
    e.source_file,
    mg.multipart_base,
    mg.total_parts,
    COUNT(pv.id) AS parts_found,
    ARRAY_AGG(pv.multipart_part ORDER BY pv.multipart_part) AS parts_array,
    ARRAY_AGG(pv.parameter_value ORDER BY pv.multipart_part) AS values_array
FROM multipart_groups mg
JOIN equipments e ON mg.equipment_id = e.id
JOIN parameter_values pv ON pv.equipment_id = e.id 
    AND pv.multipart_base = mg.multipart_base
GROUP BY e.source_file, mg.multipart_base, mg.total_parts
ORDER BY e.source_file, mg.multipart_base;

-- View: Estatísticas por tipo de relé
CREATE OR REPLACE VIEW v_relay_statistics AS
SELECT 
    rt.type_name AS relay_type,
    COUNT(DISTINCT e.id) AS total_equipments,
    COUNT(DISTINCT pv.parameter_id) AS unique_parameters,
    COUNT(pv.id) AS total_parameter_values,
    SUM(CASE WHEN pv.is_active THEN 1 ELSE 0 END) AS active_parameters,
    SUM(CASE WHEN pv.is_multipart THEN 1 ELSE 0 END) AS multipart_parameters,
    AVG(CASE WHEN pv.is_active THEN 1.0 ELSE 0.0 END) * 100 AS avg_active_percentage
FROM relay_types rt
LEFT JOIN equipments e ON rt.id = e.relay_type_id
LEFT JOIN parameter_values pv ON e.id = pv.equipment_id
GROUP BY rt.type_name
ORDER BY total_equipments DESC;

-- View: Metadados dos equipamentos
CREATE OR REPLACE VIEW v_equipment_metadata AS
SELECT 
    e.id AS equipment_id,
    e.source_file,
    rt.type_name AS relay_type,
    -- Metadados SEPAM
    e.sepam_repere,
    e.sepam_modele,
    e.sepam_mes,
    e.sepam_gamme,
    e.sepam_typemat,
    -- Metadados PDF
    e.code_0079 AS description,
    e.code_0081 AS serial_number,
    e.code_010a AS reference,
    e.code_0005 AS software_version,
    e.code_0104 AS additional_info,
    e.extraction_date
FROM equipments e
LEFT JOIN relay_types rt ON e.relay_type_id = rt.id
ORDER BY e.source_file;

-- ============================================================================
-- TRIGGERS PARA ATUALIZAÇÃO AUTOMÁTICA
-- ============================================================================

-- Função para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers de updated_at
CREATE TRIGGER update_relay_types_updated_at
    BEFORE UPDATE ON relay_types
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_equipments_updated_at
    BEFORE UPDATE ON equipments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parameters_updated_at
    BEFORE UPDATE ON parameters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parameter_values_updated_at
    BEFORE UPDATE ON parameter_values
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DADOS INICIAIS (SEED DATA)
-- ============================================================================

-- Tipos de relés conhecidos
INSERT INTO relay_types (type_name, manufacturer, description) VALUES
('SEPAM', 'Schneider Electric', 'SEPAM series protection relays'),
('EASERGY_P122', 'Schneider Electric', 'Easergy P1 line protection relay'),
('EASERGY_P220', 'Schneider Electric', 'Easergy P2 motor protection relay'),
('EASERGY_P922', 'Schneider Electric', 'Easergy P9 multifunction relay'),
('MICOM_P143', 'GE Grid Solutions', 'MiCOM P143 line distance protection'),
('MICOM_P241', 'GE Grid Solutions', 'MiCOM P241 feeder protection'),
('UNKNOWN', 'Unknown', 'Unidentified relay type')
ON CONFLICT (type_name) DO NOTHING;

-- Unidades de medida comuns
INSERT INTO units (unit_symbol, unit_name, unit_category) VALUES
('Hz', 'Hertz', 'frequency'),
('A', 'Ampere', 'current'),
('V', 'Volt', 'voltage'),
('kV', 'Kilovolt', 'voltage'),
('ms', 'Millisecond', 'time'),
('s', 'Second', 'time'),
('Ω', 'Ohm', 'resistance'),
('W', 'Watt', 'power'),
('kW', 'Kilowatt', 'power'),
('°C', 'Celsius', 'temperature'),
('%', 'Percent', 'percentage'),
('deg', 'Degree', 'angle')
ON CONFLICT (unit_symbol) DO NOTHING;

-- ============================================================================
-- COMENTÁRIOS FINAIS
-- ============================================================================

COMMENT ON TABLE relay_types IS 'Catálogo de tipos de relés de proteção';
COMMENT ON TABLE units IS 'Unidades de medida para valores de parâmetros';
COMMENT ON TABLE equipments IS 'Equipamentos individuais com metadados completos';
COMMENT ON TABLE parameters IS 'Catálogo de códigos e descrições de parâmetros';
COMMENT ON TABLE parameter_values IS 'Valores dos parâmetros por equipamento (N:M)';
COMMENT ON TABLE multipart_groups IS 'Agrupamento de parâmetros multipart';

COMMENT ON VIEW v_active_parameters IS 'Parâmetros ativos com informações completas';
COMMENT ON VIEW v_multipart_groups IS 'Grupos multipart completos com arrays de valores';
COMMENT ON VIEW v_relay_statistics IS 'Estatísticas agregadas por tipo de relé';
COMMENT ON VIEW v_equipment_metadata IS 'Metadados completos dos equipamentos';

-- ============================================================================
-- FIM DO SCHEMA
-- ============================================================================

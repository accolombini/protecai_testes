-- ============================================================================
-- CRIAR TABELAS FALTANTES NO SCHEMA protec_ai
-- ============================================================================

-- Tabela: units - Catálogo de unidades de medida
CREATE TABLE IF NOT EXISTS protec_ai.units (
    id SERIAL PRIMARY KEY,
    unit_symbol VARCHAR(20) NOT NULL UNIQUE,
    unit_name VARCHAR(100),
    unit_category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: multipart_groups - Agrupamento de parâmetros multipart
CREATE TABLE IF NOT EXISTS protec_ai.multipart_groups (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES protec_ai.relay_equipment(id) ON DELETE CASCADE,
    multipart_base VARCHAR(100) NOT NULL,
    total_parts INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_equipment_multipart_base UNIQUE(equipment_id, multipart_base)
);

-- ============================================================================
-- POPULAR TABELA units COM DADOS INICIAIS
-- ============================================================================
INSERT INTO protec_ai.units (unit_symbol, unit_name, unit_category) VALUES
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
('deg', 'Degree', 'angle'),
('In', 'Nominal Current', 'current'),
('Vn', 'Nominal Voltage', 'voltage')
ON CONFLICT (unit_symbol) DO NOTHING;

-- ============================================================================
-- ADICIONAR FOREIGN KEY PARA units EM relay_settings
-- ============================================================================
ALTER TABLE protec_ai.relay_settings 
ADD COLUMN IF NOT EXISTS unit_id INTEGER REFERENCES protec_ai.units(id);

-- ============================================================================
-- CRIAR ÍNDICES ADICIONAIS
-- ============================================================================

-- Índices em relay_equipment
CREATE INDEX IF NOT EXISTS idx_relay_equipment_source_file 
    ON protec_ai.relay_equipment(source_file);
CREATE INDEX IF NOT EXISTS idx_relay_equipment_extraction_date 
    ON protec_ai.relay_equipment(extraction_date);
CREATE INDEX IF NOT EXISTS idx_relay_equipment_sepam_repere 
    ON protec_ai.relay_equipment(sepam_repere);
CREATE INDEX IF NOT EXISTS idx_relay_equipment_code_0081 
    ON protec_ai.relay_equipment(code_0081);

-- Índices em relay_settings
CREATE INDEX IF NOT EXISTS idx_relay_settings_is_active 
    ON protec_ai.relay_settings(is_active);
CREATE INDEX IF NOT EXISTS idx_relay_settings_is_multipart 
    ON protec_ai.relay_settings(is_multipart);
CREATE INDEX IF NOT EXISTS idx_relay_settings_multipart_base 
    ON protec_ai.relay_settings(multipart_base);
CREATE INDEX IF NOT EXISTS idx_relay_settings_value_type 
    ON protec_ai.relay_settings(value_type);
CREATE INDEX IF NOT EXISTS idx_relay_settings_unit_id 
    ON protec_ai.relay_settings(unit_id);

-- Índices em multipart_groups
CREATE INDEX IF NOT EXISTS idx_multipart_groups_equipment 
    ON protec_ai.multipart_groups(equipment_id);
CREATE INDEX IF NOT EXISTS idx_multipart_groups_base 
    ON protec_ai.multipart_groups(multipart_base);

-- ============================================================================
-- CRIAR VIEWS ÚTEIS
-- ============================================================================

-- View: Parâmetros ativos com informações completas
CREATE OR REPLACE VIEW protec_ai.v_active_parameters AS
SELECT 
    e.id AS equipment_id,
    e.equipment_tag,
    e.source_file,
    rm.model_name AS relay_model,
    e.sepam_repere,
    e.code_0081 AS serial_number,
    rs.parameter_code,
    rs.parameter_name,
    rs.set_value,
    rs.set_value_text,
    u.unit_symbol,
    rs.value_type,
    rs.is_multipart,
    rs.multipart_base,
    rs.multipart_part,
    pf.function_code,
    pf.function_name
FROM protec_ai.relay_settings rs
JOIN protec_ai.relay_equipment e ON rs.equipment_id = e.id
LEFT JOIN protec_ai.relay_models rm ON e.relay_model_id = rm.id
LEFT JOIN protec_ai.units u ON rs.unit_id = u.id
LEFT JOIN protec_ai.protection_functions pf ON rs.function_id = pf.id
WHERE rs.is_active = TRUE
ORDER BY e.equipment_tag, rs.parameter_code, rs.multipart_part;

-- View: Grupos multipart completos
CREATE OR REPLACE VIEW protec_ai.v_multipart_groups AS
SELECT 
    e.equipment_tag,
    e.source_file,
    mg.multipart_base,
    mg.total_parts,
    COUNT(rs.id) AS parts_found,
    ARRAY_AGG(rs.multipart_part ORDER BY rs.multipart_part) AS parts_array,
    ARRAY_AGG(rs.set_value_text ORDER BY rs.multipart_part) AS values_array
FROM protec_ai.multipart_groups mg
JOIN protec_ai.relay_equipment e ON mg.equipment_id = e.id
LEFT JOIN protec_ai.relay_settings rs ON rs.equipment_id = e.id 
    AND rs.multipart_base = mg.multipart_base
GROUP BY e.equipment_tag, e.source_file, mg.multipart_base, mg.total_parts
ORDER BY e.equipment_tag, mg.multipart_base;

-- View: Metadados dos equipamentos
CREATE OR REPLACE VIEW protec_ai.v_equipment_metadata AS
SELECT 
    e.id AS equipment_id,
    e.equipment_tag,
    e.source_file,
    rm.model_name AS relay_model,
    f.name AS manufacturer,
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
    e.extraction_date
FROM protec_ai.relay_equipment e
LEFT JOIN protec_ai.relay_models rm ON e.relay_model_id = rm.id
LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
ORDER BY e.equipment_tag;

-- ============================================================================
-- COMENTÁRIOS DAS TABELAS
-- ============================================================================

COMMENT ON TABLE protec_ai.units IS 'Catálogo de unidades de medida (Hz, A, V, etc.)';
COMMENT ON TABLE protec_ai.multipart_groups IS 'Agrupamento de parâmetros multipart (ex: LED 5 com parts 1-4)';

COMMENT ON COLUMN protec_ai.relay_equipment.source_file IS 'Arquivo de origem da extração (PDF ou SEPAM)';
COMMENT ON COLUMN protec_ai.relay_equipment.extraction_date IS 'Data/hora da extração dos dados';
COMMENT ON COLUMN protec_ai.relay_equipment.sepam_repere IS 'SEPAM: Equipment ID (repere)';
COMMENT ON COLUMN protec_ai.relay_equipment.sepam_modele IS 'SEPAM: Model (modele)';
COMMENT ON COLUMN protec_ai.relay_equipment.sepam_mes IS 'SEPAM: Measurement type (mes)';
COMMENT ON COLUMN protec_ai.relay_equipment.code_0079 IS 'PDF: Description (código 0079)';
COMMENT ON COLUMN protec_ai.relay_equipment.code_0081 IS 'PDF: Serial Number (código 0081)';
COMMENT ON COLUMN protec_ai.relay_equipment.code_010a IS 'PDF: Reference (código 010A)';

COMMENT ON COLUMN protec_ai.relay_settings.is_active IS 'Parâmetro ativo no setup (checkbox detection)';
COMMENT ON COLUMN protec_ai.relay_settings.is_multipart IS 'Parâmetro faz parte de grupo multipart';
COMMENT ON COLUMN protec_ai.relay_settings.multipart_base IS 'Nome base do grupo multipart (ex: LED 5)';
COMMENT ON COLUMN protec_ai.relay_settings.multipart_part IS 'Número da parte no grupo multipart (1, 2, 3, 4)';
COMMENT ON COLUMN protec_ai.relay_settings.value_type IS 'Tipo do valor: null, numeric, boolean, text';

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================

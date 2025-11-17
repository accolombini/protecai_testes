-- ============================================================================
-- SETUP SCHEMA PARA PIPELINE DE EXTRAÇÃO
-- Database: protecai_db
-- Schema: protec_ai
-- ============================================================================

-- Dropar tabelas antigas se existirem
DROP TABLE IF EXISTS protec_ai.parameter_values CASCADE;
DROP TABLE IF EXISTS protec_ai.parameters CASCADE;
DROP TABLE IF EXISTS protec_ai.equipments CASCADE;
DROP TABLE IF EXISTS protec_ai.relay_types CASCADE;

-- ============================================================================
-- TABELA: relay_types
-- ============================================================================
CREATE TABLE protec_ai.relay_types (
    id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL UNIQUE,
    manufacturer VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABELA: equipments
-- ============================================================================
CREATE TABLE protec_ai.equipments (
    id SERIAL PRIMARY KEY,
    relay_type_id INTEGER REFERENCES protec_ai.relay_types(id),
    source_file VARCHAR(255) NOT NULL,
    extraction_date TIMESTAMP NOT NULL,
    
    -- Metadados para PDFs (Easergy, MiCOM)
    code_0079 TEXT,
    code_0081 TEXT,
    code_010a TEXT,
    code_0005 TEXT,
    code_0104 TEXT,
    
    -- Metadados para SEPAM
    sepam_repere VARCHAR(100),
    sepam_modele VARCHAR(100),
    sepam_mes VARCHAR(100),
    sepam_gamme VARCHAR(100),
    sepam_typemat VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_equipment_source UNIQUE(source_file, extraction_date)
);

-- ============================================================================
-- TABELA: parameters
-- ============================================================================
CREATE TABLE protec_ai.parameters (
    id SERIAL PRIMARY KEY,
    parameter_code VARCHAR(50) NOT NULL,
    parameter_description TEXT,
    is_metadata BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_parameter_code UNIQUE(parameter_code)
);

-- ============================================================================
-- TABELA: parameter_values
-- ============================================================================
CREATE TABLE protec_ai.parameter_values (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES protec_ai.equipments(id) ON DELETE CASCADE,
    parameter_id INTEGER NOT NULL REFERENCES protec_ai.parameters(id) ON DELETE CASCADE,
    unit_id INTEGER REFERENCES protec_ai.units(id),
    
    parameter_value TEXT,
    value_type VARCHAR(20),
    is_active BOOLEAN DEFAULT FALSE,
    
    is_multipart BOOLEAN DEFAULT FALSE,
    multipart_base VARCHAR(100),
    multipart_part INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_equipment_parameter UNIQUE(equipment_id, parameter_id, multipart_part)
);

-- ============================================================================
-- ÍNDICES
-- ============================================================================
CREATE INDEX idx_equipments_relay_type ON protec_ai.equipments(relay_type_id);
CREATE INDEX idx_equipments_source_file ON protec_ai.equipments(source_file);
CREATE INDEX idx_parameters_code ON protec_ai.parameters(parameter_code);
CREATE INDEX idx_parameter_values_equipment ON protec_ai.parameter_values(equipment_id);
CREATE INDEX idx_parameter_values_parameter ON protec_ai.parameter_values(parameter_id);
CREATE INDEX idx_parameter_values_is_active ON protec_ai.parameter_values(is_active);

-- ============================================================================
-- SEED DATA
-- ============================================================================
INSERT INTO protec_ai.relay_types (type_name, manufacturer, description) VALUES
('SEPAM', 'Schneider Electric', 'SEPAM series protection relays'),
('EASERGY_P122', 'Schneider Electric', 'Easergy P1 line protection relay'),
('EASERGY_P220', 'Schneider Electric', 'Easergy P2 motor protection relay'),
('EASERGY_P922', 'Schneider Electric', 'Easergy P9 multifunction relay'),
('MICOM_P143', 'GE Grid Solutions', 'MiCOM P143 line distance protection'),
('MICOM_P241', 'GE Grid Solutions', 'MiCOM P241 feeder protection'),
('UNKNOWN', 'Unknown', 'Unidentified relay type')
ON CONFLICT (type_name) DO NOTHING;

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================
SELECT 'Schema criado com sucesso!' as status;
SELECT COUNT(*) as relay_types_count FROM protec_ai.relay_types;

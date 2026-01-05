-- ================================================================================================
-- SCHEMA POSTGRESQL PARA CONFIGURAÇÕES COMPLETAS DE RELÉS - VERSÃO CORRETA
-- ================================================================================================
-- Sistema: ProtecAI
-- Objetivo: Armazenar configurações completas de relés para reprodução de status
-- Compatível com: src/importar_configuracoes_reles.py
-- Data: 2025-10-18
-- ================================================================================================

-- Criar schema
CREATE SCHEMA IF NOT EXISTS relay_configs;

-- ================================================================================================
-- TABELAS PRINCIPAIS
-- ================================================================================================

-- 1. FABRICANTES
CREATE TABLE relay_configs.manufacturers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    country VARCHAR(100),
    website VARCHAR(500),
    support_contact VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. MODELOS DE RELÉS
CREATE TABLE relay_configs.relay_models (
    id SERIAL PRIMARY KEY,
    manufacturer_id INTEGER NOT NULL REFERENCES relay_configs.manufacturers(id),
    name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100) DEFAULT 'protection',
    family VARCHAR(100),
    application_type VARCHAR(100),
    voltage_class VARCHAR(50),
    current_class VARCHAR(50),
    protection_functions TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(manufacturer_id, name)
);

-- 3. EQUIPAMENTOS (RELÉS INSTALADOS)
CREATE TABLE relay_configs.relay_equipment (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES relay_configs.relay_models(id),
    serial_number VARCHAR(100),
    tag_reference VARCHAR(100),
    plant_reference VARCHAR(255),
    bay_position VARCHAR(100),
    software_version VARCHAR(50),
    frequency DECIMAL(5,2),
    description TEXT,
    installation_date DATE,
    commissioning_date DATE,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. CONFIGURAÇÃO ELÉTRICA
CREATE TABLE relay_configs.electrical_configuration (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES relay_configs.relay_equipment(id),
    phase_ct_primary DECIMAL(10,3),
    phase_ct_secondary DECIMAL(10,3),
    neutral_ct_primary DECIMAL(10,3),
    neutral_ct_secondary DECIMAL(10,3),
    vt_primary DECIMAL(10,2),
    vt_secondary DECIMAL(10,2),
    nvd_vt_primary DECIMAL(10,2),
    nvd_vt_secondary DECIMAL(10,2),
    vt_connection_mode VARCHAR(100),
    nominal_voltage DECIMAL(10,2),
    equipment_load DECIMAL(10,2),
    power_supply VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(equipment_id)
);

-- 5. FUNÇÕES DE PROTEÇÃO
CREATE TABLE relay_configs.protection_functions (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES relay_configs.relay_equipment(id),
    function_name VARCHAR(255) NOT NULL,
    ansi_code VARCHAR(20),
    enabled BOOLEAN DEFAULT false,
    current_setting DECIMAL(10,3),
    time_setting DECIMAL(10,3),
    characteristic VARCHAR(100),
    direction VARCHAR(50),
    pickup_value DECIMAL(10,3),
    time_delay DECIMAL(10,3),
    coordination_group VARCHAR(50),
    priority INTEGER,
    additional_settings_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. CONFIGURAÇÃO DE I/O
CREATE TABLE relay_configs.io_configuration (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES relay_configs.relay_equipment(id),
    io_type VARCHAR(50) NOT NULL, -- 'digital_input', 'digital_output', 'analog_input', 'analog_output', 'relay_output'
    channel_number VARCHAR(10) NOT NULL,
    label VARCHAR(255),
    signal_type VARCHAR(50), -- 'optical', 'contact', 'rtd', 'voltage', 'current'
    function_assignment VARCHAR(255),
    alarm_settings JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. VERSÕES DE CONFIGURAÇÃO (HISTÓRICO)
CREATE TABLE relay_configs.configuration_versions (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES relay_configs.relay_equipment(id),
    version_number VARCHAR(20) NOT NULL,
    source_file VARCHAR(500),
    configuration_json JSONB NOT NULL,
    hash_checksum VARCHAR(64),
    import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. PARÂMETROS ADICIONAIS
CREATE TABLE relay_configs.additional_parameters (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES relay_configs.relay_equipment(id),
    parameter_name VARCHAR(255) NOT NULL,
    parameter_value TEXT,
    parameter_type VARCHAR(50),
    category VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================================================
-- VIEWS PARA CONSULTAS OTIMIZADAS
-- ================================================================================================

-- VIEW: Equipamentos com informações completas
CREATE VIEW relay_configs.v_equipment_complete AS
SELECT 
    e.id as equipment_id,
    e.tag_reference,
    e.plant_reference,
    e.bay_position,
    e.serial_number,
    e.software_version,
    e.description,
    m.name as model_name,
    mf.name as manufacturer_name,
    ec.phase_ct_primary,
    ec.phase_ct_secondary,
    ec.vt_primary,
    ec.vt_secondary,
    COUNT(pf.id) as protection_functions_count,
    COUNT(CASE WHEN pf.enabled = true THEN 1 END) as enabled_functions_count,
    COUNT(io.id) as io_channels_count,
    e.status,
    e.created_at,
    e.updated_at
FROM relay_configs.relay_equipment e
LEFT JOIN relay_configs.relay_models m ON e.model_id = m.id
LEFT JOIN relay_configs.manufacturers mf ON m.manufacturer_id = mf.id
LEFT JOIN relay_configs.electrical_configuration ec ON e.id = ec.equipment_id
LEFT JOIN relay_configs.protection_functions pf ON e.id = pf.equipment_id
LEFT JOIN relay_configs.io_configuration io ON e.id = io.equipment_id
GROUP BY e.id, e.tag_reference, e.plant_reference, e.bay_position, e.serial_number, 
         e.software_version, e.description, m.name, mf.name, ec.phase_ct_primary, 
         ec.phase_ct_secondary, ec.vt_primary, ec.vt_secondary, e.status, e.created_at, e.updated_at;

-- VIEW: Resumo de proteções por equipamento
CREATE VIEW relay_configs.v_protection_summary AS
SELECT 
    e.id as equipment_id,
    e.tag_reference,
    m.name as model_name,
    mf.name as manufacturer_name,
    COUNT(pf.id) as total_functions,
    COUNT(CASE WHEN pf.enabled = true THEN 1 END) as enabled_functions,
    STRING_AGG(CASE WHEN pf.enabled = true THEN pf.function_name END, ', ' ORDER BY pf.function_name) as enabled_function_names,
    STRING_AGG(CASE WHEN pf.enabled = false THEN pf.function_name END, ', ' ORDER BY pf.function_name) as disabled_function_names
FROM relay_configs.relay_equipment e
LEFT JOIN relay_configs.relay_models m ON e.model_id = m.id
LEFT JOIN relay_configs.manufacturers mf ON m.manufacturer_id = mf.id
LEFT JOIN relay_configs.protection_functions pf ON e.id = pf.equipment_id
GROUP BY e.id, e.tag_reference, m.name, mf.name;

-- ================================================================================================
-- ÍNDICES PARA PERFORMANCE
-- ================================================================================================

-- Índices principais
CREATE INDEX idx_equipment_manufacturer ON relay_configs.relay_equipment USING btree(model_id);
CREATE INDEX idx_equipment_tag ON relay_configs.relay_equipment USING btree(tag_reference);
CREATE INDEX idx_equipment_plant ON relay_configs.relay_equipment USING btree(plant_reference);
CREATE INDEX idx_equipment_status ON relay_configs.relay_equipment USING btree(status);

CREATE INDEX idx_models_manufacturer ON relay_configs.relay_models USING btree(manufacturer_id);
CREATE INDEX idx_models_name ON relay_configs.relay_models USING btree(name);

CREATE INDEX idx_protection_equipment ON relay_configs.protection_functions USING btree(equipment_id);
CREATE INDEX idx_protection_enabled ON relay_configs.protection_functions USING btree(enabled);
CREATE INDEX idx_protection_function ON relay_configs.protection_functions USING btree(function_name);

CREATE INDEX idx_io_equipment ON relay_configs.io_configuration USING btree(equipment_id);
CREATE INDEX idx_io_type ON relay_configs.io_configuration USING btree(io_type);
CREATE INDEX idx_io_status ON relay_configs.io_configuration USING btree(status);

CREATE INDEX idx_versions_equipment ON relay_configs.configuration_versions USING btree(equipment_id);
CREATE INDEX idx_versions_timestamp ON relay_configs.configuration_versions USING btree(import_timestamp);
CREATE INDEX idx_versions_hash ON relay_configs.configuration_versions USING btree(hash_checksum);

CREATE INDEX idx_additional_equipment ON relay_configs.additional_parameters USING btree(equipment_id);
CREATE INDEX idx_additional_category ON relay_configs.additional_parameters USING btree(category);

-- Índice JSON para configurações
CREATE INDEX idx_versions_config_gin ON relay_configs.configuration_versions USING gin(configuration_json);
CREATE INDEX idx_protection_settings_gin ON relay_configs.protection_functions USING gin(additional_settings_json);

-- ================================================================================================
-- DADOS INICIAIS
-- ================================================================================================

-- Fabricantes principais
INSERT INTO relay_configs.manufacturers (name, country, website) VALUES
('Schneider Electric', 'France', 'https://www.schneider-electric.com'),
('ABB', 'Switzerland', 'https://new.abb.com'),
('Siemens', 'Germany', 'https://www.siemens.com'),
('General Electric', 'USA', 'https://www.ge.com'),
('SEL (Schweitzer Engineering)', 'USA', 'https://selinc.com'),
('Alstom', 'France', 'https://www.alstom.com'),
('Mitsubishi Electric', 'Japan', 'https://www.mitsubishielectric.com'),
('Hitachi Energy', 'Japan', 'https://www.hitachienergy.com');

-- ================================================================================================
-- FUNÇÕES AUXILIARES
-- ================================================================================================

-- Função para calcular hash de configuração
CREATE OR REPLACE FUNCTION relay_configs.calculate_config_hash(config_json JSONB) 
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(digest(config_json::text, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Função para criar snapshot de configuração
CREATE OR REPLACE FUNCTION relay_configs.create_equipment_snapshot(
    p_equipment_id INTEGER,
    p_version VARCHAR(20),
    p_notes TEXT DEFAULT NULL,
    p_created_by VARCHAR(100) DEFAULT 'System'
) RETURNS INTEGER AS $$
DECLARE
    v_config_json JSONB;
    v_hash VARCHAR(64);
    v_version_id INTEGER;
BEGIN
    -- Monta JSON completo da configuração
    SELECT jsonb_build_object(
        'equipment', row_to_json(e.*),
        'model', row_to_json(m.*),
        'manufacturer', row_to_json(mf.*),
        'electrical', row_to_json(ec.*),
        'protection_functions', COALESCE(
            (SELECT jsonb_agg(row_to_json(pf.*)) 
             FROM relay_configs.protection_functions pf 
             WHERE pf.equipment_id = p_equipment_id), '[]'::jsonb
        ),
        'io_configuration', COALESCE(
            (SELECT jsonb_agg(row_to_json(io.*)) 
             FROM relay_configs.io_configuration io 
             WHERE io.equipment_id = p_equipment_id), '[]'::jsonb
        ),
        'additional_parameters', COALESCE(
            (SELECT jsonb_agg(row_to_json(ap.*)) 
             FROM relay_configs.additional_parameters ap 
             WHERE ap.equipment_id = p_equipment_id), '[]'::jsonb
        )
    ) INTO v_config_json
    FROM relay_configs.relay_equipment e
    LEFT JOIN relay_configs.relay_models m ON e.model_id = m.id
    LEFT JOIN relay_configs.manufacturers mf ON m.manufacturer_id = mf.id
    LEFT JOIN relay_configs.electrical_configuration ec ON e.id = ec.equipment_id
    WHERE e.id = p_equipment_id;
    
    -- Calcula hash
    v_hash := relay_configs.calculate_config_hash(v_config_json);
    
    -- Insere versão
    INSERT INTO relay_configs.configuration_versions (
        equipment_id, version_number, configuration_json, 
        hash_checksum, created_by, notes
    ) VALUES (
        p_equipment_id, p_version, v_config_json, 
        v_hash, p_created_by, p_notes
    ) RETURNING id INTO v_version_id;
    
    RETURN v_version_id;
END;
$$ LANGUAGE plpgsql;

-- ================================================================================================
-- COMENTÁRIOS PARA DOCUMENTAÇÃO
-- ================================================================================================

COMMENT ON SCHEMA relay_configs IS 'Schema para armazenamento completo de configurações de relés de proteção';
COMMENT ON TABLE relay_configs.manufacturers IS 'Fabricantes de relés e equipamentos de proteção';
COMMENT ON TABLE relay_configs.relay_models IS 'Modelos de relés disponíveis por fabricante';
COMMENT ON TABLE relay_configs.relay_equipment IS 'Relés instalados na planta industrial';
COMMENT ON TABLE relay_configs.electrical_configuration IS 'Configuração elétrica dos relés (TCs, TPs, etc.)';
COMMENT ON TABLE relay_configs.protection_functions IS 'Funções de proteção configuradas nos relés';
COMMENT ON TABLE relay_configs.io_configuration IS 'Configuração de entradas e saídas dos relés';
COMMENT ON TABLE relay_configs.configuration_versions IS 'Histórico de versões das configurações';
COMMENT ON TABLE relay_configs.additional_parameters IS 'Parâmetros adicionais específicos por modelo';

-- ================================================================================================
-- FIM DO SCHEMA
-- ================================================================================================
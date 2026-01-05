-- ============================================================================
-- PROTECAI - SCHEMA ESPECIALIZADO PARA CONFIGURAÇÕES COMPLETAS DE RELÉS
-- Para reprodução total do status de configuração dos relés de proteção
-- ============================================================================

-- Criação do schema especializado
CREATE SCHEMA IF NOT EXISTS relay_configs;

-- ============================================================================
-- TABELAS PRINCIPAIS PARA IDENTIFICAÇÃO E CONFIGURAÇÃO
-- ============================================================================

-- Equipamentos (Relés)
CREATE TABLE relay_configs.equipments (
    id SERIAL PRIMARY KEY,
    model VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    serial_number VARCHAR(50),
    software_version VARCHAR(50),
    tag_reference VARCHAR(100),
    plant_reference VARCHAR(200),
    bay_position VARCHAR(50),
    frequency VARCHAR(20),
    description TEXT,
    firmware_version VARCHAR(50),
    hardware_version VARCHAR(50),
    installation_date DATE,
    last_maintenance DATE,
    
    -- Campos de controle
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    source_file VARCHAR(500),
    import_timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Índices e constraints
    CONSTRAINT unique_serial_model UNIQUE (serial_number, model),
    CONSTRAINT chk_manufacturer CHECK (manufacturer IS NOT NULL)
);

-- Configurações Elétricas
CREATE TABLE relay_configs.electrical_configs (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES relay_configs.equipments(id) ON DELETE CASCADE,
    
    -- Transformadores de Corrente
    phase_ct_primary NUMERIC(12,3),
    phase_ct_secondary NUMERIC(12,3),
    neutral_ct_primary NUMERIC(12,3),
    neutral_ct_secondary NUMERIC(12,3),
    
    -- Transformadores de Potencial
    vt_primary VARCHAR(50),
    vt_secondary VARCHAR(50),
    nvd_vt_primary VARCHAR(50),
    nvd_vt_secondary VARCHAR(50),
    vt_connection_mode VARCHAR(100),
    
    -- Configurações da instalação
    nominal_voltage VARCHAR(50),
    equipment_load VARCHAR(50),
    system_frequency VARCHAR(20),
    earthing_type VARCHAR(50),
    
    -- Campos de controle
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_electrical_per_equipment UNIQUE (equipment_id)
);

-- ============================================================================
-- FUNÇÕES DE PROTEÇÃO
-- ============================================================================

-- Tipos de Função de Proteção (lookup table)
CREATE TABLE relay_configs.protection_function_types (
    id SERIAL PRIMARY KEY,
    function_name VARCHAR(100) NOT NULL UNIQUE,
    ansi_code VARCHAR(10),
    iec_code VARCHAR(10),
    description TEXT,
    category VARCHAR(50), -- overcurrent, voltage, frequency, thermal, etc.
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Funções de Proteção Configuradas
CREATE TABLE relay_configs.protection_functions (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES relay_configs.equipments(id) ON DELETE CASCADE,
    function_type_id INTEGER REFERENCES relay_configs.protection_function_types(id),
    
    -- Identificação da função
    code VARCHAR(20),
    function_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Ajustes principais
    current_setting VARCHAR(50),
    time_setting VARCHAR(50),
    characteristic VARCHAR(100),
    direction VARCHAR(50),
    
    -- Configurações específicas (JSON para flexibilidade)
    additional_settings JSONB,
    
    -- Campos de controle
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Índices
    CONSTRAINT unique_function_per_equipment UNIQUE (equipment_id, code, function_name)
);

-- ============================================================================
-- CONFIGURAÇÃO DE ENTRADAS E SAÍDAS
-- ============================================================================

-- Tipos de I/O
CREATE TABLE relay_configs.io_types (
    id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL UNIQUE, -- opto_input, relay_output, rtd_input, analog_output
    description TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Configurações de I/O
CREATE TABLE relay_configs.io_configurations (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES relay_configs.equipments(id) ON DELETE CASCADE,
    io_type_id INTEGER REFERENCES relay_configs.io_types(id),
    
    -- Identificação do I/O
    channel_number INTEGER NOT NULL,
    label VARCHAR(200),
    description TEXT,
    
    -- Configurações específicas
    status VARCHAR(50),
    function_mapping VARCHAR(200),
    alarm_settings JSONB,
    trip_settings JSONB,
    
    -- Para RTDs - configurações específicas
    sensor_type VARCHAR(50), -- PT100, PT1000, etc.
    unit VARCHAR(20), -- Celsius, Fahrenheit
    alarm_threshold NUMERIC(10,3),
    alarm_delay NUMERIC(10,3),
    trip_threshold NUMERIC(10,3),
    trip_delay NUMERIC(10,3),
    
    -- Campos de controle
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_io_per_equipment UNIQUE (equipment_id, io_type_id, channel_number)
);

-- ============================================================================
-- PARÂMETROS ADICIONAIS E CONFIGURAÇÕES DO SISTEMA
-- ============================================================================

-- Categorias de Parâmetros
CREATE TABLE relay_configs.parameter_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Parâmetros Adicionais (configurações gerais do sistema)
CREATE TABLE relay_configs.additional_parameters (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES relay_configs.equipments(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES relay_configs.parameter_categories(id),
    
    -- Identificação do parâmetro
    parameter_code VARCHAR(50),
    parameter_name VARCHAR(200) NOT NULL,
    parameter_value TEXT,
    
    -- Metadados
    data_type VARCHAR(50), -- string, numeric, boolean, datetime
    unit VARCHAR(50),
    range_min NUMERIC(15,6),
    range_max NUMERIC(15,6),
    
    -- Campos de controle
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_param_per_equipment UNIQUE (equipment_id, parameter_code, parameter_name)
);

-- ============================================================================
-- HISTÓRICO E VERSIONAMENTO
-- ============================================================================

-- Snapshots de Configuração (para comparações e histórico)
CREATE TABLE relay_configs.configuration_snapshots (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES relay_configs.equipments(id) ON DELETE CASCADE,
    
    -- Metadados do snapshot
    snapshot_name VARCHAR(200),
    description TEXT,
    created_by VARCHAR(100),
    
    -- Configuração completa em JSON
    full_configuration JSONB NOT NULL,
    
    -- Hash para detecção de mudanças
    configuration_hash VARCHAR(64) NOT NULL,
    
    -- Campos de controle
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Índices para busca rápida
    CONSTRAINT unique_hash_per_equipment UNIQUE (equipment_id, configuration_hash)
);

-- ============================================================================
-- VIEWS PARA CONSULTAS FACILITADAS
-- ============================================================================

-- View completa de equipamento com configuração elétrica
CREATE VIEW relay_configs.v_equipment_full AS
SELECT 
    e.id,
    e.model,
    e.manufacturer,
    e.serial_number,
    e.software_version,
    e.tag_reference,
    e.plant_reference,
    e.bay_position,
    e.frequency,
    e.description,
    
    -- Configuração elétrica
    ec.phase_ct_primary,
    ec.phase_ct_secondary,
    ec.neutral_ct_primary,
    ec.neutral_ct_secondary,
    ec.vt_primary,
    ec.vt_secondary,
    ec.vt_connection_mode,
    
    -- Metadados
    e.source_file,
    e.import_timestamp,
    e.created_at,
    e.updated_at
    
FROM relay_configs.equipments e
LEFT JOIN relay_configs.electrical_configs ec ON e.id = ec.equipment_id;

-- View de funções de proteção por equipamento
CREATE VIEW relay_configs.v_protection_summary AS
SELECT 
    e.id as equipment_id,
    e.model,
    e.manufacturer,
    e.tag_reference,
    
    COUNT(pf.id) as total_functions,
    COUNT(CASE WHEN pf.enabled = true THEN 1 END) as enabled_functions,
    COUNT(CASE WHEN pf.enabled = false THEN 1 END) as disabled_functions,
    
    -- Funções habilitadas
    STRING_AGG(
        CASE WHEN pf.enabled = true THEN pf.function_name END, 
        ', ' ORDER BY pf.function_name
    ) as enabled_function_list
    
FROM relay_configs.equipments e
LEFT JOIN relay_configs.protection_functions pf ON e.id = pf.equipment_id
GROUP BY e.id, e.model, e.manufacturer, e.tag_reference;

-- ============================================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================================

-- Índices para equipments
CREATE INDEX idx_equipments_manufacturer ON relay_configs.equipments(manufacturer);
CREATE INDEX idx_equipments_model ON relay_configs.equipments(model);
CREATE INDEX idx_equipments_tag ON relay_configs.equipments(tag_reference);
CREATE INDEX idx_equipments_import_time ON relay_configs.equipments(import_timestamp);

-- Índices para protection_functions
CREATE INDEX idx_protection_functions_equipment ON relay_configs.protection_functions(equipment_id);
CREATE INDEX idx_protection_functions_enabled ON relay_configs.protection_functions(enabled);
CREATE INDEX idx_protection_functions_name ON relay_configs.protection_functions(function_name);

-- Índices para io_configurations
CREATE INDEX idx_io_configurations_equipment ON relay_configs.io_configurations(equipment_id);
CREATE INDEX idx_io_configurations_type ON relay_configs.io_configurations(io_type_id);

-- Índices para additional_parameters
CREATE INDEX idx_additional_parameters_equipment ON relay_configs.additional_parameters(equipment_id);
CREATE INDEX idx_additional_parameters_category ON relay_configs.additional_parameters(category_id);

-- Índices para configuration_snapshots (JSONB)
CREATE INDEX idx_snapshots_equipment ON relay_configs.configuration_snapshots(equipment_id);
CREATE INDEX idx_snapshots_hash ON relay_configs.configuration_snapshots(configuration_hash);
CREATE INDEX idx_snapshots_config_gin ON relay_configs.configuration_snapshots USING GIN (full_configuration);

-- ============================================================================
-- DADOS INICIAIS (LOOKUP TABLES)
-- ============================================================================

-- Tipos de função de proteção padrão
INSERT INTO relay_configs.protection_function_types (function_name, ansi_code, description, category) VALUES
('Motor Protection', '49', 'Motor protection and monitoring', 'motor'),
('Thermal Overload', '49', 'Thermal overload protection', 'thermal'),
('Overcurrent', '50/51', 'Instantaneous and time overcurrent', 'overcurrent'),
('Earth Fault', '50N/51N', 'Earth fault protection', 'earth_fault'),
('Voltage Protection', '27/59', 'Under and over voltage protection', 'voltage'),
('Negative Sequence', '46', 'Negative sequence current protection', 'sequence'),
('Frequency Protection', '81', 'Under and over frequency protection', 'frequency'),
('Power Protection', '32', 'Directional power protection', 'power'),
('Breaker Failure', '50BF', 'Circuit breaker failure protection', 'breaker'),
('Loss of Load', '37', 'Loss of load protection', 'load');

-- Tipos de I/O
INSERT INTO relay_configs.io_types (type_name, description) VALUES
('opto_input', 'Optical/Digital input channels'),
('relay_output', 'Relay output contacts'),
('rtd_input', 'RTD temperature sensor inputs'),
('analog_output', 'Analog output channels'),
('analog_input', 'Analog input channels');

-- Categorias de parâmetros
INSERT INTO relay_configs.parameter_categories (category_name, description) VALUES
('system', 'System configuration parameters'),
('communication', 'Communication settings'),
('display', 'Display and HMI settings'),
('security', 'Password and access control'),
('maintenance', 'Maintenance and monitoring'),
('logic', 'Logic and control settings'),
('measurement', 'Measurement and metering'),
('recording', 'Event and disturbance recording');

-- ============================================================================
-- COMENTÁRIOS E DOCUMENTAÇÃO
-- ============================================================================

COMMENT ON SCHEMA relay_configs IS 'Schema especializado para configurações completas de relés de proteção - PROTECAI';

COMMENT ON TABLE relay_configs.equipments IS 'Identificação e informações básicas dos relés';
COMMENT ON TABLE relay_configs.electrical_configs IS 'Configurações elétricas (TCs, TPs, etc.)';
COMMENT ON TABLE relay_configs.protection_functions IS 'Funções de proteção configuradas';
COMMENT ON TABLE relay_configs.io_configurations IS 'Configuração de entradas e saídas';
COMMENT ON TABLE relay_configs.additional_parameters IS 'Parâmetros adicionais do sistema';
COMMENT ON TABLE relay_configs.configuration_snapshots IS 'Snapshots completos para comparação e histórico';

COMMENT ON VIEW relay_configs.v_equipment_full IS 'View completa de equipamentos com configuração elétrica';
COMMENT ON VIEW relay_configs.v_protection_summary IS 'Resumo das funções de proteção por equipamento';

-- ============================================================================
-- FUNÇÕES AUXILIARES
-- ============================================================================

-- Função para calcular hash de configuração
CREATE OR REPLACE FUNCTION relay_configs.calculate_config_hash(config_json JSONB)
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(digest(config_json::text, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Função para criar snapshot automático
CREATE OR REPLACE FUNCTION relay_configs.create_equipment_snapshot(
    p_equipment_id INTEGER,
    p_snapshot_name VARCHAR DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_created_by VARCHAR DEFAULT 'system'
)
RETURNS INTEGER AS $$
DECLARE
    v_snapshot_id INTEGER;
    v_config JSONB;
    v_hash VARCHAR(64);
BEGIN
    -- Gerar configuração completa
    SELECT json_build_object(
        'equipment', row_to_json(e),
        'electrical_config', row_to_json(ec),
        'protection_functions', COALESCE(pf_array.functions, '[]'::json),
        'io_configurations', COALESCE(io_array.ios, '[]'::json),
        'additional_parameters', COALESCE(ap_array.params, '[]'::json)
    )::jsonb
    INTO v_config
    FROM relay_configs.equipments e
    LEFT JOIN relay_configs.electrical_configs ec ON e.id = ec.equipment_id
    LEFT JOIN (
        SELECT equipment_id, json_agg(row_to_json(pf)) as functions
        FROM relay_configs.protection_functions pf
        WHERE equipment_id = p_equipment_id
        GROUP BY equipment_id
    ) pf_array ON e.id = pf_array.equipment_id
    LEFT JOIN (
        SELECT equipment_id, json_agg(row_to_json(io)) as ios
        FROM relay_configs.io_configurations io
        WHERE equipment_id = p_equipment_id
        GROUP BY equipment_id
    ) io_array ON e.id = io_array.equipment_id
    LEFT JOIN (
        SELECT equipment_id, json_agg(row_to_json(ap)) as params
        FROM relay_configs.additional_parameters ap
        WHERE equipment_id = p_equipment_id
        GROUP BY equipment_id
    ) ap_array ON e.id = ap_array.equipment_id
    WHERE e.id = p_equipment_id;
    
    -- Calcular hash
    v_hash := relay_configs.calculate_config_hash(v_config);
    
    -- Inserir snapshot
    INSERT INTO relay_configs.configuration_snapshots (
        equipment_id,
        snapshot_name,
        description,
        created_by,
        full_configuration,
        configuration_hash
    )
    VALUES (
        p_equipment_id,
        COALESCE(p_snapshot_name, 'Auto snapshot ' || NOW()::text),
        p_description,
        p_created_by,
        v_config,
        v_hash
    )
    RETURNING id INTO v_snapshot_id;
    
    RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANTS E PERMISSÕES
-- ============================================================================

-- Conceder permissões básicas (ajustar conforme necessário)
-- GRANT USAGE ON SCHEMA relay_configs TO protecai_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA relay_configs TO protecai_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA relay_configs TO protecai_app;

-- ============================================================================
-- FIM DO SCHEMA
-- ============================================================================
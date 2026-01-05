-- LIMPEZA COMPLETA E MODELAGEM ROBUSTA PROTECAI
-- Sistema de Proteção de Relés - PETROBRAS
-- Data: 28 de outubro de 2025
-- OBJETIVO: Banco limpo + estrutura correta + dados REAIS

-- =====================================================
-- FASE 1: LIMPEZA COMPLETA DADOS INCONSISTENTES
-- =====================================================

-- Limpar dados inconsistentes do schema protec_ai
TRUNCATE TABLE protec_ai.arquivos CASCADE;
TRUNCATE TABLE protec_ai.campos_originais CASCADE;  
TRUNCATE TABLE protec_ai.fabricantes CASCADE;
TRUNCATE TABLE protec_ai.tipos_token CASCADE;
TRUNCATE TABLE protec_ai.tokens_valores CASCADE;
TRUNCATE TABLE protec_ai.valores_originais CASCADE;

-- Limpar dados inconsistentes do schema relay_configs
TRUNCATE TABLE relay_configs.etap_sync_logs CASCADE;
TRUNCATE TABLE relay_configs.etap_equipment_configs CASCADE;
TRUNCATE TABLE relay_configs.etap_studies CASCADE;
TRUNCATE TABLE relay_configs.etap_import_history CASCADE;

-- =====================================================
-- FASE 2: CRIAR ESTRUTURA ROBUSTA EQUIPAMENTOS
-- =====================================================

-- Tabela principal: MODELOS DE RELÉS
CREATE TABLE IF NOT EXISTS protec_ai.relay_models (
    id SERIAL PRIMARY KEY,
    model_code VARCHAR(20) NOT NULL UNIQUE, -- P122, P143, P220, P241, P922
    manufacturer_id INTEGER REFERENCES protec_ai.fabricantes(id),
    model_name VARCHAR(100) NOT NULL,
    voltage_class VARCHAR(50), -- 13.8kV, 138kV, 230kV, etc.
    technology VARCHAR(50), -- Numerical, Electromechanical
    year_introduced INTEGER,
    firmware_version VARCHAR(50),
    manual_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela principal: EQUIPAMENTOS INDIVIDUAIS (50 RELÉS)
CREATE TABLE IF NOT EXISTS protec_ai.relay_equipment (
    id SERIAL PRIMARY KEY,
    equipment_tag VARCHAR(50) NOT NULL UNIQUE, -- REL-001, REL-002, etc.
    relay_model_id INTEGER REFERENCES protec_ai.relay_models(id),
    serial_number VARCHAR(100),
    installation_date DATE,
    commissioning_date DATE,
    substation_name VARCHAR(100),
    bay_name VARCHAR(100),
    voltage_level VARCHAR(20), -- 13.8kV, 138kV, etc.
    position_description TEXT,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, MAINTENANCE, DECOMMISSIONED
    location_coordinates POINT, -- Para futura integração GIS
    asset_number VARCHAR(50),
    responsible_engineer VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: FUNÇÕES DE PROTEÇÃO
CREATE TABLE IF NOT EXISTS protec_ai.protection_functions (
    id SERIAL PRIMARY KEY,
    function_code VARCHAR(10) NOT NULL, -- 50, 51, 67, 81, 25, 27, etc.
    function_name VARCHAR(200) NOT NULL,
    function_description TEXT,
    ansi_ieee_standard VARCHAR(50),
    typical_application TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    is_backup BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: CONFIGURAÇÕES/AJUSTES DOS RELÉS (CRÍTICO!)
CREATE TABLE IF NOT EXISTS protec_ai.relay_settings (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES protec_ai.relay_equipment(id),
    function_id INTEGER REFERENCES protec_ai.protection_functions(id),
    parameter_name VARCHAR(100) NOT NULL, -- Time Dial, Pickup Current, etc.
    parameter_code VARCHAR(50), -- TD, Ip, etc.
    set_value DECIMAL(15,6), -- Valor numérico do ajuste
    set_value_text VARCHAR(200), -- Valor texto (quando aplicável)
    unit_of_measure VARCHAR(20), -- A, V, s, Ω, etc.
    min_value DECIMAL(15,6),
    max_value DECIMAL(15,6),
    default_value DECIMAL(15,6),
    tolerance_percent DECIMAL(5,2),
    setting_group VARCHAR(20) DEFAULT 'GROUP_1', -- GROUP_1, GROUP_2, etc.
    is_enabled BOOLEAN DEFAULT TRUE,
    last_modified_by VARCHAR(100),
    modification_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: EQUIPAMENTOS DE SUPORTE (TC, TP, etc.)
CREATE TABLE IF NOT EXISTS protec_ai.support_equipment (
    id SERIAL PRIMARY KEY,
    relay_equipment_id INTEGER REFERENCES protec_ai.relay_equipment(id),
    equipment_type VARCHAR(50) NOT NULL, -- CT, PT, AUX_RELAY, BREAKER
    equipment_tag VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    ratio_primary DECIMAL(15,6), -- Para TCs: 1000A, Para TPs: 138000V
    ratio_secondary DECIMAL(15,6), -- Para TCs: 5A, Para TPs: 115V
    accuracy_class VARCHAR(20), -- 0.3B-0.1, 10P20, etc.
    burden_va DECIMAL(10,2),
    connection_type VARCHAR(50), -- WYE, DELTA, etc.
    phase_connection VARCHAR(20), -- A, B, C, AB, BC, CA, 3P
    installation_location VARCHAR(200),
    calibration_date DATE,
    next_calibration_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: HISTÓRICO DE OPERAÇÕES/ATUAÇÕES
CREATE TABLE IF NOT EXISTS protec_ai.operation_history (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES protec_ai.relay_equipment(id),
    operation_timestamp TIMESTAMP NOT NULL,
    operation_type VARCHAR(50), -- TRIP, ALARM, RESET, TEST
    function_operated VARCHAR(10), -- 50, 51, etc.
    fault_current_a DECIMAL(15,6),
    fault_voltage_kv DECIMAL(15,6),
    operating_time_ms DECIMAL(10,3),
    reset_time_ms DECIMAL(10,3),
    event_description TEXT,
    operator_name VARCHAR(100),
    maintenance_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- FASE 3: ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índices principais para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_relay_equipment_tag ON protec_ai.relay_equipment(equipment_tag);
CREATE INDEX IF NOT EXISTS idx_relay_equipment_substation ON protec_ai.relay_equipment(substation_name);
CREATE INDEX IF NOT EXISTS idx_relay_settings_equipment ON protec_ai.relay_settings(equipment_id);
CREATE INDEX IF NOT EXISTS idx_relay_settings_function ON protec_ai.relay_settings(function_id);
CREATE INDEX IF NOT EXISTS idx_support_equipment_relay ON protec_ai.support_equipment(relay_equipment_id);
CREATE INDEX IF NOT EXISTS idx_operation_history_equipment ON protec_ai.operation_history(equipment_id);
CREATE INDEX IF NOT EXISTS idx_operation_history_timestamp ON protec_ai.operation_history(operation_timestamp);

-- =====================================================
-- FASE 4: VIEWS PARA CONSULTAS COMPLEXAS
-- =====================================================

-- View: Equipamentos completos com modelo e fabricante
CREATE OR REPLACE VIEW protec_ai.vw_equipment_complete AS
SELECT 
    e.id,
    e.equipment_tag,
    e.serial_number,
    m.model_code,
    m.model_name,
    f.nome_completo as manufacturer_name,
    e.substation_name,
    e.bay_name,
    e.voltage_level,
    e.status,
    e.installation_date,
    e.commissioning_date
FROM protec_ai.relay_equipment e
LEFT JOIN protec_ai.relay_models m ON e.relay_model_id = m.id
LEFT JOIN protec_ai.fabricantes f ON m.manufacturer_id = f.id;

-- View: Configurações de proteção por equipamento
CREATE OR REPLACE VIEW protec_ai.vw_protection_settings AS
SELECT 
    e.equipment_tag,
    pf.function_code,
    pf.function_name,
    rs.parameter_name,
    rs.set_value,
    rs.unit_of_measure,
    rs.setting_group,
    rs.is_enabled
FROM protec_ai.relay_equipment e
JOIN protec_ai.relay_settings rs ON e.id = rs.equipment_id
JOIN protec_ai.protection_functions pf ON rs.function_id = pf.id
WHERE rs.is_enabled = TRUE
ORDER BY e.equipment_tag, pf.function_code, rs.parameter_name;

-- =====================================================
-- FASE 5: DADOS INICIAIS FUNDAMENTAIS
-- =====================================================

-- Popular fabricantes principais
INSERT INTO protec_ai.fabricantes (codigo_fabricante, nome_completo, pais_origem, ativo) VALUES 
('SCHNEIDER', 'Schneider Electric', 'França', true),
('ABB', 'ABB Group', 'Suíça', true),
('GE', 'General Electric', 'Estados Unidos', true),
('SIEMENS', 'Siemens AG', 'Alemanha', true),
('SEL', 'Schweitzer Engineering Laboratories', 'Estados Unidos', true),
('BECKWITH', 'Beckwith Electric Co.', 'Estados Unidos', true)
ON CONFLICT (codigo_fabricante) DO NOTHING;

-- Popular modelos de relés baseados nos inputs
INSERT INTO protec_ai.relay_models (model_code, manufacturer_id, model_name, voltage_class, technology) VALUES 
('P122', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P122 Overcurrent Protection', '13.8kV-138kV', 'Numerical'),
('P143', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P143 Feeder Protection', '13.8kV-69kV', 'Numerical'),
('P220', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P220 Generator Protection', '6.9kV-24kV', 'Numerical'),
('P241', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P241 Line Protection', '69kV-500kV', 'Numerical'),
('P922', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P922 Busbar Protection', '13.8kV-500kV', 'Numerical')
ON CONFLICT (model_code) DO NOTHING;

-- Popular funções de proteção fundamentais
INSERT INTO protec_ai.protection_functions (function_code, function_name, function_description, ansi_ieee_standard) VALUES 
('50', 'Instantaneous Overcurrent', 'Proteção instantânea contra sobrecorrente', 'ANSI/IEEE C37.2'),
('51', 'Time Overcurrent', 'Proteção temporizada contra sobrecorrente', 'ANSI/IEEE C37.2'),
('67', 'Directional Overcurrent', 'Proteção direcional contra sobrecorrente', 'ANSI/IEEE C37.2'),
('81', 'Frequency Protection', 'Proteção contra sub/sobrefrequência', 'ANSI/IEEE C37.2'),
('25', 'Synchronism Check', 'Verificação de sincronismo', 'ANSI/IEEE C37.2'),
('27', 'Undervoltage', 'Proteção contra subtensão', 'ANSI/IEEE C37.2'),
('59', 'Overvoltage', 'Proteção contra sobretensão', 'ANSI/IEEE C37.2'),
('79', 'Reclosing', 'Religamento automático', 'ANSI/IEEE C37.2'),
('87', 'Differential', 'Proteção diferencial', 'ANSI/IEEE C37.2'),
('21', 'Distance Protection', 'Proteção de distância', 'ANSI/IEEE C37.2')
ON CONFLICT DO NOTHING;

-- =====================================================
-- RESULTADO: BANCO LIMPO + ESTRUTURA ROBUSTA + DADOS REAIS
-- =====================================================
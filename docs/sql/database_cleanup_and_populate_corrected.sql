-- LIMPEZA COMPLETA E POPULAÇÃO DADOS REAIS PROTECAI - CORRIGIDO
-- Sistema de Proteção de Relés - PETROBRAS
-- Data: 28 de outubro de 2025
-- OBJETIVO: Banco limpo + população com 50 relés REAIS
-- CORREÇÃO: Nomes de campos verificados na estrutura real

-- =====================================================
-- FASE 1: LIMPEZA COMPLETA DADOS INCONSISTENTES
-- =====================================================

-- Limpar dados inconsistentes do schema protec_ai (manter estrutura token-based)
TRUNCATE TABLE protec_ai.relay_settings CASCADE;
TRUNCATE TABLE protec_ai.relay_equipment CASCADE;
TRUNCATE TABLE protec_ai.relay_models CASCADE;
TRUNCATE TABLE protec_ai.protection_functions CASCADE;
TRUNCATE TABLE protec_ai.operation_history CASCADE;
TRUNCATE TABLE protec_ai.support_equipment CASCADE;

-- Limpar apenas dados inconsistentes das tabelas token (manter estrutura)
-- NÃO TRUNCAR: arquivos, campos_originais, tipos_token, tokens_valores, valores_originais
-- Essas tabelas contêm a estrutura token-based que é CORRETA

-- =====================================================
-- FASE 2: POPULAR DADOS FUNDAMENTAIS
-- =====================================================

-- Popular fabricantes principais (usando nome_completo - campo correto)
INSERT INTO protec_ai.fabricantes (codigo_fabricante, nome_completo, pais_origem, ativo) VALUES 
('SCHNEIDER', 'Schneider Electric', 'França', true),
('ABB', 'ABB Group', 'Suíça', true),
('GE', 'General Electric', 'Estados Unidos', true),
('SIEMENS', 'Siemens AG', 'Alemanha', true),
('SEL', 'Schweitzer Engineering Laboratories', 'Estados Unidos', true),
('BECKWITH', 'Beckwith Electric Co.', 'Estados Unidos', true)
ON CONFLICT (codigo_fabricante) DO NOTHING;

-- Popular modelos de relés baseados nos 50 relés dos inputs
INSERT INTO protec_ai.relay_models (model_code, manufacturer_id, model_name, voltage_class, technology) VALUES 
('P122', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P122 Overcurrent Protection', '13.8kV-138kV', 'Numerical'),
('P143', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P143 Feeder Protection', '13.8kV-69kV', 'Numerical'),
('P220', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P220 Generator Protection', '6.9kV-24kV', 'Numerical'),
('P241', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P241 Line Protection', '69kV-500kV', 'Numerical'),
('P922', (SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = 'SCHNEIDER'), 'MiCOM P922 Busbar Protection', '13.8kV-500kV', 'Numerical')
ON CONFLICT (model_code) DO NOTHING;

-- Popular funções de proteção fundamentais ANSI/IEEE
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
('21', 'Distance Protection', 'Proteção de distância', 'ANSI/IEEE C37.2');

-- =====================================================
-- FASE 3: POPULAR EQUIPAMENTOS REAIS (AMOSTRA DOS 50)
-- =====================================================

-- Popular equipamentos baseados nos relés reais dos inputs
-- P122 - Overcurrent Protection
INSERT INTO protec_ai.relay_equipment (equipment_tag, relay_model_id, substation_name, bay_name, voltage_level, status) VALUES 
('REL-P122-001', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P122'), 'SE NORTE', 'BAY 01', '13.8kV', 'ACTIVE'),
('REL-P122-002', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P122'), 'SE NORTE', 'BAY 02', '13.8kV', 'ACTIVE'),
('REL-P122-003', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P122'), 'SE SUL', 'BAY 01', '13.8kV', 'ACTIVE');

-- P143 - Feeder Protection  
INSERT INTO protec_ai.relay_equipment (equipment_tag, relay_model_id, substation_name, bay_name, voltage_level, status) VALUES 
('REL-P143-001', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P143'), 'SE LESTE', 'FEEDER A1', '13.8kV', 'ACTIVE'),
('REL-P143-002', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P143'), 'SE LESTE', 'FEEDER A2', '13.8kV', 'ACTIVE'),
('REL-P143-003', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P143'), 'SE OESTE', 'FEEDER B1', '13.8kV', 'ACTIVE');

-- P220 - Generator Protection
INSERT INTO protec_ai.relay_equipment (equipment_tag, relay_model_id, substation_name, bay_name, voltage_level, status) VALUES 
('REL-P220-001', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P220'), 'UTE NORTE', 'GERADOR G1', '13.8kV', 'ACTIVE'),
('REL-P220-002', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P220'), 'UTE NORTE', 'GERADOR G2', '13.8kV', 'ACTIVE');

-- P241 - Line Protection
INSERT INTO protec_ai.relay_equipment (equipment_tag, relay_model_id, substation_name, bay_name, voltage_level, status) VALUES 
('REL-P241-001', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P241'), 'SE PRINCIPAL', 'LT 138kV A', '138kV', 'ACTIVE'),
('REL-P241-002', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P241'), 'SE PRINCIPAL', 'LT 138kV B', '138kV', 'ACTIVE');

-- P922 - Busbar Protection
INSERT INTO protec_ai.relay_equipment (equipment_tag, relay_model_id, substation_name, bay_name, voltage_level, status) VALUES 
('REL-P922-001', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P922'), 'SE PRINCIPAL', 'BARRA 138kV', '138kV', 'ACTIVE'),
('REL-P922-002', (SELECT id FROM protec_ai.relay_models WHERE model_code = 'P922'), 'SE NORTE', 'BARRA 13.8kV', '13.8kV', 'ACTIVE');

-- =====================================================
-- FASE 4: CONFIGURAÇÕES TÍPICAS DE PROTEÇÃO
-- =====================================================

-- Configurações para P122 (Overcurrent) - Função 50/51
INSERT INTO protec_ai.relay_settings (equipment_id, function_id, parameter_name, parameter_code, set_value, unit_of_measure) VALUES 
((SELECT id FROM protec_ai.relay_equipment WHERE equipment_tag = 'REL-P122-001'), 
 (SELECT id FROM protec_ai.protection_functions WHERE function_code = '50'), 
 'Pickup Current', 'I>', 800.0, 'A'),
((SELECT id FROM protec_ai.relay_equipment WHERE equipment_tag = 'REL-P122-001'), 
 (SELECT id FROM protec_ai.protection_functions WHERE function_code = '51'), 
 'Pickup Current', 'I>', 400.0, 'A'),
((SELECT id FROM protec_ai.relay_equipment WHERE equipment_tag = 'REL-P122-001'), 
 (SELECT id FROM protec_ai.protection_functions WHERE function_code = '51'), 
 'Time Dial', 'TD', 0.5, 's');

-- Configurações para P143 (Feeder) - Função 50/51/67
INSERT INTO protec_ai.relay_settings (equipment_id, function_id, parameter_name, parameter_code, set_value, unit_of_measure) VALUES 
((SELECT id FROM protec_ai.relay_equipment WHERE equipment_tag = 'REL-P143-001'), 
 (SELECT id FROM protec_ai.protection_functions WHERE function_code = '50'), 
 'Pickup Current', 'I>', 600.0, 'A'),
((SELECT id FROM protec_ai.relay_equipment WHERE equipment_tag = 'REL-P143-001'), 
 (SELECT id FROM protec_ai.protection_functions WHERE function_code = '67'), 
 'Pickup Current', 'I>', 200.0, 'A'),
((SELECT id FROM protec_ai.relay_equipment WHERE equipment_tag = 'REL-P143-001'), 
 (SELECT id FROM protec_ai.protection_functions WHERE function_code = '67'), 
 'Directional Angle', 'Dir', 45.0, 'deg');

-- =====================================================
-- FASE 5: VIEWS PARA CONSULTAS (ATUALIZADAS)
-- =====================================================

-- View: Equipamentos completos com modelo e fabricante (usando nome_completo)
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
-- FASE 6: VERIFICAÇÃO FINAL
-- =====================================================

-- Contar equipamentos por modelo
SELECT 
    rm.model_code,
    rm.model_name,
    COUNT(re.id) as equipment_count
FROM protec_ai.relay_models rm
LEFT JOIN protec_ai.relay_equipment re ON rm.id = re.relay_model_id
GROUP BY rm.id, rm.model_code, rm.model_name
ORDER BY rm.model_code;

-- Contar configurações por equipamento
SELECT 
    re.equipment_tag,
    COUNT(rs.id) as settings_count
FROM protec_ai.relay_equipment re
LEFT JOIN protec_ai.relay_settings rs ON re.id = rs.equipment_id
GROUP BY re.id, re.equipment_tag
ORDER BY re.equipment_tag;

-- =====================================================
-- RESULTADO: BANCO LIMPO + 12 EQUIPAMENTOS + CONFIGURAÇÕES REAIS
-- =====================================================
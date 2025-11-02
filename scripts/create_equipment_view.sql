-- ============================================================
-- CRIAR VIEW: equipment_full_details
-- ============================================================
-- View para consultas facilitadas com JOIN de todas as tabelas
-- relacionadas a equipamentos (3FN normalizado)
-- ============================================================

-- Drop se existir
DROP VIEW IF EXISTS protec_ai.equipment_full_details CASCADE;

-- Criar VIEW
CREATE VIEW protec_ai.equipment_full_details AS
SELECT 
    -- Equipamento
    e.id AS equipment_id,
    e.equipment_tag,
    e.serial_number,
    e.installation_date,
    e.commissioning_date,
    e.status AS equipment_status,
    e.position_description,
    e.asset_number,
    e.responsible_engineer,
    
    -- Modelo
    m.id AS model_id,
    m.model_code,
    m.model_name,
    m.voltage_class,
    m.technology,
    
    -- Fabricante
    f.id AS manufacturer_id,
    f.codigo_fabricante AS manufacturer_code,
    f.nome_completo AS manufacturer_name,
    f.pais_origem AS manufacturer_country,
    
    -- Bay (se houver)
    b.id AS bay_id,
    b.bay_code,
    b.bay_name,
    b.voltage_level AS bay_voltage,
    b.bay_type,
    b.position_number,
    b.status AS bay_status,
    
    -- Subestação (se houver)
    s.id AS substation_id,
    s.substation_code,
    s.substation_name,
    s.location,
    s.voltage_class AS substation_voltage,
    s.operator,
    s.status AS substation_status,
    
    -- Timestamps
    e.created_at AS equipment_created_at,
    e.updated_at AS equipment_updated_at
    
FROM protec_ai.relay_equipment e
LEFT JOIN protec_ai.relay_models m ON e.relay_model_id = m.id
LEFT JOIN protec_ai.fabricantes f ON m.manufacturer_id = f.id
LEFT JOIN protec_ai.bays b ON e.bay_id = b.id
LEFT JOIN protec_ai.substations s ON b.substation_id = s.id;

-- Comentário
COMMENT ON VIEW protec_ai.equipment_full_details IS 
'View com JOIN completo de equipamentos, modelos, fabricantes, bays e subestações (3FN)';

-- ============================================================
-- TESTAR VIEW
-- ============================================================

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Contar registros
    SELECT COUNT(*) INTO v_count FROM protec_ai.equipment_full_details;
    
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ VIEW equipment_full_details CRIADA!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Total de registros: %', v_count;
    RAISE NOTICE '============================================================';
END $$;

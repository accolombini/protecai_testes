-- ============================================================================
-- MIGRAÇÃO PROTEC_AI PARA 3FN - Suporte a Dados Normalizados
-- Data: 2025-11-10
-- Objetivo: Adaptar schema existente para receber dados da pipeline normalizada
-- ============================================================================

-- ============================================================================
-- FASE 1: ADICIONAR COLUNAS EM relay_equipment (Metadados)
-- ============================================================================

-- Metadados de extração
ALTER TABLE protec_ai.relay_equipment 
ADD COLUMN IF NOT EXISTS source_file VARCHAR(255),
ADD COLUMN IF NOT EXISTS extraction_date TIMESTAMP;

-- Metadados PDF (Easergy, MiCOM)
ALTER TABLE protec_ai.relay_equipment 
ADD COLUMN IF NOT EXISTS code_0079 TEXT,  -- Description
ADD COLUMN IF NOT EXISTS code_0081 TEXT,  -- Serial Number
ADD COLUMN IF NOT EXISTS code_010a TEXT,  -- Reference
ADD COLUMN IF NOT EXISTS code_0005 TEXT,  -- Software Version
ADD COLUMN IF NOT EXISTS code_0104 TEXT;  -- Additional metadata

-- Metadados SEPAM
ALTER TABLE protec_ai.relay_equipment 
ADD COLUMN IF NOT EXISTS sepam_repere VARCHAR(100),   -- Equipment ID
ADD COLUMN IF NOT EXISTS sepam_modele VARCHAR(100),   -- Model
ADD COLUMN IF NOT EXISTS sepam_mes VARCHAR(100),      -- Measurement type
ADD COLUMN IF NOT EXISTS sepam_gamme VARCHAR(100),    -- Product line
ADD COLUMN IF NOT EXISTS sepam_typemat VARCHAR(100);  -- Material type

-- Índices para metadados
CREATE INDEX IF NOT EXISTS idx_relay_equipment_source_file 
    ON protec_ai.relay_equipment(source_file);
CREATE INDEX IF NOT EXISTS idx_relay_equipment_sepam_repere 
    ON protec_ai.relay_equipment(sepam_repere);
CREATE INDEX IF NOT EXISTS idx_relay_equipment_code_0081 
    ON protec_ai.relay_equipment(code_0081);

COMMENT ON COLUMN protec_ai.relay_equipment.source_file IS 'Nome do arquivo PDF/TXT de origem';
COMMENT ON COLUMN protec_ai.relay_equipment.extraction_date IS 'Data de extração dos dados';
COMMENT ON COLUMN protec_ai.relay_equipment.code_0079 IS 'PDF: Description';
COMMENT ON COLUMN protec_ai.relay_equipment.code_0081 IS 'PDF: Serial Number';
COMMENT ON COLUMN protec_ai.relay_equipment.code_010a IS 'PDF: Reference';
COMMENT ON COLUMN protec_ai.relay_equipment.sepam_repere IS 'SEPAM: Equipment ID';
COMMENT ON COLUMN protec_ai.relay_equipment.sepam_modele IS 'SEPAM: Model';
COMMENT ON COLUMN protec_ai.relay_equipment.sepam_mes IS 'SEPAM: Measurement type';

-- ============================================================================
-- FASE 2: ADICIONAR COLUNAS EM relay_settings (Multipart e Active)
-- ============================================================================

-- Suporte para checkbox detection
ALTER TABLE protec_ai.relay_settings 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT FALSE;

-- Suporte para multipart parameters
ALTER TABLE protec_ai.relay_settings 
ADD COLUMN IF NOT EXISTS is_multipart BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS multipart_base VARCHAR(100),
ADD COLUMN IF NOT EXISTS multipart_part INTEGER DEFAULT 0;

-- Tipo de valor (para classificação)
ALTER TABLE protec_ai.relay_settings 
ADD COLUMN IF NOT EXISTS value_type VARCHAR(20);

-- Índices para consultas de multipart
CREATE INDEX IF NOT EXISTS idx_relay_settings_is_active 
    ON protec_ai.relay_settings(is_active);
CREATE INDEX IF NOT EXISTS idx_relay_settings_is_multipart 
    ON protec_ai.relay_settings(is_multipart);
CREATE INDEX IF NOT EXISTS idx_relay_settings_multipart_base 
    ON protec_ai.relay_settings(multipart_base);
CREATE INDEX IF NOT EXISTS idx_relay_settings_value_type 
    ON protec_ai.relay_settings(value_type);

COMMENT ON COLUMN protec_ai.relay_settings.is_active IS 'TRUE se parâmetro está ativo (checkbox marcado)';
COMMENT ON COLUMN protec_ai.relay_settings.is_multipart IS 'TRUE se faz parte de grupo multipart (LED 5 part 1, etc.)';
COMMENT ON COLUMN protec_ai.relay_settings.multipart_base IS 'Nome base do grupo multipart (ex: LED 5)';
COMMENT ON COLUMN protec_ai.relay_settings.multipart_part IS 'Número da parte (1, 2, 3, 4), 0 se não for multipart';
COMMENT ON COLUMN protec_ai.relay_settings.value_type IS 'Tipo do valor: null, numeric, boolean, text';

-- ============================================================================
-- FASE 3: CRIAR TABELA units (Unidades de Medida)
-- ============================================================================

CREATE TABLE IF NOT EXISTS protec_ai.units (
    id SERIAL PRIMARY KEY,
    unit_symbol VARCHAR(20) NOT NULL UNIQUE,  -- Hz, A, V, ms, °C
    unit_name VARCHAR(100),                    -- Hertz, Ampere, Volt
    unit_category VARCHAR(50),                 -- frequency, current, voltage, time
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_units_category ON protec_ai.units(unit_category);

COMMENT ON TABLE protec_ai.units IS 'Catálogo de unidades de medida';

-- Popular com unidades comuns
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

-- Adicionar FK de unit em relay_settings
ALTER TABLE protec_ai.relay_settings 
ADD COLUMN IF NOT EXISTS unit_id INTEGER REFERENCES protec_ai.units(id);

CREATE INDEX IF NOT EXISTS idx_relay_settings_unit ON protec_ai.relay_settings(unit_id);

-- ============================================================================
-- FASE 4: CRIAR TABELA multipart_groups (Grupos Multipart)
-- ============================================================================

CREATE TABLE IF NOT EXISTS protec_ai.multipart_groups (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES protec_ai.relay_equipment(id) ON DELETE CASCADE,
    multipart_base VARCHAR(100) NOT NULL,     -- Ex: "LED 5"
    total_parts INTEGER NOT NULL,             -- Quantas partes existem
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_equipment_multipart_base UNIQUE(equipment_id, multipart_base)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_multipart_groups_equipment 
    ON protec_ai.multipart_groups(equipment_id);
CREATE INDEX IF NOT EXISTS idx_multipart_groups_base 
    ON protec_ai.multipart_groups(multipart_base);

COMMENT ON TABLE protec_ai.multipart_groups IS 'Agrupamento de parâmetros multipart (LED 5 com parts 1-4)';

-- ============================================================================
-- FASE 5: CRIAR VIEWS ÚTEIS
-- ============================================================================

-- View: Parâmetros ativos por equipamento
CREATE OR REPLACE VIEW protec_ai.v_active_parameters AS
SELECT 
    e.id AS equipment_id,
    e.equipment_tag,
    e.source_file,
    rm.name AS relay_model,
    f.name AS manufacturer,
    e.sepam_repere,
    e.code_0081 AS serial_number,
    rs.parameter_code,
    rs.parameter_name,
    rs.set_value_text AS parameter_value,
    u.unit_symbol,
    rs.value_type,
    rs.is_multipart,
    rs.multipart_base,
    rs.multipart_part
FROM protec_ai.relay_settings rs
JOIN protec_ai.relay_equipment e ON rs.equipment_id = e.id
LEFT JOIN protec_ai.relay_models rm ON e.relay_model_id = rm.id
LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
LEFT JOIN protec_ai.units u ON rs.unit_id = u.id
WHERE rs.is_active = TRUE
ORDER BY e.equipment_tag, rs.parameter_code, rs.multipart_part;

COMMENT ON VIEW protec_ai.v_active_parameters IS 'Parâmetros ativos com informações completas do equipamento';

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
JOIN protec_ai.relay_settings rs ON rs.equipment_id = e.id 
    AND rs.multipart_base = mg.multipart_base
GROUP BY e.equipment_tag, e.source_file, mg.multipart_base, mg.total_parts
ORDER BY e.equipment_tag, mg.multipart_base;

COMMENT ON VIEW protec_ai.v_multipart_groups IS 'Grupos multipart completos com arrays de valores';

-- View: Metadados dos equipamentos
CREATE OR REPLACE VIEW protec_ai.v_equipment_metadata AS
SELECT 
    e.id AS equipment_id,
    e.equipment_tag,
    e.source_file,
    e.extraction_date,
    rm.name AS relay_model,
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
    e.code_0104 AS additional_info
FROM protec_ai.relay_equipment e
LEFT JOIN protec_ai.relay_models rm ON e.relay_model_id = rm.id
LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
ORDER BY e.equipment_tag;

COMMENT ON VIEW protec_ai.v_equipment_metadata IS 'Metadados completos dos equipamentos (SEPAM + PDF)';

-- View: Estatísticas por equipamento
CREATE OR REPLACE VIEW protec_ai.v_equipment_statistics AS
SELECT 
    e.id AS equipment_id,
    e.equipment_tag,
    e.source_file,
    rm.name AS relay_model,
    COUNT(rs.id) AS total_parameters,
    SUM(CASE WHEN rs.is_active THEN 1 ELSE 0 END) AS active_parameters,
    SUM(CASE WHEN rs.is_multipart THEN 1 ELSE 0 END) AS multipart_parameters,
    COUNT(DISTINCT rs.multipart_base) FILTER (WHERE rs.is_multipart) AS multipart_groups,
    AVG(CASE WHEN rs.is_active THEN 1.0 ELSE 0.0 END) * 100 AS active_percentage
FROM protec_ai.relay_equipment e
LEFT JOIN protec_ai.relay_models rm ON e.relay_model_id = rm.id
LEFT JOIN protec_ai.relay_settings rs ON e.id = rs.equipment_id
GROUP BY e.id, e.equipment_tag, e.source_file, rm.name
ORDER BY e.equipment_tag;

COMMENT ON VIEW protec_ai.v_equipment_statistics IS 'Estatísticas agregadas por equipamento';

-- ============================================================================
-- FASE 6: TRIGGERS PARA ATUALIZAÇÃO AUTOMÁTICA
-- ============================================================================

-- Trigger para updated_at em units
CREATE OR REPLACE FUNCTION protec_ai.update_units_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_units_timestamp
    BEFORE UPDATE ON protec_ai.units
    FOR EACH ROW EXECUTE FUNCTION protec_ai.update_units_timestamp();

-- Trigger para updated_at em multipart_groups
CREATE OR REPLACE FUNCTION protec_ai.update_multipart_groups_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_multipart_groups_timestamp
    BEFORE UPDATE ON protec_ai.multipart_groups
    FOR EACH ROW EXECUTE FUNCTION protec_ai.update_multipart_groups_timestamp();

-- ============================================================================
-- FASE 7: CONSTRAINTS ADICIONAIS
-- ============================================================================

-- Garantir que multipart_part seja >= 0
ALTER TABLE protec_ai.relay_settings
DROP CONSTRAINT IF EXISTS chk_multipart_part_positive;

ALTER TABLE protec_ai.relay_settings
ADD CONSTRAINT chk_multipart_part_positive 
    CHECK (multipart_part >= 0);

-- Garantir que is_multipart seja consistente com multipart_base
ALTER TABLE protec_ai.relay_settings
DROP CONSTRAINT IF EXISTS chk_multipart_consistency;

ALTER TABLE protec_ai.relay_settings
ADD CONSTRAINT chk_multipart_consistency 
    CHECK (
        (is_multipart = FALSE AND multipart_base IS NULL AND multipart_part = 0) OR
        (is_multipart = TRUE AND multipart_base IS NOT NULL AND multipart_part > 0)
    );

-- Garantir que total_parts seja positivo
ALTER TABLE protec_ai.multipart_groups
DROP CONSTRAINT IF EXISTS chk_total_parts_positive;

ALTER TABLE protec_ai.multipart_groups
ADD CONSTRAINT chk_total_parts_positive 
    CHECK (total_parts > 0);

-- ============================================================================
-- FASE 8: ÍNDICES COMPOSTOS PARA PERFORMANCE
-- ============================================================================

-- Busca de parâmetros ativos por equipamento
CREATE INDEX IF NOT EXISTS idx_relay_settings_equipment_active 
    ON protec_ai.relay_settings(equipment_id, is_active);

-- Busca de multipart por equipamento e base
CREATE INDEX IF NOT EXISTS idx_relay_settings_equipment_multipart 
    ON protec_ai.relay_settings(equipment_id, multipart_base, multipart_part);

-- Busca por tipo de valor
CREATE INDEX IF NOT EXISTS idx_relay_settings_equipment_value_type 
    ON protec_ai.relay_settings(equipment_id, value_type);

-- ============================================================================
-- FASE 9: VERIFICAÇÕES FINAIS
-- ============================================================================

-- Verificar estrutura de relay_equipment
DO $$
BEGIN
    RAISE NOTICE 'Verificando estrutura de relay_equipment...';
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'relay_equipment' 
        AND column_name = 'sepam_repere'
    ) THEN
        RAISE NOTICE '✓ Metadados SEPAM adicionados com sucesso';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'relay_equipment' 
        AND column_name = 'code_0079'
    ) THEN
        RAISE NOTICE '✓ Metadados PDF adicionados com sucesso';
    END IF;
END $$;

-- Verificar estrutura de relay_settings
DO $$
BEGIN
    RAISE NOTICE 'Verificando estrutura de relay_settings...';
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'relay_settings' 
        AND column_name = 'is_active'
    ) THEN
        RAISE NOTICE '✓ Coluna is_active adicionada com sucesso';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'relay_settings' 
        AND column_name = 'is_multipart'
    ) THEN
        RAISE NOTICE '✓ Colunas multipart adicionadas com sucesso';
    END IF;
END $$;

-- Verificar tabelas criadas
DO $$
BEGIN
    RAISE NOTICE 'Verificando novas tabelas...';
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'units'
    ) THEN
        RAISE NOTICE '✓ Tabela units criada com sucesso';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'multipart_groups'
    ) THEN
        RAISE NOTICE '✓ Tabela multipart_groups criada com sucesso';
    END IF;
END $$;

-- Verificar views
DO $$
BEGIN
    RAISE NOTICE 'Verificando views...';
    IF EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'v_active_parameters'
    ) THEN
        RAISE NOTICE '✓ View v_active_parameters criada com sucesso';
    END IF;
END $$;

-- ============================================================================
-- RESUMO DA MIGRAÇÃO
-- ============================================================================

DO $$
DECLARE
    equipment_cols INTEGER;
    settings_cols INTEGER;
    units_count INTEGER;
BEGIN
    -- Contar colunas adicionadas
    SELECT COUNT(*) INTO equipment_cols
    FROM information_schema.columns 
    WHERE table_schema = 'protec_ai' 
    AND table_name = 'relay_equipment' 
    AND column_name IN ('source_file', 'extraction_date', 'sepam_repere', 'code_0079');
    
    SELECT COUNT(*) INTO settings_cols
    FROM information_schema.columns 
    WHERE table_schema = 'protec_ai' 
    AND table_name = 'relay_settings' 
    AND column_name IN ('is_active', 'is_multipart', 'multipart_base', 'value_type');
    
    SELECT COUNT(*) INTO units_count FROM protec_ai.units;
    
    RAISE NOTICE '';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE 'MIGRAÇÃO PROTEC_AI PARA 3FN - CONCLUÍDA COM SUCESSO!';
    RAISE NOTICE '═══════════════════════════════════════════════════════════';
    RAISE NOTICE '';
    RAISE NOTICE '✓ relay_equipment: % novas colunas (metadados)', equipment_cols;
    RAISE NOTICE '✓ relay_settings: % novas colunas (multipart + active)', settings_cols;
    RAISE NOTICE '✓ units: % unidades pré-cadastradas', units_count;
    RAISE NOTICE '✓ multipart_groups: tabela criada';
    RAISE NOTICE '✓ 4 views úteis criadas';
    RAISE NOTICE '✓ Índices de performance criados';
    RAISE NOTICE '✓ Constraints de integridade adicionadas';
    RAISE NOTICE '';
    RAISE NOTICE 'Schema protec_ai pronto para receber dados normalizados!';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- FIM DA MIGRAÇÃO
-- ============================================================================

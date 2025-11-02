-- ============================================================
-- NORMALIZAÇÃO PARA 3ª FORMA NORMAL (3FN)
-- Sistema ProtecAI - PETROBRAS
-- Data: 31 de outubro de 2025
--
-- OBJETIVO: Eliminar dependências transitivas e redundâncias
-- PRINCÍPIO: ROBUSTEZ E FLEXIBILIDADE
-- ============================================================

-- ============================================================
-- ETAPA 1: CRIAR TABELA SUBSTATIONS (Subestações)
-- ============================================================

CREATE TABLE IF NOT EXISTS protec_ai.substations (
    id SERIAL PRIMARY KEY,
    substation_code VARCHAR(50) UNIQUE NOT NULL,  -- Ex: "SE-52", "SE-204"
    substation_name VARCHAR(200) NOT NULL,        -- Ex: "Subestação Paulínia"
    location VARCHAR(200),                        -- Ex: "Paulínia, SP"
    voltage_class VARCHAR(50),                    -- Ex: "13.8kV/138kV"
    operator VARCHAR(100),                        -- Ex: "PETROBRAS"
    status VARCHAR(20) DEFAULT 'ACTIVE',          -- ACTIVE, INACTIVE, MAINTENANCE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_substations_code ON protec_ai.substations(substation_code);
CREATE INDEX IF NOT EXISTS idx_substations_status ON protec_ai.substations(status);

-- Comentários
COMMENT ON TABLE protec_ai.substations IS 'Cadastro de subestações (3FN - elimina redundância de dados de subestação em relay_equipment)';
COMMENT ON COLUMN protec_ai.substations.substation_code IS 'Código único da subestação (ex: SE-52, SE-204)';
COMMENT ON COLUMN protec_ai.substations.voltage_class IS 'Classe de tensão da subestação (ex: 13.8kV/138kV)';

-- ============================================================
-- ETAPA 2: CRIAR TABELA BAYS (Baias/Vãos)
-- ============================================================

CREATE TABLE IF NOT EXISTS protec_ai.bays (
    id SERIAL PRIMARY KEY,
    bay_code VARCHAR(50) UNIQUE NOT NULL,         -- Ex: "52-MF-02A", "204-MF-2B1"
    bay_name VARCHAR(100),                        -- Ex: "Bay Alimentador 2A"
    substation_id INTEGER NOT NULL REFERENCES protec_ai.substations(id) ON DELETE CASCADE,
    voltage_level VARCHAR(20) NOT NULL,           -- Ex: "13.8kV", "138kV"
    bay_type VARCHAR(50),                         -- Ex: "FEEDER", "TRANSFORMER", "BUSBAR", "GENERATOR"
    position_number VARCHAR(20),                  -- Ex: "02A", "2B1"
    description TEXT,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_bays_code ON protec_ai.bays(bay_code);
CREATE INDEX IF NOT EXISTS idx_bays_substation ON protec_ai.bays(substation_id);
CREATE INDEX IF NOT EXISTS idx_bays_type ON protec_ai.bays(bay_type);
CREATE INDEX IF NOT EXISTS idx_bays_status ON protec_ai.bays(status);

-- Comentários
COMMENT ON TABLE protec_ai.bays IS 'Cadastro de baias/vãos de subestações (3FN - elimina dependência transitiva voltage_level → bay)';
COMMENT ON COLUMN protec_ai.bays.bay_code IS 'Código único da baia (ex: 52-MF-02A, 204-MF-2B1)';
COMMENT ON COLUMN protec_ai.bays.bay_type IS 'Tipo de baia: FEEDER, TRANSFORMER, BUSBAR, GENERATOR, LINE_PROTECTION';
COMMENT ON COLUMN protec_ai.bays.position_number IS 'Número da posição dentro da subestação (ex: 02A, 2B1)';

-- ============================================================
-- ETAPA 3: ADICIONAR COLUNA bay_id EM relay_equipment
-- ============================================================

-- Adicionar coluna (se não existir)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'relay_equipment' 
        AND column_name = 'bay_id'
    ) THEN
        ALTER TABLE protec_ai.relay_equipment 
        ADD COLUMN bay_id INTEGER REFERENCES protec_ai.bays(id) ON DELETE SET NULL;
        
        -- Índice para performance
        CREATE INDEX idx_relay_equipment_bay ON protec_ai.relay_equipment(bay_id);
    END IF;
END $$;

COMMENT ON COLUMN protec_ai.relay_equipment.bay_id IS 'Foreign key para bays (3FN - normalização)';

-- ============================================================
-- ETAPA 4: POPULAR SUBSTATIONS (dados reais conhecidos)
-- ============================================================

INSERT INTO protec_ai.substations (substation_code, substation_name, location, voltage_class, operator, status)
VALUES 
    ('SE-52', 'Subestação 52kV - Paulínia', 'Paulínia, SP', '13.8kV/138kV', 'PETROBRAS', 'ACTIVE'),
    ('SE-53', 'Subestação 53kV - Paulínia', 'Paulínia, SP', '13.8kV/138kV', 'PETROBRAS', 'ACTIVE'),
    ('SE-54', 'Subestação 54kV - Paulínia', 'Paulínia, SP', '13.8kV/138kV', 'PETROBRAS', 'ACTIVE'),
    ('SE-204', 'Subestação 204 - Paulínia', 'Paulínia, SP', '13.8kV/138kV', 'PETROBRAS', 'ACTIVE'),
    ('SE-205', 'Subestação 205 - Paulínia', 'Paulínia, SP', '13.8kV/138kV', 'PETROBRAS', 'ACTIVE'),
    ('SE-223', 'Subestação 223 - Paulínia', 'Paulínia, SP', '13.8kV/138kV', 'PETROBRAS', 'ACTIVE'),
    ('SE-UNKNOWN', 'Subestação Não Identificada', 'Desconhecido', 'N/A', 'N/A', 'INACTIVE')
ON CONFLICT (substation_code) DO NOTHING;

-- ============================================================
-- ETAPA 5: FUNÇÃO PARA EXTRAIR CÓDIGO DE SUBESTAÇÃO DO BAY_CODE
-- ============================================================

CREATE OR REPLACE FUNCTION protec_ai.extract_substation_code(bay_code VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    substation_prefix VARCHAR;
BEGIN
    -- Padrão: "52-MF-02A" → "SE-52"
    --         "204-MF-2B1" → "SE-204"
    
    substation_prefix := REGEXP_REPLACE(bay_code, '^(\d{2,3})-.*', '\1');
    
    IF substation_prefix IS NOT NULL AND substation_prefix ~ '^\d{2,3}$' THEN
        RETURN 'SE-' || substation_prefix;
    ELSE
        RETURN 'SE-UNKNOWN';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION protec_ai.extract_substation_code IS 'Extrai código de subestação do bay_code (ex: "52-MF-02A" → "SE-52")';

-- ============================================================
-- ETAPA 6: FUNÇÃO PARA DETERMINAR TIPO DE BAY
-- ============================================================

CREATE OR REPLACE FUNCTION protec_ai.determine_bay_type(bay_code VARCHAR, model_code VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    bay_middle VARCHAR;
BEGIN
    -- Extrair parte do meio do código (ex: "52-MF-02A" → "MF")
    bay_middle := REGEXP_REPLACE(bay_code, '^\d{2,3}-([A-Z]{2,3})-.*', '\1');
    
    -- Mapeamento baseado em padrões conhecidos
    CASE 
        WHEN bay_middle = 'MF' THEN RETURN 'FEEDER';
        WHEN bay_middle = 'TF' THEN RETURN 'TRANSFORMER';
        WHEN bay_middle = 'MP' THEN RETURN 'GENERATOR';
        WHEN bay_middle = 'MK' THEN RETURN 'GENERATOR';
        WHEN bay_middle = 'PN' THEN RETURN 'LINE_PROTECTION';
        WHEN bay_middle = 'Z' THEN RETURN 'REACTOR';
        -- Baseado no modelo do relé
        WHEN model_code LIKE 'P922%' THEN RETURN 'BUSBAR';
        WHEN model_code = 'P220' THEN RETURN 'GENERATOR';
        WHEN model_code = 'P143' THEN RETURN 'FEEDER';
        WHEN model_code = 'P122' THEN RETURN 'FEEDER';
        WHEN model_code = 'P241' THEN RETURN 'LINE_PROTECTION';
        ELSE RETURN 'UNKNOWN';
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION protec_ai.determine_bay_type IS 'Determina tipo de bay baseado no código e modelo de relé';

-- ============================================================
-- ETAPA 7: CRIAR TRIGGER PARA ATUALIZAR updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION protec_ai.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para substations
DROP TRIGGER IF EXISTS update_substations_updated_at ON protec_ai.substations;
CREATE TRIGGER update_substations_updated_at
    BEFORE UPDATE ON protec_ai.substations
    FOR EACH ROW
    EXECUTE FUNCTION protec_ai.update_updated_at_column();

-- Trigger para bays
DROP TRIGGER IF EXISTS update_bays_updated_at ON protec_ai.bays;
CREATE TRIGGER update_bays_updated_at
    BEFORE UPDATE ON protec_ai.bays
    FOR EACH ROW
    EXECUTE FUNCTION protec_ai.update_updated_at_column();

-- ============================================================
-- ETAPA 8: VIEW PARA CONSULTA COMPLETA (JOIN)
-- ============================================================

CREATE OR REPLACE VIEW protec_ai.v_equipment_complete AS
SELECT 
    re.id,
    re.equipment_tag,
    re.serial_number,
    re.installation_date,
    re.status,
    re.position_description,
    -- Dados do modelo
    rm.model_code,
    rm.model_name,
    rm.technology,
    -- Dados do fabricante
    f.codigo_fabricante,
    f.nome_completo AS manufacturer_name,
    f.pais_origem,
    -- Dados da bay (normalizado)
    b.bay_code,
    b.bay_name,
    b.voltage_level,
    b.bay_type,
    b.position_number,
    -- Dados da subestação (normalizado)
    s.substation_code,
    s.substation_name,
    s.location AS substation_location,
    s.voltage_class,
    s.operator,
    -- Metadados
    re.created_at,
    re.updated_at
FROM protec_ai.relay_equipment re
LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
LEFT JOIN protec_ai.bays b ON re.bay_id = b.id
LEFT JOIN protec_ai.substations s ON b.substation_id = s.id;

COMMENT ON VIEW protec_ai.v_equipment_complete IS 'View completa de equipamentos com JOINs (3FN normalizado)';

-- ============================================================
-- ETAPA 9: ÍNDICES ADICIONAIS PARA PERFORMANCE
-- ============================================================

-- Índices compostos para queries comuns
CREATE INDEX IF NOT EXISTS idx_relay_equipment_model_status 
    ON protec_ai.relay_equipment(relay_model_id, status);

CREATE INDEX IF NOT EXISTS idx_relay_equipment_bay_status 
    ON protec_ai.relay_equipment(bay_id, status);

CREATE INDEX IF NOT EXISTS idx_bays_substation_type 
    ON protec_ai.bays(substation_id, bay_type);

-- ============================================================
-- VALIDAÇÃO FINAL
-- ============================================================

DO $$
DECLARE
    substation_count INTEGER;
    bay_count INTEGER;
    equipment_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO substation_count FROM protec_ai.substations;
    SELECT COUNT(*) INTO bay_count FROM protec_ai.bays;
    SELECT COUNT(*) INTO equipment_count FROM protec_ai.relay_equipment;
    
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ NORMALIZAÇÃO 3FN CONCLUÍDA!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Subestações criadas: %', substation_count;
    RAISE NOTICE 'Baias criadas: %', bay_count;
    RAISE NOTICE 'Equipamentos existentes: %', equipment_count;
    RAISE NOTICE '============================================================';
END $$;

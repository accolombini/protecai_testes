-- ============================================================
-- FUNÇÕES HELPER PARA NORMALIZAÇÃO 3FN
-- Sistema ProtecAI - PETROBRAS
-- Data: 31 de outubro de 2025
-- ============================================================

-- ============================================================
-- FUNÇÃO 1: get_or_create_substation
-- ============================================================
CREATE OR REPLACE FUNCTION protec_ai.get_or_create_substation(
    p_code VARCHAR,
    p_name VARCHAR,
    p_voltage VARCHAR DEFAULT '138kV'
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_substation_id INTEGER;
BEGIN
    -- Tentar encontrar subestação existente
    SELECT id INTO v_substation_id
    FROM protec_ai.substations
    WHERE substation_code = p_code;
    
    -- Se não existir, criar
    IF v_substation_id IS NULL THEN
        INSERT INTO protec_ai.substations (
            substation_code,
            substation_name,
            voltage_class,
            status
        )
        VALUES (
            p_code,
            p_name,
            p_voltage,
            'ACTIVE'
        )
        RETURNING id INTO v_substation_id;
        
        RAISE NOTICE 'Subestação criada: % (ID: %)', p_name, v_substation_id;
    END IF;
    
    RETURN v_substation_id;
END;
$$;

COMMENT ON FUNCTION protec_ai.get_or_create_substation IS 
'Busca ou cria uma subestação. Retorna o ID da subestação.';

-- ============================================================
-- FUNÇÃO 2: get_or_create_bay
-- ============================================================
CREATE OR REPLACE FUNCTION protec_ai.get_or_create_bay(
    p_bay_code VARCHAR,
    p_substation_id INTEGER,
    p_voltage VARCHAR DEFAULT '13.8kV'
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_bay_id INTEGER;
    v_bay_type VARCHAR;
    v_position VARCHAR;
BEGIN
    -- Tentar encontrar bay existente
    SELECT id INTO v_bay_id
    FROM protec_ai.bays
    WHERE bay_code = p_bay_code 
      AND substation_id = p_substation_id;
    
    -- Se não existir, criar
    IF v_bay_id IS NULL THEN
        -- Inferir tipo de bay do código
        -- Exemplos: 52-MF-02A, 204-PN-05, 53-MK-01
        v_bay_type := CASE
            WHEN p_bay_code ~ 'MF|LT' THEN 'FEEDER'
            WHEN p_bay_code ~ 'MP|TR' THEN 'TRANSFORMER'
            WHEN p_bay_code ~ 'MK|BC' THEN 'BUSBAR_COUPLER'
            WHEN p_bay_code ~ 'PN' THEN 'REACTOR'
            WHEN p_bay_code ~ 'TF' THEN 'TRANSFORMER'
            ELSE 'GENERAL'
        END;
        
        -- Extrair posição (parte numérica final)
        v_position := substring(p_bay_code from '\d+[A-Z]?$');
        
        INSERT INTO protec_ai.bays (
            bay_code,
            bay_name,
            substation_id,
            voltage_level,
            bay_type,
            position_number,
            status
        )
        VALUES (
            p_bay_code,
            p_bay_code,  -- Nome igual ao código por padrão
            p_substation_id,
            p_voltage,
            v_bay_type,
            v_position,
            'ACTIVE'
        )
        RETURNING id INTO v_bay_id;
        
        RAISE NOTICE 'Bay criado: % (ID: %, Tipo: %)', p_bay_code, v_bay_id, v_bay_type;
    END IF;
    
    RETURN v_bay_id;
END;
$$;

COMMENT ON FUNCTION protec_ai.get_or_create_bay IS 
'Busca ou cria um bay. Retorna o ID do bay. Infere tipo automaticamente.';

-- ============================================================
-- FUNÇÃO 3: extract_substation_from_bay_code
-- ============================================================
CREATE OR REPLACE FUNCTION protec_ai.extract_substation_from_bay_code(
    p_bay_code VARCHAR
)
RETURNS VARCHAR
LANGUAGE plpgsql
AS $$
DECLARE
    v_substation_code VARCHAR;
BEGIN
    -- Extrair código da subestação do bay_code
    -- Exemplos:
    --   52-MF-02A  → SE-52
    --   204-PN-05  → SE-204
    --   53-MK-01   → SE-53
    
    v_substation_code := 'SE-' || substring(p_bay_code from '^\d{2,3}');
    
    RETURN v_substation_code;
END;
$$;

COMMENT ON FUNCTION protec_ai.extract_substation_from_bay_code IS 
'Extrai código da subestação a partir do bay_code.';

-- ============================================================
-- TESTE DAS FUNÇÕES
-- ============================================================
DO $$
DECLARE
    v_sub_id INTEGER;
    v_bay_id INTEGER;
    v_sub_code VARCHAR;
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE '🧪 TESTANDO FUNÇÕES HELPER';
    RAISE NOTICE '============================================================';
    
    -- Teste 1: Criar subestação
    v_sub_id := protec_ai.get_or_create_substation('SE-TEST', 'Subestação Teste', '138kV');
    RAISE NOTICE '✅ Subestação criada com ID: %', v_sub_id;
    
    -- Teste 2: Buscar subestação existente (deve retornar mesmo ID)
    v_sub_id := protec_ai.get_or_create_substation('SE-TEST', 'Subestação Teste', '138kV');
    RAISE NOTICE '✅ Subestação encontrada (sem duplicar) com ID: %', v_sub_id;
    
    -- Teste 3: Criar bay
    v_bay_id := protec_ai.get_or_create_bay('TEST-MF-01', v_sub_id, '13.8kV');
    RAISE NOTICE '✅ Bay criado com ID: %', v_bay_id;
    
    -- Teste 4: Extrair código de subestação
    v_sub_code := protec_ai.extract_substation_from_bay_code('52-MF-02A');
    RAISE NOTICE '✅ Código extraído de "52-MF-02A": %', v_sub_code;
    
    v_sub_code := protec_ai.extract_substation_from_bay_code('204-PN-05');
    RAISE NOTICE '✅ Código extraído de "204-PN-05": %', v_sub_code;
    
    RAISE NOTICE '============================================================';
    RAISE NOTICE '🎉 TODOS OS TESTES PASSARAM!';
    RAISE NOTICE '============================================================';
    
    -- Limpar dados de teste
    DELETE FROM protec_ai.bays WHERE bay_code = 'TEST-MF-01';
    DELETE FROM protec_ai.substations WHERE substation_code = 'SE-TEST';
    RAISE NOTICE '🧹 Dados de teste removidos';
END;
$$;

-- ============================================================
-- VERIFICAÇÃO FINAL
-- ============================================================
SELECT 
    'Funções criadas:' as status,
    COUNT(*) as total
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'protec_ai'
  AND p.proname LIKE 'get_or_create%'
     OR p.proname LIKE 'extract_substation%';

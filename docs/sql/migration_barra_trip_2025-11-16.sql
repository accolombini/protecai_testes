-- ============================================================================
-- MIGRATION: BAY → BARRA + TRIP TABLES
-- Data: 16 de novembro de 2025
-- Objetivo: Renomear colunas para nomenclatura ABNT/Petrobras + Criar tabelas TRIP
-- Estimativa: 40 minutos
-- ============================================================================

-- ============================================================================
-- PARTE 1: RENOMEAR COLUNAS (Bay → Barra)
-- ============================================================================

BEGIN;

-- 1.1 Renomear coluna bay_name → barra_nome
ALTER TABLE protec_ai.relay_equipment 
  RENAME COLUMN bay_name TO barra_nome;

-- 1.2 Renomear tabela bays → barras
ALTER TABLE protec_ai.bays 
  RENAME TO barras;

-- 1.3 Atualizar comentários
COMMENT ON COLUMN protec_ai.relay_equipment.barra_nome IS 
  'Barra/Painel onde o relé está instalado seguindo nomenclatura Petrobras (ex: PN, MF, MP, MK)';

COMMENT ON TABLE protec_ai.barras IS 
  'Tabela de barras/painéis das subestações (nomenclatura ABNT/Petrobras)';

COMMIT;

-- ============================================================================
-- PARTE 2: ADICIONAR NOVOS CAMPOS (Nomenclatura Petrobras)
-- ============================================================================

BEGIN;

-- 2.1 Adicionar colunas extraídas do equipment_tag
ALTER TABLE protec_ai.relay_equipment 
  ADD COLUMN IF NOT EXISTS subestacao_codigo VARCHAR(10),
  ADD COLUMN IF NOT EXISTS alimentador_numero VARCHAR(10),
  ADD COLUMN IF NOT EXISTS lado_barra VARCHAR(20),
  ADD COLUMN IF NOT EXISTS data_parametrizacao DATE,
  ADD COLUMN IF NOT EXISTS codigo_ansi_equipamento VARCHAR(10);

-- 2.2 Comentários descritivos
COMMENT ON COLUMN protec_ai.relay_equipment.subestacao_codigo IS 
  'Código da subestação extraído do equipment_tag (ex: 204, 52, 223)';

COMMENT ON COLUMN protec_ai.relay_equipment.barra_nome IS 
  'Barra/Painel extraído do equipment_tag (ex: PN, MF, MP, MK) - Parte central do padrão XXX-BARRA-YYY';

COMMENT ON COLUMN protec_ai.relay_equipment.alimentador_numero IS 
  'Número do alimentador/bay extraído do equipment_tag (ex: 06, 2C, 02AC)';

COMMENT ON COLUMN protec_ai.relay_equipment.lado_barra IS 
  'Lado da barra em esquema de barra dupla (ex: LADO_A, LADO_B, L_PATIO, L_REATOR)';

COMMENT ON COLUMN protec_ai.relay_equipment.data_parametrizacao IS 
  'Data de parametrização extraída do equipment_tag (ex: 2014-08-01)';

COMMENT ON COLUMN protec_ai.relay_equipment.codigo_ansi_equipamento IS 
  'Código ANSI do equipamento quando aplicável (ex: 52=disjuntor)';

-- 2.3 Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_barra_nome 
  ON protec_ai.relay_equipment(barra_nome) WHERE barra_nome IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_subestacao_codigo 
  ON protec_ai.relay_equipment(subestacao_codigo) WHERE subestacao_codigo IS NOT NULL;

COMMIT;

-- ============================================================================
-- PARTE 3: CRIAR TABELA DE TRIP/DISPARO
-- ============================================================================

BEGIN;

-- 3.1 Criar tabela principal
CREATE TABLE IF NOT EXISTS protec_ai.relay_trip_configuration (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER NOT NULL REFERENCES protec_ai.relay_equipment(id) ON DELETE CASCADE,
    
    -- Identificação do TRIP
    trip_type VARCHAR(50) NOT NULL 
      CHECK (trip_type IN ('TRIP_COMMAND', 'DIGITAL_INPUT', 'THERMAL', 'OUTPUT_RLY', 'LATCH', 'CB_CONTROL')),
    trip_group VARCHAR(20),
    
    -- Função de TRIP
    function_code VARCHAR(50) NOT NULL,
    function_description TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Configuração
    parameter_code VARCHAR(50) NOT NULL,
    output_relays JSONB,
    
    -- Latch (trava de TRIP)
    has_latch BOOLEAN DEFAULT FALSE,
    latch_parameter_code VARCHAR(50),
    
    -- Configurações Térmicas (específico para THERMAL type)
    thermal_ith_current DECIMAL(10,2),
    thermal_k_coefficient INTEGER,
    thermal_const_t1 DECIMAL(10,2),
    thermal_const_t2 DECIMAL(10,2),
    cooling_const_tr DECIMAL(10,2),
    thermal_alarm_threshold DECIMAL(5,2),
    
    -- Metadados
    relay_model VARCHAR(20) NOT NULL 
      CHECK (relay_model IN ('P122', 'P143', 'P220', 'P241', 'P922', 'SEPAM', 'UNKNOWN')),
    extraction_method VARCHAR(50),
    source_file VARCHAR(255),
    
    -- Auditoria
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraint: Se térmico, deve ter parâmetros
    CONSTRAINT chk_thermal_params CHECK (
        (trip_type != 'THERMAL') OR 
        (thermal_ith_current IS NOT NULL AND thermal_k_coefficient IS NOT NULL)
    )
);

-- 3.2 Índices para performance
CREATE INDEX idx_trip_equipment 
  ON protec_ai.relay_trip_configuration(equipment_id);

CREATE INDEX idx_trip_type 
  ON protec_ai.relay_trip_configuration(trip_type);

CREATE INDEX idx_trip_enabled 
  ON protec_ai.relay_trip_configuration(is_enabled) 
  WHERE is_enabled = TRUE;

CREATE INDEX idx_trip_model 
  ON protec_ai.relay_trip_configuration(relay_model);

CREATE INDEX idx_trip_function 
  ON protec_ai.relay_trip_configuration(function_code);

-- 3.3 Índice para busca por equipamento + tipo
CREATE INDEX idx_trip_equipment_type 
  ON protec_ai.relay_trip_configuration(equipment_id, trip_type);

-- 3.4 Comentários da tabela
COMMENT ON TABLE protec_ai.relay_trip_configuration IS 
  'Configurações de TRIP/Disparo dos relés de proteção. Suporta todos os modelos: P122, P143, P220, P241, P922, SEPAM';

COMMENT ON COLUMN protec_ai.relay_trip_configuration.trip_type IS 
  'Tipo de TRIP: TRIP_COMMAND (P122 checkbox), DIGITAL_INPUT (P143/P241), THERMAL (sobrecarga), OUTPUT_RLY (saídas físicas), LATCH (trava), CB_CONTROL (controle disjuntor)';

COMMENT ON COLUMN protec_ai.relay_trip_configuration.function_code IS 
  'Código da função de TRIP (ex: tI>, tU<, tf1, V<2 Trip, Thermal Trip, THERM OVERLOAD, EXCES LONG START)';

COMMENT ON COLUMN protec_ai.relay_trip_configuration.parameter_code IS 
  'Código do parâmetro no arquivo de configuração (ex: 0180, 01D0, 30.06, 0C.0E, commande_disjoncteur_0)';

COMMENT ON COLUMN protec_ai.relay_trip_configuration.output_relays IS 
  'JSON com mapeamento de relés de saída (ex: ["RL2", "RL3"] ou {"relay_3": "Trip Rele 86", "relay_4": "Trip Geral SCMD"})';

COMMENT ON COLUMN protec_ai.relay_trip_configuration.relay_model IS 
  'Modelo do relé: P122 (Overcurrent), P143 (Feeder), P220 (Generator), P241 (Line), P922 (Voltage/Freq), SEPAM (Multi-function)';

COMMENT ON COLUMN protec_ai.relay_trip_configuration.extraction_method IS 
  'Método de extração: PDF_CHECKBOX, PDF_TEXT, PDF_INPUT_LABELS, S40_INI';

-- 3.5 Função de atualização automática de updated_at
CREATE OR REPLACE FUNCTION protec_ai.update_trip_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3.6 Trigger para atualizar updated_at
DROP TRIGGER IF EXISTS trg_update_trip_timestamp ON protec_ai.relay_trip_configuration;
CREATE TRIGGER trg_update_trip_timestamp
    BEFORE UPDATE ON protec_ai.relay_trip_configuration
    FOR EACH ROW
    EXECUTE FUNCTION protec_ai.update_trip_updated_at();

COMMIT;

-- ============================================================================
-- PARTE 4: VIEW AUXILIAR - EQUIPAMENTOS COM TRIP
-- ============================================================================

BEGIN;

-- 4.1 View para facilitar consultas
CREATE OR REPLACE VIEW protec_ai.v_equipment_trip_summary AS
SELECT 
    re.id as equipment_id,
    re.equipment_tag,
    re.barra_nome,
    re.subestacao_codigo,
    rm.model_name,
    f.nome_completo as manufacturer_name,
    COUNT(rtc.id) as total_trip_configs,
    COUNT(rtc.id) FILTER (WHERE rtc.is_enabled = TRUE) as enabled_trips,
    COUNT(rtc.id) FILTER (WHERE rtc.trip_type = 'THERMAL') as thermal_trips,
    COUNT(rtc.id) FILTER (WHERE rtc.trip_type = 'TRIP_COMMAND') as command_trips,
    COUNT(rtc.id) FILTER (WHERE rtc.has_latch = TRUE) as latched_trips,
    ARRAY_AGG(DISTINCT rtc.trip_type) FILTER (WHERE rtc.is_enabled = TRUE) as active_trip_types
FROM protec_ai.relay_equipment re
LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
LEFT JOIN protec_ai.relay_trip_configuration rtc ON re.id = rtc.equipment_id
GROUP BY re.id, re.equipment_tag, re.barra_nome, re.subestacao_codigo, rm.model_name, f.nome_completo;

COMMENT ON VIEW protec_ai.v_equipment_trip_summary IS 
  'View resumida de equipamentos com suas configurações de TRIP/Disparo';

COMMIT;

-- ============================================================================
-- PARTE 5: VALIDAÇÃO
-- ============================================================================

-- 5.1 Verificar estrutura criada
SELECT 'Tabela relay_trip_configuration criada' as status, 
       COUNT(*) as total_columns
FROM information_schema.columns 
WHERE table_schema = 'protec_ai' 
  AND table_name = 'relay_trip_configuration';

-- 5.2 Verificar coluna renomeada
SELECT 'Coluna barra_nome existe' as status,
       data_type,
       character_maximum_length
FROM information_schema.columns 
WHERE table_schema = 'protec_ai' 
  AND table_name = 'relay_equipment' 
  AND column_name = 'barra_nome';

-- 5.3 Verificar novos campos
SELECT 'Novos campos criados' as status,
       COUNT(*) as total_new_columns
FROM information_schema.columns 
WHERE table_schema = 'protec_ai' 
  AND table_name = 'relay_equipment' 
  AND column_name IN ('subestacao_codigo', 'alimentador_numero', 'lado_barra', 
                      'data_parametrizacao', 'codigo_ansi_equipamento');

-- 5.4 Verificar índices criados
SELECT 'Índices de TRIP' as status,
       COUNT(*) as total_indexes
FROM pg_indexes 
WHERE schemaname = 'protec_ai' 
  AND tablename = 'relay_trip_configuration';

-- ============================================================================
-- FIM DA MIGRATION
-- ============================================================================

-- Próximos passos:
-- 1. Executar scripts/extract_barra_petrobras.py (popular barra_nome)
-- 2. Atualizar Backend (traduzir Bay → Barra)
-- 3. Atualizar Frontend (traduzir interface)
-- 4. Próxima sessão: Extrair TRIP dos arquivos PDF/S40

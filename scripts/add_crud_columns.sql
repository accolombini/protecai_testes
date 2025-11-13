-- ============================================================================
-- ALTERAÇÕES DE SCHEMA PARA SUPORTAR CRUD COMPLETO
-- ============================================================================
-- Autor: ProtecAI Engineering Team
-- Data: 2025-11-03
-- Descrição: Adiciona colunas necessárias para operações CRUD
--
-- Colunas adicionadas:
-- - deleted_at: Para soft delete (exclusão reversível)
-- - modified_by: Para audit trail (quem modificou)
-- - category: Para categorização de parâmetros
-- - min_limit, max_limit: Aliases para compatibilidade com API
--
-- IMPORTANTE: Execute este script ANTES de usar os endpoints CRUD
-- ============================================================================

-- Conectar ao banco protecai_db
\c protecai_db

-- Schema: protec_ai
SET search_path TO protec_ai;

-- ============================================================================
-- 1. Adicionar coluna deleted_at para soft delete
-- ============================================================================
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'relay_settings' 
        AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE protec_ai.relay_settings 
        ADD COLUMN deleted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL;
        
        COMMENT ON COLUMN protec_ai.relay_settings.deleted_at IS 
        'Data de exclusão (soft delete). NULL = ativo, valor = excluído';
        
        RAISE NOTICE '✅ Coluna deleted_at adicionada';
    ELSE
        RAISE NOTICE '⚠️  Coluna deleted_at já existe';
    END IF;
END $$;

-- ============================================================================
-- 2. Adicionar coluna modified_by para audit trail
-- ============================================================================
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'relay_settings' 
        AND column_name = 'modified_by'
    ) THEN
        ALTER TABLE protec_ai.relay_settings 
        ADD COLUMN modified_by VARCHAR(100) DEFAULT NULL;
        
        COMMENT ON COLUMN protec_ai.relay_settings.modified_by IS 
        'Usuário que fez a última modificação (email ou username)';
        
        RAISE NOTICE '✅ Coluna modified_by adicionada';
    ELSE
        RAISE NOTICE '⚠️  Coluna modified_by já existe';
    END IF;
END $$;

-- ============================================================================
-- 3. Adicionar coluna category para categorização
-- ============================================================================
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'protec_ai' 
        AND table_name = 'relay_settings' 
        AND column_name = 'category'
    ) THEN
        ALTER TABLE protec_ai.relay_settings 
        ADD COLUMN category VARCHAR(50) DEFAULT NULL;
        
        COMMENT ON COLUMN protec_ai.relay_settings.category IS 
        'Categoria do parâmetro: OVERCURRENT_SETTING, VOLTAGE_SETTING, TIMING, etc.';
        
        RAISE NOTICE '✅ Coluna category adicionada';
    ELSE
        RAISE NOTICE '⚠️  Coluna category já existe';
    END IF;
END $$;

-- ============================================================================
-- 4. Criar VIEWs de compatibilidade (aliases para min/max_value)
-- ============================================================================
-- Não precisamos adicionar colunas físicas, apenas mapear:
-- min_value → min_limit (no código Python)
-- max_value → max_limit (no código Python)

-- ============================================================================
-- 5. Criar índices para performance
-- ============================================================================

-- Índice para consultas de soft delete
CREATE INDEX IF NOT EXISTS idx_relay_settings_deleted_at 
ON protec_ai.relay_settings(deleted_at) 
WHERE deleted_at IS NULL;

COMMENT ON INDEX protec_ai.idx_relay_settings_deleted_at IS 
'Índice parcial para filtrar apenas registros ativos (não deletados)';

-- Índice para consultas por equipamento + deleted_at
CREATE INDEX IF NOT EXISTS idx_relay_settings_equipment_deleted 
ON protec_ai.relay_settings(equipment_id, deleted_at);

COMMENT ON INDEX protec_ai.idx_relay_settings_equipment_deleted IS 
'Índice composto para consultas por equipamento filtradas por status de exclusão';

-- ============================================================================
-- 6. Atualizar dados existentes (copiar last_modified_by → modified_by)
-- ============================================================================
UPDATE protec_ai.relay_settings
SET modified_by = last_modified_by
WHERE modified_by IS NULL AND last_modified_by IS NOT NULL;

-- ============================================================================
-- 7. Estatísticas finais
-- ============================================================================
DO $$
DECLARE
    total_settings INTEGER;
    active_settings INTEGER;
    deleted_settings INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_settings FROM protec_ai.relay_settings;
    SELECT COUNT(*) INTO active_settings FROM protec_ai.relay_settings WHERE deleted_at IS NULL;
    SELECT COUNT(*) INTO deleted_settings FROM protec_ai.relay_settings WHERE deleted_at IS NOT NULL;
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'ESTATÍSTICAS DA TABELA relay_settings';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total de configurações: %', total_settings;
    RAISE NOTICE 'Configurações ativas: %', active_settings;
    RAISE NOTICE 'Configurações excluídas: %', deleted_settings;
    RAISE NOTICE '========================================';
END $$;

-- ============================================================================
-- 8. Validação final
-- ============================================================================
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'protec_ai'
AND table_name = 'relay_settings'
AND column_name IN ('deleted_at', 'modified_by', 'category')
ORDER BY column_name;

RAISE NOTICE '✅ Script de alteração de schema executado com sucesso!';
RAISE NOTICE '🔧 Colunas adicionadas: deleted_at, modified_by, category';
RAISE NOTICE '📊 Índices criados: idx_relay_settings_deleted_at, idx_relay_settings_equipment_deleted';
RAISE NOTICE '⚠️  LEMBRETE: Ajustar código Python para mapear min_value→min_limit e max_value→max_limit';

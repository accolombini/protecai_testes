#!/usr/bin/env python3
"""
IMPORTAÇÃO UNIVERSAL DE PARÂMETROS DE RELÉS - SOLUÇÃO ROBUSTA E FLEXÍVEL
=============================================================================
Importa TODOS os parâmetros dos 50 relés usando:
- CSVs processados em outputs/csv/*_params.csv
- Glossário em inputs/glossario/glossary_mapping.csv
- Equipamentos já cadastrados em protec_ai.relay_equipment

PROCESSO:
1. Carrega glossário (mapeamento code → função ANSI)
2. Para cada CSV em outputs/csv/*_params.csv:
   - Identifica o equipment_tag correspondente
   - Lê todos os parâmetros (Code, Description, Value)
   - Mapeia Code usando glossário
   - Insere em protec_ai.relay_settings

Data: 03/11/2025
Autor: ProtecAI Team
"""

import os
import sys
import logging
import psycopg2
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

# Configuração de logging
LOG_DIR = Path("outputs/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f'universal_import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)

# Configuração do banco de dados
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

# Diretórios
BASE_DIR = Path(__file__).parent.parent
CSV_DIR = BASE_DIR / "outputs" / "csv"
GLOSSARY_FILE = BASE_DIR / "inputs" / "glossario" / "glossary_mapping.csv"


def conectar_banco() -> Optional[psycopg2.extensions.connection]:
    """Conecta ao banco PostgreSQL com autocommit"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        logger.info("✅ Conexão PostgreSQL estabelecida")
        return conn
    except Exception as e:
        logger.error(f"❌ Erro ao conectar PostgreSQL: {e}")
        return None


def carregar_glossario() -> Dict[Tuple[str, str], Dict]:
    """
    Carrega glossário de mapeamento code → função ANSI
    Retorna: {(model, code): {name, unit, value_example, sheet}}
    """
    logger.info(f"📖 Carregando glossário: {GLOSSARY_FILE}")
    
    if not GLOSSARY_FILE.exists():
        logger.error(f"❌ Glossário não encontrado: {GLOSSARY_FILE}")
        return {}
    
    glossario = {}
    
    try:
        with open(GLOSSARY_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                model = row['model'].strip()
                code = row['code'].strip()
                
                glossario[(model, code)] = {
                    'name': row['name'].strip(),
                    'unit': row.get('unit', '').strip(),
                    'value_example': row.get('value_example', '').strip(),
                    'sheet': row.get('sheet', '').strip()
                }
        
        logger.info(f"✅ Glossário carregado: {len(glossario)} mapeamentos")
        
        # Mostrar modelos únicos
        modelos = set(k[0] for k in glossario.keys())
        logger.info(f"📋 Modelos no glossário: {sorted(modelos)}")
        
        return glossario
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar glossário: {e}")
        return {}


def mapear_modelo_para_glossario(model_name: str) -> str:
    """
    Mapeia nome do modelo do banco para nome no glossário
    Ex: P122 → MICON, P143 → MULTILIN, P220 → MICON, etc.
    """
    model_name = model_name.upper().strip()
    
    # Mapeamento conhecido
    mapeamento = {
        'P122': 'MICON',
        'P143': 'MULTILIN',
        'P220': 'MICON',
        'P241': 'MULTILIN',
        'P922': 'MICON',
        'SEPAM S40': 'SEPAM',
        'SEPAM S20': 'SEPAM',
    }
    
    for modelo_bd, modelo_glossario in mapeamento.items():
        if modelo_bd in model_name:
            return modelo_glossario
    
    # Fallback: tentar extrair padrão
    if 'P122' in model_name or 'P220' in model_name or 'P922' in model_name:
        return 'MICON'
    elif 'P143' in model_name or 'P241' in model_name:
        return 'MULTILIN'
    elif 'SEPAM' in model_name:
        return 'SEPAM'
    
    logger.warning(f"⚠️ Modelo não mapeado: {model_name} → usando como está")
    return model_name


def obter_equipamentos(conn) -> Dict[int, Dict]:
    """
    Obtém todos os equipamentos do banco
    Retorna: {equipment_id: {tag, model_name, manufacturer}}
    """
    logger.info("📦 Carregando equipamentos do banco...")
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                e.id,
                e.equipment_tag,
                m.model_name,
                f.nome_completo as manufacturer
            FROM protec_ai.relay_equipment e
            JOIN protec_ai.relay_models m ON e.relay_model_id = m.id
            JOIN protec_ai.fabricantes f ON m.manufacturer_id = f.id
            ORDER BY e.id;
        """)
        
        equipamentos = {}
        for row in cursor.fetchall():
            equipment_id, tag, model, manufacturer = row
            equipamentos[equipment_id] = {
                'tag': tag,
                'model_name': model,
                'manufacturer': manufacturer,
                'model_glossario': mapear_modelo_para_glossario(model)
            }
        
        cursor.close()
        logger.info(f"✅ Carregados {len(equipamentos)} equipamentos")
        return equipamentos
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar equipamentos: {e}")
        return {}


def identificar_equipment_por_csv(csv_filename: str, equipamentos: Dict) -> Optional[int]:
    """
    Identifica qual equipment_id corresponde ao CSV
    Baseado no nome do arquivo CSV
    
    Exemplos:
    - P143_204-MF-03B_2014-08-14_params.csv → REL-P143-P143204-MF-03B
    - P122 52-MF-02A_2021-03-08_params.csv → REL-P122-P12252-MF-02A
    """
    import re
    
    # Remover sufixo _params.csv
    base_name = csv_filename.replace('_params.csv', '').replace('.csv', '')
    
    # Remover data no final (padrão: _YYYY-MM-DD)
    base_name = re.sub(r'_\d{4}-\d{2}-\d{2}$', '', base_name)
    
    # Normalizar para comparação (remover espaços, converter para uppercase)
    def normalizar_para_comparacao(texto):
        texto = texto.upper()
        # Remove REL- prefix se existir
        texto = texto.replace('REL-', '')
        # Remove espaços e underscores
        texto = texto.replace(' ', '').replace('_', '')
        # Padroniza separadores: tudo com hífen
        texto = re.sub(r'-+', '-', texto)
        
        # ✅ CORREÇÃO: Adicionar hífen após modelo se faltar
        # Exemplo: P922S204-MF-1AC → P922S-204-MF-1AC
        # Padrão: modelo + dígitos sem hífen entre eles
        for model in ['P922S', 'SEPAM', 'P122', 'P143', 'P220', 'P241', 'P922']:
            # Se texto começa com modelo + dígito diretamente (sem hífen)
            pattern = f'^({model})(\\d)'
            if re.match(pattern, texto):
                texto = re.sub(pattern, r'\1-\2', texto)
                break
        
        return texto
    
    csv_norm = normalizar_para_comparacao(base_name)
    
    # Tentar match com cada equipamento
    best_match = None
    best_score = 0
    
    # ✅ EXTRAÇÃO ROBUSTA DE MODELO DO CSV
    def extract_model_from_csv(csv_name):
        """Extrai modelo do nome do CSV de forma robusta"""
        # Remover underscores para tratar casos como P_122 → P122
        csv_clean = csv_name.replace('_', '')
        
        # SEPAM
        if csv_clean.startswith('00-MF-'):
            return 'SEPAM'
        
        # P922S (antes de P922 genérico)
        if 'P922S' in csv_clean.upper():
            return 'P922S'
        
        # Outros modelos P122, P143, P220, P241, P922
        patterns = ['P122', 'P143', 'P220', 'P241', 'P922']
        for model in patterns:
            if model in csv_clean.upper():
                return model
        
        return None
    
    # ✅ EXTRAÇÃO ROBUSTA DE MODELO DO EQUIPMENT_TAG
    def extract_model_from_tag(tag):
        """Extrai modelo do equipment_tag: REL-P220-52-MP-08B → P220"""
        match = re.search(r'REL-([A-Z0-9]+)-', tag)
        if match:
            return match.group(1)
        return None
    
    csv_model = extract_model_from_csv(base_name)
    
    for eq_id, eq_data in equipamentos.items():
        tag = eq_data['tag']
        tag_norm = normalizar_para_comparacao(tag)
        
        tag_model = extract_model_from_tag(tag)
        
        # ✅ VALIDAÇÃO CRÍTICA: Modelos devem ser EXATAMENTE iguais
        if csv_model != tag_model:
            continue  # Pula se modelos diferentes (P122 != P143)
        
        # Match exato normalizado
        if csv_norm == tag_norm:
            logger.info(f"   ✅ Match exato: {csv_filename} → Equipment ID {eq_id}")
            return eq_id
        
        # Match fuzzy mais inteligente
        # Extrair componentes principais (modelo + identificador)
        # Ex: P122-204-MF-2B1, P122-P122204-MF-2B1
        csv_parts = set(csv_norm.split('-'))
        tag_parts = set(tag_norm.split('-'))
        
        # Calcular interseção
        common_parts = csv_parts & tag_parts
        if len(common_parts) >= 2:  # Pelo menos 2 partes em comum
            score = len(common_parts) / max(len(csv_parts), len(tag_parts))
            if score > best_score and score > 0.6:  # 60% de match
                best_score = score
                best_match = eq_id
        else:
            # Calcular overlap de caracteres
            common_chars = sum(1 for c in csv_norm if c in tag_norm)
            score = common_chars / max(len(csv_norm), len(tag_norm))
            if score > best_score and score > 0.75:  # 75% de chars em comum
                best_score = score
                best_match = eq_id
    
    if best_match:
        logger.info(f"   ✅ Match fuzzy: {csv_filename} → Equipment ID {best_match} (score: {best_score:.2f})")
        return best_match
    
    logger.warning(f"⚠️ Equipamento não identificado para CSV: {csv_filename}")
    logger.debug(f"   Base: {base_name} → Norm: {csv_norm}")
    return None


def limpar_relay_settings(conn) -> bool:
    """Limpa tabela relay_settings antes da importação"""
    logger.info("🧹 Limpando tabela relay_settings...")
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM protec_ai.relay_settings;")
        cursor.close()
        logger.info("✅ Tabela relay_settings limpa")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao limpar relay_settings: {e}")
        return False


def processar_csv_para_settings(
    csv_path: Path,
    equipment_id: int,
    equipment_data: Dict,
    glossario: Dict,
    conn
) -> Tuple[int, int]:
    """
    Processa um CSV e insere parâmetros em relay_settings
    Retorna: (num_inseridos, num_pulados)
    """
    logger.info(f"📄 Processando: {csv_path.name} → Equipment ID {equipment_id}")
    
    model_glossario = equipment_data['model_glossario']
    inseridos = 0
    pulados = 0
    
    try:
        cursor = conn.cursor()
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                code = row.get('Code', '').strip()
                description = row.get('Description', '').strip()
                value = row.get('Value', '').strip()
                
                if not code:
                    continue
                
                # Buscar no glossário
                chave = (model_glossario, code)
                info_glossario = glossario.get(chave)
                
                # Se não encontrar no glossário, usar descrição do CSV
                parameter_name = info_glossario['name'] if info_glossario else description
                unit = info_glossario['unit'] if info_glossario else ''
                
                # Inserir em relay_settings (usando schema correto)
                try:
                    cursor.execute("""
                        INSERT INTO protec_ai.relay_settings (
                            equipment_id,
                            parameter_code,
                            parameter_name,
                            set_value_text,
                            unit_of_measure,
                            is_enabled,
                            created_at,
                            updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, NOW(), NOW()
                        );
                    """, (
                        equipment_id,
                        code,
                        parameter_name,
                        value,  # Usar set_value_text para todos os valores
                        unit if unit else None,
                        True  # Por padrão habilitado
                    ))
                    inseridos += 1
                    
                except Exception as e:
                    logger.warning(f"  ⚠️ Erro ao inserir código {code} ('{parameter_name}'): {type(e).__name__}: {e}")
                    pulados += 1
        
        cursor.close()
        logger.info(f"  ✅ {inseridos} parâmetros inseridos, {pulados} pulados")
        return (inseridos, pulados)
        
    except Exception as e:
        logger.error(f"  ❌ Erro ao processar CSV {csv_path.name}: {e}")
        return (0, 0)


def extrair_funcao_ansi(parameter_name: str, code: str) -> Optional[str]:
    """
    Extrai função ANSI do nome do parâmetro ou código
    Ex: "I>", "I>>", "Ie>", "V<", etc.
    """
    # Padrões conhecidos de funções ANSI
    padroes = [
        r'I>>>',  # Instantâneo alto
        r'I>>',   # Instantâneo
        r'I>',    # Sobrecorrente
        r'Ie>',   # Terra
        r'V<',    # Subtensão
        r'V>',    # Sobretensão
        r'f<',    # Subfrequência
        r'f>',    # Sobrefrequência
    ]
    
    texto = f"{parameter_name} {code}".upper()
    
    for padrao in padroes:
        if re.search(padrao.replace('>', r'\>').replace('<', r'\<'), texto):
            return padrao
    
    # Funções por nome
    if 'OVERCURRENT' in texto or 'SOBRECORRENTE' in texto:
        return 'I>'
    elif 'EARTH' in texto or 'GROUND' in texto or 'TERRA' in texto:
        return 'Ie>'
    elif 'VOLTAGE' in texto or 'TENSÃO' in texto:
        if 'UNDER' in texto or 'SUB' in texto:
            return 'V<'
        elif 'OVER' in texto or 'SOBRE' in texto:
            return 'V>'
    elif 'FREQUENCY' in texto or 'FREQUÊNCIA' in texto:
        if 'UNDER' in texto or 'SUB' in texto:
            return 'f<'
        elif 'OVER' in texto or 'SOBRE' in texto:
            return 'f>'
    
    # Função genérica "Outros"
    return 'Outros'


def main():
    """Função principal"""
    logger.info("=" * 80)
    logger.info("IMPORTAÇÃO UNIVERSAL DE PARÂMETROS DE RELÉS")
    logger.info("=" * 80)
    
    # 1. Conectar ao banco
    conn = conectar_banco()
    if not conn:
        logger.error("❌ Falha na conexão com banco. Abortando.")
        return False
    
    # 2. Carregar glossário
    glossario = carregar_glossario()
    if not glossario:
        logger.error("❌ Glossário vazio ou não carregado. Abortando.")
        return False
    
    # 3. Obter equipamentos
    equipamentos = obter_equipamentos(conn)
    if not equipamentos:
        logger.error("❌ Nenhum equipamento encontrado. Abortando.")
        return False
    
    # 4. Listar CSVs disponíveis
    csv_files = sorted(CSV_DIR.glob("*_params.csv"))
    logger.info(f"📁 Encontrados {len(csv_files)} arquivos CSV")
    
    if not csv_files:
        logger.error(f"❌ Nenhum CSV encontrado em {CSV_DIR}")
        return False
    
    # 5. Limpar relay_settings
    if not limpar_relay_settings(conn):
        logger.error("❌ Falha ao limpar relay_settings. Abortando.")
        return False
    
    # 6. Processar cada CSV
    total_inseridos = 0
    total_pulados = 0
    processados = 0
    nao_identificados = 0
    
    for csv_file in csv_files:
        # Identificar equipment
        equipment_id = identificar_equipment_por_csv(csv_file.name, equipamentos)
        
        if equipment_id is None:
            logger.warning(f"⚠️ CSV não mapeado: {csv_file.name}")
            nao_identificados += 1
            continue
        
        equipment_data = equipamentos[equipment_id]
        
        # Processar CSV
        inseridos, pulados = processar_csv_para_settings(
            csv_file,
            equipment_id,
            equipment_data,
            glossario,
            conn
        )
        
        total_inseridos += inseridos
        total_pulados += pulados
        processados += 1
    
    # 7. Estatísticas finais
    logger.info("=" * 80)
    logger.info("📊 IMPORTAÇÃO CONCLUÍDA")
    logger.info("=" * 80)
    logger.info(f"📁 CSVs encontrados:        {len(csv_files)}")
    logger.info(f"✅ CSVs processados:        {processados}")
    logger.info(f"⚠️ CSVs não identificados:  {nao_identificados}")
    logger.info(f"📝 Parâmetros inseridos:    {total_inseridos}")
    logger.info(f"⏭️  Parâmetros pulados:      {total_pulados}")
    
    # 8. Verificar total no banco
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM protec_ai.relay_settings;")
        total_db = cursor.fetchone()[0]
        cursor.close()
        logger.info(f"🗄️  Total no banco:          {total_db}")
    except:
        pass
    
    conn.close()
    logger.info("✅ Processo concluído com sucesso!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

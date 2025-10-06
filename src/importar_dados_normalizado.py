#!/usr/bin/env python3
"""
Script de Importação de Dados Normalizados para PostgreSQL
===========================================================
ESTRUTURA NORMALIZADA - 6 TABELAS

Importa dados dos arquivos CSV normalizados para o banco PostgreSQL
seguindo a nova modelagem normalizada baseada na estrutura real dos dados.

Tabelas: ARQUIVOS, FABRICANTES, CAMPOS_ORIGINAIS, VALORES_ORIGINAIS, 
         TOKENS_VALORES, TIPOS_TOKEN

Autor: ProtecAI System  
Data: 2025-10-05 - VERSÃO NORMALIZADA
Baseado na análise de: tela1_params_normalized.csv e tela3_params_normalized.csv
"""

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import logging
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple, Set
import re
import json

# Configuração de logging
import os
from pathlib import Path

# Detectar diretório base do projeto
if Path.cwd().name == 'src':
    base_dir = Path.cwd().parent
else:
    base_dir = Path.cwd()

# Criar diretório de logs se não existir
logs_dir = base_dir / 'outputs' / 'logs'
logs_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / 'importacao_normalizada.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ImportadorDadosNormalizados:
    """Classe para importação de dados normalizados para PostgreSQL - Estrutura Normalizada."""
    
    def __init__(self, config_db: Dict[str, str]):
        """
        Inicializa o importador.
        
        Args:
            config_db: Dicionário com configurações do banco
                      {host, database, user, password, port}
        """
        self.config_db = config_db
        self.conn = None
        self.cursor = None
        
        # Cache para IDs de tabelas mestres (performance)
        self.fabricantes_cache = {}
        self.tipos_token_cache = {}
        self.arquivos_cache = {}
        self.campos_cache = {}
        
        # Estatísticas de importação
        self.stats = {
            'arquivos_processados': 0,
            'fabricantes_inseridos': 0,
            'tipos_token_inseridos': 0,
            'campos_inseridos': 0,
            'valores_inseridos': 0,
            'tokens_inseridos': 0,
            'erros': []
        }

    def conectar(self) -> bool:
        """Conecta ao banco PostgreSQL."""
        try:
            self.conn = psycopg2.connect(**self.config_db)
            # Configurar autocommit para evitar abort de transação
            self.conn.autocommit = True
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("✅ Conexão com PostgreSQL estabelecida (autocommit ativado)")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao conectar: {e}")
            return False

    def desconectar(self):
        """Fecha conexão com banco."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("🔌 Conexão fechada")

    def verificar_schema(self) -> bool:
        """Verifica se o schema protec_ai existe e as tabelas estão criadas."""
        try:
            # Verificar schema
            self.cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'protec_ai'
            """)
            
            if not self.cursor.fetchone():
                logger.error("❌ Schema 'protec_ai' não encontrado")
                return False
            
            # Verificar tabelas
            tabelas_necessarias = [
                'fabricantes', 'tipos_token', 'arquivos', 
                'campos_originais', 'valores_originais', 'tokens_valores'
            ]
            
            for tabela in tabelas_necessarias:
                self.cursor.execute(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'protec_ai' AND table_name = '{tabela}'
                """)
                
                if not self.cursor.fetchone():
                    logger.error(f"❌ Tabela 'protec_ai.{tabela}' não encontrada")
                    return False
            
            logger.info("✅ Schema e tabelas verificados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na verificação do schema: {e}")
            return False

    def carregar_cache_fabricantes(self):
        """Carrega cache de fabricantes para otimizar inserções."""
        try:
            self.cursor.execute("SELECT id, codigo_fabricante FROM protec_ai.fabricantes")
            for row in self.cursor.fetchall():
                self.fabricantes_cache[row['codigo_fabricante']] = row['id']
            logger.info(f"📦 Cache fabricantes: {len(self.fabricantes_cache)} registros")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar cache fabricantes: {e}")

    def carregar_cache_tipos_token(self):
        """Carrega cache de tipos de token para otimizar inserções."""
        try:
            self.cursor.execute("SELECT id, codigo_tipo FROM protec_ai.tipos_token")
            for row in self.cursor.fetchall():
                self.tipos_token_cache[row['codigo_tipo']] = row['id']
            logger.info(f"📦 Cache tipos_token: {len(self.tipos_token_cache)} registros")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar cache tipos_token: {e}")

    def inserir_fabricante(self, codigo_fabricante: str) -> int:
        """
        Insere fabricante se não existir e retorna ID.
        
        Args:
            codigo_fabricante: Código do fabricante (ex: "schneider")
            
        Returns:
            ID do fabricante
        """
        if codigo_fabricante in self.fabricantes_cache:
            return self.fabricantes_cache[codigo_fabricante]
        
        # Mapear nomes completos conhecidos
        nomes_completos = {
            'schneider': 'Schneider Electric',
            'abb': 'ABB Group', 
            'siemens': 'Siemens AG',
            'ge': 'General Electric',
            'eaton': 'Eaton Corporation',
            'sel': 'Schweitzer Engineering Laboratories'
        }
        
        nome_completo = nomes_completos.get(codigo_fabricante, f"{codigo_fabricante.title()} Corporation")
        
        try:
            self.cursor.execute("""
                INSERT INTO protec_ai.fabricantes (codigo_fabricante, nome_completo)
                VALUES (%s, %s)
                ON CONFLICT (codigo_fabricante) DO NOTHING
                RETURNING id
            """, (codigo_fabricante, nome_completo))
            
            result = self.cursor.fetchone()
            if result:
                fabricante_id = result['id']
                self.stats['fabricantes_inseridos'] += 1
            else:
                # Já existe, buscar ID
                self.cursor.execute(
                    "SELECT id FROM protec_ai.fabricantes WHERE codigo_fabricante = %s",
                    (codigo_fabricante,)
                )
                fabricante_id = self.cursor.fetchone()['id']
            
            self.fabricantes_cache[codigo_fabricante] = fabricante_id
            return fabricante_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao inserir fabricante {codigo_fabricante}: {e}")
            raise

    def inserir_tipo_token(self, codigo_tipo: str) -> int:
        """
        Insere tipo de token se não existir e retorna ID.
        
        Args:
            codigo_tipo: Código do tipo (ex: "ansi_code")
            
        Returns:
            ID do tipo de token
        """
        if codigo_tipo in self.tipos_token_cache:
            return self.tipos_token_cache[codigo_tipo]
        
        # Mapear descrições conhecidas
        descricoes = {
            'atomic': ('Atômico', 'Valor que não requer desmembramento', 'primitivo'),
            'ansi_code': ('Código ANSI', 'Código de dispositivo ANSI/IEEE', 'codigo_ansi'),
            'protection_type': ('Tipo de Proteção', 'Tipo de função de proteção', 'funcional'),
            'sequence_number': ('Número Sequencial', 'Identificador numérico sequencial', 'identificacao'),
            'model_prefix': ('Prefixo do Modelo', 'Prefixo identificador do modelo', 'especificacao_tecnica'),
            'model_series': ('Série do Modelo', 'Série ou família do produto', 'especificacao_tecnica'),
            'model_variant': ('Variante do Modelo', 'Variação específica do modelo', 'especificacao_tecnica'),
            'model_suffix': ('Sufixo do Modelo', 'Sufixo do número do modelo', 'especificacao_tecnica'),
            'plant_reference': ('Referência da Planta', 'Código de área/equipamento da planta', 'localizacao'),
            'revision': ('Revisão', 'Número de revisão do documento/equipamento', 'versionamento'),
            'unknown': ('Desconhecido', 'Token não classificado especificamente', 'generico')
        }
        
        nome, descricao, categoria = descricoes.get(
            codigo_tipo, 
            (codigo_tipo.replace('_', ' ').title(), f'Tipo {codigo_tipo}', 'generico')
        )
        
        try:
            self.cursor.execute("""
                INSERT INTO protec_ai.tipos_token (codigo_tipo, nome, descricao, categoria)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo_tipo) DO NOTHING
                RETURNING id
            """, (codigo_tipo, nome, descricao, categoria))
            
            result = self.cursor.fetchone()
            if result:
                tipo_id = result['id']
                self.stats['tipos_token_inseridos'] += 1
            else:
                # Já existe, buscar ID
                self.cursor.execute(
                    "SELECT id FROM protec_ai.tipos_token WHERE codigo_tipo = %s",
                    (codigo_tipo,)
                )
                tipo_id = self.cursor.fetchone()['id']
            
            self.tipos_token_cache[codigo_tipo] = tipo_id
            return tipo_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao inserir tipo_token {codigo_tipo}: {e}")
            raise

    def inserir_arquivo(self, nome_arquivo: str, identificador: str, fabricante_id: int) -> int:
        """
        Insere arquivo se não existir e retorna ID.
        
        Args:
            nome_arquivo: Nome do arquivo (ex: "tela1_params_clean.xlsx")
            identificador: Identificador único (ex: "tela1")
            fabricante_id: ID do fabricante
            
        Returns:
            ID do arquivo
        """
        cache_key = f"{identificador}_{fabricante_id}"
        if cache_key in self.arquivos_cache:
            return self.arquivos_cache[cache_key]
        
        try:
            self.cursor.execute("""
                INSERT INTO protec_ai.arquivos (nome_arquivo, identificador, fabricante_id, status_processamento)
                VALUES (%s, %s, %s, 'processado')
                ON CONFLICT (identificador, fabricante_id) DO NOTHING
                RETURNING id
            """, (nome_arquivo, identificador, fabricante_id))
            
            result = self.cursor.fetchone()
            if result:
                arquivo_id = result['id']
                self.stats['arquivos_processados'] += 1
            else:
                # Já existe, buscar ID
                self.cursor.execute(
                    "SELECT id FROM protec_ai.arquivos WHERE identificador = %s AND fabricante_id = %s",
                    (identificador, fabricante_id)
                )
                arquivo_id = self.cursor.fetchone()['id']
            
            self.arquivos_cache[cache_key] = arquivo_id
            return arquivo_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao inserir arquivo {nome_arquivo}: {e}")
            raise

    def inserir_campo_original(self, arquivo_id: int, codigo_campo: str, 
                              nome_coluna: str, descricao_campo: str) -> int:
        """
        Insere campo original se não existir e retorna ID.
        
        Args:
            arquivo_id: ID do arquivo
            codigo_campo: Código do campo (ex: "00.04")
            nome_coluna: Nome da coluna (ex: "Value")
            descricao_campo: Descrição (ex: "Description")
            
        Returns:
            ID do campo
        """
        cache_key = f"{arquivo_id}_{codigo_campo}_{nome_coluna}"
        if cache_key in self.campos_cache:
            return self.campos_cache[cache_key]
        
        try:
            self.cursor.execute("""
                INSERT INTO protec_ai.campos_originais (arquivo_id, codigo_campo, nome_coluna, descricao_campo)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (arquivo_id, codigo_campo, nome_coluna) DO NOTHING
                RETURNING id
            """, (arquivo_id, codigo_campo, nome_coluna, descricao_campo))
            
            result = self.cursor.fetchone()
            if result:
                campo_id = result['id']
                self.stats['campos_inseridos'] += 1
            else:
                # Já existe, buscar ID
                self.cursor.execute("""
                    SELECT id FROM protec_ai.campos_originais 
                    WHERE arquivo_id = %s AND codigo_campo = %s AND nome_coluna = %s
                """, (arquivo_id, codigo_campo, nome_coluna))
                campo_id = self.cursor.fetchone()['id']
            
            self.campos_cache[cache_key] = campo_id
            return campo_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao inserir campo {codigo_campo}: {e}")
            raise

    def processar_linha_csv(self, row: pd.Series) -> bool:
        """
        Processa uma linha do CSV e insere nas tabelas normalizadas.
        
        Args:
            row: Linha do DataFrame pandas
            
        Returns:
            True se processada com sucesso
        """
        try:
            # 1. Processar fabricante
            fabricante_id = self.inserir_fabricante(row['fabricante'])
            
            # 2. Processar arquivo
            arquivo_id = self.inserir_arquivo(
                row['arquivo_origem'],
                row['identificador_arquivo'], 
                fabricante_id
            )
            
            # 3. Processar campo original
            campo_id = self.inserir_campo_original(
                arquivo_id,
                row['codigo_campo'],
                row['nome_coluna'],
                row['descricao_campo']
            )
            
            # 4. Inserir valor original
            eh_multivalorado = not row['eh_atomico']  # Inverter boolean
            processado_em = pd.to_datetime(row['processado_em'])
            
            # Verificar se valor já existe para evitar duplicatas
            self.cursor.execute("""
                SELECT id FROM protec_ai.valores_originais 
                WHERE campo_id = %s AND valor_original = %s
            """, (campo_id, row['valor_original']))
            
            existing_valor = self.cursor.fetchone()
            if existing_valor:
                valor_id = existing_valor['id']
                logger.debug(f"Valor já existe, reutilizando ID {valor_id}")
            else:
                self.cursor.execute("""
                    INSERT INTO protec_ai.valores_originais 
                    (campo_id, valor_original, eh_multivalorado, padrao_detectado, 
                     num_partes, confianca_geral, processado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    campo_id,
                    row['valor_original'],
                    eh_multivalorado,
                    row['padrao_detectado'],
                    row['num_partes'],
                    row['confianca_geral'],
                    processado_em
                ))
                
                valor_id = self.cursor.fetchone()['id']
                self.stats['valores_inseridos'] += 1
            
            # 5. Processar tokens (parte_1 até parte_7)
            for i in range(1, 8):  # 1 a 7
                parte_col = f'parte_{i}'
                tipo_col = f'tipo_{i}'
                significado_col = f'significado_{i}'
                confianca_col = f'confianca_{i}'
                
                if pd.notna(row.get(parte_col)) and row.get(parte_col) != '':
                    # Verificar se token já existe
                    self.cursor.execute("""
                        SELECT id FROM protec_ai.tokens_valores 
                        WHERE valor_id = %s AND posicao_token = %s
                    """, (valor_id, i))
                    
                    if self.cursor.fetchone():
                        logger.debug(f"Token já existe para valor_id {valor_id}, posição {i}")
                        continue
                    
                    # Inserir/obter tipo de token
                    tipo_token_id = self.inserir_tipo_token(row[tipo_col])
                    
                    # Inserir token
                    self.cursor.execute("""
                        INSERT INTO protec_ai.tokens_valores 
                        (valor_id, posicao_token, valor_token, tipo_token_id, significado, confianca)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        valor_id,
                        i,
                        row[parte_col],
                        tipo_token_id,
                        row.get(significado_col, ''),
                        row.get(confianca_col)
                    ))
                    
                    self.stats['tokens_inseridos'] += 1
            
            return True
            
        except Exception as e:
            error_msg = f"Erro ao processar linha: {e}\nRow: {row.to_dict()}"
            logger.error(f"❌ {error_msg}")
            self.stats['erros'].append(error_msg)
            return False

    def processar_arquivo_csv(self, caminho_csv: str) -> bool:
        """
        Processa um arquivo CSV completo.
        
        Args:
            caminho_csv: Caminho para o arquivo CSV
            
        Returns:
            True se processado com sucesso
        """
        try:
            logger.info(f"📂 Processando arquivo: {caminho_csv}")
            
            # Carregar CSV
            df = pd.read_csv(caminho_csv)
            total_linhas = len(df)
            logger.info(f"📊 Total de registros: {total_linhas}")
            
            # Processar linha por linha
            sucessos = 0
            for idx, row in df.iterrows():
                if self.processar_linha_csv(row):
                    sucessos += 1
                
                # Log de progresso a cada 50 registros
                if (idx + 1) % 50 == 0:
                    logger.info(f"⏳ Processados {idx + 1}/{total_linhas} registros")
            
            logger.info(f"✅ Arquivo processado: {sucessos}/{total_linhas} registros inseridos")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar arquivo {caminho_csv}: {e}")
            return False

    def atualizar_estatisticas_arquivo(self, arquivo_id: int):
        """Atualiza estatísticas do arquivo após processamento."""
        try:
            # Contar registros
            self.cursor.execute("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN vo.eh_multivalorado = true THEN 1 END) as multivalorados
                FROM protec_ai.valores_originais vo
                    JOIN protec_ai.campos_originais co ON vo.campo_id = co.id
                WHERE co.arquivo_id = %s
            """, (arquivo_id,))
            
            stats = self.cursor.fetchone()
            
            # Atualizar arquivo
            self.cursor.execute("""
                UPDATE protec_ai.arquivos 
                SET total_registros = %s,
                    registros_multivalorados = %s,
                    data_processamento = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (stats['total'], stats['multivalorados'], arquivo_id))
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar estatísticas: {e}")

    def executar_importacao(self, arquivos_csv: List[str]) -> Dict:
        """
        Executa importação completa de múltiplos arquivos CSV.
        
        Args:
            arquivos_csv: Lista de caminhos para arquivos CSV
            
        Returns:
            Dicionário com estatísticas da importação
        """
        inicio = datetime.now()
        logger.info("🚀 Iniciando importação de dados normalizados")
        
        if not self.conectar():
            return {"erro": "Falha na conexão"}
        
        if not self.verificar_schema():
            self.desconectar()
            return {"erro": "Schema inválido"}
        
        # Carregar caches
        self.carregar_cache_fabricantes()
        self.carregar_cache_tipos_token()
        
        # Processar arquivos
        arquivos_processados = 0
        for arquivo_csv in arquivos_csv:
            if Path(arquivo_csv).exists():
                if self.processar_arquivo_csv(arquivo_csv):
                    arquivos_processados += 1
            else:
                logger.warning(f"⚠️ Arquivo não encontrado: {arquivo_csv}")
        
        # Atualizar estatísticas
        for arquivo_id in self.arquivos_cache.values():
            self.atualizar_estatisticas_arquivo(arquivo_id)
        
        fim = datetime.now()
        duracao = fim - inicio
        
        # Estatísticas finais
        self.stats.update({
            'arquivos_csv_processados': arquivos_processados,
            'duracao_segundos': duracao.total_seconds(),
            'inicio': inicio.isoformat(),
            'fim': fim.isoformat()
        })
        
        logger.info("🎯 Importação concluída!")
        logger.info(f"📊 Estatísticas: {json.dumps(self.stats, indent=2, ensure_ascii=False)}")
        
        self.desconectar()
        return self.stats


def main():
    """Função principal para execução do script."""
    # Configuração do banco de dados
    config_db = {
        'host': 'localhost',
        'database': 'protecai_db',
        'user': 'protecai',
        'password': 'protecai',  # Senha simplificada para testes
        'port': 5432
    }
    
    # Arquivos CSV para importar (caminhos relativos ao diretório base)
    arquivos_csv = [
        str(base_dir / 'outputs/norm_csv/tela1_params_normalized.csv'),
        str(base_dir / 'outputs/norm_csv/tela3_params_normalized.csv')
    ]
    
    # Executar importação
    importador = ImportadorDadosNormalizados(config_db)
    resultado = importador.executar_importacao(arquivos_csv)
    
    # Salvar relatório
    relatorio_path = base_dir / 'outputs/logs/relatorio_importacao.json'
    with open(relatorio_path, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Relatório salvo em: {relatorio_path}")


if __name__ == "__main__":
    main()
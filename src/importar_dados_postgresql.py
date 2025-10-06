#!/usr/bin/env python3
"""
Script de Importação de Dados Normalizados para PostgreSQL
===========================================================

Importa dados dos arquivos CSV normalizados para o banco PostgreSQL
seguindo a modelagem refinada baseada na estrutura real dos dados.

Autor: ProtecAI System
Data: 2025-10-05
Baseado na análise de: tela1_params_normalized.csv
"""

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import logging
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple
import re

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('importacao_dados.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ImportadorDadosNormalizados:
    """Classe para importação de dados normalizados para PostgreSQL."""
    
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
        
        # Cache para IDs de tabelas mestres
        self.fabricantes_cache = {}
        self.padroes_cache = {}
        self.tipos_token_cache = {}
        self.arquivos_cache = {}
    
    def conectar(self) -> bool:
        """Estabelece conexão com PostgreSQL."""
        try:
            self.conn = psycopg2.connect(**self.config_db)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            
            # Definir schema
            self.cursor.execute("SET search_path TO protec_ai;")
            self.conn.commit()
            
            logger.info("Conexão com PostgreSQL estabelecida com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao conectar com PostgreSQL: {e}")
            return False
    
    def desconectar(self):
        """Fecha conexão com PostgreSQL."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Conexão com PostgreSQL fechada")
    
    def carregar_caches(self):
        """Carrega caches das tabelas mestres para melhor performance."""
        logger.info("Carregando caches das tabelas mestres...")
        
        # Cache fabricantes
        self.cursor.execute("SELECT id, nome FROM fabricantes")
        self.fabricantes_cache = {row['nome']: row['id'] for row in self.cursor.fetchall()}
        
        # Cache padrões detectados
        self.cursor.execute("SELECT id, codigo FROM padroes_detectados")
        self.padroes_cache = {row['codigo']: row['id'] for row in self.cursor.fetchall()}
        
        # Cache tipos de token
        self.cursor.execute("SELECT id, codigo FROM tipos_token")
        self.tipos_token_cache = {row['codigo']: row['id'] for row in self.cursor.fetchall()}
        
        # Cache arquivos origem
        self.cursor.execute("SELECT id, nome_arquivo, identificador FROM arquivos_origem")
        self.arquivos_cache = {row['nome_arquivo']: row['id'] for row in self.cursor.fetchall()}
        
        logger.info(f"Caches carregados: {len(self.fabricantes_cache)} fabricantes, "
                   f"{len(self.padroes_cache)} padrões, {len(self.tipos_token_cache)} tipos de token")
    
    def obter_ou_criar_fabricante(self, nome_fabricante: str) -> int:
        """Obtém ID do fabricante ou cria se não existir."""
        if nome_fabricante in self.fabricantes_cache:
            return self.fabricantes_cache[nome_fabricante]
        
        # Criar novo fabricante
        self.cursor.execute(
            "INSERT INTO fabricantes (nome, nome_completo) VALUES (%s, %s) "
            "ON CONFLICT (nome) DO UPDATE SET nome = EXCLUDED.nome "
            "RETURNING id",
            (nome_fabricante, nome_fabricante.title())
        )
        fabricante_id = self.cursor.fetchone()['id']
        self.fabricantes_cache[nome_fabricante] = fabricante_id
        logger.info(f"Fabricante criado: {nome_fabricante} (ID: {fabricante_id})")
        return fabricante_id
    
    def obter_ou_criar_padrao(self, codigo_padrao: str) -> Optional[int]:
        """Obtém ID do padrão detectado ou cria se não existir."""
        if not codigo_padrao or codigo_padrao == '':
            return None
            
        if codigo_padrao in self.padroes_cache:
            return self.padroes_cache[codigo_padrao]
        
        # Criar novo padrão
        nome_padrao = codigo_padrao.replace('_', ' ').title()
        self.cursor.execute(
            "INSERT INTO padroes_detectados (codigo, nome, descricao) VALUES (%s, %s, %s) "
            "ON CONFLICT (codigo) DO UPDATE SET codigo = EXCLUDED.codigo "
            "RETURNING id",
            (codigo_padrao, nome_padrao, f"Padrão {nome_padrao} detectado automaticamente")
        )
        padrao_id = self.cursor.fetchone()['id']
        self.padroes_cache[codigo_padrao] = padrao_id
        logger.info(f"Padrão criado: {codigo_padrao} (ID: {padrao_id})")
        return padrao_id
    
    def obter_ou_criar_tipo_token(self, codigo_tipo: str) -> Optional[int]:
        """Obtém ID do tipo de token ou cria se não existir."""
        if not codigo_tipo or codigo_tipo == '':
            return None
            
        if codigo_tipo in self.tipos_token_cache:
            return self.tipos_token_cache[codigo_tipo]
        
        # Criar novo tipo de token
        nome_tipo = codigo_tipo.replace('_', ' ').title()
        categoria = 'generico'
        
        # Classificar categoria baseado no código
        if 'ansi' in codigo_tipo:
            categoria = 'codigo_ansi'
        elif 'model' in codigo_tipo:
            categoria = 'especificacao_tecnica'
        elif 'sequence' in codigo_tipo:
            categoria = 'identificacao'
        elif 'plant' in codigo_tipo:
            categoria = 'localizacao'
        
        self.cursor.execute(
            "INSERT INTO tipos_token (codigo, nome, descricao, categoria) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (codigo) DO UPDATE SET codigo = EXCLUDED.codigo "
            "RETURNING id",
            (codigo_tipo, nome_tipo, f"Tipo {nome_tipo} detectado automaticamente", categoria)
        )
        tipo_id = self.cursor.fetchone()['id']
        self.tipos_token_cache[codigo_tipo] = tipo_id
        logger.info(f"Tipo de token criado: {codigo_tipo} (ID: {tipo_id})")
        return tipo_id
    
    def obter_ou_criar_arquivo(self, nome_arquivo: str, identificador: str, fabricante_id: int) -> int:
        """Obtém ID do arquivo origem ou cria se não existir."""
        if nome_arquivo in self.arquivos_cache:
            return self.arquivos_cache[nome_arquivo]
        
        # Criar novo arquivo origem
        self.cursor.execute(
            "INSERT INTO arquivos_origem (nome_arquivo, identificador, fabricante_id, data_processamento, status_processamento) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (nome_arquivo, identificador) DO UPDATE SET "
            "data_processamento = EXCLUDED.data_processamento, status_processamento = EXCLUDED.status_processamento "
            "RETURNING id",
            (nome_arquivo, identificador, fabricante_id, datetime.now(), 'processado')
        )
        arquivo_id = self.cursor.fetchone()['id']
        self.arquivos_cache[nome_arquivo] = arquivo_id
        logger.info(f"Arquivo origem criado: {nome_arquivo} -> {identificador} (ID: {arquivo_id})")
        return arquivo_id
    
    def processar_linha_csv(self, row: pd.Series) -> Tuple[Dict, List[Dict]]:
        """
        Processa uma linha do CSV e retorna dados para inserção.
        
        Returns:
            Tuple com (dados_parametro, lista_tokens)
        """
        # Obter IDs das tabelas mestres
        fabricante_id = self.obter_ou_criar_fabricante(row['fabricante'])
        arquivo_id = self.obter_ou_criar_arquivo(
            row['arquivo_origem'], 
            row['identificador_arquivo'], 
            fabricante_id
        )
        padrao_id = self.obter_ou_criar_padrao(row['padrao_detectado'])
        
        # Converter timestamp
        processado_em = pd.to_datetime(row['processado_em'])
        
        # Dados do parâmetro principal
        parametro_data = {
            'arquivo_origem_id': arquivo_id,
            'fabricante_id': fabricante_id,
            'codigo_campo': row['codigo_campo'],
            'descricao_campo': row['descricao_campo'],
            'nome_coluna': row['nome_coluna'],
            'valor_original': row['valor_original'],
            'eh_atomico': row['eh_atomico'] == True or row['eh_atomico'] == 'True',
            'padrao_detectado_id': padrao_id,
            'processado_em': processado_em,
            'num_partes': int(row['num_partes']) if pd.notna(row['num_partes']) else 1,
            'confianca_geral': float(row['confianca_geral']) if pd.notna(row['confianca_geral']) else None
        }
        
        # Processar tokens (partes 1-7)
        tokens_data = []
        for i in range(1, 8):  # parte_1 até parte_7
            parte_col = f'parte_{i}'
            tipo_col = f'tipo_{i}'
            significado_col = f'significado_{i}'
            confianca_col = f'confianca_{i}'
            
            if parte_col in row and pd.notna(row[parte_col]) and row[parte_col] != '':
                tipo_token_id = self.obter_ou_criar_tipo_token(row[tipo_col]) if pd.notna(row[tipo_col]) else None
                
                token_data = {
                    'posicao': i,
                    'valor_token': str(row[parte_col]),
                    'tipo_token_id': tipo_token_id,
                    'significado': row[significado_col] if pd.notna(row[significado_col]) else None,
                    'confianca': float(row[confianca_col]) if pd.notna(row[confianca_col]) else None
                }
                tokens_data.append(token_data)
        
        return parametro_data, tokens_data
    
    def inserir_parametro_com_tokens(self, parametro_data: Dict, tokens_data: List[Dict]) -> int:
        """Insere parâmetro e seus tokens, retorna ID do parâmetro."""
        # Inserir parâmetro principal
        colunas = list(parametro_data.keys())
        valores = list(parametro_data.values())
        placeholders = ', '.join(['%s'] * len(colunas))
        
        query_parametro = f"""
            INSERT INTO parametros_normalizados ({', '.join(colunas)})
            VALUES ({placeholders})
            ON CONFLICT (arquivo_origem_id, codigo_campo, nome_coluna, valor_original) 
            DO UPDATE SET processado_em = EXCLUDED.processado_em
            RETURNING id
        """
        
        self.cursor.execute(query_parametro, valores)
        parametro_id = self.cursor.fetchone()['id']
        
        # Inserir tokens se existirem
        if tokens_data:
            # Limpar tokens existentes
            self.cursor.execute("DELETE FROM tokens_normalizados WHERE parametro_id = %s", (parametro_id,))
            
            # Inserir novos tokens
            for token_data in tokens_data:
                token_data['parametro_id'] = parametro_id
                
                colunas_token = list(token_data.keys())
                valores_token = list(token_data.values())
                placeholders_token = ', '.join(['%s'] * len(colunas_token))
                
                query_token = f"""
                    INSERT INTO tokens_normalizados ({', '.join(colunas_token)})
                    VALUES ({placeholders_token})
                """
                
                self.cursor.execute(query_token, valores_token)
        
        return parametro_id
    
    def importar_arquivo_csv(self, caminho_csv: str) -> Dict[str, int]:
        """
        Importa um arquivo CSV completo.
        
        Returns:
            Dict com estatísticas da importação
        """
        logger.info(f"Iniciando importação do arquivo: {caminho_csv}")
        
        # Carregar CSV
        try:
            df = pd.read_csv(caminho_csv)
            logger.info(f"CSV carregado: {len(df)} linhas, {len(df.columns)} colunas")
        except Exception as e:
            logger.error(f"Erro ao carregar CSV: {e}")
            return {'erro': 1}
        
        # Estatísticas
        stats = {
            'total_linhas': len(df),
            'parametros_inseridos': 0,
            'parametros_atualizados': 0,
            'tokens_inseridos': 0,
            'erros': 0
        }
        
        # Processar linha por linha
        for idx, row in df.iterrows():
            try:
                parametro_data, tokens_data = self.processar_linha_csv(row)
                parametro_id = self.inserir_parametro_com_tokens(parametro_data, tokens_data)
                
                stats['parametros_inseridos'] += 1
                stats['tokens_inseridos'] += len(tokens_data)
                
                # Commit a cada 100 registros
                if (idx + 1) % 100 == 0:
                    self.conn.commit()
                    logger.info(f"Processadas {idx + 1}/{len(df)} linhas...")
                    
            except Exception as e:
                logger.error(f"Erro na linha {idx + 1}: {e}")
                stats['erros'] += 1
                # Continue processando outras linhas
                continue
        
        # Commit final
        self.conn.commit()
        
        # Atualizar estatísticas do arquivo
        if self.arquivos_cache:
            arquivo_nome = df.iloc[0]['arquivo_origem']
            if arquivo_nome in self.arquivos_cache:
                arquivo_id = self.arquivos_cache[arquivo_nome]
                multivalorados = len(df[df['eh_atomico'] == False])
                
                self.cursor.execute(
                    "UPDATE arquivos_origem SET total_registros = %s, registros_multivalorados = %s "
                    "WHERE id = %s",
                    (stats['parametros_inseridos'], multivalorados, arquivo_id)
                )
                self.conn.commit()
        
        logger.info(f"Importação concluída: {stats}")
        return stats
    
    def importar_multiplos_arquivos(self, diretorio_csv: str) -> Dict[str, Dict]:
        """Importa todos os arquivos CSV de um diretório."""
        logger.info(f"Importando arquivos CSV do diretório: {diretorio_csv}")
        
        path = Path(diretorio_csv)
        arquivos_csv = list(path.glob("*_normalized.csv"))
        
        if not arquivos_csv:
            logger.warning(f"Nenhum arquivo *_normalized.csv encontrado em {diretorio_csv}")
            return {}
        
        resultados = {}
        
        for arquivo_csv in arquivos_csv:
            logger.info(f"Processando arquivo: {arquivo_csv.name}")
            try:
                stats = self.importar_arquivo_csv(str(arquivo_csv))
                resultados[arquivo_csv.name] = stats
            except Exception as e:
                logger.error(f"Erro ao processar {arquivo_csv.name}: {e}")
                resultados[arquivo_csv.name] = {'erro': str(e)}
        
        # Resumo final
        total_parametros = sum(r.get('parametros_inseridos', 0) for r in resultados.values())
        total_tokens = sum(r.get('tokens_inseridos', 0) for r in resultados.values())
        total_erros = sum(r.get('erros', 0) for r in resultados.values())
        
        logger.info(f"RESUMO FINAL: {len(arquivos_csv)} arquivos processados")
        logger.info(f"Total de parâmetros: {total_parametros}")
        logger.info(f"Total de tokens: {total_tokens}")
        logger.info(f"Total de erros: {total_erros}")
        
        return resultados

def main():
    """Função principal para execução do script."""
    # Configuração do banco PostgreSQL
    config_db = {
        'host': 'localhost',
        'database': 'protecai',
        'user': 'postgres',
        'password': 'sua_senha',  # ALTERAR CONFORME NECESSÁRIO
        'port': '5432'
    }
    
    # Diretório com arquivos CSV normalizados
    diretorio_csv = "outputs/norm_csv"
    
    # Criar importador
    importador = ImportadorDadosNormalizados(config_db)
    
    try:
        # Conectar
        if not importador.conectar():
            logger.error("Falha na conexão com o banco")
            return 1
        
        # Carregar caches
        importador.carregar_caches()
        
        # Importar arquivos
        resultados = importador.importar_multiplos_arquivos(diretorio_csv)
        
        # Exibir resultados
        print("\n" + "="*60)
        print("RELATÓRIO DE IMPORTAÇÃO")
        print("="*60)
        
        for arquivo, stats in resultados.items():
            print(f"\n{arquivo}:")
            if 'erro' in stats:
                print(f"  ❌ ERRO: {stats['erro']}")
            else:
                print(f"  ✅ Parâmetros: {stats.get('parametros_inseridos', 0)}")
                print(f"  🔤 Tokens: {stats.get('tokens_inseridos', 0)}")
                print(f"  ⚠️  Erros: {stats.get('erros', 0)}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        return 1
        
    finally:
        importador.desconectar()

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
🎯 REPLICAÇÃO DA ARQUITETURA CORRETA PARA TODOS OS SCHEMAS
===========================================================
Replica a estrutura corrigida (equipment_protection_functions + relay_settings) 
nos schemas relay_configs e ml_gateway para garantir robustez para toda equipe.

OBJETIVO: 
- Schema protec_ai: ✅ JÁ CORRIGIDO (158 funções, 23 ativas)
- Schema relay_configs: Team ETAP 
- Schema ml_gateway: Team ML

ESTRUTURA PADRÃO:
- equipment_protection_functions (com is_enabled)  
- relay_settings (com is_enabled)
- relay_equipment, relay_models, protection_functions (já existem)
"""

import logging
import psycopg2
from datetime import datetime
import os
import sys

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('replicate_architecture.log'),
        logging.StreamHandler()
    ]
)

class ArchitectureReplicator:
    def __init__(self):
        self.conn = None
        self.schemas_target = ['relay_configs', 'ml_gateway']
        self.reference_schema = 'protec_ai'
        
    def conectar_db(self):
        """Conecta ao PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host="localhost",
                database="protecai_db",
                user="protecai",
                password="protecai",
                port="5432"
            )
            self.conn.autocommit = True
            logging.info("✅ Conectado ao PostgreSQL")
            return True
        except Exception as e:
            logging.error(f"❌ Erro conectando PostgreSQL: {e}")
            return False
    
    def verificar_schemas_existentes(self):
        """Verifica quais schemas existem"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('protec_ai', 'relay_configs', 'ml_gateway')
            ORDER BY schema_name
        """)
        schemas_existentes = [row[0] for row in cursor.fetchall()]
        logging.info(f"📂 Schemas existentes: {schemas_existentes}")
        return schemas_existentes
    
    def criar_schema_se_necessario(self, schema_name):
        """Cria schema se não existir"""
        cursor = self.conn.cursor()
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        logging.info(f"✅ Schema {schema_name} garantido")
    
    def obter_estrutura_tabela(self, schema, tabela):
        """Obtém a estrutura DDL de uma tabela"""
        cursor = self.conn.cursor()
        
        # Verifica se tabela existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
        """, (schema, tabela))
        
        if cursor.fetchone()[0] == 0:
            return None
            
        # Obtém colunas
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, 
                   is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, tabela))
        
        colunas = cursor.fetchall()
        
        # Obtém constraints (primary key, foreign key)
        cursor.execute("""
            SELECT tc.constraint_type, tc.constraint_name, kcu.column_name,
                   ccu.table_schema AS foreign_table_schema,
                   ccu.table_name AS foreign_table_name,
                   ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            LEFT JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.table_schema = %s AND tc.table_name = %s
        """, (schema, tabela))
        
        constraints = cursor.fetchall()
        
        return {'colunas': colunas, 'constraints': constraints}
    
    def gerar_ddl_tabela(self, tabela_info, schema_destino, nome_tabela):
        """Gera DDL para criar tabela"""
        if not tabela_info:
            return None
            
        ddl = f"CREATE TABLE IF NOT EXISTS {schema_destino}.{nome_tabela} (\n"
        
        # Adiciona colunas
        colunas_ddl = []
        for col in tabela_info['colunas']:
            col_name, data_type, max_length, is_nullable, default = col
            
            # Monta tipo
            if data_type == 'character varying' and max_length:
                tipo = f"VARCHAR({max_length})"
            elif data_type == 'integer':
                tipo = "INTEGER"
            elif data_type == 'bigint':
                tipo = "BIGINT"
            elif data_type == 'boolean':
                tipo = "BOOLEAN"
            elif data_type == 'timestamp without time zone':
                tipo = "TIMESTAMP"
            elif data_type == 'numeric':
                tipo = "NUMERIC"
            elif data_type == 'text':
                tipo = "TEXT"
            else:
                tipo = data_type.upper()
            
            # Nullable
            nullable = "" if is_nullable == 'YES' else " NOT NULL"
            
            # Default
            default_val = f" DEFAULT {default}" if default else ""
            
            colunas_ddl.append(f"    {col_name} {tipo}{nullable}{default_val}")
        
        ddl += ",\n".join(colunas_ddl)
        
        # Adiciona primary key
        for constraint in tabela_info['constraints']:
            if constraint[0] == 'PRIMARY KEY':
                ddl += f",\n    PRIMARY KEY ({constraint[2]})"
                break
        
        ddl += "\n);"
        
        # Adiciona foreign keys
        for constraint in tabela_info['constraints']:
            if constraint[0] == 'FOREIGN KEY':
                constraint_type, constraint_name, column_name, foreign_schema, foreign_table, foreign_column = constraint
                ddl += f"\n\nALTER TABLE {schema_destino}.{nome_tabela} "
                ddl += f"ADD CONSTRAINT {constraint_name}_{schema_destino} "
                ddl += f"FOREIGN KEY ({column_name}) "
                ddl += f"REFERENCES {schema_destino}.{foreign_table}({foreign_column});"
        
        return ddl
    
    def replicar_tabela(self, nome_tabela, schema_destino):
        """Replica uma tabela do schema de referência para o destino"""
        logging.info(f"🔄 Replicando {nome_tabela} para {schema_destino}")
        
        # Obtém estrutura da tabela de referência
        estrutura = self.obter_estrutura_tabela(self.reference_schema, nome_tabela)
        if not estrutura:
            logging.warning(f"⚠️ Tabela {nome_tabela} não encontrada em {self.reference_schema}")
            return False
        
        # Gera DDL
        ddl = self.gerar_ddl_tabela(estrutura, schema_destino, nome_tabela)
        if not ddl:
            return False
        
        # Executa DDL
        cursor = self.conn.cursor()
        try:
            cursor.execute(ddl)
            logging.info(f"✅ Tabela {schema_destino}.{nome_tabela} criada")
            return True
        except Exception as e:
            logging.error(f"❌ Erro criando {schema_destino}.{nome_tabela}: {e}")
            return False
    
    def copiar_dados_basicos(self, schema_destino):
        """Copia dados básicos (fabricantes, relay_models, protection_functions)"""
        tabelas_dados = [
            'fabricantes',
            'relay_models', 
            'protection_functions'
        ]
        
        cursor = self.conn.cursor()
        
        for tabela in tabelas_dados:
            try:
                # Verifica se origem tem dados
                cursor.execute(f"SELECT COUNT(*) FROM {self.reference_schema}.{tabela}")
                count_origem = cursor.fetchone()[0]
                
                if count_origem == 0:
                    continue
                
                # Verifica se destino já tem dados
                cursor.execute(f"SELECT COUNT(*) FROM {schema_destino}.{tabela}")
                count_destino = cursor.fetchone()[0]
                
                if count_destino > 0:
                    logging.info(f"📊 {schema_destino}.{tabela} já tem dados ({count_destino})")
                    continue
                
                # Copia dados
                cursor.execute(f"""
                    INSERT INTO {schema_destino}.{tabela} 
                    SELECT * FROM {self.reference_schema}.{tabela}
                    ON CONFLICT DO NOTHING
                """)
                
                logging.info(f"✅ Dados copiados para {schema_destino}.{tabela}")
                
            except Exception as e:
                logging.error(f"❌ Erro copiando dados {tabela}: {e}")
    
    def obter_estatisticas_schema(self, schema):
        """Obtém estatísticas de um schema"""
        cursor = self.conn.cursor()
        stats = {}
        
        tabelas = [
            'relay_equipment',
            'equipment_protection_functions', 
            'relay_settings',
            'fabricantes',
            'relay_models',
            'protection_functions'
        ]
        
        for tabela in tabelas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {schema}.{tabela}")
                stats[tabela] = cursor.fetchone()[0]
            except:
                stats[tabela] = 0
        
        return stats
    
    def executar_replicacao(self):
        """Executa replicação completa"""
        logging.info("🎯 INICIANDO REPLICAÇÃO DA ARQUITETURA PARA TODOS SCHEMAS")
        logging.info("=" * 65)
        
        if not self.conectar_db():
            return False
        
        # Verifica schemas existentes
        schemas_existentes = self.verificar_schemas_existentes()
        
        # Tabelas essenciais para replicar
        tabelas_essenciais = [
            'fabricantes',
            'relay_models',
            'protection_functions',
            'relay_equipment',
            'equipment_protection_functions',
            'relay_settings'
        ]
        
        # Processa cada schema de destino
        for schema_destino in self.schemas_target:
            logging.info(f"\n🎯 PROCESSANDO SCHEMA: {schema_destino}")
            logging.info("-" * 50)
            
            # Cria schema se necessário
            self.criar_schema_se_necessario(schema_destino)
            
            # Replica cada tabela
            for tabela in tabelas_essenciais:
                self.replicar_tabela(tabela, schema_destino)
            
            # Copia dados básicos
            self.copiar_dados_basicos(schema_destino)
            
            # Mostra estatísticas
            stats = self.obter_estatisticas_schema(schema_destino)
            logging.info(f"📊 ESTATÍSTICAS {schema_destino}:")
            for tabela, count in stats.items():
                logging.info(f"   📋 {tabela}: {count} registros")
        
        # Relatório final
        logging.info("\n" + "=" * 65)
        logging.info("📊 RELATÓRIO FINAL - ARQUITETURA REPLICADA")
        logging.info("=" * 65)
        
        for schema in [self.reference_schema] + self.schemas_target:
            if schema in schemas_existentes or schema in self.schemas_target:
                stats = self.obter_estatisticas_schema(schema)
                logging.info(f"\n🏗️ SCHEMA: {schema}")
                logging.info(f"   📋 relay_equipment: {stats.get('relay_equipment', 0)}")
                logging.info(f"   🔧 equipment_protection_functions: {stats.get('equipment_protection_functions', 0)}")
                logging.info(f"   ⚙️ relay_settings: {stats.get('relay_settings', 0)}")
                logging.info(f"   🏭 fabricantes: {stats.get('fabricantes', 0)}")
                logging.info(f"   📱 relay_models: {stats.get('relay_models', 0)}")
                logging.info(f"   🛡️ protection_functions: {stats.get('protection_functions', 0)}")
        
        logging.info("\n🎉 REPLICAÇÃO COMPLETA - ARQUITETURA ROBUSTA EM TODOS SCHEMAS!")
        return True

def main():
    replicator = ArchitectureReplicator()
    success = replicator.executar_replicacao()
    
    if success:
        print("\n✅ SUCESSO: Arquitetura replicada com sucesso!")
        return 0
    else:
        print("\n❌ ERRO: Falha na replicação da arquitetura!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
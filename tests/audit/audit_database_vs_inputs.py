#!/usr/bin/env python3
"""
AUDITORIA COMPLETA: BANCO DE DADOS vs ARQUIVOS INPUTS
Sistema ProtecAI - PETROBRAS
Data: 28 de outubro de 2025

OBJETIVO: Verificar se os dados do PostgreSQL refletem exatamente
os documentos de entrada em inputs/
"""

import os
import json
import glob
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Configuração base
BASE_DIR = Path(__file__).parent.parent
INPUTS_DIR = BASE_DIR / "inputs"

class DatabaseAuditor:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'protecai_db',
            'user': 'protecai',
            'password': 'protecai'
        }
        
    def audit_input_files(self):
        """Auditar arquivos reais em inputs/"""
        print("🔍 AUDITANDO ARQUIVOS DE ENTRADA...")
        
        audit_results = {
            'pdf_files': [],
            'txt_files': [],
            'csv_files': [],
            'xlsx_files': [],
            'total_relays': 0,
            'by_manufacturer': {},
            'by_model': {}
        }
        
        # PDFs - cada PDF = 1 relé
        pdf_files = glob.glob(str(INPUTS_DIR / "pdf" / "*.pdf"))
        for pdf_file in pdf_files:
            filename = os.path.basename(pdf_file)
            
            # Extrair modelo do nome do arquivo
            if 'P122' in filename:
                model = 'MICOM P122'
            elif 'P143' in filename:
                model = 'MICOM P143'
            elif 'P220' in filename:
                model = 'MICOM P220'
            elif 'P241' in filename:
                model = 'MICOM P241'
            elif 'P922' in filename:
                model = 'MICOM P922'
            else:
                model = 'Unknown'
            
            audit_results['pdf_files'].append({
                'file': filename,
                'model': model,
                'manufacturer': 'Schneider Electric' if 'MICOM' in model else 'Unknown'
            })
            
            # Contagem por modelo
            if model not in audit_results['by_model']:
                audit_results['by_model'][model] = 0
            audit_results['by_model'][model] += 1
        
        # TXT/S40 files - cada arquivo = 1 relé
        txt_files = glob.glob(str(INPUTS_DIR / "txt" / "*.S40"))
        for txt_file in txt_files:
            filename = os.path.basename(txt_file)
            audit_results['txt_files'].append({
                'file': filename,
                'model': 'MICOM S40 Format',
                'manufacturer': 'Schneider Electric'
            })
            
            if 'MICOM S40 Format' not in audit_results['by_model']:
                audit_results['by_model']['MICOM S40 Format'] = 0
            audit_results['by_model']['MICOM S40 Format'] += 1
        
        # CSV files (dados processados)
        csv_files = glob.glob(str(INPUTS_DIR / "csv" / "*.csv"))
        audit_results['csv_files'] = [os.path.basename(f) for f in csv_files]
        
        # XLSX files
        xlsx_files = glob.glob(str(INPUTS_DIR / "xlsx" / "*.xlsx"))
        audit_results['xlsx_files'] = [os.path.basename(f) for f in xlsx_files]
        
        # Total de relés = PDFs + TXTs
        audit_results['total_relays'] = len(pdf_files) + len(txt_files)
        
        # Contagem por fabricante
        for item in audit_results['pdf_files'] + audit_results['txt_files']:
            manufacturer = item['manufacturer']
            if manufacturer not in audit_results['by_manufacturer']:
                audit_results['by_manufacturer'][manufacturer] = 0
            audit_results['by_manufacturer'][manufacturer] += 1
        
        return audit_results
    
    def audit_database(self):
        """Auditar dados do PostgreSQL"""
        print("🗄️ AUDITANDO BANCO DE DADOS PostgreSQL...")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Verificar schemas
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            """)
            schemas = [row['schema_name'] for row in cursor.fetchall()]
            
            db_audit = {
                'schemas': {},
                'total_records': 0,
                'relay_specific_tables': {}
            }
            
            for schema in schemas:
                # Obter tabelas do schema
                cursor.execute(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = '{schema}'
                """)
                tables = [row['table_name'] for row in cursor.fetchall()]
                
                schema_data = {'tables': {}, 'total_records': 0}
                
                for table in tables:
                    try:
                        # Pular tabelas problemáticas do PostgreSQL
                        if table in ['pg_stat_statements', 'pg_stat_statements_info']:
                            print(f"⚠️ Pulando tabela de extensão: {schema}.{table}")
                            schema_data['tables'][table] = "SKIPPED - Extension table"
                            continue
                            
                        cursor.execute(f'SELECT COUNT(*) as count FROM "{schema}"."{table}"')
                        count = cursor.fetchone()['count']
                        schema_data['tables'][table] = count
                        schema_data['total_records'] += count
                        
                        # Tabelas específicas de relés
                        if any(keyword in table.lower() for keyword in ['relay', 'equipment', 'etap', 'micom']):
                            db_audit['relay_specific_tables'][f"{schema}.{table}"] = count
                            
                    except Exception as e:
                        print(f"⚠️ Erro ao contar {schema}.{table}: {e}")
                        schema_data['tables'][table] = f"ERRO: {e}"
                        # COMMIT para resetar transação abortada
                        conn.commit()
                
                db_audit['schemas'][schema] = schema_data
                db_audit['total_records'] += schema_data['total_records']
            
            cursor.close()
            conn.close()
            
            return db_audit
            
        except Exception as e:
            print(f"❌ Erro ao conectar PostgreSQL: {e}")
            return {'error': str(e), 'total_records': 0, 'schemas': {}}
    
    def generate_audit_report(self, file_audit, db_audit):
        """Gerar relatório completo da auditoria"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'input_files_total_relays': file_audit['total_relays'],
                'database_total_records': db_audit['total_records'],
                'discrepancy': abs(db_audit['total_records'] - file_audit['total_relays']),
                'consistency_ratio': 0
            },
            'file_audit': file_audit,
            'database_audit': db_audit,
            'recommendations': []
        }
        
        # Calcular ratio de consistência
        if file_audit['total_relays'] > 0:
            min_val = min(db_audit['total_records'], file_audit['total_relays'])
            max_val = max(db_audit['total_records'], file_audit['total_relays'])
            report['summary']['consistency_ratio'] = (min_val / max_val) * 100 if max_val > 0 else 0
        
        # Recomendações baseadas na auditoria
        if report['summary']['discrepancy'] > file_audit['total_relays'] * 0.1:  # > 10% discrepância
            report['recommendations'].append({
                'priority': 'HIGH',
                'issue': 'Discrepância crítica entre arquivos e banco',
                'description': f"Diferença de {report['summary']['discrepancy']} registros é muito alta",
                'action': 'Revisar processo de importação e limpeza do banco'
            })
        
        if db_audit['total_records'] > file_audit['total_relays'] * 100:  # 100x mais registros
            report['recommendations'].append({
                'priority': 'CRITICAL',
                'issue': 'Banco de dados inflado artificialmente',
                'description': f"Banco tem {db_audit['total_records']} registros vs {file_audit['total_relays']} relés reais",
                'action': 'URGENTE: Limpar dados duplicados/irrelevantes do banco'
            })
        
        if file_audit['total_relays'] == 0:
            report['recommendations'].append({
                'priority': 'CRITICAL',
                'issue': 'Nenhum arquivo de entrada encontrado',
                'description': 'Pasta inputs/ não contém arquivos de relés',
                'action': 'Verificar localização dos arquivos de configuração'
            })
        
        return report
    
    def save_report(self, report):
        """Salvar relatório em arquivo"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = BASE_DIR / f"audit_database_vs_inputs_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_file
    
    def print_summary(self, report):
        """Imprimir resumo da auditoria"""
        print("\n" + "="*70)
        print("🔍 RELATÓRIO DE AUDITORIA COMPLETA")
        print("="*70)
        
        print(f"\n📁 ARQUIVOS DE ENTRADA:")
        print(f"   • PDFs (relés individuais): {len(report['file_audit']['pdf_files'])}")
        print(f"   • TXTs (.S40 format): {len(report['file_audit']['txt_files'])}")
        print(f"   • Total de relés REAIS: {report['summary']['input_files_total_relays']}")
        
        print(f"\n📊 DISTRIBUIÇÃO POR MODELO:")
        for model, count in report['file_audit']['by_model'].items():
            print(f"   • {model}: {count} relés")
        
        print(f"\n🗄️ BANCO DE DADOS PostgreSQL:")
        print(f"   • Total de registros: {report['summary']['database_total_records']:,}")
        print(f"   • Schemas encontrados: {len(report['database_audit']['schemas'])}")
        
        if 'relay_specific_tables' in report['database_audit']:
            print(f"\n🔧 TABELAS ESPECÍFICAS DE RELÉS:")
            for table, count in report['database_audit']['relay_specific_tables'].items():
                print(f"   • {table}: {count:,} registros")
        
        print(f"\n⚖️ ANÁLISE DE CONSISTÊNCIA:")
        print(f"   • Discrepância: {report['summary']['discrepancy']:,} registros")
        print(f"   • Ratio de consistência: {report['summary']['consistency_ratio']:.1f}%")
        
        if report['recommendations']:
            print(f"\n🚨 RECOMENDAÇÕES:")
            for rec in report['recommendations']:
                priority_icon = "🔴" if rec['priority'] == 'CRITICAL' else "🟡" if rec['priority'] == 'HIGH' else "🟢"
                print(f"   {priority_icon} {rec['priority']}: {rec['issue']}")
                print(f"      {rec['description']}")
                print(f"      AÇÃO: {rec['action']}")
        else:
            print(f"\n✅ SISTEMA CONSISTENTE - Nenhuma recomendação crítica")
        
        print("\n" + "="*70)

def main():
    """Executar auditoria completa"""
    print("🚀 INICIANDO AUDITORIA COMPLETA - BANCO vs INPUTS")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    auditor = DatabaseAuditor()
    
    # 1. Auditar arquivos de entrada
    file_audit = auditor.audit_input_files()
    
    # 2. Auditar banco de dados
    db_audit = auditor.audit_database()
    
    # 3. Gerar relatório completo
    report = auditor.generate_audit_report(file_audit, db_audit)
    
    # 4. Salvar relatório
    report_file = auditor.save_report(report)
    print(f"\n💾 Relatório salvo em: {report_file}")
    
    # 5. Imprimir resumo
    auditor.print_summary(report)
    
    return report

if __name__ == "__main__":
    main()
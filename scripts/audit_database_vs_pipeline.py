#!/usr/bin/env python3
"""
🔬 AUDITORIA COMPLETA: BANCO DE DADOS vs PIPELINE
================================================

Compara dados do PostgreSQL com CSVs normalizados do pipeline.
Identifica divergências e gera relatório detalhado.

Database: protecai_db
User: protecai
Schema: protec_ai

Autor: ProtecAI Team
Data: 06/11/2025
"""

import os
import sys
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

# Configurações do banco
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}

# Diretórios
BASE_DIR = Path(__file__).parent.parent
NORM_CSV_DIR = BASE_DIR / 'outputs' / 'norm_csv'
REPORTS_DIR = BASE_DIR / 'outputs' / 'reports'
REPORTS_DIR.mkdir(exist_ok=True)


class DatabaseAuditor:
    """Auditor de banco de dados vs pipeline"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.audit_results = {
            'timestamp': datetime.now().isoformat(),
            'database': {},
            'pipeline': {},
            'divergences': {},
            'recommendations': []
        }
    
    def connect_db(self):
        """Conecta ao PostgreSQL"""
        try:
            print("🔌 Conectando ao PostgreSQL...")
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            print("✅ Conexão estabelecida com sucesso!")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar ao banco: {e}")
            return False
    
    def audit_database(self):
        """Audita o estado atual do banco de dados"""
        print("\n" + "="*80)
        print("📊 AUDITANDO BANCO DE DADOS")
        print("="*80)
        
        try:
            # Total de parâmetros
            self.cursor.execute("""
                SELECT COUNT(*) FROM protec_ai.relay_settings
            """)
            result = self.cursor.fetchone()
            total_params = result['count'] if result else 0
            print(f"📦 Total de parâmetros: {total_params}")
            
            # Total de equipamentos
            self.cursor.execute("SELECT COUNT(*) FROM protec_ai.relay_equipment")
            result = self.cursor.fetchone()
            total_equipment = result['count'] if result else 0
            print(f"⚙️  Total de equipamentos: {total_equipment}")
            
            # Distribuição por equipamento
            self.cursor.execute("""
                SELECT re.equipment_tag,
                    rm.model_code,
                    rm.model_name,
                    COUNT(rs.id) as params
                FROM protec_ai.relay_equipment re
                LEFT JOIN protec_ai.relay_settings rs ON rs.equipment_id = re.id
                LEFT JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
                GROUP BY re.equipment_tag, rm.model_code, rm.model_name
                ORDER BY params DESC
            """)
            distribution = self.cursor.fetchall()
            
            # Última importação
            self.cursor.execute("""
                SELECT MAX(created_at) as last_import 
                FROM protec_ai.relay_settings;
            """)
            last_import = self.cursor.fetchone()['last_import']
            
            # Parâmetros sem equipamento (órfãos)
            self.cursor.execute("""
                SELECT COUNT(*) as orphans 
                FROM protec_ai.relay_settings 
                WHERE equipment_id IS NULL;
            """)
            orphans = self.cursor.fetchone()['orphans']
            
            # Campos vazios críticos
            self.cursor.execute("""
                SELECT COUNT(*) as empty_codes 
                FROM protec_ai.relay_settings 
                WHERE parameter_code IS NULL OR parameter_code = '';
            """)
            empty_codes = self.cursor.fetchone()['empty_codes']
            
            self.cursor.execute("""
                SELECT COUNT(*) as empty_names 
                FROM protec_ai.relay_settings 
                WHERE parameter_name IS NULL OR parameter_name = '';
            """)
            empty_names = self.cursor.fetchone()['empty_names']
            
            # Armazenar resultados
            self.audit_results['database'] = {
                'total_params': total_params,
                'total_equipment': total_equipment,
                'last_import': str(last_import) if last_import else None,
                'orphan_params': orphans,
                'empty_codes': empty_codes,
                'empty_names': empty_names,
                'distribution': [dict(row) for row in distribution]
            }
            
            print(f"📅 Última importação: {last_import}")
            print(f"👻 Parâmetros órfãos: {orphans}")
            print(f"⚠️  Códigos vazios: {empty_codes}")
            print(f"⚠️  Nomes vazios: {empty_names}")
            
            # Mostrar top 10 equipamentos com mais parâmetros
            if distribution:
                print("\n📊 Top 10 equipamentos com mais parâmetros:")
                for i, row in enumerate(distribution[:10], 1):
                    model_code = row.get('model_code', 'N/A') or 'N/A'
                    params = row.get('param_count', 0)
                    equipment = row.get('equipment_tag', 'UNKNOWN')
                    print(f"  {i:2d}. {equipment:20s} ({model_code:10s}) → {params:5d} params")
            else:
                print("\n⚠️  NENHUM equipamento tem parâmetros no banco!")
            
            # Mostrar equipamentos sem parâmetros
            if distribution:
                no_params = [row for row in distribution if row.get('param_count', 0) == 0]
                if no_params:
                    print(f"\n⚠️  {len(no_params)} equipamentos SEM parâmetros:")
                    for row in no_params:
                        model_code = row.get('model_code', 'N/A') or 'N/A'
                        equipment = row.get('equipment_tag', 'UNKNOWN')
                        print(f"  - {equipment} ({model_code})")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao auditar banco: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def audit_pipeline_csvs(self):
        """Audita CSVs normalizados do pipeline"""
        print("\n" + "="*80)
        print("📂 AUDITANDO CSVS NORMALIZADOS DO PIPELINE")
        print("="*80)
        
        if not NORM_CSV_DIR.exists():
            print(f"❌ Diretório não encontrado: {NORM_CSV_DIR}")
            return False
        
        csv_files = list(NORM_CSV_DIR.glob("*.csv"))
        print(f"📁 Total de CSVs encontrados: {len(csv_files)}")
        
        total_params = 0
        csv_details = []
        equipment_distribution = {}
        
        for csv_file in sorted(csv_files):
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    param_count = len(rows)
                    total_params += param_count
                    
                    # Extrair equipment_tag do nome do arquivo
                    # Formato esperado: REL-P220-XXX_normalized.csv
                    equipment_tag = csv_file.stem.replace('_normalized', '')
                    
                    # Detectar modelo do nome do arquivo
                    model = 'UNKNOWN'
                    if 'P122' in equipment_tag:
                        model = 'P122'
                    elif 'P143' in equipment_tag:
                        model = 'P143'
                    elif 'P220' in equipment_tag:
                        model = 'P220'
                    elif 'P241' in equipment_tag:
                        model = 'P241'
                    elif 'P922S' in equipment_tag:
                        model = 'P922S'
                    elif 'P922' in equipment_tag:
                        model = 'P922'
                    elif 'SEPAM' in equipment_tag or 'S40' in equipment_tag:
                        model = 'SEPAM'
                    
                    csv_details.append({
                        'filename': csv_file.name,
                        'equipment_tag': equipment_tag,
                        'model': model,
                        'param_count': param_count
                    })
                    
                    # Distribuição por modelo
                    equipment_distribution[model] = equipment_distribution.get(model, 0) + 1
                    
            except Exception as e:
                print(f"⚠️  Erro ao ler {csv_file.name}: {e}")
        
        self.audit_results['pipeline'] = {
            'total_csvs': len(csv_files),
            'total_params': total_params,
            'avg_params_per_csv': round(total_params / len(csv_files), 2) if csv_files else 0,
            'distribution': equipment_distribution,
            'csv_details': csv_details
        }
        
        print(f"📦 Total de parâmetros nos CSVs: {total_params:,}")
        print(f"📊 Média de parâmetros por CSV: {total_params / len(csv_files):.2f}")
        
        print("\n📊 Distribuição por modelo:")
        for model, count in sorted(equipment_distribution.items()):
            print(f"  {model:10s} → {count:3d} equipamentos")
        
        print(f"\n📊 Top 10 CSVs com mais parâmetros:")
        sorted_csvs = sorted(csv_details, key=lambda x: x['param_count'], reverse=True)
        for i, csv_row in enumerate(sorted_csvs[:10], 1):
            print(f"  {i:2d}. {csv_row['equipment_tag']:30s} ({csv_row['model']:10s}) → {csv_row['param_count']:5d} params")
        
        # CSVs com poucos parâmetros (possível problema)
        low_param_csvs = [csv_row for csv_row in csv_details if csv_row['param_count'] < 10]
        if low_param_csvs:
            print(f"\n⚠️  {len(low_param_csvs)} CSVs com menos de 10 parâmetros:")
            for csv_row in low_param_csvs:
                print(f"  - {csv_row['equipment_tag']} ({csv_row['model']}) → {csv_row['param_count']} params")
        
        return True
    
    def compare_database_vs_pipeline(self):
        """Compara banco vs pipeline e identifica divergências"""
        print("\n" + "="*80)
        print("🔍 COMPARANDO BANCO vs PIPELINE")
        print("="*80)
        
        db_data = self.audit_results['database']
        pipeline_data = self.audit_results['pipeline']
        
        # Comparar totais
        db_total = db_data['total_params']
        pipeline_total = pipeline_data['total_params']
        diff = db_total - pipeline_total
        diff_pct = (diff / pipeline_total * 100) if pipeline_total > 0 else 0
        
        print(f"\n📊 COMPARAÇÃO DE TOTAIS:")
        print(f"  Banco:    {db_total:7,} parâmetros")
        print(f"  Pipeline: {pipeline_total:7,} parâmetros")
        print(f"  Diferença: {diff:+7,} ({diff_pct:+.2f}%)")
        
        # Identificar equipamentos no banco vs CSVs
        db_equipment = {row['equipment_tag'] for row in db_data['distribution']}
        csv_equipment = {csv_row['equipment_tag'] for csv_row in pipeline_data['csv_details']}
        
        missing_in_db = csv_equipment - db_equipment
        extra_in_db = db_equipment - csv_equipment
        
        print(f"\n📊 COMPARAÇÃO DE EQUIPAMENTOS:")
        print(f"  No Banco:    {len(db_equipment)} equipamentos")
        print(f"  No Pipeline: {len(csv_equipment)} equipamentos")
        
        if missing_in_db:
            print(f"\n⚠️  {len(missing_in_db)} equipamentos no PIPELINE mas NÃO no BANCO:")
            for tag in sorted(missing_in_db):
                print(f"  - {tag}")
        
        if extra_in_db:
            print(f"\n⚠️  {len(extra_in_db)} equipamentos no BANCO mas NÃO no PIPELINE:")
            for tag in sorted(extra_in_db):
                print(f"  - {tag}")
        
        # Comparar parâmetros por equipamento (equipamentos em comum)
        common_equipment = db_equipment & csv_equipment
        param_divergences = []
        
        if common_equipment:
            print(f"\n📊 Comparando parâmetros dos {len(common_equipment)} equipamentos em comum:")
            
            for tag in sorted(common_equipment):
                # Buscar no banco
                db_row = next((row for row in db_data['distribution'] if row['equipment_tag'] == tag), None)
                db_count = db_row['param_count'] if db_row else 0
                
                # Buscar no CSV
                csv_row = next((csv_row for csv_row in pipeline_data['csv_details'] if csv_row['equipment_tag'] == tag), None)
                csv_count = csv_row['param_count'] if csv_row else 0
                
                diff = db_count - csv_count
                if diff != 0:
                    param_divergences.append({
                        'equipment_tag': tag,
                        'db_count': db_count,
                        'csv_count': csv_count,
                        'difference': diff
                    })
        
        if param_divergences:
            print(f"\n⚠️  {len(param_divergences)} equipamentos com DIVERGÊNCIA de parâmetros:")
            for div in sorted(param_divergences, key=lambda x: abs(x['difference']), reverse=True)[:20]:
                print(f"  {div['equipment_tag']:30s} → DB: {div['db_count']:5d} | CSV: {div['csv_count']:5d} | Diff: {div['difference']:+5d}")
        else:
            print("\n✅ TODOS os equipamentos comuns têm mesma quantidade de parâmetros!")
        
        # Armazenar divergências
        self.audit_results['divergences'] = {
            'total_params_diff': diff,
            'total_params_diff_pct': round(diff_pct, 2),
            'missing_in_db': sorted(missing_in_db),
            'extra_in_db': sorted(extra_in_db),
            'param_divergences': param_divergences
        }
        
        return True
    
    def generate_recommendations(self):
        """Gera recomendações baseadas na auditoria"""
        print("\n" + "="*80)
        print("💡 RECOMENDAÇÕES")
        print("="*80)
        
        recommendations = []
        db_data = self.audit_results['database']
        div_data = self.audit_results['divergences']
        
        # Recomendação 1: Parâmetros órfãos
        if db_data['orphan_params'] > 0:
            rec = f"❌ CRÍTICO: {db_data['orphan_params']} parâmetros órfãos (sem equipment_id). LIMPAR antes de re-importar."
            print(rec)
            recommendations.append(rec)
        
        # Recomendação 2: Campos vazios
        if db_data['empty_codes'] > 0 or db_data['empty_names'] > 0:
            rec = f"❌ CRÍTICO: {db_data['empty_codes']} códigos vazios e {db_data['empty_names']} nomes vazios. LIMPAR."
            print(rec)
            recommendations.append(rec)
        
        # Recomendação 3: Divergência de totais
        if abs(div_data['total_params_diff']) > 100:
            rec = f"⚠️  IMPORTANTE: Divergência de {div_data['total_params_diff']:+,} parâmetros ({div_data['total_params_diff_pct']:+.2f}%). RE-IMPORTAR recomendado."
            print(rec)
            recommendations.append(rec)
        
        # Recomendação 4: Equipamentos faltando
        if div_data['missing_in_db']:
            rec = f"⚠️  IMPORTANTE: {len(div_data['missing_in_db'])} equipamentos no pipeline não estão no banco. RE-IMPORTAR."
            print(rec)
            recommendations.append(rec)
        
        # Recomendação 5: Equipamentos extras
        if div_data['extra_in_db']:
            rec = f"ℹ️  INFO: {len(div_data['extra_in_db'])} equipamentos no banco não estão no pipeline. Possível dados antigos."
            print(rec)
            recommendations.append(rec)
        
        # Recomendação 6: Divergências de parâmetros
        if div_data['param_divergences']:
            rec = f"⚠️  IMPORTANTE: {len(div_data['param_divergences'])} equipamentos com divergência de parâmetros. RE-IMPORTAR recomendado."
            print(rec)
            recommendations.append(rec)
        
        # Recomendação final
        if not recommendations:
            rec = "✅ EXCELENTE: Banco 100% sincronizado com pipeline. Nenhuma ação necessária."
            print(rec)
            recommendations.append(rec)
        else:
            rec = "🔧 AÇÃO REQUERIDA: Executar FASE 1.2 (Limpar banco) e FASE 1.3 (Re-importar dados)."
            print(rec)
            recommendations.append(rec)
        
        self.audit_results['recommendations'] = recommendations
        
        return True
    
    def save_report(self):
        """Salva relatório JSON"""
        report_file = REPORTS_DIR / f'database_audit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.audit_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Relatório salvo: {report_file}")
            return str(report_file)
            
        except Exception as e:
            print(f"❌ Erro ao salvar relatório: {e}")
            return None
    
    def close(self):
        """Fecha conexão com banco"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("\n🔌 Conexão com banco fechada.")


def main():
    """Função principal"""
    print("="*80)
    print("🔬 AUDITORIA COMPLETA: BANCO DE DADOS vs PIPELINE")
    print("="*80)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🗂️  Base Dir: {BASE_DIR}")
    print(f"📂 Norm CSV Dir: {NORM_CSV_DIR}")
    print(f"📊 Reports Dir: {REPORTS_DIR}")
    
    auditor = DatabaseAuditor()
    
    try:
        # Conectar ao banco
        if not auditor.connect_db():
            print("❌ Falha ao conectar ao banco. Verifique se o Docker está rodando.")
            return 1
        
        # Auditar banco
        if not auditor.audit_database():
            print("❌ Falha ao auditar banco de dados.")
            return 1
        
        # Auditar CSVs
        if not auditor.audit_pipeline_csvs():
            print("❌ Falha ao auditar CSVs do pipeline.")
            return 1
        
        # Comparar
        if not auditor.compare_database_vs_pipeline():
            print("❌ Falha ao comparar banco vs pipeline.")
            return 1
        
        # Gerar recomendações
        auditor.generate_recommendations()
        
        # Salvar relatório
        report_file = auditor.save_report()
        
        if report_file:
            print("\n" + "="*80)
            print("✅ AUDITORIA CONCLUÍDA COM SUCESSO!")
            print("="*80)
            print(f"📄 Relatório: {report_file}")
            print("\n🎯 PRÓXIMO PASSO: Revisar recomendações e decidir se precisa re-importar dados.")
            return 0
        else:
            print("\n⚠️  Auditoria concluída mas falha ao salvar relatório.")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        auditor.close()


if __name__ == '__main__':
    sys.exit(main())

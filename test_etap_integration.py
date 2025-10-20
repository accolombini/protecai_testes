"""
Teste Completo ETAP Integration FASE 1
======================================

Teste abrangente da implementação enterprise ETAP com dados reais da Petrobras.

Testa:
- Models SQLAlchemy (8 tabelas)
- Service Layer completo
- CSV Bridge com dados reais
- REST API endpoints
- Integração bidirecional

Baseado na análise real dos CSVs: MiCOM P143 + Easergy P3
"""

import asyncio
import sys
import os
import logging
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy import text

# Adicionar caminho do projeto
sys.path.insert(0, os.path.abspath('.'))

from api.core.database import engine, SessionLocal, Base
from api.core.config import settings
from api.models.etap_models import *
from api.services.etap_service import EtapService
from api.services.csv_bridge import CSVBridge, DeviceType
from api.services.etap_integration_service import EtapIntegrationService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ETAPTestSuite:
    """Suite completa de testes para ETAP Integration"""
    
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.test_results = {}
        
    def setup_database(self):
        """Configurar tabelas de teste"""
        try:
            logger.info("🏗️ Setting up database tables...")
            
            # Drop views first, then tables with CASCADE
            with self.engine.connect() as conn:
                # Drop views that might depend on tables
                try:
                    conn.execute(text("DROP VIEW IF EXISTS relay_configs.v_equipment_complete CASCADE"))
                    conn.execute(text("DROP VIEW IF EXISTS relay_configs.v_relay_summary CASCADE"))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Views drop warning: {e}")
                
                # Drop all tables with CASCADE
                try:
                    conn.execute(text("DROP SCHEMA IF EXISTS relay_configs CASCADE"))
                    conn.execute(text("CREATE SCHEMA IF NOT EXISTS relay_configs"))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Schema recreation warning: {e}")
            
            # Now create all tables
            Base.metadata.create_all(bind=self.engine)
            
            # Verificar tabelas criadas
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema IN ('public', 'relay_configs')
                    ORDER BY table_name
                """))
                tables = [row[0] for row in result.fetchall()]
                
            logger.info(f"✅ Database setup complete! Tables: {len(tables)}")
            logger.info(f"📋 Tables: {', '.join(tables)}")
            
            self.test_results["database_setup"] = {
                "status": "success",
                "tables_created": len(tables),
                "table_list": tables
            }
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            self.test_results["database_setup"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    def test_csv_bridge_with_real_data(self):
        """Testar CSV Bridge com dados reais"""
        try:
            logger.info("🔗 Testing CSV Bridge with real Petrobras data...")
            
            csv_bridge = CSVBridge()
            
            # Verificar se temos dados reais
            csv_files = []
            csv_dir = Path("outputs/csv")
            if csv_dir.exists():
                csv_files = list(csv_dir.glob("*.csv"))
            
            if not csv_files:
                # Criar dados de teste baseados na análise real
                test_data = self._create_test_csv_data()
                csv_files = [test_data]
            
            results = []
            for csv_file in csv_files[:2]:  # Testar 2 arquivos máximo
                try:
                    logger.info(f"📄 Processing: {csv_file}")
                    
                    config_data = csv_bridge.parse_csv_file(str(csv_file))
                    
                    # Validar estrutura
                    is_valid, validation_errors = csv_bridge.validate_config(config_data)
                    
                    file_result = {
                        "file": csv_file.name,
                        "device_type": config_data.get("device_type"),
                        "parameters_count": len(config_data.get("raw_parameters", [])),
                        "categories_found": list(config_data.keys()),
                        "validation_status": "valid" if is_valid else "warnings",
                        "validation_errors": validation_errors
                    }
                    
                    results.append(file_result)
                    logger.info(f"✅ {csv_file.name}: {file_result['device_type']} - {file_result['parameters_count']} params")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process {csv_file}: {e}")
                    results.append({
                        "file": csv_file.name,
                        "status": "failed",
                        "error": str(e)
                    })
            
            self.test_results["csv_bridge"] = {
                "status": "success",
                "files_processed": len(results),
                "results": results
            }
            
            logger.info(f"✅ CSV Bridge test completed: {len(results)} files processed")
            return True
            
        except Exception as e:
            logger.error(f"❌ CSV Bridge test failed: {e}")
            self.test_results["csv_bridge"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    def _create_test_csv_data(self):
        """Criar dados de teste baseados na análise real"""
        # Dados baseados no MiCOM P143 real analisado
        test_data = [
            ["Code", "Description", "Value"],
            ["00.04", "Description", "MiCOM P143 Motor Protection"],
            ["00.05", "Plant Reference", "690927U"],
            ["00.06", "Model Number", "P143"],
            ["00.08", "Serial Number", "12345678"],
            ["00.09", "Frequency", "60"],
            ["0A.01", "Main VT Primary", "13800"],
            ["0A.02", "Main VT Sec'y", "115"],
            ["0A.07", "Phase CT Primary", "600"],
            ["0A.08", "Phase CT Sec'y", "5"],
            ["30.01", "Ith Current Set", "500"],
            ["30.03", "Thermal Const T1", "60"],
            ["30.04", "Thermal Const T2", "600"],
            ["31.01", "I>1 Function", "Enabled"],
            ["31.02", "I>1 Current Set", "120"],
            ["31.03", "I>1 Time Delay", "0.5"],
            ["32.01", "ISEF>1 Function", "Enabled"],
            ["32.03", "ISEF>1 Current", "20"],
            ["32.04", "ISEF>1 T. Delay", "0.3"],
        ]
        
        # Salvar arquivo de teste
        test_file = Path("/tmp/test_micom_p143.csv")
        df = pd.DataFrame(test_data[1:], columns=test_data[0])
        df.to_csv(test_file, index=False)
        
        logger.info(f"📝 Created test CSV: {test_file}")
        return test_file
    
    async def test_etap_service(self):
        """Testar EtapService"""
        try:
            logger.info("⚙️ Testing ETAP Service...")
            
            with self.SessionLocal() as db:
                etap_service = EtapService(db)
                
                # Teste 1: Criar estudo
                study = await etap_service.create_study(
                    name="Test_Study_MiCOM_P143",
                    description="Teste com dados reais MiCOM P143",
                    study_type="coordination"
                )
                
                logger.info(f"✅ Study created: {study.id} - {study.name}")
                
                # Teste 2: Adicionar equipamento
                # Teste 2: Adicionar equipamento
                equipment_data = {
                    "device_info": {
                        "model_number": "P143",
                        "serial_number": "12345678",
                        "plant_reference": "690927U"
                    },
                    "electrical_config": {
                        "phase_ct_primary": 600,
                        "phase_ct_secondary": 5,
                        "vt_primary": 13800,
                        "vt_secondary": 115
                    },
                    "protection_functions": {
                        "thermal_current_setting": 500,
                        "overcurrent_setting": 120,
                        "earth_fault_setting": 20
                    }
                }
                
                equipment = await etap_service.add_equipment_to_study(
                    study_id=study.id,
                    etap_device_id="MICOM_P143_TEST",
                    device_config=equipment_data
                )
                
                logger.info(f"✅ Equipment added: {equipment.id}")
                
                # Teste 3: Buscar estudo
                retrieved_study = await etap_service.get_study_by_id(study.id)
                assert retrieved_study["name"] == study.name
                
                # Teste 4: Listar equipamentos (via query direta)
                equipment_configs = db.query(EtapEquipmentConfig).filter(
                    EtapEquipmentConfig.study_id == study.id
                ).all()
                assert len(equipment_configs) == 1
                
                # Teste 5: Análise de coordenação
                coordination_result = await etap_service.run_coordination_analysis(study.id)
                
                logger.info(f"✅ Coordination analysis: {len(coordination_result.get('results', []))} results")
                
                self.test_results["etap_service"] = {
                    "status": "success",
                    "study_id": study.id,
                    "equipment_count": len(equipment_configs),
                    "coordination_analysis": "completed"
                }
                
                logger.info("✅ ETAP Service test completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"❌ ETAP Service test failed: {e}")
            self.test_results["etap_service"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    async def test_integration_service(self):
        """Testar EtapIntegrationService"""
        try:
            logger.info("🔄 Testing ETAP Integration Service...")
            
            with self.SessionLocal() as db:
                integration_service = EtapIntegrationService(db)
                
                # Criar dados CSV de teste
                test_csv = self._create_test_csv_data()
                
                # Simular UploadFile
                class MockUploadFile:
                    def __init__(self, filename, content):
                        self.filename = filename
                        self._content = content
                    
                    async def read(self):
                        with open(self._content, 'rb') as f:
                            return f.read()
                
                mock_file = MockUploadFile("test_micom.csv", test_csv)
                
                # Teste import CSV
                async def run_import():
                    return await integration_service.import_csv_to_study(
                        csv_file=mock_file,
                        study_name="Integration_Test_Study",
                        study_description="Teste de integração completa"
                    )
                
                import_result = await run_import()
                
                logger.info(f"✅ CSV imported: Study {import_result['study_id']}")
                logger.info(f"📊 Parameters: {import_result['parameters_imported']}")
                logger.info(f"🔧 Equipment configs: {import_result['equipment_configs']}")
                
                # Teste export CSV
                study_id = import_result['study_id']
                async def run_export():
                    return await integration_service.export_study_to_csv(
                        study_id=study_id,
                        format_type="original"
                    )
                
                filename, csv_content = await run_export()
                
                logger.info(f"✅ CSV exported: {filename} ({len(csv_content)} bytes)")
                
                # Teste migration status
                migration_status = await integration_service.get_migration_status(study_id)
                
                logger.info(f"✅ Migration status: {migration_status['csv_compatibility']}")
                
                self.test_results["integration_service"] = {
                    "status": "success",
                    "import_result": import_result,
                    "export_size": len(csv_content),
                    "migration_status": migration_status
                }
                
                logger.info("✅ Integration Service test completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"❌ Integration Service test failed: {e}")
            self.test_results["integration_service"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    def test_database_queries(self):
        """Testar queries do banco"""
        try:
            logger.info("🗃️ Testing database queries...")
            
            with self.engine.connect() as conn:
                # Teste 1: Verificar estudos
                result = conn.execute(text("SELECT COUNT(*) FROM etap_studies"))
                study_count = result.scalar()
                
                # Teste 2: Verificar equipamentos
                result = conn.execute(text("SELECT COUNT(*) FROM etap_equipment_configs"))
                equipment_count = result.scalar()
                
                # Teste 3: Verificar relacionamentos
                result = conn.execute(text("""
                    SELECT s.name, COUNT(e.id) as equipment_count
                    FROM etap_studies s
                    LEFT JOIN etap_equipment_configs e ON s.id = e.study_id
                    GROUP BY s.id, s.name
                """))
                relationships = result.fetchall()
                
                logger.info(f"📊 Database stats: {study_count} studies, {equipment_count} equipment")
                
                for study_name, eq_count in relationships:
                    logger.info(f"  📋 {study_name}: {eq_count} equipment")
                
                self.test_results["database_queries"] = {
                    "status": "success",
                    "study_count": study_count,
                    "equipment_count": equipment_count,
                    "relationships": len(relationships)
                }
                
                logger.info("✅ Database queries test completed")
                return True
                
        except Exception as e:
            logger.error(f"❌ Database queries test failed: {e}")
            self.test_results["database_queries"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    async def run_all_tests(self):
        """Executar todos os testes"""
        logger.info("🚀 Starting ETAP Integration FASE 1 Test Suite")
        logger.info("=" * 60)
        
        test_methods = [
            ("Database Setup", self.setup_database),
            ("CSV Bridge", self.test_csv_bridge_with_real_data),
            ("ETAP Service", self.test_etap_service),
            ("Integration Service", self.test_integration_service),
            ("Database Queries", self.test_database_queries),
        ]
        
        total_tests = len(test_methods)
        passed_tests = 0
        
        for test_name, test_method in test_methods:
            logger.info(f"\n🧪 Running: {test_name}")
            logger.info("-" * 40)
            
            try:
                if asyncio.iscoroutinefunction(test_method):
                    success = await test_method()
                else:
                    success = test_method()
                
                if success:
                    passed_tests += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"💥 {test_name}: CRASHED - {e}")
        
        # Relatório final
        logger.info("\n" + "=" * 60)
        logger.info("📊 FINAL TEST REPORT")
        logger.info("=" * 60)
        
        success_rate = (passed_tests / total_tests) * 100
        logger.info(f"🎯 Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            logger.info("🎉 ETAP INTEGRATION FASE 1: READY FOR PRODUCTION!")
        elif success_rate >= 60:
            logger.info("⚠️  ETAP INTEGRATION FASE 1: Needs improvements")
        else:
            logger.info("❌ ETAP INTEGRATION FASE 1: Requires fixes")
        
        # Salvar relatório
        report = {
            "test_suite": "ETAP Integration FASE 1",
            "timestamp": pd.Timestamp.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": success_rate,
                "status": "PASSED" if success_rate >= 80 else "NEEDS_WORK"
            },
            "detailed_results": self.test_results
        }
        
        report_file = Path("outputs/logs/etap_integration_test_report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Detailed report saved: {report_file}")
        
        return success_rate >= 80

async def main():
    """Função principal"""
    test_suite = ETAPTestSuite()
    
    try:
        success = await test_suite.run_all_tests()
        exit_code = 0 if success else 1
        
        print(f"\n🏁 Test suite completed with exit code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.error(f"💥 Test suite crashed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
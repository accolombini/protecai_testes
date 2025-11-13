#!/usr/bin/env python3
"""
================================================================================
GERADOR DE RELATÓRIOS DE CONFIGURAÇÃO - SCRIPT STANDALONE
================================================================================
Author: ProtecAI Engineering Team
Project: PETRO_ProtecAI
Date: 2025-11-03
Version: 1.0.0

Description:
    Script standalone para gerar relatórios de configuração de relés
    sem necessidade de rodar a API FastAPI.
    
    Útil para:
    - Testes rápidos
    - Geração em batch
    - Automação de relatórios
    - Validação de dados

Usage:
    # Gerar relatório JSON
    python scripts/generate_relay_config_report.py --equipment-id 1 --format json
    
    # Gerar e salvar CSV
    python scripts/generate_relay_config_report.py --equipment-id 1 --format csv --output reports/
    
    # Gerar PDF com funções desabilitadas
    python scripts/generate_relay_config_report.py --equipment-id 1 --format pdf --include-disabled --output reports/

Prerequisites:
    - PostgreSQL rodando
    - Tabelas populadas (relay_equipment, protection_functions, relay_settings)
================================================================================
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Adicionar path do projeto
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração do banco
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'protecai_db',
    'user': 'protecai',
    'password': 'protecai'
}


def create_db_session():
    """Cria sessão do banco de dados."""
    try:
        db_url = (
            f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        return SessionLocal()
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}")
        sys.exit(1)


def generate_report(equipment_id: int, format: str, include_disabled: bool, output_dir: Path = None):
    """
    Gera relatório de configuração.
    
    Args:
        equipment_id: ID do equipamento
        format: Formato (json, csv, xlsx, pdf)
        include_disabled: Incluir funções desabilitadas
        output_dir: Diretório de saída (None = stdout para JSON)
    """
    try:
        # Importar serviço
        from api.services.relay_config_report_service import RelayConfigReportService
        
        # Criar sessão
        db = create_db_session()
        
        # Gerar relatório
        logger.info(f"📋 Gerando relatório: equipment_id={equipment_id}, format={format}")
        service = RelayConfigReportService(db)
        
        result = service.generate_configuration_report(
            equipment_id=equipment_id,
            format=format,
            include_disabled=include_disabled
        )
        
        # Processar saída
        if format == 'json':
            if output_dir:
                # Salvar em arquivo
                filename = result.get('filename', f'config_{equipment_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                filepath = output_dir / filename
                
                import json
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result['data'], f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Relatório JSON salvo: {filepath}")
            else:
                # Imprimir no stdout
                import json
                print(json.dumps(result['data'], indent=2, ensure_ascii=False))
        
        else:
            # Formatos binários (csv, xlsx, pdf)
            if not output_dir:
                logger.error("❌ Para formatos CSV/XLSX/PDF, é necessário especificar --output")
                sys.exit(1)
            
            filename = result.get('filename', f'config_{equipment_id}.{format}')
            filepath = output_dir / filename
            
            # Salvar conteúdo
            mode = 'w' if format == 'csv' else 'wb'
            with open(filepath, mode) as f:
                if format == 'csv':
                    f.write(result['data'])
                else:
                    f.write(result['data'])
            
            logger.info(f"✅ Relatório {format.upper()} salvo: {filepath}")
            logger.info(f"📊 Tamanho: {len(result['data']) / 1024:.2f} KB")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def list_equipment(manufacturer: str = None, model: str = None):
    """
    Lista equipamentos disponíveis.
    
    Args:
        manufacturer: Filtro por fabricante
        model: Filtro por modelo
    """
    try:
        from sqlalchemy import text
        
        db = create_db_session()
        
        # Montar query
        filters = []
        params = {}
        
        if manufacturer:
            filters.append("mf.name ILIKE :manufacturer")
            params['manufacturer'] = f"%{manufacturer}%"
        
        if model:
            filters.append("m.name ILIKE :model")
            params['model'] = f"%{model}%"
        
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        query = text(f"""
            SELECT 
                e.id,
                e.equipment_tag,
                m.name as model_name,
                mf.name as manufacturer_name,
                e.status,
                COUNT(DISTINCT rs.id) as settings_count
            FROM protec_ai.relay_equipment e
            LEFT JOIN protec_ai.relay_models m ON e.model_id = m.id
            LEFT JOIN protec_ai.manufacturers mf ON m.manufacturer_id = mf.id
            LEFT JOIN protec_ai.relay_settings rs ON e.id = rs.equipment_id
            {where_clause}
            GROUP BY e.id, e.equipment_tag, m.name, mf.name, e.status
            ORDER BY e.id
            LIMIT 50
        """)
        
        results = db.execute(query, params).fetchall()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"EQUIPAMENTOS DISPONÍVEIS ({len(results)} encontrados)")
        logger.info(f"{'='*80}")
        logger.info(f"{'ID':<6} {'Tag':<20} {'Fabricante':<20} {'Modelo':<15} {'Settings':<10} {'Status'}")
        logger.info(f"{'-'*80}")
        
        for row in results:
            logger.info(
                f"{row.id:<6} {row.equipment_tag or 'N/A':<20} "
                f"{row.manufacturer_name or 'N/A':<20} {row.model_name or 'N/A':<15} "
                f"{row.settings_count:<10} {row.status or 'N/A'}"
            )
        
        logger.info(f"{'='*80}\n")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar equipamentos: {e}")
        sys.exit(1)


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Gerador de Relatórios de Configuração de Relés',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Listar equipamentos disponíveis
  %(prog)s --list
  
  # Listar equipamentos Schneider
  %(prog)s --list --manufacturer Schneider
  
  # Gerar relatório JSON no stdout
  %(prog)s --equipment-id 1 --format json
  
  # Gerar relatório CSV e salvar
  %(prog)s --equipment-id 1 --format csv --output outputs/reports/
  
  # Gerar PDF com funções desabilitadas
  %(prog)s --equipment-id 1 --format pdf --include-disabled --output outputs/reports/
        """
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='Listar equipamentos disponíveis'
    )
    
    parser.add_argument(
        '--equipment-id',
        type=int,
        help='ID do equipamento para gerar relatório'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'csv', 'xlsx', 'pdf'],
        default='json',
        help='Formato do relatório (default: json)'
    )
    
    parser.add_argument(
        '--include-disabled',
        action='store_true',
        help='Incluir funções e parâmetros desabilitados'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Diretório de saída (requerido para CSV/XLSX/PDF)'
    )
    
    parser.add_argument(
        '--manufacturer',
        type=str,
        help='Filtro por fabricante (usado com --list)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        help='Filtro por modelo (usado com --list)'
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.list:
        list_equipment(args.manufacturer, args.model)
        return
    
    if not args.equipment_id:
        parser.error("--equipment-id é obrigatório (ou use --list)")
    
    # Criar diretório de saída se especificado
    output_dir = None
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Diretório de saída: {output_dir}")
    
    # Gerar relatório
    generate_report(
        equipment_id=args.equipment_id,
        format=args.format,
        include_disabled=args.include_disabled,
        output_dir=output_dir
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)

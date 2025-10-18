#!/usr/bin/env python3
"""
🔬 ProtecAI - Comparador de Configurações de Relés
Implementação do TODO #6: Sistema robusto para comparação de configurações entre relés

Autor: ProtecAI Development Team
Data: 18/10/2025
Versão: 1.0.0
"""

import psycopg2
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from decimal import Decimal


class ComparisonType(Enum):
    """Tipos de comparação disponíveis"""
    IDENTICAL = "identical"
    DIFFERENT = "different"
    MISSING_LEFT = "missing_left"
    MISSING_RIGHT = "missing_right"
    SIMILAR = "similar"
    WARNING = "warning"


@dataclass
class ComparisonResult:
    """Resultado de uma comparação individual"""
    field_name: str
    comparison_type: ComparisonType
    left_value: Any
    right_value: Any
    difference: Optional[str] = None
    severity: str = "info"  # info, warning, critical
    notes: Optional[str] = None


@dataclass
class EquipmentSummary:
    """Resumo de um equipamento"""
    id: int
    tag_reference: Optional[str]
    serial_number: Optional[str]
    manufacturer: str
    model_type: str
    family: Optional[str]
    status: str
    software_version: Optional[str]


class RelayConfigurationComparator:
    """
    🔬 Comparador de Configurações de Relés
    
    Sistema completo para comparação de configurações entre relés,
    identificação de diferenças e geração de relatórios estruturados.
    """
    
    def __init__(self, db_config: Dict[str, str]):
        """
        Inicializa o comparador com configuração do banco de dados
        
        Args:
            db_config: Dicionário com configurações de conexão
        """
        self.db_config = db_config
        self.conn = None
        self.comparison_results = {}
        
    def connect(self):
        """Estabelece conexão com o banco de dados"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            return True
        except Exception as e:
            print(f"❌ Erro na conexão: {e}")
            return False
    
    def disconnect(self):
        """Fecha conexão com o banco"""
        if self.conn:
            self.conn.close()
    
    def get_equipment_summary(self, equipment_id: int) -> Optional[EquipmentSummary]:
        """
        Obtém resumo de um equipamento
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            EquipmentSummary ou None se não encontrado
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    re.id,
                    re.tag_reference, 
                    re.serial_number, 
                    m.name as manufacturer, 
                    rm.model_type,
                    rm.family,
                    re.status,
                    re.software_version
                FROM relay_configs.relay_equipment re
                LEFT JOIN relay_configs.relay_models rm ON re.model_id = rm.id
                LEFT JOIN relay_configs.manufacturers m ON rm.manufacturer_id = m.id
                WHERE re.id = %s;
            """, (equipment_id,))
            
            result = cursor.fetchone()
            if result:
                return EquipmentSummary(*result)
            return None
            
        except Exception as e:
            print(f"❌ Erro ao buscar equipamento {equipment_id}: {e}")
            return None
        finally:
            cursor.close()
    
    def get_electrical_configuration(self, equipment_id: int) -> Dict[str, Any]:
        """
        Obtém configuração elétrica de um equipamento
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Dicionário com configurações elétricas
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    phase_ct_primary,
                    phase_ct_secondary,
                    neutral_ct_primary,
                    neutral_ct_secondary,
                    vt_primary,
                    vt_secondary,
                    nvd_vt_primary,
                    nvd_vt_secondary,
                    nominal_voltage,
                    equipment_load,
                    vt_connection_mode,
                    power_supply
                FROM relay_configs.electrical_configuration
                WHERE equipment_id = %s;
            """, (equipment_id,))
            
            result = cursor.fetchone()
            if result:
                columns = [
                    'phase_ct_primary', 'phase_ct_secondary',
                    'neutral_ct_primary', 'neutral_ct_secondary',
                    'vt_primary', 'vt_secondary',
                    'nvd_vt_primary', 'nvd_vt_secondary',
                    'nominal_voltage', 'equipment_load',
                    'vt_connection_mode', 'power_supply'
                ]
                return dict(zip(columns, result))
            return {}
            
        except Exception as e:
            print(f"❌ Erro ao buscar configuração elétrica {equipment_id}: {e}")
            return {}
        finally:
            cursor.close()
    
    def get_protection_functions(self, equipment_id: int) -> List[Dict[str, Any]]:
        """
        Obtém funções de proteção de um equipamento
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Lista de funções de proteção
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    ansi_code,
                    function_name,
                    enabled,
                    current_setting,
                    time_setting,
                    characteristic,
                    direction,
                    pickup_value,
                    time_delay,
                    coordination_group,
                    priority,
                    additional_settings_json
                FROM relay_configs.protection_functions
                WHERE equipment_id = %s
                ORDER BY ansi_code;
            """, (equipment_id,))
            
            results = cursor.fetchall()
            columns = [
                'ansi_code', 'function_name', 'enabled',
                'current_setting', 'time_setting', 'characteristic',
                'direction', 'pickup_value', 'time_delay',
                'coordination_group', 'priority', 'additional_settings_json'
            ]
            
            functions = []
            for result in results:
                func_dict = dict(zip(columns, result))
                functions.append(func_dict)
            
            return functions
            
        except Exception as e:
            print(f"❌ Erro ao buscar funções de proteção {equipment_id}: {e}")
            return []
        finally:
            cursor.close()
    
    def get_io_configuration(self, equipment_id: int) -> List[Dict[str, Any]]:
        """
        Obtém configurações I/O de um equipamento
        
        Args:
            equipment_id: ID do equipamento
            
        Returns:
            Lista de configurações I/O
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    io_type,
                    channel_number,
                    label,
                    signal_type,
                    function_assignment,
                    alarm_settings,
                    status
                FROM relay_configs.io_configuration
                WHERE equipment_id = %s
                ORDER BY channel_number;
            """, (equipment_id,))
            
            results = cursor.fetchall()
            columns = [
                'io_type', 'channel_number', 'label',
                'signal_type', 'function_assignment',
                'alarm_settings', 'status'
            ]
            
            ios = []
            for result in results:
                io_dict = dict(zip(columns, result))
                ios.append(io_dict)
            
            return ios
            
        except Exception as e:
            print(f"❌ Erro ao buscar configurações I/O {equipment_id}: {e}")
            return []
        finally:
            cursor.close()
    
    def compare_electrical_configurations(self, left_config: Dict, right_config: Dict) -> List[ComparisonResult]:
        """
        Compara configurações elétricas entre dois equipamentos
        
        Args:
            left_config: Configuração do primeiro equipamento
            right_config: Configuração do segundo equipamento
            
        Returns:
            Lista de resultados de comparação
        """
        results = []
        
        # Campos críticos para comparação
        critical_fields = [
            'phase_ct_primary', 'phase_ct_secondary',
            'neutral_ct_primary', 'neutral_ct_secondary',
            'vt_primary', 'vt_secondary',
            'nominal_voltage'
        ]
        
        # Campos informativos
        info_fields = [
            'nvd_vt_primary', 'nvd_vt_secondary',
            'equipment_load', 'vt_connection_mode', 'power_supply'
        ]
        
        all_fields = critical_fields + info_fields
        
        for field in all_fields:
            left_val = left_config.get(field)
            right_val = right_config.get(field)
            
            # Determinar severidade
            severity = "critical" if field in critical_fields else "info"
            
            if left_val is None and right_val is None:
                comp_type = ComparisonType.IDENTICAL
                notes = "Ambos valores não configurados"
            elif left_val is None:
                comp_type = ComparisonType.MISSING_LEFT
                notes = "Valor não configurado no equipamento esquerdo"
            elif right_val is None:
                comp_type = ComparisonType.MISSING_RIGHT
                notes = "Valor não configurado no equipamento direito"
            elif left_val == right_val:
                comp_type = ComparisonType.IDENTICAL
                notes = "Valores idênticos"
            else:
                comp_type = ComparisonType.DIFFERENT
                
                # Calcular diferença percentual para valores numéricos
                if isinstance(left_val, (int, float, Decimal)) and isinstance(right_val, (int, float, Decimal)):
                    if left_val != 0:
                        diff_percent = abs((float(right_val) - float(left_val)) / float(left_val)) * 100
                        notes = f"Diferença: {diff_percent:.2f}%"
                    else:
                        notes = f"Valores diferentes: {left_val} vs {right_val}"
                else:
                    notes = f"Valores diferentes: {left_val} vs {right_val}"
            
            results.append(ComparisonResult(
                field_name=field,
                comparison_type=comp_type,
                left_value=left_val,
                right_value=right_val,
                difference=notes,
                severity=severity,
                notes=notes
            ))
        
        return results
    
    def compare_protection_functions(self, left_functions: List[Dict], right_functions: List[Dict]) -> List[ComparisonResult]:
        """
        Compara funções de proteção entre dois equipamentos
        
        Args:
            left_functions: Funções do primeiro equipamento
            right_functions: Funções do segundo equipamento
            
        Returns:
            Lista de resultados de comparação
        """
        results = []
        
        # Indexar funções por código ANSI
        left_by_ansi = {f['ansi_code']: f for f in left_functions}
        right_by_ansi = {f['ansi_code']: f for f in right_functions}
        
        # Obter todos os códigos ANSI únicos
        all_ansi_codes = set(left_by_ansi.keys()) | set(right_by_ansi.keys())
        
        for ansi_code in sorted(all_ansi_codes):
            left_func = left_by_ansi.get(ansi_code)
            right_func = right_by_ansi.get(ansi_code)
            
            prefix = f"protection_function_{ansi_code}"
            
            if left_func is None:
                results.append(ComparisonResult(
                    field_name=f"{prefix}_existence",
                    comparison_type=ComparisonType.MISSING_LEFT,
                    left_value=None,
                    right_value=right_func['function_name'],
                    severity="warning",
                    notes=f"Função {ansi_code} ausente no equipamento esquerdo"
                ))
                continue
            
            if right_func is None:
                results.append(ComparisonResult(
                    field_name=f"{prefix}_existence",
                    comparison_type=ComparisonType.MISSING_RIGHT,
                    left_value=left_func['function_name'],
                    right_value=None,
                    severity="warning",
                    notes=f"Função {ansi_code} ausente no equipamento direito"
                ))
                continue
            
            # Comparar campos importantes
            comparison_fields = [
                ('enabled', 'critical'),
                ('current_setting', 'critical'),
                ('time_setting', 'critical'),
                ('pickup_value', 'warning'),
                ('time_delay', 'warning'),
                ('characteristic', 'info'),
                ('direction', 'info')
            ]
            
            for field, severity in comparison_fields:
                left_val = left_func.get(field)
                right_val = right_func.get(field)
                
                if left_val == right_val:
                    comp_type = ComparisonType.IDENTICAL
                    notes = "Valores idênticos"
                else:
                    comp_type = ComparisonType.DIFFERENT
                    if field == 'enabled':
                        notes = f"Habilitação diferente: {'ON' if left_val else 'OFF'} vs {'ON' if right_val else 'OFF'}"
                    else:
                        notes = f"Valores diferentes: {left_val} vs {right_val}"
                
                results.append(ComparisonResult(
                    field_name=f"{prefix}_{field}",
                    comparison_type=comp_type,
                    left_value=left_val,
                    right_value=right_val,
                    severity=severity,
                    notes=notes
                ))
        
        return results
    
    def compare_io_configurations(self, left_ios: List[Dict], right_ios: List[Dict]) -> List[ComparisonResult]:
        """
        Compara configurações I/O entre dois equipamentos
        
        Args:
            left_ios: I/Os do primeiro equipamento
            right_ios: I/Os do segundo equipamento
            
        Returns:
            Lista de resultados de comparação
        """
        results = []
        
        # Estatísticas gerais
        left_counts = {}
        right_counts = {}
        
        for io in left_ios:
            io_type = io['io_type']
            left_counts[io_type] = left_counts.get(io_type, 0) + 1
        
        for io in right_ios:
            io_type = io['io_type']
            right_counts[io_type] = right_counts.get(io_type, 0) + 1
        
        # Comparar contadores por tipo
        all_io_types = set(left_counts.keys()) | set(right_counts.keys())
        
        for io_type in sorted(all_io_types):
            left_count = left_counts.get(io_type, 0)
            right_count = right_counts.get(io_type, 0)
            
            if left_count == right_count:
                comp_type = ComparisonType.IDENTICAL
                notes = f"Mesmo número de canais: {left_count}"
            else:
                comp_type = ComparisonType.DIFFERENT
                notes = f"Contagem diferente: {left_count} vs {right_count}"
            
            results.append(ComparisonResult(
                field_name=f"io_count_{io_type}",
                comparison_type=comp_type,
                left_value=left_count,
                right_value=right_count,
                severity="info",
                notes=notes
            ))
        
        return results
    
    def compare_equipments(self, equipment_id_1: int, equipment_id_2: int) -> Dict[str, Any]:
        """
        Compara dois equipamentos completamente
        
        Args:
            equipment_id_1: ID do primeiro equipamento
            equipment_id_2: ID do segundo equipamento
            
        Returns:
            Dicionário com resultados completos da comparação
        """
        if not self.conn:
            raise Exception("Conexão com banco não estabelecida")
        
        # Obter resumos dos equipamentos
        eq1_summary = self.get_equipment_summary(equipment_id_1)
        eq2_summary = self.get_equipment_summary(equipment_id_2)
        
        if not eq1_summary or not eq2_summary:
            raise Exception("Um ou ambos equipamentos não encontrados")
        
        comparison_report = {
            'comparison_metadata': {
                'timestamp': datetime.now().isoformat(),
                'equipment_1': eq1_summary.__dict__,
                'equipment_2': eq2_summary.__dict__
            },
            'electrical_comparison': [],
            'protection_comparison': [],
            'io_comparison': [],
            'summary': {
                'total_comparisons': 0,
                'identical': 0,
                'different': 0,
                'missing': 0,
                'critical_differences': 0,
                'warnings': 0
            }
        }
        
        # 1. Comparar configurações elétricas
        eq1_electrical = self.get_electrical_configuration(equipment_id_1)
        eq2_electrical = self.get_electrical_configuration(equipment_id_2)
        electrical_results = self.compare_electrical_configurations(eq1_electrical, eq2_electrical)
        comparison_report['electrical_comparison'] = [r.__dict__ for r in electrical_results]
        
        # 2. Comparar funções de proteção
        eq1_protection = self.get_protection_functions(equipment_id_1)
        eq2_protection = self.get_protection_functions(equipment_id_2)
        protection_results = self.compare_protection_functions(eq1_protection, eq2_protection)
        comparison_report['protection_comparison'] = [r.__dict__ for r in protection_results]
        
        # 3. Comparar configurações I/O
        eq1_io = self.get_io_configuration(equipment_id_1)
        eq2_io = self.get_io_configuration(equipment_id_2)
        io_results = self.compare_io_configurations(eq1_io, eq2_io)
        comparison_report['io_comparison'] = [r.__dict__ for r in io_results]
        
        # 4. Calcular estatísticas resumidas
        all_results = electrical_results + protection_results + io_results
        
        summary = comparison_report['summary']
        summary['total_comparisons'] = len(all_results)
        
        for result in all_results:
            if result.comparison_type == ComparisonType.IDENTICAL:
                summary['identical'] += 1
            elif result.comparison_type == ComparisonType.DIFFERENT:
                summary['different'] += 1
            elif result.comparison_type in [ComparisonType.MISSING_LEFT, ComparisonType.MISSING_RIGHT]:
                summary['missing'] += 1
            
            if result.severity == 'critical':
                summary['critical_differences'] += 1
            elif result.severity == 'warning':
                summary['warnings'] += 1
        
        return comparison_report
    
    def generate_comparison_report(self, comparison_data: Dict[str, Any], format_type: str = "console") -> str:
        """
        Gera relatório formatado da comparação
        
        Args:
            comparison_data: Dados da comparação
            format_type: Tipo do formato (console, json, html)
            
        Returns:
            Relatório formatado
        """
        if format_type == "console":
            return self._generate_console_report(comparison_data)
        elif format_type == "json":
            return json.dumps(comparison_data, indent=2, default=str)
        else:
            raise ValueError(f"Formato não suportado: {format_type}")
    
    def _generate_console_report(self, comparison_data: Dict[str, Any]) -> str:
        """Gera relatório formatado para console"""
        report = []
        
        # Cabeçalho
        report.append("🔬 RELATÓRIO DE COMPARAÇÃO DE CONFIGURAÇÕES")
        report.append("=" * 60)
        
        # Metadados
        metadata = comparison_data['comparison_metadata']
        eq1 = metadata['equipment_1']
        eq2 = metadata['equipment_2']
        
        report.append(f"\n📊 EQUIPAMENTOS COMPARADOS:")
        report.append(f"  🔹 Equipamento 1: {eq1['manufacturer']} {eq1['model_type']}")
        report.append(f"     Tag: {eq1['tag_reference'] or 'N/A'} | Serial: {eq1['serial_number'] or 'N/A'}")
        report.append(f"     Software: {eq1['software_version'] or 'N/A'}")
        
        report.append(f"  🔹 Equipamento 2: {eq2['manufacturer']} {eq2['model_type']}")
        report.append(f"     Tag: {eq2['tag_reference'] or 'N/A'} | Serial: {eq2['serial_number'] or 'N/A'}")
        report.append(f"     Software: {eq2['software_version'] or 'N/A'}")
        
        # Resumo
        summary = comparison_data['summary']
        report.append(f"\n📈 RESUMO DA COMPARAÇÃO:")
        report.append(f"  • Total de comparações: {summary['total_comparisons']}")
        report.append(f"  • Idênticos: {summary['identical']} ✅")
        report.append(f"  • Diferentes: {summary['different']} ⚠️")
        report.append(f"  • Ausentes: {summary['missing']} ❌")
        report.append(f"  • Diferenças críticas: {summary['critical_differences']} 🚨")
        report.append(f"  • Avisos: {summary['warnings']} ⚠️")
        
        # Configurações elétricas
        if comparison_data['electrical_comparison']:
            report.append(f"\n⚡ CONFIGURAÇÕES ELÉTRICAS:")
            for comp in comparison_data['electrical_comparison']:
                if comp['comparison_type'] != 'identical':
                    icon = "🚨" if comp['severity'] == 'critical' else "⚠️" if comp['severity'] == 'warning' else "ℹ️"
                    report.append(f"  {icon} {comp['field_name']}: {comp['notes']}")
        
        # Funções de proteção
        if comparison_data['protection_comparison']:
            report.append(f"\n🛡️ FUNÇÕES DE PROTEÇÃO:")
            for comp in comparison_data['protection_comparison']:
                if comp['comparison_type'] != 'identical':
                    icon = "🚨" if comp['severity'] == 'critical' else "⚠️" if comp['severity'] == 'warning' else "ℹ️"
                    report.append(f"  {icon} {comp['field_name']}: {comp['notes']}")
        
        # I/O
        if comparison_data['io_comparison']:
            report.append(f"\n🔌 CONFIGURAÇÕES I/O:")
            for comp in comparison_data['io_comparison']:
                if comp['comparison_type'] != 'identical':
                    icon = "ℹ️"
                    report.append(f"  {icon} {comp['field_name']}: {comp['notes']}")
        
        report.append(f"\n⏰ Gerado em: {metadata['timestamp']}")
        report.append("=" * 60)
        
        return "\n".join(report)


def main():
    """Função principal para demonstração"""
    # Configuração do banco
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'protecai',
        'password': 'protecai',
        'database': 'protecai_db'
    }
    
    # Criar instância do comparador
    comparator = RelayConfigurationComparator(db_config)
    
    try:
        # Conectar ao banco
        if not comparator.connect():
            print("❌ Falha na conexão com o banco")
            return
        
        print("🔬 DEMONSTRAÇÃO DO COMPARADOR - TODO #6")
        print("=" * 50)
        
        # Comparar os dois equipamentos disponíveis (IDs 3 e 4)
        comparison_result = comparator.compare_equipments(3, 4)
        
        # Gerar relatório
        report = comparator.generate_comparison_report(comparison_result, "console")
        print(report)
        
        # Salvar relatório JSON
        with open('outputs/logs/comparison_report.json', 'w', encoding='utf-8') as f:
            json.dump(comparison_result, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\n💾 Relatório JSON salvo em: outputs/logs/comparison_report.json")
        
    except Exception as e:
        print(f"❌ Erro durante comparação: {e}")
    finally:
        comparator.disconnect()


if __name__ == "__main__":
    main()
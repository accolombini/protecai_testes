"""
🌍 UNIVERSAL GLOSSARY PARSER
============================

Parser universal para processar glossários de relés de QUALQUER fabricante/modelo.
Elimina necessidade de parsers específicos por modelo.

Recursos:
---------
✅ Auto-detecção de fabricante/modelo
✅ Hierarquia de seções (células amarelas)
✅ Processamento de avisos e condicionais
✅ Múltiplos formatos de código (0104:, 02.05:, etc)
✅ Normalização universal
✅ Exportação para PostgreSQL/CSV/Excel

Autor: ProtecAI Team
Data: 06/11/2025
"""

import pandas as pd
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class UniversalParameter:
    """Estrutura universal de parâmetro normalizado"""
    # Identificação
    codigo: str
    nome: str
    valor: str
    
    # Contexto
    fabricante: str
    modelo: str
    tipo_rele: Optional[str] = None
    
    # Hierarquia
    secao_principal: Optional[str] = None
    subsecao: Optional[str] = None
    grupo: Optional[str] = None  # G1, G2, etc
    
    # Metadados
    unidade: Optional[str] = None
    opcoes: Optional[List[str]] = field(default_factory=list)
    condicional: Optional[str] = None
    aviso: Optional[str] = None
    
    # Origem
    aba_origem: str = ""
    linha_origem: int = 0
    coluna_origem: int = 0
    
    # Timestamps
    data_extracao: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return asdict(self)


class UniversalGlossaryParser:
    """
    Parser universal que processa qualquer glossário de relé
    sem necessidade de lógica específica por fabricante/modelo
    """
    
    # Padrões universais de código de parâmetro
    CODE_PATTERNS = [
        r'^([0-9A-F]{4}):\s*(.+)',           # 0104: Frequency
        r'^([0-9]{2}\.[0-9]{2}[A-Z]?):\s*(.+)',  # 02.05A: Setting
        r'^([a-z_]+):\s*(.+)',                # i_nominal: 600
        r'^([a-z_]+)=(.+)',                   # i_base=240
    ]
    
    # Palavras-chave que indicam avisos
    WARNING_KEYWORDS = [
        'Idem', 'Repete', 'caso', 'execeção', 'introduzidos',
        'porem', 'anteriores', 'mesmos', 'nomenclatutras'
    ]
    
    # Padrões de seção (células amarelas)
    SECTION_INDICATORS = [
        'PARAMETERS', 'CONFIGURATION', 'PROTECTION', 'AUTOMAT',
        'SYSTEM DATA', 'CT AND VT', 'CB MONITOR', 'Group',
        'Sepam_', 'Protection'
    ]
    
    def __init__(self, excel_path: str):
        """
        Inicializa parser
        
        Args:
            excel_path: Caminho para arquivo Excel do glossário
        """
        self.excel_path = Path(excel_path)
        self.workbook = pd.ExcelFile(excel_path, engine='openpyxl')
        self.all_parameters: List[UniversalParameter] = []
        
        logger.info(f"✅ Parser inicializado: {self.excel_path.name}")
        logger.info(f"📊 Abas encontradas: {len(self.workbook.sheet_names)}")
    
    def parse_all(self) -> List[UniversalParameter]:
        """
        Processa todas as abas do glossário
        
        Returns:
            Lista de todos os parâmetros normalizados
        """
        logger.info("\n" + "="*80)
        logger.info("🌍 INICIANDO PARSING UNIVERSAL")
        logger.info("="*80)
        
        for sheet_name in self.workbook.sheet_names:
            logger.info(f"\n📋 Processando aba: {sheet_name}")
            params = self.parse_sheet(sheet_name)
            self.all_parameters.extend(params)
            logger.info(f"   ✅ {len(params)} parâmetros extraídos")
        
        logger.info("\n" + "="*80)
        logger.info(f"✅ PARSING COMPLETO: {len(self.all_parameters)} parâmetros totais")
        logger.info("="*80)
        
        return self.all_parameters
    
    def parse_sheet(self, sheet_name: str) -> List[UniversalParameter]:
        """
        Processa uma aba específica
        
        Args:
            sheet_name: Nome da aba
            
        Returns:
            Lista de parâmetros da aba
        """
        # Carregar dados
        df = pd.read_excel(
            self.excel_path,
            sheet_name=sheet_name,
            header=None,
            dtype=str
        )
        
        # Detectar fabricante/modelo
        fabricante, modelo, tipo_rele = self._detect_relay_info(df)
        
        parameters = []
        current_section = None
        current_subsection = None
        current_group = None
        current_warning = None
        
        # Processar linha por linha
        for idx, row in df.iterrows():
            # Detectar seção (célula amarela)
            section_info = self._detect_section(row, idx)
            if section_info:
                current_section = section_info.get('section')
                current_subsection = section_info.get('subsection')
                current_group = section_info.get('group')
                continue
            
            # Detectar aviso
            warning = self._detect_warning(row)
            if warning:
                current_warning = warning
                continue
            
            # Extrair parâmetros
            params = self._extract_parameters_from_row(
                row=row,
                idx=idx,
                fabricante=fabricante,
                modelo=modelo,
                tipo_rele=tipo_rele,
                secao=current_section,
                subsecao=current_subsection,
                grupo=current_group,
                aviso=current_warning,
                aba_origem=sheet_name
            )
            
            parameters.extend(params)
        
        return parameters
    
    def _detect_relay_info(self, df: pd.DataFrame) -> Tuple[str, str, Optional[str]]:
        """
        Detecta fabricante, modelo e tipo de relé
        
        Args:
            df: DataFrame da planilha
            
        Returns:
            (fabricante, modelo, tipo_rele)
        """
        fabricante = "Unknown"
        modelo = "Unknown"
        tipo_rele = None
        
        # Procurar nas primeiras 5 linhas
        for idx in range(min(5, len(df))):
            row = df.iloc[idx]
            
            for cell in row:
                if pd.isna(cell):
                    continue
                    
                cell_str = str(cell).strip()
                
                # Detectar fabricante
                if 'Schneider' in cell_str:
                    fabricante = 'Schneider'
                elif 'GE' in cell_str:
                    fabricante = 'GE'
                elif 'ABB' in cell_str:
                    fabricante = 'ABB'
                elif 'Siemens' in cell_str:
                    fabricante = 'Siemens'
                
                # Detectar modelo
                if 'MiCON' in cell_str or 'MICON' in cell_str:
                    # Extrair modelo completo
                    modelo_match = re.search(r'(MiCON|MICON)\s+([^\s\(]+)', cell_str)
                    if modelo_match:
                        modelo = f"{modelo_match.group(1)} {modelo_match.group(2)}"
                elif 'SEPAM' in cell_str:
                    sepam_match = re.search(r'SEPAM\s+([^\s\(]+)', cell_str)
                    if sepam_match:
                        modelo = f"SEPAM {sepam_match.group(1)}"
                
                # Detectar tipo
                if 'Tensão' in cell_str or 'Voltage' in cell_str:
                    tipo_rele = 'Relé de Tensão'
                elif 'Multifunção' in cell_str or 'Multifunction' in cell_str:
                    tipo_rele = 'Relé de Multifunção'
        
        return fabricante, modelo, tipo_rele
    
    def _detect_section(self, row: pd.Series, idx: int) -> Optional[Dict[str, str]]:
        """
        Detecta se linha contém marcador de seção (célula amarela)
        
        Args:
            row: Linha da planilha
            idx: Índice da linha
            
        Returns:
            Dicionário com informações da seção ou None
        """
        for cell in row:
            if pd.isna(cell):
                continue
            
            cell_str = str(cell).strip()
            
            # Verificar se contém indicador de seção
            for indicator in self.SECTION_INDICATORS:
                if indicator in cell_str:
                    # Extrair grupo se houver (G1, G2, Group 1, etc)
                    group = None
                    if 'G1' in cell_str or 'Group 1' in cell_str:
                        group = 'G1'
                    elif 'G2' in cell_str or 'Group 2' in cell_str:
                        group = 'G2'
                    
                    return {
                        'section': cell_str,
                        'subsection': None,
                        'group': group
                    }
        
        return None
    
    def _detect_warning(self, row: pd.Series) -> Optional[str]:
        """
        Detecta se linha contém aviso importante
        
        Args:
            row: Linha da planilha
            
        Returns:
            Texto do aviso ou None
        """
        for cell in row:
            if pd.isna(cell):
                continue
            
            cell_str = str(cell).strip()
            
            # Verificar palavras-chave de aviso
            for keyword in self.WARNING_KEYWORDS:
                if keyword.lower() in cell_str.lower():
                    return cell_str
        
        return None
    
    def _extract_parameters_from_row(
        self,
        row: pd.Series,
        idx: int,
        fabricante: str,
        modelo: str,
        tipo_rele: Optional[str],
        secao: Optional[str],
        subsecao: Optional[str],
        grupo: Optional[str],
        aviso: Optional[str],
        aba_origem: str
    ) -> List[UniversalParameter]:
        """
        Extrai parâmetros de uma linha
        
        Args:
            row: Linha da planilha
            idx: Índice da linha
            fabricante: Fabricante detectado
            modelo: Modelo detectado
            tipo_rele: Tipo de relé
            secao: Seção atual
            subsecao: Subseção atual
            grupo: Grupo atual (G1/G2)
            aviso: Aviso atual
            aba_origem: Nome da aba
            
        Returns:
            Lista de parâmetros extraídos
        """
        parameters = []
        
        for col_idx, cell in enumerate(row):
            if pd.isna(cell):
                continue
            
            cell_str = str(cell).strip()
            
            # Tentar extrair com cada padrão
            for pattern in self.CODE_PATTERNS:
                match = re.match(pattern, cell_str)
                if match:
                    codigo = match.group(1).strip()
                    resto = match.group(2).strip()
                    
                    # Separar nome e valor
                    nome, valor, unidade, opcoes, condicional = self._parse_parameter_details(resto)
                    
                    # Criar parâmetro
                    param = UniversalParameter(
                        codigo=codigo,
                        nome=nome,
                        valor=valor,
                        fabricante=fabricante,
                        modelo=modelo,
                        tipo_rele=tipo_rele,
                        secao_principal=secao,
                        subsecao=subsecao,
                        grupo=grupo,
                        unidade=unidade,
                        opcoes=opcoes,
                        condicional=condicional,
                        aviso=aviso,
                        aba_origem=aba_origem,
                        linha_origem=idx,
                        coluna_origem=col_idx
                    )
                    
                    parameters.append(param)
                    break
        
        return parameters
    
    def _parse_parameter_details(self, text: str) -> Tuple[str, str, Optional[str], List[str], Optional[str]]:
        """
        Analisa detalhes de um parâmetro
        
        Args:
            text: Texto do parâmetro
            
        Returns:
            (nome, valor, unidade, opcoes, condicional)
        """
        # Padrões comuns
        # Formato: "Nome: Valor Unidade"
        if ':' in text:
            parts = text.split(':', 1)
            nome = parts[0].strip()
            valor_parte = parts[1].strip() if len(parts) > 1 else ""
        else:
            nome = text
            valor_parte = ""
        
        # Extrair valor e unidade
        valor = valor_parte
        unidade = None
        
        # Detectar unidade (Hz, A, V, s, etc)
        unidade_match = re.search(r'(\d+\.?\d*)\s*([A-Za-z]+)$', valor_parte)
        if unidade_match:
            valor = unidade_match.group(1)
            unidade = unidade_match.group(2)
        
        # Detectar opções (YES / NO, Group 1 / Group 2)
        opcoes = []
        if '/' in valor_parte:
            opcoes = [opt.strip() for opt in valor_parte.split('/')]
            valor = opcoes[0] if opcoes else valor_parte
        
        # Detectar condicional
        condicional = None
        if 'caso' in text.lower() or 'if' in text.lower():
            condicional = text
        
        return nome, valor, unidade, opcoes, condicional
    
    def export_to_json(self, output_path: str) -> None:
        """
        Exporta parâmetros para JSON
        
        Args:
            output_path: Caminho do arquivo de saída
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'metadata': {
                'total_parameters': len(self.all_parameters),
                'extraction_date': datetime.now().isoformat(),
                'source_file': str(self.excel_path)
            },
            'parameters': [p.to_dict() for p in self.all_parameters]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ JSON exportado: {output_file}")
    
    def export_to_csv(self, output_path: str) -> None:
        """
        Exporta parâmetros para CSV
        
        Args:
            output_path: Caminho do arquivo de saída
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        df = pd.DataFrame([p.to_dict() for p in self.all_parameters])
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        logger.info(f"✅ CSV exportado: {output_file}")
    
    def export_to_excel(self, output_path: str) -> None:
        """
        Exporta parâmetros para Excel
        
        Args:
            output_path: Caminho do arquivo de saída
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        df = pd.DataFrame([p.to_dict() for p in self.all_parameters])
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Parameters', index=False)
        
        logger.info(f"✅ Excel exportado: {output_file}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Gera estatísticas da extração
        
        Returns:
            Dicionário com estatísticas
        """
        stats = {
            'total_parameters': len(self.all_parameters),
            'by_manufacturer': {},
            'by_model': {},
            'by_section': {},
            'by_group': {},
            'by_sheet': {}
        }
        
        for param in self.all_parameters:
            # Por fabricante
            stats['by_manufacturer'][param.fabricante] = \
                stats['by_manufacturer'].get(param.fabricante, 0) + 1
            
            # Por modelo
            stats['by_model'][param.modelo] = \
                stats['by_model'].get(param.modelo, 0) + 1
            
            # Por seção
            if param.secao_principal:
                stats['by_section'][param.secao_principal] = \
                    stats['by_section'].get(param.secao_principal, 0) + 1
            
            # Por grupo
            if param.grupo:
                stats['by_group'][param.grupo] = \
                    stats['by_group'].get(param.grupo, 0) + 1
            
            # Por aba
            stats['by_sheet'][param.aba_origem] = \
                stats['by_sheet'].get(param.aba_origem, 0) + 1
        
        return stats
    
    def print_statistics(self) -> None:
        """Imprime estatísticas formatadas"""
        stats = self.get_statistics()
        
        print("\n" + "="*80)
        print("📊 ESTATÍSTICAS DA EXTRAÇÃO")
        print("="*80)
        
        print(f"\n📝 Total de Parâmetros: {stats['total_parameters']}")
        
        print("\n🏭 Por Fabricante:")
        for fab, count in sorted(stats['by_manufacturer'].items()):
            print(f"   • {fab}: {count}")
        
        print("\n📦 Por Modelo:")
        for model, count in sorted(stats['by_model'].items()):
            print(f"   • {model}: {count}")
        
        print("\n📁 Por Seção (Top 10):")
        for section, count in sorted(stats['by_section'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   • {section}: {count}")
        
        print("\n🎯 Por Grupo:")
        for group, count in sorted(stats['by_group'].items()):
            print(f"   • {group}: {count}")
        
        print("\n📋 Por Aba:")
        for sheet, count in sorted(stats['by_sheet'].items()):
            print(f"   • {sheet}: {count}")


def main():
    """Função principal para teste"""
    import sys
    
    # Caminho do glossário
    glossary_path = "inputs/glossario/Dados_Glossario_Micon_Sepam.xlsx"
    
    print("="*80)
    print("🌍 UNIVERSAL GLOSSARY PARSER")
    print("="*80)
    print(f"\n📁 Arquivo: {glossary_path}\n")
    
    try:
        # Criar parser
        parser = UniversalGlossaryParser(glossary_path)
        
        # Processar tudo
        parameters = parser.parse_all()
        
        # Mostrar estatísticas
        parser.print_statistics()
        
        # Exportar resultados
        output_base = "outputs/universal_parser"
        parser.export_to_json(f"{output_base}/parameters.json")
        parser.export_to_csv(f"{output_base}/parameters.csv")
        parser.export_to_excel(f"{output_base}/parameters.xlsx")
        
        print("\n" + "="*80)
        print("✅ PARSING UNIVERSAL COMPLETO!")
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

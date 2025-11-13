#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Setup Detector - Identificação de Setup Ativo de Relés
================================================================

Este módulo implementa detecção universal de setup ativo para múltiplos
fabricantes e formatos de relés de proteção.

ESTRATÉGIAS SUPORTADAS:
1. Schneider Easergy (P122, P220, P922) → Detecção de checkboxes visuais
2. GE MiCOM (P143, P241) → Extração direta (todos parâmetros ativos)
3. Schneider SEPAM (S40) → Parser INI (formato chave=valor)

Author: ProtecAI Team
Date: 2025-11-10
Version: 1.0.0
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import fitz  # PyMuPDF
import cv2
import numpy as np
import sys

# Adicionar scripts/ ao path para importar UniversalCheckboxDetector
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

# Tentar importar UniversalCheckboxDetector
try:
    from universal_checkbox_detector import UniversalCheckboxDetector
    CHECKBOX_DETECTOR_AVAILABLE = True
except ImportError as e:
    CHECKBOX_DETECTOR_AVAILABLE = False
    UniversalCheckboxDetector = None

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


class RelayType(Enum):
    """Tipos de relé suportados"""
    EASERGY = "easergy"      # Schneider - usa checkboxes
    MICOM = "micom"          # GE - extração direta
    SEPAM = "sepam"          # Schneider - formato INI
    UNKNOWN = "unknown"


@dataclass
class SetupParameter:
    """Estrutura de dados para parâmetro de setup"""
    code: str
    description: str
    value: str
    unit: str
    is_active: bool          # ← FLAG CRÍTICO!
    confidence: float        # 0.0-1.0 (confiança da detecção)
    detection_method: str    # "checkbox", "direct", "ini_parser"
    page_number: Optional[int] = None
    position: Optional[Tuple[int, int]] = None


class UniversalSetupDetector:
    """
    Detector Universal de Setup Ativo
    
    Detecta automaticamente o tipo de relé e aplica a estratégia
    apropriada para identificar parâmetros ativos.
    """
    
    def __init__(self):
        """Inicializa o detector universal"""
        logger.info("🌍 Inicializando UniversalSetupDetector")
        
        # Padrões de código por tipo
        self.code_patterns = {
            RelayType.EASERGY: re.compile(r'^[0-9A-F]{4}[A-Z]?$', re.IGNORECASE),
            RelayType.MICOM: re.compile(r'^\d{2}\.\d{2}[A-Z]?$', re.IGNORECASE),
            RelayType.SEPAM: re.compile(r'^[a-z_]+$', re.IGNORECASE)
        }
        
        # Verificar disponibilidade do UniversalCheckboxDetector
        # (será instanciado apenas quando necessário, pois precisa do pdf_path)
        self.checkbox_detector_available = CHECKBOX_DETECTOR_AVAILABLE
        if self.checkbox_detector_available:
            logger.info("  ✅ UniversalCheckboxDetector disponível")
        else:
            logger.warning("  ⚠️  UniversalCheckboxDetector não disponível - modo fallback")
    
    def detect_relay_type(self, csv_path: Path) -> RelayType:
        """
        Detecta o tipo de relé baseado no filename E nos códigos dos parâmetros
        
        Args:
            csv_path: Caminho para arquivo CSV normalizado
            
        Returns:
            RelayType identificado
        """
        try:
            # 1. DETECÇÃO POR FILENAME (mais confiável)
            filename_lower = csv_path.name.lower()
            
            if any(model in filename_lower for model in ['p122', 'p220', 'p922']):
                logger.info(f"  🔍 Tipo detectado por filename: easergy")
                return RelayType.EASERGY
            elif any(model in filename_lower for model in ['p143', 'p241']):
                logger.info(f"  🔍 Tipo detectado por filename: micom")
                return RelayType.MICOM
            elif 'sepam' in filename_lower or filename_lower.endswith('.s40') or any(x in filename_lower for x in ['00-mf', '_2016-', '_2024-']):
                logger.info(f"  🔍 Tipo detectado por filename: sepam")
                return RelayType.SEPAM
            
            # 2. DETECÇÃO POR PADRÃO DE CÓDIGOS (fallback)
            df = pd.read_csv(csv_path)
            
            if 'Code' not in df.columns:
                logger.error(f"❌ Arquivo sem coluna 'Code': {csv_path.name}")
                return RelayType.UNKNOWN
            
            # Pegar amostra de 20 códigos não-vazios
            codes = df['Code'].dropna().head(20).tolist()
            
            if not codes:
                return RelayType.UNKNOWN
            
            # Testar cada padrão
            scores = {relay_type: 0 for relay_type in RelayType}
            
            for code in codes:
                code_str = str(code).strip()
                for relay_type, pattern in self.code_patterns.items():
                    if pattern.match(code_str):
                        scores[relay_type] += 1
            
            # Retornar tipo com maior score
            best_type = max(scores, key=scores.get)
            
            if scores[best_type] > 5:  # Threshold: pelo menos 5 matches
                logger.info(f"  🔍 Tipo detectado por padrão: {best_type.value} (score: {scores[best_type]}/20)")
                return best_type
            
            logger.warning(f"  ⚠️  Padrões ambíguos: {scores}")
            return RelayType.UNKNOWN
            
        except Exception as e:
            logger.error(f"❌ Erro ao detectar tipo: {e}")
            return RelayType.UNKNOWN
    
    def detect_active_setup_easergy(
        self, 
        csv_path: Path, 
        pdf_path: Optional[Path] = None
    ) -> List[SetupParameter]:
        """
        Detecta setup ativo para relés Schneider Easergy (com checkboxes)
        
        Estratégia:
        1. Se PDF disponível: usar UniversalCheckboxDetector
        2. Senão: heurística baseada em valores preenchidos
        
        Args:
            csv_path: Arquivo CSV normalizado
            pdf_path: Arquivo PDF original (opcional)
            
        Returns:
            Lista de SetupParameter com is_active=True
        """
        logger.info(f"📘 Detectando setup Easergy: {csv_path.name}")
        
        df = pd.read_csv(csv_path)
        parameters = []
        
        # ESTRATÉGIA 1: Usar checkbox detector se PDF disponível
        if pdf_path and pdf_path.exists() and self.checkbox_detector_available:
            try:
                # Criar instância do detector com o PDF
                checkbox_detector = UniversalCheckboxDetector(str(pdf_path), debug=False)
                
                # Detectar checkboxes em todas as páginas
                checkbox_results = self._detect_checkboxes_all_pages(pdf_path, checkbox_detector)
                
                # Correlacionar com parâmetros do CSV
                parameters = self._correlate_checkboxes_with_params(
                    df, checkbox_results
                )
                
                logger.info(f"  ✅ {len(parameters)} parâmetros ativos (via checkboxes)")
                return parameters
                
            except Exception as e:
                logger.warning(f"  ⚠️  Checkbox detection falhou: {e}, usando fallback")
        
        # ESTRATÉGIA 2: Heurística baseada em valores preenchidos
        for idx, row in df.iterrows():
            value = str(row.get('Value', '')).strip()
            
            # Considerar ativo se:
            # - Tem valor preenchido E não é vazio/placeholder
            is_active = bool(value) and value not in ['', 'nan', 'None', '****']
            
            param = SetupParameter(
                code=str(row.get('Code', '')),
                description=str(row.get('Description', '')),
                value=value,
                unit=str(row.get('unit', '')),
                is_active=is_active,
                confidence=0.7 if is_active else 0.3,  # Confiança média (heurística)
                detection_method='heuristic_value'
            )
            
            if is_active:
                parameters.append(param)
        
        logger.info(f"  ✅ {len(parameters)} parâmetros ativos (via heurística)")
        return parameters
    
    def detect_active_setup_micom(self, csv_path: Path) -> List[SetupParameter]:
        """
        Detecta setup ativo para relés GE MiCOM
        
        Estratégia: TODOS os parâmetros são considerados ativos
        (MiCOM não usa checkboxes, exporta apenas configuração ativa)
        
        Args:
            csv_path: Arquivo CSV normalizado
            
        Returns:
            Lista de SetupParameter (todos com is_active=True)
        """
        logger.info(f"📗 Detectando setup MiCOM: {csv_path.name}")
        
        df = pd.read_csv(csv_path)
        parameters = []
        
        for idx, row in df.iterrows():
            param = SetupParameter(
                code=str(row.get('Code', '')),
                description=str(row.get('Description', '')),
                value=str(row.get('Value', '')),
                unit=str(row.get('unit', '')),
                is_active=True,  # ← TODOS ATIVOS!
                confidence=1.0,   # Confiança máxima
                detection_method='micom_direct'
            )
            parameters.append(param)
        
        logger.info(f"  ✅ {len(parameters)} parâmetros ativos (extração direta)")
        return parameters
    
    def detect_active_setup_sepam(self, csv_path: Path) -> List[SetupParameter]:
        """
        Detecta setup ativo para relés Schneider SEPAM
        
        Estratégia: No arquivo .S40, cada seção [ProtectionXXX] tem múltiplos grupos (_0, _1, _2, _3)
        com um campo activite_X antes de cada grupo. Parâmetros são ativos somente se estiverem
        ENTRE um activite_X=1 e o próximo activite_Y.
        
        Args:
            csv_path: Arquivo CSV normalizado
            
        Returns:
            Lista de SetupParameter com is_active baseado no campo activite
        """
        logger.info(f"📙 Detectando setup SEPAM: {csv_path.name}")
        
        df = pd.read_csv(csv_path)
        
        parameters = []
        active_count = 0
        inactive_count = 0
        config_count = 0
        
        # Estado: estamos dentro de um grupo ativo?
        in_active_group = False
        current_index = None
        
        for idx, row in df.iterrows():
            code = str(row.get('Code', ''))
            description = str(row.get('Description', ''))
            value = str(row.get('Value', ''))
            
            # Detectar linha activite_X
            if code.startswith('activite_'):
                # Extrair índice (último número após _)
                parts = code.split('_')
                if len(parts) >= 2 and parts[-1].isdigit():
                    index = parts[-1]
                    current_index = index
                    in_active_group = (value == '1')
                    logger.debug(f"  🔍 {code} = {value} → grupo {index} {'ATIVO' if in_active_group else 'INATIVO'}")
                
                # Não incluir activite na lista final
                continue
            
            # Determinar status do parâmetro atual
            is_active = False
            confidence = 0.8
            detection_method = 'sepam_config'
            
            # Verificar se tem sufixo _X no código
            parts = code.split('_')
            if len(parts) >= 2 and parts[-1].isdigit():
                param_index = parts[-1]
                
                # Se o índice do parâmetro bate com o grupo atual E está ativo
                if current_index == param_index and in_active_group:
                    is_active = True
                    confidence = 1.0
                    detection_method = 'sepam_activite'
                    active_count += 1
                else:
                    # Índice diferente ou grupo inativo
                    is_active = False
                    confidence = 1.0
                    detection_method = 'sepam_activite'
                    inactive_count += 1
            else:
                # Parâmetro sem índice (configuração geral), marcar como ativo
                is_active = True
                confidence = 0.8
                detection_method = 'sepam_config'
                config_count += 1
            
            param = SetupParameter(
                code=code,
                description=description,
                value=value,
                unit=str(row.get('unit', '')),
                is_active=is_active,
                confidence=confidence,
                detection_method=detection_method
            )
            parameters.append(param)
        
        logger.info(f"  ✅ {active_count} ativos | ❌ {inactive_count} inativos | ⚙️  {config_count} configuração")
        logger.info(f"  📊 Total: {len(parameters)} parâmetros")
        return parameters
    
    def detect_active_setup(
        self, 
        csv_path: Path, 
        pdf_path: Optional[Path] = None
    ) -> List[SetupParameter]:
        """
        Detecta setup ativo usando estratégia apropriada
        
        Este é o método PRINCIPAL que deve ser usado externamente.
        Detecta automaticamente o tipo e aplica a estratégia correta.
        
        Args:
            csv_path: Arquivo CSV normalizado
            pdf_path: Arquivo PDF original (opcional, para checkboxes)
            
        Returns:
            Lista de SetupParameter ativos
        """
        # 1. Detectar tipo de relé
        relay_type = self.detect_relay_type(csv_path)
        
        # 2. Aplicar estratégia apropriada
        if relay_type == RelayType.EASERGY:
            return self.detect_active_setup_easergy(csv_path, pdf_path)
        
        elif relay_type == RelayType.MICOM:
            return self.detect_active_setup_micom(csv_path)
        
        elif relay_type == RelayType.SEPAM:
            return self.detect_active_setup_sepam(csv_path)
        
        else:
            logger.warning(f"⚠️  Tipo desconhecido para {csv_path.name}, usando extração direta")
            # Fallback: considerar todos ativos
            return self.detect_active_setup_micom(csv_path)
    
    def _detect_checkboxes_all_pages(self, pdf_path: Path, checkbox_detector) -> Dict[int, List[Dict]]:
        """
        Detecta checkboxes em todas as páginas do PDF usando pipeline COMPLETO
        
        CRÍTICO: Usa analyze_page() que faz:
        1. Detecta checkboxes
        2. Extrai parâmetros do PDF
        3. Correlaciona espacialmente checkbox → parâmetro
        4. Classifica marcado/vazio (densidade > threshold)
        5. Retorna checkboxes com 'param_code' e 'is_marked'
        
        Args:
            pdf_path: Caminho para PDF
            checkbox_detector: Instância do UniversalCheckboxDetector
            
        Returns:
            Dict[page_num, List[checkbox_data]] onde checkbox_data tem:
            - 'param_code': código do parâmetro correlacionado
            - 'is_marked': boolean (True = checkbox marcado)
            - 'density': densidade interior (0-1)
        """
        if not checkbox_detector:
            return {}
        
        results = {}
        
        try:
            num_pages = len(checkbox_detector.doc)
            
            for page_num in range(num_pages):
                try:
                    # Usar analyze_page() para pipeline COMPLETO
                    # Retorna: {'results': List[checkbox_dict], 'marked': int, ...}
                    analysis = checkbox_detector.analyze_page(
                        page_num + 1,  # 1-based
                        output_dir=None,
                        save_visualization=False
                    )
                    
                    checkboxes = analysis.get('results', [])
                    if checkboxes:
                        results[page_num] = checkboxes
                        marked_count = sum(1 for cb in checkboxes if cb.get('is_marked', False))
                        logger.info(f"  📄 Página {page_num+1}: {len(checkboxes)} checkboxes (☑️ {marked_count} marcados)")
                    else:
                        logger.info(f"  📄 Página {page_num+1}: 0 checkboxes detectados")
                        
                except Exception as e:
                    logger.warning(f"  ⚠️  Erro na página {page_num+1}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar PDF: {e}")
        
        return results
    
    def _correlate_checkboxes_with_params(
        self, 
        df: pd.DataFrame, 
        checkbox_results: Dict[int, List[Dict]]
    ) -> List[SetupParameter]:
        """
        Correlaciona checkboxes detectados com parâmetros do CSV
        
        ESTRATÉGIA CRÍTICA (VIDAS EM RISCO) - CHECKBOXES COMO FONTE PRIMÁRIA:
        
        Prioridade 1 (Confidence 1.0): Checkbox marcado detectado visualmente
        - Parâmetro ATIVO mesmo se não existir no CSV ou sem valor
        - Cria entrada com código do checkbox e descrição "Visual detection only"
        
        Prioridade 2 (Confidence 0.95): Checkbox marcado + valor no CSV
        - Dupla confirmação: visual + textual
        
        Prioridade 3 (Confidence 0.8): Valor preenchido no CSV mas sem checkbox
        - Pode ser parâmetro sem checkbox ou default configurado
        
        Args:
            df: DataFrame com parâmetros do CSV
            checkbox_results: Dict[page_num → List[checkbox_dict]]
                             checkbox_dict tem: 'param_code', 'is_marked', 'density', 'x_pdf', 'y_pdf'
            
        Returns:
            Lista completa de SetupParameter ativos (união de checkboxes + CSV)
        """
        parameters = []
        
        # PASSO 1: Coletar TODOS os checkboxes marcados (fonte primária)
        marked_checkboxes = {}  # {param_code: checkbox_data}
        
        for page_num, checkboxes in checkbox_results.items():
            for cb in checkboxes:
                if cb.get('is_marked', False):
                    param_code = cb.get('param_code', 'UNKNOWN')
                    if param_code not in marked_checkboxes:
                        marked_checkboxes[param_code] = cb
                        logger.debug(f"    ☑️  Página {page_num}: {param_code} marcado (densidade={cb.get('density', 0):.2f})")
        
        logger.info(f"  🎯 Checkboxes marcados: {len(marked_checkboxes)} códigos únicos")
        
        # PASSO 2: Criar set de códigos no CSV para validação
        # CRÍTICO: Normalizar códigos removendo zeros à esquerda para comparação
        csv_codes_map = {}  # {normalized_code: original_code}
        for code in df['Code'].astype(str).str.strip():
            normalized = code.lstrip('0') or '0'  # Remove zeros à esquerda, mas mantém "0" se for só zeros
            csv_codes_map[normalized] = code
        
        logger.info(f"  📋 CSV contém {len(csv_codes_map)} códigos únicos")
        
        # PASSO 3: Processar checkboxes marcados (PRIORIDADE 1 e 2)
        processed_codes = set()
        
        for param_code, cb_data in marked_checkboxes.items():
            # Normalizar código do checkbox para comparação
            normalized_code = param_code.lstrip('0') or '0'
            
            # Buscar no CSV usando código normalizado
            if normalized_code in csv_codes_map:
                # PRIORIDADE 2: Checkbox marcado + existe no CSV
                csv_code = csv_codes_map[normalized_code]
                matching_rows = df[df['Code'].astype(str).str.strip() == csv_code]
            
            if not matching_rows.empty:
                # PRIORIDADE 2: Checkbox marcado + existe no CSV
                row = matching_rows.iloc[0]
                value = str(row.get('Value', '')).strip()
                has_value = bool(value) and value not in ['', 'nan', 'None']
                
                param = SetupParameter(
                    code=param_code,
                    description=str(row.get('Description', '')),
                    value=value if has_value else 'N/A',
                    unit=str(row.get('unit', '')),
                    is_active=True,
                    confidence=0.95 if has_value else 1.0,  # 0.95 com valor, 1.0 sem valor (100% checkbox)
                    detection_method='checkbox_marked_with_csv' if has_value else 'checkbox_marked_only'
                )
                parameters.append(param)
                processed_codes.add(csv_code)  # Usar código do CSV (normalizado)
                
                if not has_value:
                    logger.warning(f"    ⚠️  {param_code}: checkbox marcado mas SEM valor no CSV")
            else:
                # PRIORIDADE 1: Checkbox marcado mas NÃO existe no CSV
                logger.warning(f"    🚨 {param_code}: checkbox marcado mas NÃO ENCONTRADO no CSV!")
                
                param = SetupParameter(
                    code=param_code,
                    description=f"Visual detection only (not in CSV extraction)",
                    value='N/A',
                    unit='',
                    is_active=True,
                    confidence=1.0,  # Confiança MÁXIMA - evidência visual direta
                    detection_method='checkbox_marked_missing_csv'
                )
                parameters.append(param)
                processed_codes.add(param_code)
        
        # PASSO 4: Processar parâmetros do CSV com valores mas SEM checkbox marcado (PRIORIDADE 3)
        for idx, row in df.iterrows():
            code = str(row.get('Code', '')).strip()
            value = str(row.get('Value', '')).strip()
            
            # Já processado via checkbox?
            if code in processed_codes:
                continue
            
            # Tem valor preenchido?
            has_value = bool(value) and value not in ['', 'nan', 'None']
            
            if has_value:
                logger.info(f"    📋 {code}: valor presente mas sem checkbox marcado")
                
                param = SetupParameter(
                    code=code,
                    description=str(row.get('Description', '')),
                    value=value,
                    unit=str(row.get('unit', '')),
                    is_active=True,
                    confidence=0.9,  # Confiança alta - valor presente indica uso ativo
                    detection_method='csv_value_no_checkbox'
                )
                parameters.append(param)
        
        return parameters
    
    def export_active_setup(
        self, 
        parameters: List[SetupParameter], 
        output_path: Path
    ) -> None:
        """
        Exporta parâmetros ativos para CSV
        
        Args:
            parameters: Lista de SetupParameter
            output_path: Caminho de saída
        """
        data = {
            'Code': [p.code for p in parameters],
            'Description': [p.description for p in parameters],
            'Value': [p.value for p in parameters],
            'unit': [p.unit for p in parameters],
            'is_active': [p.is_active for p in parameters],
            'confidence': [p.confidence for p in parameters],
            'detection_method': [p.detection_method for p in parameters]
        }
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
        
        logger.info(f"  💾 Exportado: {output_path.name} ({len(parameters)} params)")


def main():
    """Função de teste"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python universal_setup_detector.py <csv_path> [pdf_path]")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1]).resolve()  # ← ABSOLUTO!
    pdf_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    
    # Se PDF não fornecido, tentar localizar automaticamente
    if not pdf_path:
        # Tentar construir o caminho baseado no nome do CSV
        # Exemplo: "P122 52-MF-02A_2021-03-08_params.csv" → "P122 52-MF-02A_2021-03-08.pdf"
        csv_name = csv_path.stem
        
        # Remover sufixos comuns: _params, _normalized, _active_setup
        for suffix in ['_params', '_normalized', '_active_setup']:
            if csv_name.endswith(suffix):
                csv_name = csv_name[:-len(suffix)]
                break
        
        pdf_name = csv_name + '.pdf'
        
        # Encontrar raiz do projeto
        # CSV está em: <raiz>/outputs/norm_csv/arquivo.csv
        # Precisamos: <raiz>/inputs/pdf/arquivo.pdf
        csv_abs = csv_path.resolve()
        
        # Subir até encontrar a pasta que contém "outputs" e "inputs"
        current = csv_abs.parent
        while current.parent != current:  # Não chegou na raiz do sistema
            if (current / 'inputs').exists() and (current / 'outputs').exists():
                project_root = current
                break
            current = current.parent
        else:
            # Fallback: assumir que está 2 níveis acima de norm_csv
            project_root = csv_abs.parent.parent.parent
        
        potential_pdf = project_root / 'inputs' / 'pdf' / pdf_name
        
        logger.info(f"  🔍 Procurando PDF: {potential_pdf}")
        
        if potential_pdf.exists():
            pdf_path = potential_pdf
            logger.info(f"  📄 PDF localizado: {pdf_path.name}")
        else:
            # Tentar também em inputs/txt/ para SEPAM
            potential_txt = project_root / 'inputs' / 'txt' / (csv_name + '.S40')
            if potential_txt.exists():
                pdf_path = potential_txt
                logger.info(f"  📄 Arquivo SEPAM localizado: {pdf_path.name}")
            else:
                logger.warning(f"  ⚠️  Arquivo fonte não encontrado")
                logger.warning(f"      Tentei: {potential_pdf}")
                logger.warning(f"      E: {potential_txt}")
    
    detector = UniversalSetupDetector()
    
    # Detectar tipo
    relay_type = detector.detect_relay_type(csv_path)
    print(f"\n🔍 Tipo detectado: {relay_type.value}")
    
    # Detectar setup ativo
    parameters = detector.detect_active_setup(csv_path, pdf_path)
    
    print(f"\n📊 RESULTADO:")
    print(f"  Total de parâmetros: {len(parameters)}")
    print(f"  Ativos: {sum(1 for p in parameters if p.is_active)}")
    if len(parameters) > 0:
        print(f"  Confiança média: {sum(p.confidence for p in parameters) / len(parameters):.2f}")
    else:
        print(f"  Confiança média: N/A (nenhum parâmetro detectado)")
    
    # Exportar
    output_path = csv_path.parent / f"{csv_path.stem}_active_setup.csv"
    detector.export_active_setup(parameters, output_path)
    
    print(f"\n✅ Setup ativo exportado para: {output_path}")


if __name__ == '__main__':
    main()

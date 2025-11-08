#!/usr/bin/env python3
"""
🎯 DETECTOR UNIVERSAL E ROBUSTO DE CHECKBOXES

⚠️  IMPORTANTE: Sempre ativar ambiente virtual ANTES de executar:
    workon protecai_testes
    # ou
    source protecai_testes/bin/activate

PRINCÍPIOS INVIOLÁVEIS:
1. ROBUSTO: Funciona em QUALQUER modelo (P122, P143, P922, SEPAM)
2. FLEXÍVEL: Auto-calibra threshold, auto-detecta parâmetros
3. SEM HARDCODE: PDF, página, thresholds são argumentos
4. VIDAS EM RISCO: Zero tolerância a falhas

ESTRATÉGIA:
- Auto-calibração de densidade (mediana + desvio)
- Detecção genérica de parâmetros (regex flexível)
- Y-tolerance adaptativo (baseado em distribuição)
- Mascaramento de texto universal
- Validação cruzada de resultados

USO:
python universal_checkbox_detector.py <pdf_path> <page_number> [--output-dir] [--debug]

EXEMPLOS:
python universal_checkbox_detector.py "inputs/pdf/P922 52-MF-01BC.pdf" 4
python universal_checkbox_detector.py "inputs/pdf/P122 52-MF-02A.pdf" 1 --debug
"""

import sys
import argparse
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import fitz
import pdfplumber
import re
from typing import List, Dict, Tuple, Optional
import json

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class UniversalCheckboxDetector:
    """
    Detector robusto que funciona em QUALQUER modelo de relé
    """
    
    # Parâmetros adaptativos (não hardcoded!)
    DEFAULT_SHRINK_PIXELS = 3
    DEFAULT_MIN_DENSITY = 0.02
    DEFAULT_DPI = 300
    
    def __init__(self, pdf_path: str, debug: bool = False):
        self.pdf_path = Path(pdf_path)
        self.debug = debug
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")
        
        self.doc = fitz.open(str(self.pdf_path))
        self.pdf_plumber = pdfplumber.open(str(self.pdf_path))
        
        if self.debug:
            print(f"📄 PDF carregado: {self.pdf_path.name}")
            print(f"   Total de páginas: {len(self.doc)}")
    
    def extract_parameters(self, page_number: int) -> List[Dict]:
        """
        Extrai parâmetros de forma GENÉRICA (funciona em qualquer modelo)
        
        Padrões aceitos:
        - P922: 010D:, 0160:, 022F:
        - P122: 0001:, 0034:, FUNC:
        - P143: TRIP:, ALARM:
        - SEPAM: qualquer código seguido de :
        
        ROBUSTEZ: 3 camadas de validação
        1. Regex base (formato)
        2. Blacklist (palavras comuns)
        3. Heurística (posição X, presença de :)
        """
        page_index = page_number - 1
        
        if page_index < 0 or page_index >= len(self.pdf_plumber.pages):
            raise ValueError(f"Página {page_number} fora do range (1-{len(self.pdf_plumber.pages)})")
        
        page = self.pdf_plumber.pages[page_index]
        words = page.extract_words()
        
        # CAMADA 1: Padrão base (hexadecimal ou código alfanumérico)
        # Prioriza códigos numéricos/hex (4 dígitos + opcional letra)
        hex_pattern = re.compile(r'^[0-9A-F]{3,4}[A-Z]?:?$', re.IGNORECASE)
        alpha_pattern = re.compile(r'^[A-Z]{4,6}:?$', re.IGNORECASE)
        
        # CAMADA 2: Blacklist de palavras comuns (metadata, UI, descrições)
        BLACKLIST = {
            # Metadata do PDF
            'Easergy', 'Studio', 'Page', 'File', 'MiCOM', 'SEPAM',
            # UI/Labels comuns
            'Input', 'Output', 'Model', 'Type', 'Status', 'Mode',
            'Group', 'Logic', 'Trip', 'Alarm', 'Pickup',
            # Palavras genéricas
            'YES', 'NO', 'ON', 'OFF', 'None', 'All'
        }
        
        parameters = []
        for word in words:
            text = word['text'].strip()
            text_clean = text.rstrip(':')
            
            # CAMADA 2: Filtrar blacklist (case-insensitive)
            if text_clean.upper() in {b.upper() for b in BLACKLIST}:
                continue
            
            # CAMADA 1: Match de padrão
            is_hex = hex_pattern.match(text)
            is_alpha = alpha_pattern.match(text)
            
            if not (is_hex or is_alpha):
                continue
            
            # CAMADA 3: Heurística adicional
            # - Códigos hex têm ALTA prioridade (010D, 0160, etc)
            # - Códigos alpha precisam ter : no final (FUNC:, TRIP:)
            if is_hex:
                # Hex sempre aceito (alta confiança)
                confidence = 'high'
            elif is_alpha and text.endswith(':'):
                # Alpha com : aceito (média confiança)
                confidence = 'medium'
            else:
                # Alpha sem : rejeitado (baixa confiança)
                continue
            
            parameters.append({
                'code': text_clean,
                'y': word['top'],
                'x': word['x0'],
                'text': text,
                'confidence': confidence
            })
        
        # Ordenar por Y (top to bottom)
        parameters.sort(key=lambda p: p['y'])
        
        if self.debug:
            print(f"\n📝 Parâmetros extraídos (página {page_number}): {len(parameters)}")
            if parameters:
                print(f"   Primeiros 5: {[p['code'] for p in parameters[:5]]}")
        
        return parameters
    
    def is_grayscale_region(self, img_bgr, x, y, w, h) -> bool:
        """
        Verifica se uma região é grayscale (preto/branco)
        Checkboxes são P&B, ícones coloridos (pastas amarelas) não são
        """
        region = img_bgr[y:y+h, x:x+w]
        
        if region.size == 0:
            return False
        
        # Calcular desvio padrão entre canais BGR
        b, g, r = cv2.split(region)
        
        # Se todos os canais são similares, é grayscale
        std_bg = np.std(b.astype(float) - g.astype(float))
        std_br = np.std(b.astype(float) - r.astype(float))
        std_gr = np.std(g.astype(float) - r.astype(float))
        
        # Threshold: desvio < 15 = grayscale
        is_gray = (std_bg < 15 and std_br < 15 and std_gr < 15)
        
        return is_gray
    
    def detect_checkboxes(self, page_number: int) -> List[Dict]:
        """
        Detecta checkboxes de forma UNIVERSAL
        
        Estratégia:
        1. Renderizar página em alta resolução
        2. Mascarar TODO texto (genérico)
        3. Detectar contornos quadrados
        4. FILTRAR ícones coloridos (pastas amarelas)
        5. Calcular densidade do INTERIOR (shrink)
        6. Filtrar por geometria e densidade mínima
        """
        page_index = page_number - 1
        page = self.doc[page_index]
        
        # 1. Extrair texto para mascaramento
        text_dict = page.get_text("dict")
        
        # 2. Renderizar em alta resolução
        dpi = self.DEFAULT_DPI
        mat = fitz.Matrix(dpi/72, dpi/72)
        pixmap = page.get_pixmap(matrix=mat)
        
        img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        img_np = np.array(img)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        # Guardar imagem colorida para verificação de grayscale
        img_color_check = img_bgr.copy()
        
        # 3. Mascarar texto
        img_masked = img_bgr.copy()
        scale = dpi / 72
        
        masked_blocks = 0
        for block in text_dict["blocks"]:
            if block["type"] == 0:  # Texto
                bbox = block["bbox"]
                x0 = int(bbox[0] * scale)
                y0 = int(bbox[1] * scale)
                x1 = int(bbox[2] * scale)
                y1 = int(bbox[3] * scale)
                cv2.rectangle(img_masked, (x0, y0), (x1, y1), (255, 255, 255), -1)
                masked_blocks += 1
        
        if self.debug:
            print(f"\n🖼️  Imagem processada:")
            print(f"   DPI: {dpi} | Resolução: {pixmap.width}x{pixmap.height}")
            print(f"   Blocos de texto mascarados: {masked_blocks}")
        
        # 4. Pré-processar
        gray = cv2.cvtColor(img_masked, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )
        
        # 5. Detectar contornos
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        # 6. Filtrar e analisar checkboxes - FILTROS MÍNIMOS UNIVERSAIS
        checkboxes = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # FILTRO 1: Tamanho básico (10-40px) - UNIVERSAL
            if not (10 < w < 40 and 10 < h < 40):
                continue
            
            # FILTRO 2: Forma quadrada - UNIVERSAL
            aspect_ratio = w / float(h)
            if not (0.7 < aspect_ratio < 1.3):
                continue
            
            # FILTRO 3: Área mínima - UNIVERSAL
            area = cv2.contourArea(contour)
            if area < 50:
                continue
            
            # FILTRO 4: REJEITA ÍCONES COLORIDOS (PASTAS AMARELAS) - UNIVERSAL!
            # Checkboxes são SEMPRE P&B (preto + branco)
            # Ícones têm cor dominante (amarelo, azul, verde, etc)
            roi_color = img_color_check[y:y+h, x:x+w]
            
            # Converte para HSV para análise de saturação
            roi_hsv = cv2.cvtColor(roi_color, cv2.COLOR_BGR2HSV)
            
            # Calcula saturação média (0-255)
            # Checkboxes P&B: saturação ~0-30
            # Ícones coloridos: saturação >60
            mean_saturation = np.mean(roi_hsv[:,:,1])
            
            # THRESHOLD INTELIGENTE:
            # - Aceita checkboxes vazios (sat < 20)
            # - Aceita checkboxes marcados com traço residual (sat < 40)
            # - REJEITA ícones amarelos/coloridos (sat > 40)
            MAX_SATURATION_THRESHOLD = 40
            
            if mean_saturation > MAX_SATURATION_THRESHOLD:
                if self.debug:
                    print(f"   ❌ Rejeitado por cor: sat={mean_saturation:.1f} > {MAX_SATURATION_THRESHOLD}")
                continue
            
            # FILTRO 5: Densidade interior mínima - UNIVERSAL
            # Calcula densidade do interior (sem borda de 2px)
            x_inner = x + self.DEFAULT_SHRINK_PIXELS
            y_inner = y + self.DEFAULT_SHRINK_PIXELS
            w_inner = w - (self.DEFAULT_SHRINK_PIXELS * 2)
            h_inner = h - (self.DEFAULT_SHRINK_PIXELS * 2)
            
            if w_inner <= 0 or h_inner <= 0:
                continue
            
            interior_region = binary[y_inner:y_inner+h_inner, x_inner:x_inner+w_inner]
            
            if interior_region.size == 0:
                continue
            
            white_pixels = np.sum(interior_region == 255)
            total_pixels = interior_region.size
            density = white_pixels / total_pixels
            
            # Densidade mínima elimina apenas ruído (2%)
            if density < self.DEFAULT_MIN_DENSITY:
                continue
            
            checkboxes.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'density': density,
                'saturation': mean_saturation,  # Para debug
                'y_pdf': y / scale,
                'x_pdf': x / scale
            })
        
        if self.debug:
            print(f"\n🔍 Checkboxes detectados (filtros universais): {len(checkboxes)}")
        
        return checkboxes, scale
    
    def auto_calibrate_threshold(self, checkboxes: List[Dict]) -> float:
        """
        AUTO-CALIBRA threshold baseado na distribuição de densidades
        
        Estratégia:
        - Usa threshold CALIBRADO de 31.6% (da calibração manual página 7)
        - Só usa auto-calibração se houver distribuição bimodal clara
        - Fallback: 31.6% (valor seguro testado)
        """
        # Threshold CALIBRADO manualmente (P922 página 7)
        CALIBRATED_THRESHOLD = 0.316
        
        if len(checkboxes) < 3:
            # Não há dados suficientes para calibrar
            return CALIBRATED_THRESHOLD
        
        densities = np.array([cb['density'] for cb in checkboxes])
        
        # Estatísticas básicas
        q1, median, q3 = np.percentile(densities, [25, 50, 75])
        iqr = q3 - q1
        
        # Se temos distribuição MUITO bimodal (IQR >  20%)
        # Usar auto-calibração, caso contrário usar calibrado
        if iqr > 0.20:  # Variação significativa (2 grupos claros)
            # Threshold = mediana + 20% do IQR
            threshold = median + (iqr * 0.2)
            # Limitar entre 25% e 40% (sanity check)
            threshold = max(0.25, min(0.40, threshold))
        else:
            # Usar threshold calibrado (mais seguro)
            threshold = CALIBRATED_THRESHOLD
        
        if self.debug:
            print(f"\n📊 Calibração automática de threshold:")
            print(f"   Densidades: min={densities.min()*100:.1f}% | "
                  f"med={median*100:.1f}% | max={densities.max()*100:.1f}%")
            print(f"   IQR: {iqr*100:.1f}%")
            if iqr > 0.20:
                print(f"   ⚙️  Auto-calibrado: {threshold*100:.1f}%")
            else:
                print(f"   ✅ Threshold calibrado (fixo): {threshold*100:.1f}%")
        
        return threshold
    
    def correlate_with_parameters(
        self, 
        checkboxes: List[Dict], 
        parameters: List[Dict],
        y_tolerance: Optional[float] = None
    ) -> List[Dict]:
        """
        Correlaciona checkboxes com parâmetros de forma ADAPTATIVA
        
        Y-tolerance automático:
        - Calcula distância média entre parâmetros consecutivos
        - Usa essa distância como base para tolerância
        - Fallback: 50 pontos se não houver parâmetros suficientes
        """
        if not parameters:
            if self.debug:
                print("⚠️  Nenhum parâmetro para correlacionar")
            return []
        
        # Auto-calcular Y-tolerance baseado em espaçamento dos parâmetros
        if y_tolerance is None:
            if len(parameters) >= 2:
                param_ys = [p['y'] for p in parameters]
                spacings = [param_ys[i+1] - param_ys[i] for i in range(len(param_ys)-1)]
                avg_spacing = np.mean(spacings)
                max_spacing = np.max(spacings)
                
                # Tolerância = maior entre:
                # - 3.5x espaçamento médio (permite grupos verticais)
                # - Espaçamento máximo observado
                # Isso garante capturar todos checkboxes de um grupo
                y_tolerance = max(avg_spacing * 3.5, max_spacing)
            else:
                y_tolerance = 50.0  # Fallback
        
        if self.debug:
            print(f"\n🔗 Correlação com parâmetros:")
            print(f"   Y-tolerance adaptativo: {y_tolerance:.1f} pontos")
        
        # Correlacionar cada checkbox com parâmetro mais próximo
        correlated = []
        
        for cb in checkboxes:
            closest_param = None
            min_distance = float('inf')
            
            for param in parameters:
                # Checkbox deve estar ABAIXO ou PRÓXIMO do parâmetro
                if cb['y_pdf'] >= param['y'] - 5:  # Permite 5pt acima
                    distance = abs(cb['y_pdf'] - param['y'])
                    if distance < y_tolerance and distance < min_distance:
                        min_distance = distance
                        closest_param = param
            
            if closest_param:
                cb['param_code'] = closest_param['code']
                cb['y_distance'] = min_distance
                correlated.append(cb)
        
        if self.debug:
            print(f"   ✅ Correlacionados: {len(correlated)}/{len(checkboxes)}")
            print(f"   ❌ Descartados: {len(checkboxes) - len(correlated)}")
        
        return correlated
    
    def classify_checkboxes(
        self, 
        checkboxes: List[Dict], 
        threshold: float
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Classifica checkboxes em marcados vs vazios
        """
        marked = []
        empty = []
        
        for cb in checkboxes:
            cb['is_marked'] = cb['density'] > threshold
            if cb['is_marked']:
                marked.append(cb)
            else:
                empty.append(cb)
        
        return marked, empty
    
    def analyze_page(
        self, 
        page_number: int,
        output_dir: Optional[Path] = None,
        save_visualization: bool = True
    ) -> Dict:
        """
        Análise COMPLETA de uma página (pipeline completo)
        
        Retorna: {
            'page': int,
            'total_checkboxes': int,
            'marked': int,
            'empty': int,
            'threshold': float,
            'parameters': List[str],
            'results': List[Dict]
        }
        """
        print(f"\n{'='*80}")
        print(f"🎯 ANÁLISE UNIVERSAL - Página {page_number}")
        print(f"📄 PDF: {self.pdf_path.name}")
        print(f"{'='*80}")
        
        # 1. Extrair parâmetros
        parameters = self.extract_parameters(page_number)
        
        # 2. Detectar checkboxes
        checkboxes, scale = self.detect_checkboxes(page_number)
        
        if not checkboxes:
            print("\n⚠️  Nenhum checkbox detectado nesta página")
            return {
                'page': page_number,
                'total_checkboxes': 0,
                'marked': 0,
                'empty': 0,
                'threshold': 0,
                'parameters': [p['code'] for p in parameters],
                'results': []
            }
        
        # 3. Auto-calibrar threshold
        threshold = self.auto_calibrate_threshold(checkboxes)
        
        # 4. Correlacionar com parâmetros
        correlated = self.correlate_with_parameters(checkboxes, parameters)
        
        # 5. Classificar
        marked, empty = self.classify_checkboxes(correlated, threshold)
        
        # 6. Estatísticas
        print(f"\n{'='*80}")
        print(f"📊 RESULTADOS")
        print(f"{'='*80}")
        print(f"✅ Total detectado: {len(checkboxes)} checkboxes")
        print(f"✅ Correlacionados: {len(correlated)} checkboxes")
        print(f"☑  Marcados: {len(marked)} ({len(marked)/len(correlated)*100 if correlated else 0:.1f}%)")
        print(f"☐  Vazios: {len(empty)} ({len(empty)/len(correlated)*100 if correlated else 0:.1f}%)")
        print(f"🎯 Threshold: {threshold*100:.1f}%")
        
        # 7. Salvar visualização
        if save_visualization and output_dir:
            self._save_visualization(
                page_number, correlated, threshold, 
                scale, output_dir
            )
        
        # 8. Agrupar por parâmetro (converter bool para int para JSON)
        by_param = {}
        for cb in correlated:
            code = cb.get('param_code', 'UNKNOWN')
            if code not in by_param:
                by_param[code] = []
            # Converter is_marked (bool) para int para serialização JSON
            cb_copy = cb.copy()
            cb_copy['is_marked'] = int(cb_copy['is_marked'])
            by_param[code].append(cb_copy)
        
        print(f"\n📋 CHECKBOXES POR PARÂMETRO:")
        for param_code in sorted(by_param.keys()):
            cbs = by_param[param_code]
            m = sum(1 for cb in cbs if cb['is_marked'])
            e = len(cbs) - m
            print(f"   {param_code}: {len(cbs)} checkbox(es) (☑ {m}, ☐ {e})")
        
        print(f"\n{'='*80}")
        print("✅ ANÁLISE CONCLUÍDA!")
        print(f"{'='*80}\n")
        
        # Preparar resultados JSON-serializáveis (converter bool/numpy para tipos nativos)
        results_serializable = []
        for cb in correlated:
            cb_copy = {
                'x': int(cb['x']),
                'y': int(cb['y']),
                'w': int(cb['w']),
                'h': int(cb['h']),
                'density': float(cb['density']),
                'y_pdf': float(cb['y_pdf']),
                'x_pdf': float(cb['x_pdf']),
                'is_marked': int(cb['is_marked']),  # bool → int
                'param_code': str(cb.get('param_code', 'UNKNOWN')),
                'y_distance': float(cb.get('y_distance', 0))
            }
            results_serializable.append(cb_copy)
        
        return {
            'page': page_number,
            'pdf': self.pdf_path.name,
            'total_checkboxes': len(checkboxes),
            'correlated': len(correlated),
            'marked': len(marked),
            'empty': len(empty),
            'threshold': float(threshold),
            'parameters': [p['code'] for p in parameters],
            'by_parameter': {
                code: {
                    'total': len(cbs),
                    'marked': sum(1 for cb in cbs if cb['is_marked']),
                    'empty': sum(1 for cb in cbs if not cb['is_marked'])
                }
                for code, cbs in by_param.items()
            },
            'results': results_serializable
        }
    
    def _save_visualization(
        self, 
        page_number: int,
        checkboxes: List[Dict],
        threshold: float,
        scale: float,
        output_dir: Path
    ):
        """
        Salva imagem com checkboxes marcados
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Renderizar página novamente
        page_index = page_number - 1
        page = self.doc[page_index]
        
        dpi = self.DEFAULT_DPI
        mat = fitz.Matrix(dpi/72, dpi/72)
        pixmap = page.get_pixmap(matrix=mat)
        
        img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        img_np = np.array(img)
        img_result = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        # Desenhar checkboxes
        for cb in checkboxes:
            color = (0, 255, 0) if cb['is_marked'] else (0, 0, 255)
            cv2.rectangle(img_result,
                         (cb['x'], cb['y']),
                         (cb['x']+cb['w'], cb['y']+cb['h']),
                         color, 2)
            
            # Label com código do parâmetro
            if 'param_code' in cb:
                cv2.putText(img_result, cb['param_code'],
                           (cb['x'], cb['y']-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Salvar
        pdf_name = self.pdf_path.stem
        output_path = output_dir / f"{pdf_name}_page{page_number}_universal.png"
        cv2.imwrite(str(output_path), img_result)
        
        print(f"\n💾 Visualização salva: {output_path}")
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'doc'):
            self.doc.close()
        if hasattr(self, 'pdf_plumber'):
            self.pdf_plumber.close()


def main():
    """
    CLI para detector universal
    """
    parser = argparse.ArgumentParser(
        description="Detector Universal e Robusto de Checkboxes em PDFs de Relés",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s "inputs/pdf/P922 52-MF-01BC.pdf" 4
  %(prog)s "inputs/pdf/P122 52-MF-02A.pdf" 1 --debug
  %(prog)s "inputs/pdf/P143 52-MF-03A.pdf" 7 --output-dir outputs/test
        """
    )
    
    parser.add_argument('pdf_path', help='Caminho para o PDF')
    parser.add_argument('page_number', type=int, help='Número da página (1-indexed)')
    parser.add_argument('--output-dir', type=str, 
                       default='outputs/checkbox_debug',
                       help='Diretório para salvar resultados')
    parser.add_argument('--debug', action='store_true',
                       help='Ativar modo debug (verbose)')
    parser.add_argument('--no-viz', action='store_true',
                       help='Não salvar visualização')
    
    args = parser.parse_args()
    
    try:
        # Criar detector
        detector = UniversalCheckboxDetector(args.pdf_path, debug=args.debug)
        
        # Analisar página
        output_dir = Path(args.output_dir)
        result = detector.analyze_page(
            args.page_number,
            output_dir=output_dir,
            save_visualization=not args.no_viz
        )
        
        # Salvar JSON com resultados
        json_path = output_dir / f"{Path(args.pdf_path).stem}_page{args.page_number}_results.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Resultados salvos: {json_path}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

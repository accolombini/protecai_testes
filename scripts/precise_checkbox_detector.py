#!/usr/bin/env python3
"""
DETECTOR PRECISO DE CHECKBOXES COM OPENCV
==========================================
OBJETIVO: Detectar APENAS checkboxes marcados (☒) via análise de formas geométricas
ESTRATÉGIA:
  1. Detectar quadrados pequenos (10-30px) via contornos
  2. Verificar se há pixels escuros cruzados (X) dentro do quadrado
  3. Extrair texto à direita do checkbox usando Tesseract
"""

import cv2
import numpy as np
from pdf2image import convert_from_path
from pathlib import Path
import pytesseract
from typing import List, Dict, Tuple
import pandas as pd

# Configuração
INPUT_PDF_DIR = Path("inputs/pdf")
OUTPUT_DIR = Path("outputs/checkbox_analysis")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

class PreciseCheckboxDetector:
    """Detector preciso de checkboxes marcados usando análise geométrica"""
    
    def __init__(self, min_size=8, max_size=35):
        """
        Args:
            min_size: Tamanho mínimo do checkbox em pixels (default: 8px)
            max_size: Tamanho máximo do checkbox em pixels (default: 35px)
        """
        self.min_size = min_size
        self.max_size = max_size
        
    def detect_checkboxes_in_image(self, image: np.ndarray) -> List[Dict]:
        """
        Detecta checkboxes marcados em uma imagem usando OpenCV
        
        Returns:
            Lista de dicts com {x, y, width, height, is_checked, text}
        """
        # Converter para escala de cinza
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Binarização adaptativa para detectar bordas
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Detectar contornos
        contours, _ = cv2.findContours(
            binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        
        checkboxes = []
        
        for contour in contours:
            # Obter retângulo delimitador
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filtrar por tamanho (checkboxes são pequenos e quadrados)
            if not (self.min_size <= w <= self.max_size and 
                    self.min_size <= h <= self.max_size):
                continue
            
            # Verificar se é aproximadamente quadrado (razão aspecto ~1.0)
            aspect_ratio = w / float(h)
            if not (0.7 <= aspect_ratio <= 1.3):
                continue
            
            # Verificar se é realmente um quadrado (4 vértices)
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
            if len(approx) < 4 or len(approx) > 6:  # Flexibilidade para quadrados imperfeitos
                continue
            
            # Extrair região do checkbox
            checkbox_roi = binary[y:y+h, x:x+w]
            
            # Verificar se há um "X" dentro (pixels escuros formando diagonais)
            is_checked = self._has_x_mark(checkbox_roi)
            
            if is_checked:
                # Extrair texto à direita do checkbox
                text_roi = image[y:y+h, x+w:x+w+300]  # 300px à direita
                text = self._extract_text_from_roi(text_roi)
                
                checkboxes.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'is_checked': True,
                    'text': text.strip()
                })
        
        return checkboxes
    
    def _has_x_mark(self, checkbox_roi: np.ndarray) -> bool:
        """
        Verifica se há um "X" dentro do checkbox
        
        Estratégia:
        - Contar pixels escuros nas diagonais
        - Se > 40% dos pixels das diagonais são escuros → X marcado
        """
        if checkbox_roi.size == 0:
            return False
        
        h, w = checkbox_roi.shape
        
        # Extrair diagonais
        diagonal1 = np.diagonal(checkbox_roi)
        diagonal2 = np.diagonal(np.fliplr(checkbox_roi))
        
        # Contar pixels escuros (valor > 127 após binarização invertida)
        dark_pixels_d1 = np.sum(diagonal1 > 127)
        dark_pixels_d2 = np.sum(diagonal2 > 127)
        
        total_diagonal_pixels = len(diagonal1) + len(diagonal2)
        dark_ratio = (dark_pixels_d1 + dark_pixels_d2) / total_diagonal_pixels
        
        # Se mais de 40% das diagonais são escuras → checkbox marcado
        return dark_ratio > 0.4
    
    def _extract_text_from_roi(self, roi: np.ndarray) -> str:
        """Extrai texto de uma região usando Tesseract"""
        if roi.size == 0:
            return ""
        
        try:
            # Configuração Tesseract: apenas texto de linha única
            config = '--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:.-_<>/ '
            text = pytesseract.image_to_string(roi, config=config)
            return text.strip()
        except Exception:
            return ""


def analyze_single_pdf(pdf_path: Path, max_pages: int = 5) -> pd.DataFrame:
    """
    Analisa um PDF e retorna DataFrame com checkboxes detectados
    
    Args:
        pdf_path: Caminho do PDF
        max_pages: Número máximo de páginas para processar (teste inicial)
    """
    print(f"\n{'='*80}")
    print(f"📄 ANALISANDO: {pdf_path.name}")
    print(f"{'='*80}")
    
    # Converter PDF para imagens
    print(f"🔄 Convertendo PDF → Imagens (300 DPI)...")
    images = convert_from_path(str(pdf_path), dpi=300, first_page=1, last_page=max_pages)
    print(f"   ✅ {len(images)} páginas convertidas")
    
    detector = PreciseCheckboxDetector(min_size=8, max_size=35)
    all_checkboxes = []
    
    for page_num, image in enumerate(images, 1):
        print(f"   Página {page_num}: Detectando checkboxes...")
        
        # Converter PIL Image → numpy array
        img_array = np.array(image)
        
        # Detectar checkboxes
        checkboxes = detector.detect_checkboxes_in_image(img_array)
        
        # Adicionar número da página
        for cb in checkboxes:
            cb['page'] = page_num
        
        all_checkboxes.extend(checkboxes)
        print(f"      ✅ {len(checkboxes)} checkboxes marcados detectados")
    
    # Converter para DataFrame
    if not all_checkboxes:
        print("⚠️  Nenhum checkbox marcado detectado!")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_checkboxes)
    print(f"\n✅ TOTAL: {len(df)} checkboxes marcados em {len(images)} páginas")
    print(f"   Média: {len(df)/len(images):.1f} checkboxes/página")
    
    return df


def main():
    """Testa o detector em um PDF de exemplo"""
    print("\n" + "="*80)
    print("🔬 DETECTOR PRECISO DE CHECKBOXES - TESTE")
    print("="*80)
    
    # Pegar primeiro PDF P122
    pdf_files = sorted(INPUT_PDF_DIR.glob("P122*.pdf"))
    if not pdf_files:
        print("❌ Nenhum PDF P122 encontrado!")
        return
    
    test_pdf = pdf_files[0]
    
    # Analisar primeiras 5 páginas
    df = analyze_single_pdf(test_pdf, max_pages=5)
    
    if df.empty:
        print("\n❌ FALHA: Nenhum checkbox detectado")
        return
    
    # Salvar resultados
    output_csv = OUTPUT_DIR / f"{test_pdf.stem}_checkboxes.csv"
    df.to_csv(output_csv, index=False)
    print(f"\n💾 Resultados salvos: {output_csv}")
    
    # Exibir amostra
    print(f"\n📋 AMOSTRA DOS CHECKBOXES DETECTADOS:")
    print("="*80)
    for idx, row in df.head(20).iterrows():
        print(f"Pág {row['page']}: [{row['x']},{row['y']}] {row['width']}x{row['height']}px → '{row['text']}'")
    
    print(f"\n✅ SUCESSO! Total de checkboxes: {len(df)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
EXTRATOR PRECISO DE PARÂMETROS COM CORRELAÇÃO Y-COORDINATE
============================================================
Versão ROBUSTA que corrige o problema de texto embaralhado.

ESTRATÉGIA:
1. Pré-processar PDF com melhoria de qualidade (sharpening, denoising)
2. Detectar checkboxes por densidade (30% pixels brancos = marcado)
3. Extrair TODOS os parâmetros da página (regex linha por linha)
4. Correlacionar checkboxes com parâmetros por coordenada Y
5. Marcar is_active = TRUE onde há checkbox marcado

RESULTADO ESPERADO:
0123 | CT Primary | 1          | TRUE   ☑
0124 | CT Secondary | 5        | TRUE   ☑
0125 | VT Primary | 50000      | TRUE   ☑
0126 | VT Secondary |           | FALSE  ☐
"""

import re
import cv2
import numpy as np
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
from dataclasses import dataclass

@dataclass
class ParameterLine:
    """Representa uma linha de parâmetro extraída"""
    code: str
    description: str
    value: str
    y_coordinate: float  # Coordenada Y na página (DPI 72)
    x_start: float       # Início do texto em X
    confidence: float    # Confiança da extração (0.0-1.0)

@dataclass
class Checkbox:
    """Representa um checkbox detectado"""
    x: int
    y: int
    width: int
    height: int
    is_marked: bool      # TRUE se checkbox tem X (☑)
    density: float       # Densidade de pixels brancos (0.0-1.0)

class PreciseParameterExtractor:
    """
    Extrator preciso com correlação Y-coordinate
    """
    
    # Regex para detectar linhas de parâmetros Easergy
    # Captura: 0104, 010A, 0123A, etc (4 dígitos OU 3 dígitos + letra)
    EASERGY_PATTERN = re.compile(r'^(\d{3,4}[A-Z]?):\s*(.+?)(?::\s*(.+))?$', re.MULTILINE)
    
    # Parâmetros de detecção de checkbox
    CHECKBOX_MIN_SIZE = 10
    CHECKBOX_MAX_SIZE = 40
    CHECKBOX_ASPECT_RATIO_MIN = 0.7
    CHECKBOX_ASPECT_RATIO_MAX = 1.3
    CHECKBOX_MIN_AREA = 50
    CHECKBOX_MARKED_THRESHOLD = 0.37  # 37% - AJUSTADO após análise de falsos positivos
    # Calibração: Página 4 (5 marcados: 38.3%-54.1%) + Página 7 (2 marcados: 41.8%-55.1%, 3 vazios: 0.0%-21.4%)
    # PROBLEMA: Threshold 31.6% capturava checkboxes vazios com ruído (33-34%)
    # SOLUÇÃO: Aumentado para 37% - logo abaixo do mínimo marcado real (38.3%)
    # Separação: 15.6% entre max_vazio_ruído(34%) e novo threshold(37%)
    
    # Tolerância para correlação Y (pixels)
    Y_TOLERANCE = 8  # ±8 pixels de tolerância
    
    def __init__(self):
        """Inicializa extrator"""
        pass
    
    def enhance_pdf_quality(self, image: np.ndarray) -> np.ndarray:
        """
        ETAPA 1: Melhora qualidade da imagem do PDF
        
        Aplicações:
        - Sharpening: realça bordas e texto
        - Denoising: remove ruído mantendo detalhes
        - Contrast enhancement: melhora contraste
        
        Args:
            image: Imagem em escala de cinza
            
        Returns:
            Imagem processada com melhor qualidade
        """
        # 1. Denoising bilateral (remove ruído preservando bordas)
        denoised = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        
        # 2. Sharpening (realça texto e checkboxes)
        kernel_sharpen = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ])
        sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
        
        # 3. Contrast enhancement com CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(sharpened)
        
        return enhanced
    
    def detect_checkboxes(self, image: np.ndarray) -> List[Checkbox]:
        """
        ETAPA 2: Detecta checkboxes por densidade de pixels
        
        Algoritmo:
        - Adaptive thresholding para binarização
        - Detecção de contornos
        - Filtro por tamanho e aspect ratio
        - Cálculo de densidade de pixels brancos
        - Threshold: 30% pixels brancos = checkbox marcado ☑
        
        Args:
            image: Imagem em escala de cinza (JÁ MELHORADA)
            
        Returns:
            Lista de checkboxes detectados com status (marcado/vazio)
        """
        # Binarização adaptativa
        binary = cv2.adaptiveThreshold(
            image, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 
            11, 2
        )
        
        # Detecção de contornos
        contours, _ = cv2.findContours(
            binary, 
            cv2.RETR_LIST, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        checkboxes = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filtro 1: Tamanho (10-40 pixels)
            if not (self.CHECKBOX_MIN_SIZE < w < self.CHECKBOX_MAX_SIZE and 
                    self.CHECKBOX_MIN_SIZE < h < self.CHECKBOX_MAX_SIZE):
                continue
            
            # Filtro 2: Aspect ratio (quadrado ~1.0)
            aspect_ratio = w / float(h)
            if not (self.CHECKBOX_ASPECT_RATIO_MIN < aspect_ratio < self.CHECKBOX_ASPECT_RATIO_MAX):
                continue
            
            # Filtro 3: Área mínima
            if cv2.contourArea(contour) < self.CHECKBOX_MIN_AREA:
                continue
            
            # Cálculo de densidade
            checkbox_region = binary[y:y+h, x:x+w]
            white_pixels = np.sum(checkbox_region == 255)
            total_pixels = w * h
            density = white_pixels / total_pixels
            
            # Determinar se está marcado (acima do threshold calibrado)
            is_marked = density > self.CHECKBOX_MARKED_THRESHOLD
            
            checkboxes.append(Checkbox(
                x=x, y=y, width=w, height=h,
                is_marked=is_marked,
                density=density
            ))
        
        return checkboxes
    
    def extract_parameter_lines(self, page: fitz.Page) -> List[ParameterLine]:
        """
        ETAPA 3: Extrai TODAS as linhas de parâmetros (regex linha por linha)
        
        Extrai:
        - Code (4 dígitos + letra opcional)
        - Description (nome do parâmetro)
        - Value (valor configurado, pode ser vazio)
        - Y-coordinate (posição vertical na página)
        
        Args:
            page: Página do PDF (PyMuPDF)
            
        Returns:
            Lista de linhas de parâmetros com coordenadas Y
        """
        text_dict = page.get_text("dict")
        lines = []
        
        for block in text_dict["blocks"]:
            if block["type"] != 0:  # Apenas blocos de texto
                continue
            
            for line in block["lines"]:
                # Extrair texto completo da linha
                line_text = "".join([span["text"] for span in line["spans"]])
                
                # Y-coordinate (média das spans)
                y_coords = [span["bbox"][1] for span in line["spans"]]  # bbox[1] = y0
                y_avg = sum(y_coords) / len(y_coords) if y_coords else 0
                
                # X-coordinate (início da linha)
                x_start = line["spans"][0]["bbox"][0] if line["spans"] else 0
                
                # Tentar fazer match com regex
                match = self.EASERGY_PATTERN.match(line_text.strip())
                
                if match:
                    code = match.group(1)  # Ex: 0123, 010A
                    description = match.group(2).strip() if match.group(2) else ""
                    value = match.group(3).strip() if match.group(3) else ""
                    
                    # Calcular confiança (1.0 = match perfeito)
                    confidence = 1.0 if match.group(3) else 0.9
                    
                    lines.append(ParameterLine(
                        code=code,
                        description=description,
                        value=value,
                        y_coordinate=y_avg,
                        x_start=x_start,
                        confidence=confidence
                    ))
        
        return lines
    
    def correlate_checkboxes_with_lines(
        self, 
        checkboxes: List[Checkbox], 
        lines: List[ParameterLine],
        dpi_scale: float = 300/72
    ) -> List[Dict]:
        """
        ETAPA 4: Correlaciona checkboxes com linhas de parâmetros por Y-coordinate
        
        Algoritmo:
        1. Converte Y do checkbox (DPI 300) para Y da linha (DPI 72)
        2. Para cada linha, busca checkbox na mesma altura (±8px)
        3. Se encontrou checkbox marcado → is_active = TRUE
        4. Se não encontrou ou checkbox vazio → is_active = FALSE
        
        Args:
            checkboxes: Lista de checkboxes detectados (coordenadas em DPI 300)
            lines: Lista de linhas de parâmetros (coordenadas em DPI 72)
            dpi_scale: Fator de conversão (300/72 = 4.166)
            
        Returns:
            Lista de dicts com code, description, value, is_active
        """
        results = []
        
        for line in lines:
            # Buscar checkbox na mesma linha (Y-coordinate)
            line_y = line.y_coordinate  # Já está em DPI 72
            
            matched_checkbox = None
            min_distance = float('inf')
            
            for checkbox in checkboxes:
                # Converter Y do checkbox (DPI 300) para DPI 72
                checkbox_y_72 = checkbox.y / dpi_scale
                
                # Calcular distância
                distance = abs(checkbox_y_72 - line_y)
                
                # Se está dentro da tolerância E é a mais próxima
                if distance < self.Y_TOLERANCE and distance < min_distance:
                    matched_checkbox = checkbox
                    min_distance = distance
            
            # Determinar is_active
            is_active = matched_checkbox is not None and matched_checkbox.is_marked
            
            results.append({
                'Code': line.code,
                'Description': line.description,
                'Value': line.value,
                'is_active': is_active,
                'confidence': line.confidence,
                'y_coordinate': line.y_coordinate,
                'checkbox_density': matched_checkbox.density if matched_checkbox else 0.0
            })
        
        return results
    
    def extract_from_pdf(self, pdf_path: Path) -> pd.DataFrame:
        """
        PIPELINE COMPLETO: Extrai parâmetros de PDF Easergy com checkboxes
        
        Pipeline:
        1. Abrir PDF e processar cada página
        2. Melhorar qualidade da imagem (enhance_pdf_quality)
        3. Detectar checkboxes (detect_checkboxes)
        4. Extrair linhas de parâmetros (extract_parameter_lines)
        5. Correlacionar checkboxes com linhas (correlate_checkboxes_with_lines)
        6. Consolidar resultados em DataFrame
        
        Args:
            pdf_path: Caminho do arquivo PDF
            
        Returns:
            DataFrame com colunas: Code, Description, Value, is_active, confidence
        """
        doc = fitz.open(pdf_path)
        all_results = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Renderizar página em alta resolução (300 DPI)
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            # Converter para grayscale
            if img.shape[2] == 4:  # RGBA
                gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
            elif img.shape[2] == 3:  # RGB
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else:
                gray = img
            
            # ETAPA 1: Melhorar qualidade
            enhanced = self.enhance_pdf_quality(gray)
            
            # ETAPA 2: Detectar checkboxes
            checkboxes = self.detect_checkboxes(enhanced)
            
            # ETAPA 3: Extrair linhas de parâmetros
            lines = self.extract_parameter_lines(page)
            
            # ETAPA 4: Correlacionar checkboxes com linhas
            page_results = self.correlate_checkboxes_with_lines(checkboxes, lines)
            
            all_results.extend(page_results)
        
        doc.close()
        
        # Converter para DataFrame
        df = pd.DataFrame(all_results)
        
        # Remover duplicatas (mesmo código)
        if not df.empty:
            df = df.drop_duplicates(subset=['Code'], keep='first')
            df = df.sort_values('Code').reset_index(drop=True)
        
        return df

def main():
    """Teste do extrator preciso"""
    extractor = PreciseParameterExtractor()
    
    pdf_path = Path(__file__).parent.parent / "inputs/pdf/P922 52-MF-01BC.pdf"
    
    print("=" * 80)
    print("🎯 EXTRATOR PRECISO COM CORRELAÇÃO Y-COORDINATE")
    print("=" * 80)
    print(f"📄 Arquivo: {pdf_path.name}")
    print()
    
    df = extractor.extract_from_pdf(pdf_path)
    
    print(f"✅ Total extraído: {len(df)} parâmetros")
    print(f"☑  Ativos (is_active=TRUE): {df['is_active'].sum()}")
    print(f"☐  Inativos (is_active=FALSE): {(~df['is_active']).sum()}")
    print()
    
    print("📌 Primeiros 20 parâmetros:")
    print("-" * 80)
    for _, row in df.head(20).iterrows():
        code = str(row['Code']).ljust(6)
        desc = str(row['Description'])[:35].ljust(35)
        value = str(row['Value'])[:20].ljust(20)
        status = "☑ ATIVO" if row['is_active'] else "☐ INATIVO"
        print(f"{code} | {desc} | {value} | {status}")
    
    # Salvar resultado
    output_path = Path(__file__).parent.parent / "outputs/test_results/p922_precise_extraction.csv"
    output_path.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(output_path, index=False, encoding='utf-8')
    print()
    print(f"💾 Resultado salvo em: {output_path}")

if __name__ == "__main__":
    main()

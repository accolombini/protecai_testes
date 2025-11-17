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
    Y_TOLERANCE = 25  # ±25 pixels de tolerância (ajustado após debug: menor distância real = 19.7px)
    
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
    
    def detect_checkboxes(self, page: fitz.Page, dpi: int = 300) -> List[Checkbox]:
        """
        ETAPA 2: Detecta checkboxes usando método VALIDADO (universal_checkbox_detector.py)
        
        ESTRATÉGIA VALIDADA (100% precisão P922, 42 checkboxes P122 página 1):
        1. Renderizar página em alta resolução
        2. **MASCARAR TODO O TEXTO** (crítico! elimina 229 falsos positivos)
        3. Detectar contornos quadrados
        4. FILTRAR ícones coloridos via saturação HSV
        5. Calcular densidade do interior (shrink)
        6. Filtrar por geometria e densidade mínima
        
        Args:
            page: Página PyMuPDF para processar
            dpi: Resolução de renderização (default: 300)
            
        Returns:
            Lista de checkboxes detectados com status (marcado/vazio)
        """
        # 1. Extrair texto para mascaramento
        text_dict = page.get_text("dict")
        
        # 2. Renderizar em alta resolução
        mat = fitz.Matrix(dpi/72, dpi/72)
        pixmap = page.get_pixmap(matrix=mat)
        
        # Converter pixmap para numpy array
        img_np = np.frombuffer(pixmap.samples, dtype=np.uint8)
        img_np = img_np.reshape(pixmap.height, pixmap.width, pixmap.n)
        
        # Converter para BGR
        if pixmap.n == 4:  # RGBA
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else:  # RGB
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        # Guardar imagem colorida para filtro HSV
        img_color = img_bgr.copy()
        
        # 3. MASCARAR TODO O TEXTO (crítico!)
        img_masked = img_bgr.copy()
        scale = dpi / 72
        
        for block in text_dict["blocks"]:
            if block["type"] == 0:  # Bloco de texto
                bbox = block["bbox"]
                x0 = int(bbox[0] * scale)
                y0 = int(bbox[1] * scale)
                x1 = int(bbox[2] * scale)
                y1 = int(bbox[3] * scale)
                # Pintar de branco (mascara o texto)
                cv2.rectangle(img_masked, (x0, y0), (x1, y1), (255, 255, 255), -1)
        
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
        
        # 6. Filtrar e analisar checkboxes - FILTROS UNIVERSAIS
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
            
            # FILTRO 4: REJEITA ÍCONES COLORIDOS (saturação HSV)
            # Checkboxes P&B: saturação ~0-30
            # Ícones coloridos: saturação >60
            roi_color = img_color[y:y+h, x:x+w]
            if roi_color.size > 0:
                roi_hsv = cv2.cvtColor(roi_color, cv2.COLOR_BGR2HSV)
                mean_saturation = np.mean(roi_hsv[:,:,1])
                
                MAX_SATURATION_THRESHOLD = 40
                if mean_saturation > MAX_SATURATION_THRESHOLD:
                    continue  # Rejeita ícone colorido
            
            # FILTRO 5: Densidade interior mínima
            shrink = 3
            x_inner = x + shrink
            y_inner = y + shrink
            w_inner = w - (shrink * 2)
            h_inner = h - (shrink * 2)
            
            if w_inner <= 0 or h_inner <= 0:
                continue
            
            interior_region = binary[y_inner:y_inner+h_inner, x_inner:x_inner+w_inner]
            
            if interior_region.size == 0:
                continue
            
            white_pixels = np.sum(interior_region == 255)
            total_pixels = interior_region.size
            density = white_pixels / total_pixels if total_pixels > 0 else 0
            
            # Densidade mínima elimina apenas ruído (2%)
            if density < 0.02:
                continue
            
            # Determinar se está marcado (threshold calibrado: 31.6%)
            is_marked = density > 0.316
            
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
    
    def extract_text_near_checkbox(
        self,
        page: fitz.Page,
        checkbox: Checkbox,
        dpi_scale: float = 300/72
    ) -> str:
        """
        Extrai texto que está À DIREITA de um checkbox marcado
        
        Para LED 5, captura "tI>", "tI>>", etc que aparecem ao lado do checkbox
        
        Args:
            page: Página do PDF
            checkbox: Checkbox detectado
            dpi_scale: Fator de conversão DPI (300/72)
            
        Returns:
            Texto encontrado à direita do checkbox
        """
        # Converter coordenadas do checkbox para DPI 72
        x_72 = checkbox.x / dpi_scale
        y_72 = checkbox.y / dpi_scale
        w_72 = checkbox.width / dpi_scale
        h_72 = checkbox.height / dpi_scale
        
        # Região de busca: AMPLIADA para capturar texto que pode estar à esquerda
        # Texto "tI>>" pode estar ANTES do checkbox, não depois!
        search_rect = fitz.Rect(
            x_72 - 30,           # início: 30px ANTES do checkbox (pegar texto à esquerda)
            y_72 - 5,            # topo: 5px acima
            x_72 + w_72 + 60,   # fim: 60px à direita
            y_72 + h_72 + 5     # base: 5px abaixo
        )
        
        # Extrair texto nesta região
        words = page.get_text("words", clip=search_rect)
        
        if not words:
            return ""
        
        # Pegar palavras à direita e procurar por padrões de proteção
        # words formato: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        words_sorted = sorted(words, key=lambda w: w[0])  # ordenar por X
        
        if not words_sorted:
            return ""
        
        # DEBUG: Ver todas as palavras capturadas
        # words_texts = [w[4] for w in words_sorted]
        # if words_texts:  # Só printar se houver palavras
        #     checkbox_y = checkbox.y / dpi_scale
        #     print(f"  Checkbox Y={checkbox_y:.1f}: {words_texts} → '{max(words_sorted, key=lambda w: len(w[4]))[4] if words_sorted else ''}'")
        
        # Estratégia ROBUSTA: Pegar a palavra mais significativa
        # Funciona para: tI>, tI>>, I>>>, Them Trip, Brkn Cond., etc
        
        if not words_sorted:
            return ""
        
        # Coletar todos os textos válidos (excluir ruído)
        valid_words = []
        for word in words_sorted:
            text = word[4].strip()
            # Filtrar ruído (pontuação isolada, números muito pequenos)
            if text and len(text) > 0 and text not in [':', ',', '-', '(', ')']:
                valid_words.append(text)
        
        if not valid_words:
            return ""
        
        # Prioridade 1: Se houver palavra com ">", pegar a MAIS LONGA com ">"
        words_with_arrow = [w for w in valid_words if '>' in w]
        if words_with_arrow:
            return max(words_with_arrow, key=len)
        
        # Prioridade 2: Palavra mais longa (captura "Them", "Trip", "Brkn", "Cond.", etc)
        return max(valid_words, key=len)
    
    def correlate_checkboxes_with_lines(
        self, 
        checkboxes: List[Checkbox], 
        lines: List[ParameterLine],
        page: fitz.Page,
        dpi_scale: float = 300/72
    ) -> List[Dict]:
        """
        ETAPA 4: Correlaciona checkboxes com linhas de parâmetros (LÓGICA HIERÁRQUICA)
        
        ESTRATÉGIA DUPLA:
        1. Checkboxes NA MESMA LINHA do parâmetro (±25px) → correlação direta
        2. Checkboxes ABAIXO do parâmetro (sublinhas) → correlação hierárquica
           - Ex: LED 5 (0150) tem checkboxes nas sublinhas (tI>, tI>>, etc)
           - Se QUALQUER checkbox marcado está abaixo → parâmetro-pai é ATIVO
           - NOVO: Extrair TODOS os valores dos checkboxes marcados e concatenar
        
        Args:
            checkboxes: Lista de checkboxes detectados (coordenadas em DPI 300)
            lines: Lista de linhas de parâmetros (coordenadas em DPI 72)
            page: Página do PDF (para extração de texto)
            dpi_scale: Fator de conversão (300/72 = 4.166)
            
        Returns:
            Lista de dicts com code, description, value, is_active
        """
        results = []
        matched_checkboxes = set()  # Rastrear checkboxes já usados
        
        # ETAPA 1: Correlação DIRETA + HIERÁRQUICA
        for line in lines:
            line_y = line.y_coordinate  # Já está em DPI 72
            
            matched_checkbox = None
            min_distance = float('inf')
            
            for checkbox in checkboxes:
                checkbox_y_72 = checkbox.y / dpi_scale
                distance = abs(checkbox_y_72 - line_y)
                
                # Correlação direta: checkbox na mesma altura
                if distance < self.Y_TOLERANCE and distance < min_distance:
                    matched_checkbox = checkbox
                    min_distance = distance
            
            # Verificar se há checkboxes marcados ABAIXO (sublinhas)
            # Buscar até 100px abaixo (cobre grupo de checkboxes)
            has_marked_children = False
            child_values = []  # Valores extraídos dos checkboxes filhos
            
            for checkbox in checkboxes:
                checkbox_y_72 = checkbox.y / dpi_scale
                distance_below = checkbox_y_72 - line_y
                
                # Checkbox está ABAIXO do parâmetro (sublinhas)
                if 5 < distance_below < 100:  # Entre 5px e 100px abaixo
                    matched_checkboxes.add(id(checkbox))
                    
                    if checkbox.is_marked:
                        has_marked_children = True
                        # Extrair texto do checkbox marcado
                        texto = self.extract_text_near_checkbox(page, checkbox, dpi_scale)
                        if texto:
                            child_values.append(texto)
            
            # Determinar is_active
            # ATIVO se: checkbox direto marcado OU tem checkboxes marcados nas sublinhas
            is_active = (matched_checkbox is not None and matched_checkbox.is_marked) or has_marked_children
            
            # Determinar valor
            # Prioridade 1: Valor próprio da linha
            # Prioridade 2: Valores dos checkboxes filhos (concatenados com vírgula)
            # Prioridade 3: Texto do checkbox direto
            value = line.value  # valor padrão
            
            if child_values:
                # Concatenar valores dos checkboxes filhos
                value = ", ".join(sorted(child_values))  # Ordenar para consistência
            elif matched_checkbox and matched_checkbox.is_marked and not line.value:
                checkbox_text = self.extract_text_near_checkbox(page, matched_checkbox, dpi_scale)
                if checkbox_text:
                    value = checkbox_text
                    matched_checkboxes.add(id(matched_checkbox))
            
            results.append({
                'Code': line.code,
                'Description': line.description,
                'Value': value,
                'is_active': is_active,
                'confidence': line.confidence,
                'y_coordinate': line.y_coordinate,
                'checkbox_density': matched_checkbox.density if matched_checkbox else 0.0
            })
        
        # ETAPA 2: Checkboxes órfãos (não associados a nenhuma linha)
        # Criar entradas individuais para checkboxes marcados sem linha-pai clara
        for checkbox in checkboxes:
            if checkbox.is_marked and id(checkbox) not in matched_checkboxes:
                checkbox_text = self.extract_text_near_checkbox(page, checkbox, dpi_scale)
                if checkbox_text:
                    # Tentar achar a linha "pai" mais próxima ACIMA
                    parent_line = None
                    checkbox_y_72 = checkbox.y / dpi_scale
                    min_distance_above = float('inf')
                    
                    for line in lines:
                        distance_above = checkbox_y_72 - line.y_coordinate
                        # Linha está ACIMA do checkbox (dentro de 100px)
                        if 0 < distance_above < 100 and distance_above < min_distance_above:
                            parent_line = line
                            min_distance_above = distance_above
                    
                    if parent_line:
                        results.append({
                            'Code': parent_line.code,
                            'Description': f"{parent_line.description} → {checkbox_text}",
                            'Value': checkbox_text,
                            'is_active': True,
                            'confidence': 0.95,
                            'y_coordinate': checkbox_y_72,
                            'checkbox_density': checkbox.density
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
            
            # ETAPA 1: Detectar checkboxes (usa mascaramento de texto interno)
            checkboxes = self.detect_checkboxes(page, dpi=300)
            
            # ETAPA 2: Extrair linhas de parâmetros
            lines = self.extract_parameter_lines(page)
            
            # ETAPA 3: Correlacionar checkboxes com linhas (passar dpi_scale!)
            page_results = self.correlate_checkboxes_with_lines(checkboxes, lines, page, dpi_scale=300/72)
            
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

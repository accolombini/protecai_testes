#!/usr/bin/env python3
"""
Extrator Inteligente de Parâmetros de Relés
Detecta automaticamente o tipo de relé e aplica estratégia adequada
Suporta: Easergy (P122, P220, P922), MiCOM (P143, P241), SEPAM (.S40)
"""

import re
import cv2
import numpy as np
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd

class IntelligentRelayExtractor:
    """
    Extrator inteligente que detecta tipo de relé e aplica estratégia adequada
    """
    
    # Padrões de código por tipo de relé (REGEX FLEXÍVEL - apenas detecta início de linha com código)
    PATTERNS = {
        'easergy': re.compile(r'^([0-9A-Za-z]{2,5}):'),  # Captura 2-5 chars alfanuméricos: 52b, 010D, 0104, 010A, etc.
        'micom': re.compile(r'^([0-9A-F]{2}\.[0-9A-F]{2}):', re.IGNORECASE),  # Captura grupo 1: código (0C.1E)
        'sepam': re.compile(r'^([^=]+)=(.+)$')  # parameter=value (mantido igual)
    }
    
    def __init__(self, template_checkbox_path: Optional[Path] = None):
        """
        Inicializa extrator
        
        Args:
            template_checkbox_path: Caminho para template de checkbox marcado (para Easergy)
        """
        self.template_checkbox = None
        if template_checkbox_path and template_checkbox_path.exists():
            self.template_checkbox = cv2.imread(str(template_checkbox_path))
    
    def detect_relay_type(self, file_path: Path) -> str:
        """
        Detecta tipo de relé baseado no arquivo
        
        Returns:
            'easergy', 'micom', ou 'sepam'
        """
        # SEPAM: arquivos .S40 ou .txt

        if file_path.suffix.lower() in ['.s40', '.txt']:
            return 'sepam'
        
        # PDF: analisar primeiras linhas para identificar
        if file_path.suffix.lower() == '.pdf':
            doc = fitz.open(str(file_path))
            first_page_text = doc[0].get_text()
            doc.close()
            
            # Verificar assinaturas no texto
            if 'Easergy' in first_page_text or 'Settings File Report' in first_page_text:
                # Verificar padrão de código
                if re.search(r'\d{4}:', first_page_text):
                    return 'easergy'
            
            if 'MiCOM' in first_page_text or 'Relatório de ficheiro' in first_page_text:
                # Verificar padrão hexadecimal
                if re.search(r'[0-9A-F]{2}\.[0-9A-F]{2}:', first_page_text, re.IGNORECASE):
                    return 'micom'
        
        # Fallback: tentar detectar por nome do arquivo
        filename = file_path.stem.upper()
        if 'P122' in filename or 'P220' in filename or 'P922' in filename:
            return 'easergy'
        elif 'P143' in filename or 'P241' in filename:
            return 'micom'
        
        return 'unknown'
    
    def extract_from_easergy(self, pdf_path: Path) -> pd.DataFrame:
        """
        Extrai parâmetros de relés Easergy (P122, P220, P922)
        Usa PreciseParameterExtractor com correlação Y-coordinate correta
        """
        print(f"   📘 Tipo: Easergy (usa checkboxes)")
        
        # Usa o PreciseParameterExtractor que funciona corretamente
        from src.precise_parameter_extractor import PreciseParameterExtractor
        
        extractor = PreciseParameterExtractor()
        df = extractor.extract_from_pdf(pdf_path)
        
        # Filtra apenas parâmetros ativos (checkbox marcado) E MANTÉM is_active
        if not df.empty and 'is_active' in df.columns:
            df_active = df[df['is_active'] == True].copy()
            # Remove apenas colunas auxiliares (NÃO remove is_active!)
            df_active = df_active.drop(columns=['confidence', 'y_coordinate', 'checkbox_density'], errors='ignore')
            return df_active
        
        return df
    
    def extract_from_micom(self, pdf_path: Path) -> pd.DataFrame:
        """
        Extrai parâmetros de relés MiCOM (P143, P241)
        Extrai todos os parâmetros (MiCOM não usa checkboxes)
        """
        print(f"   📗 Tipo: MiCOM (sem checkboxes, extrai todos)")
        
        # MiCOM usa layout em colunas - precisa preservar posicionamento
        return self._extract_micom_with_layout(pdf_path)
    
    def extract_from_sepam(self, file_path: Path) -> pd.DataFrame:
        """
        Extrai parâmetros de relés SEPAM (arquivos .S40/.txt)
        
        Captura:
        - Metadados do equipamento (repere, modele, mes)
        - Parâmetros de configuração
        """
        print(f"   📙 Tipo: SEPAM (formato INI)")
        
        params = []
        
        # Tentar diferentes encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    break
            except UnicodeDecodeError:
                continue
        else:
            print(f"   ❌ Erro ao ler arquivo com encodings suportados")
            return pd.DataFrame(columns=['Code', 'Description', 'Value'])
        
        # Parse INI format
        current_section = ""
        for line in content.split('\n'):
            line = line.strip()
            
            # Seção
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                continue
            
            # Parâmetro
            match = self.PATTERNS['sepam'].match(line)
            if match:
                param_name = match.group(1).strip()
                param_value = match.group(2).strip()
                
                # METADADOS CRÍTICOS: Identificação do equipamento
                # Seção [Sepam_ConfigMaterielle] contém dados essenciais
                # Comparação case-insensitive para compatibilidade
                if current_section.lower() == 'sepam_configmaterielle':
                    # Mapear nomes INI para códigos padronizados
                    metadata_map = {
                        'repere': 'SEPAM_REPERE',      # Identificador do equipamento
                        'modele': 'SEPAM_MODELE',      # Modelo do SEPAM
                        'mes': 'SEPAM_MES',            # Tipo de medição
                        'gamme': 'SEPAM_GAMME',        # Gama/família
                        'typemat': 'SEPAM_TYPEMAT'     # Tipo de material
                    }
                    
                    if param_name.lower() in metadata_map:
                        code = metadata_map[param_name.lower()]
                        params.append({
                            'Code': code,
                            'Description': param_name,
                            'Value': param_value
                        })
                        continue
                
                # Parâmetros normais - usar nome original como código
                code = param_name
                
                params.append({
                    'Code': code,
                    'Description': param_name,
                    'Value': param_value
                })
        
        df = pd.DataFrame(params)
        
        # Limpar valores None/nan
        df = df.replace(['None', 'nan', 'NaN', 'NAN'], '')
        df = df.fillna('')
        # SEPAM não usa checkboxes - TODOS são considerados ativos
        if not df.empty:
            df['is_active'] = True
        
        return df
    
    def _extract_micom_with_layout(self, pdf_path: Path) -> pd.DataFrame:
        """
        Extrai parâmetros MiCOM respeitando layout em colunas do PDF
        
        MiCOM usa layout: [Código] [Descrição] [Valor]
        Exemplo: 00.01: Language: English
        
        Palavras estão na mesma linha Y mas em posições X diferentes.
        """
        doc = fitz.open(str(pdf_path))
        params = []
        pattern = re.compile(r'^\d{2}\.\d{2}[A-Z]?:')
        
        # Processar todas as páginas
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extrair palavras com coordenadas
            words = page.get_text('words')  # (x0, y0, x1, y1, text, block, line, word_num)
            
            # Agrupar palavras por linha Y (±3px de tolerância)
            lines_dict = {}
            for word in words:
                x0, y0, x1, y1, text, block_num, line_num, word_num = word
                
                # Encontrar linha existente ou criar nova
                found_line = None
                for y_key in lines_dict:
                    if abs(y_key - y0) < 3:  # Mesma linha
                        found_line = y_key
                        break
                
                if found_line is None:
                    found_line = y0
                    lines_dict[found_line] = []
                
                lines_dict[found_line].append((x0, text))
            
            # Processar cada linha
            for y_coord in sorted(lines_dict.keys()):
                line_words = sorted(lines_dict[y_coord], key=lambda w: w[0])  # Ordenar por X
                line_text = ' '.join([w[1] for w in line_words])
                
                # Verificar se linha tem código MiCOM
                if pattern.match(line_text):
                    parts = line_text.split(':', 2)  # Dividir no máximo em 3 partes
                    
                    if len(parts) >= 2:
                        code = parts[0].strip()
                        description = parts[1].strip() if len(parts) > 1 else ""
                        value = parts[2].strip() if len(parts) > 2 else ""
                        
                        params.append({
                            'Code': code,
                            'Description': description,
                            'Value': value
                        })
        
        doc.close()
        
        df = pd.DataFrame(params)
        
        if not df.empty:
            df = df.replace(['None', 'nan', 'NaN', 'NAN'], '')
            df = df.fillna('')
            df = df.drop_duplicates(subset=['Code', 'Description'], keep='first')
            # MiCOM não usa checkboxes - TODOS são considerados ativos
            df['is_active'] = True
        
        return df
    
    def _extract_all_text_parameters(self, pdf_path: Path, relay_type: str) -> pd.DataFrame:
        """
        Extrai TODOS os parâmetros do PDF via texto - VERSÃO ROBUSTA
        Usado para MiCOM ou fallback para Easergy
        
        Lida com múltiplos formatos:
        - 0104: Frequency: 60Hz
        - 0104: Frequency:60 Hz
        - 010A: Reference:01BC
        - 0150: LED 5 Part 1: (valor em linhas seguintes)
        """
        doc = fitz.open(str(pdf_path))
        
        params = []
        pattern = self.PATTERNS[relay_type]
        
        # Processar todas as páginas
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            lines = text.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                match = pattern.match(line)
                if match:
                    if relay_type == 'easergy':
                        # Extrair código (ex: "0104")
                        code_part = match.group(1)
                        
                        # Extrair resto da linha após "XXXX:"
                        rest = line[match.end():].strip()
                        
                        # Tentar extrair descrição e valor
                        description = ""
                        value = ""
                        
                        if ':' in rest:
                            # Formato: "Frequency: 60Hz" ou "Frequency:60 Hz"
                            parts = rest.split(':', 1)
                            description = parts[0].strip()
                            value = parts[1].strip() if len(parts) > 1 else ""
                        else:
                            # Formato: "Connection 2 Upp + Vr" (sem segundo ':')
                            # Tentar separar última palavra como valor
                            words = rest.split()
                            if len(words) > 1:
                                # Último token pode ser valor, resto é descrição
                                # Mas isso é heurística fraca - melhor deixar tudo como descrição
                                description = rest
                            else:
                                description = rest
                            
                            # Tentar capturar valor nas próximas linhas (se não começarem com código)
                            # Exemplo: LED options em múltiplas linhas
                            value_lines = []
                            j = i + 1
                            while j < len(lines) and j < i + 20:  # Max 20 linhas à frente
                                next_line = lines[j].strip()
                                # Se próxima linha é um código, parar
                                if pattern.match(next_line):
                                    break
                                # Se linha tem conteúdo e não é header/footer
                                if next_line and not self._is_header_footer(next_line):
                                    value_lines.append(next_line)
                                j += 1
                            
                            # Juntar linhas de valor (máximo 5 linhas)
                            if value_lines:
                                value = ' | '.join(value_lines[:5])
                        
                        # Adicionar parâmetro
                        params.append({
                            'Code': code_part,
                            'Description': description,
                            'Value': value if value else ""
                        })
                    
                    elif relay_type == 'micom':
                        # MiCOM: 0C.1E: Digital Input: Value
                        # FORMATO: Pode ser inline ou valor na próxima linha
                        if ':' not in line:
                            i += 1
                            continue
                        
                        code_part = line.split(':', 1)[0].strip()
                        rest = line.split(':', 1)[1].strip()
                        
                        description = ""
                        value = ""
                        
                        if ':' in rest:
                            # Formato: 00.01: Description: Value
                            parts = rest.split(':', 1)
                            description = parts[0].strip()
                            value = parts[1].strip()
                        else:
                            # Formato: 00.01: Description (valor pode estar na próxima linha)
                            description = rest
                            
                            # Verificar se próxima linha tem valor (não começa com código)
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                # Se próxima linha não é código MiCOM (XX.XX:) e não é vazia
                                if next_line and not re.match(r'^\d{2}\.\d{2}[A-Z]?:', next_line):
                                    value = next_line
                                    i += 1  # Pular próxima linha pois já foi processada
                        
                        params.append({
                            'Code': code_part,
                            'Description': description,
                            'Value': value if value else ""
                        })
                
                i += 1
        
        doc.close()
        
        df = pd.DataFrame(params)
        
        # Limpar valores
        if not df.empty:
            df = df.replace(['None', 'nan', 'NaN', 'NAN'], '')
            df = df.fillna('')
            
            # Remover duplicatas (mesmo Code e Description)
            df = df.drop_duplicates(subset=['Code', 'Description'], keep='first')
        
        return df
    
    def _is_header_footer(self, line: str) -> bool:
        """
        Detecta se linha é header/footer do PDF (para não incluir em valores)
        """
        header_footer_keywords = [
            'easergy studio',
            'settings file report',
            'substation:',
            'file:',
            'model number:',
            'page:',
            'schneider electric'
        ]
        
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in header_footer_keywords)
    
    def _extract_with_checkbox_detection(self, pdf_path: Path) -> pd.DataFrame:
        """
        Extrai parâmetros usando detecção de checkboxes (Easergy)
        Retorna APENAS parâmetros com checkbox marcado
        
        Estratégia MELHORADA (correlação Y-coordinate):
        1. Detectar checkboxes marcados (densidade de pixels)
        2. Extrair palavras da página com posição (x, y)
        3. Para cada checkbox, encontrar texto na mesma linha (±5px vertical)
        4. Parsear linha como parâmetro (código: descrição: valor)
        """
        doc = fitz.open(str(pdf_path))
        
        all_params = []
        code_pattern = re.compile(r'^([0-9A-Za-z]{2,5}):')  # Mesmo padrão flexível: 52b, 010D, 0104, etc.
        
        # Processar cada página
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Converter página para imagem (para detectar checkboxes)
            mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
            pix = page.get_pixmap(matrix=mat)
            
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            
            # Detectar checkboxes marcados
            marked_positions = self._detect_checkboxes(img)
            
            if not marked_positions:
                continue
            
            # Extrair palavras com posição (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            words = page.get_text("words")
            
            # Para cada checkbox marcado
            for checkbox in marked_positions:
                checkbox_y = checkbox['y']  # Coordenada Y do checkbox
                
                # Encontrar palavras na mesma linha (±10px vertical)
                # Nota: Y-coordinate do checkbox está em 300 DPI, palavras em 72 DPI
                # Converter: checkbox_y * 72/300 = checkbox_y * 0.24
                checkbox_y_72dpi = checkbox_y * 72 / 300
                
                line_words = [
                    word for word in words 
                    if abs(word[1] - checkbox_y_72dpi) < 10  # word[1] = y0
                ]
                
                if not line_words:
                    continue
                
                # Ordenar palavras por posição X (esquerda → direita)
                line_words.sort(key=lambda w: w[0])  # w[0] = x0
                
                # Montar texto da linha
                line_text = ' '.join([w[4] for w in line_words])  # w[4] = word
                
                # Tentar parsear como parâmetro
                match = code_pattern.match(line_text)
                if not match:
                    continue
                
                code = match.group(1)
                rest = line_text[len(code)+1:].strip()  # Pula "XXXX:"
                
                description = ""
                value = ""
                
                if ':' in rest:
                    parts = rest.split(':', 1)
                    description = parts[0].strip()
                    value = parts[1].strip() if len(parts) > 1 else ""
                else:
                    description = rest
                
                all_params.append({
                    'Code': code,
                    'Description': description,
                    'Value': value
                })
        
        doc.close()
        
        # Converter para DataFrame
        df = pd.DataFrame(all_params)
        
        # Limpar e remover duplicatas
        if not df.empty:
            df = df.replace(['None', 'nan', 'NaN', 'NAN'], '')
            df = df.fillna('')
            df = df.drop_duplicates(subset=['Code', 'Description'], keep='first')
        
        return df
    
    def _detect_checkboxes(self, image: np.ndarray, threshold: float = 0.30) -> List[Dict]:
        """
        Detecta checkboxes marcados usando DENSIDADE DE PIXELS (método robusto).
        
        Args:
            image: Imagem da página (BGR)
            threshold: Densidade mínima de pixels brancos para considerar marcado (0.0-1.0)
        
        Returns:
            Lista de dicts com posições dos checkboxes marcados
        """
        # Converter para escala de cinza
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Binarização adaptativa
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Detectar contornos
        contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        marked_checkboxes = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Critérios para checkbox:
            # 1. Aproximadamente quadrado (aspect ratio ~1.0)
            # 2. Tamanho entre 10-40 pixels
            # 3. Área > 50 pixels
            aspect_ratio = float(w) / h if h > 0 else 0
            area = cv2.contourArea(contour)
            
            if (0.7 <= aspect_ratio <= 1.3 and
                10 <= w <= 40 and 10 <= h <= 40 and
                area > 50):
                
                # Extrair região do checkbox
                checkbox_region = binary[y:y+h, x:x+w]
                
                # Calcular densidade de pixels brancos (marca X)
                white_pixel_ratio = np.sum(checkbox_region == 255) / (w * h)
                
                # Se > threshold da área preenchida = checkbox MARCADO
                if white_pixel_ratio > threshold:
                    marked_checkboxes.append({
                        'x': x + w//2,  # Centro do checkbox
                        'y': y + h//2,
                        'confidence': white_pixel_ratio  # Usar densidade como confiança
                    })
        
        return marked_checkboxes
    
    def _non_max_suppression(self, matches: List[Dict], min_distance: int = 10) -> List[Dict]:
        """Remove detecções duplicadas próximas"""
        if not matches:
            return []
        
        matches = sorted(matches, key=lambda x: x['confidence'], reverse=True)
        
        filtered = []
        for match in matches:
            is_far = True
            for existing in filtered:
                dist = np.sqrt((match['x'] - existing['x'])**2 + 
                              (match['y'] - existing['y'])**2)
                if dist < min_distance:
                    is_far = False
                    break
            
            if is_far:
                filtered.append(match)
        
        return filtered
    
    def _find_text_near_position(self, words: List, x: int, y: int, 
                                  max_distance: int = 150) -> str:
        """Encontra texto próximo a uma posição (checkbox)"""
        scale = 72 / 300  # Converter DPI 300 para coordenadas PDF (72 DPI)
        pdf_x = x * scale
        pdf_y = y * scale
        
        nearby = []
        
        for word in words:
            x0, y0, x1, y1, text, *_ = word
            word_x = (x0 + x1) / 2
            word_y = (y0 + y1) / 2
            
            distance = np.sqrt((word_x - pdf_x)**2 + (word_y - pdf_y)**2)
            
            if distance < max_distance * scale:
                nearby.append({
                    'text': text,
                    'distance': distance
                })
        
        # Ordenar por distância e concatenar
        nearby.sort(key=lambda x: x['distance'])
        return " ".join([item['text'] for item in nearby[:10]])
    
    def _parse_parameter_from_text(self, text: str) -> Optional[Dict]:
        """Tenta parsear texto como parâmetro de relé"""
        # Tentar padrão Easergy: tI> ou 0104: Frequency: 60Hz
        
        # Caso 1: Apenas nome de parâmetro (ex: tI>, tIe>)
        param_name_pattern = r'^[a-zA-Z0-9><\-]+$'
        if re.match(param_name_pattern, text.strip()):
            return {
                'Code': text.strip(),
                'Description': text.strip(),
                'Value': 'Yes'  # Checkbox marcado = ativado
            }
        
        # Caso 2: Código completo (0104: Frequency: 60Hz)
        match = self.PATTERNS['easergy'].match(text)
        if match:
            parts = text.split(':', 2)
            if len(parts) >= 3:
                return {
                    'Code': parts[0].strip(),
                    'Description': parts[1].strip(),
                    'Value': parts[2].strip()
                }
        
        return None
    
    def extract(self, file_path: Path) -> pd.DataFrame:
        """
        Método principal: detecta tipo e extrai parâmetros
        
        Args:
            file_path: Caminho do arquivo (PDF ou .S40)
        
        Returns:
            DataFrame com colunas [Code, Description, Value]
        """
        print(f"\n🔍 Analisando: {file_path.name}")
        
        # Detectar tipo
        relay_type = self.detect_relay_type(file_path)
        print(f"   🎯 Tipo detectado: {relay_type.upper()}")
        
        # Aplicar estratégia adequada
        if relay_type == 'easergy':
            df = self.extract_from_easergy(file_path)
        elif relay_type == 'micom':
            df = self.extract_from_micom(file_path)
        elif relay_type == 'sepam':
            df = self.extract_from_sepam(file_path)
        else:
            print(f"   ⚠️  Tipo desconhecido - tentando extração genérica")
            df = self._extract_all_text_parameters(file_path, 'easergy')
        
        print(f"   ✅ Extraídos: {len(df)} parâmetros")
        
        return df


def main():
    """Teste do extrator inteligente"""
    
    # Configurar paths
    template_path = Path("outputs/checkbox_debug/templates/marcado_average.png")
    test_files = [
        Path("inputs/pdf/P_122 52-MF-03B1_2021-03-17.pdf"),  # Easergy
        Path("inputs/pdf/P143_204-MF-2B_2018-06-13.pdf"),     # MiCOM
    ]
    
    # Criar extrator
    extractor = IntelligentRelayExtractor(template_checkbox_path=template_path)
    
    print("=" * 80)
    print("🧠 EXTRATOR INTELIGENTE DE PARÂMETROS")
    print("=" * 80)
    
    for file_path in test_files:
        if not file_path.exists():
            print(f"\n⚠️  Arquivo não encontrado: {file_path}")
            continue
        
        # Extrair
        df = extractor.extract(file_path)
        
        # Mostrar amostra
        if not df.empty:
            print(f"\n📋 Amostra (primeiros 10):")
            print(df.head(10).to_string(index=False))
        else:
            print(f"\n⚠️  Nenhum parâmetro extraído")
        
        print("\n" + "-" * 80)
    
    print("\n✅ Teste concluído!")


if __name__ == "__main__":
    main()

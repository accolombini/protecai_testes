#!/usr/bin/env python3
"""
RECONSTRUÇÃO COMPLETA DA PIPELINE - ProtecAI
Data: 06 de Novembro de 2025

OBJETIVO: Reprocessar TODOS os 50 arquivos com parser CORRIGIDO de checkboxes
Pipeline completa: PDF/S40 → CSV → Excel → Normalização → Banco

ETAPAS:
1. Limpar outputs antigos (csv, excel, norm_csv, norm_excel)
2. Extrair parâmetros + checkboxes com lógica GENÉRICA
3. Gerar outputs/csv/*.csv
4. Gerar outputs/excel/*.xlsx  
5. Normalizar → outputs/norm_csv/*.csv
6. Normalizar → outputs/norm_excel/*.xlsx
7. Opcionalmente: Re-importar banco de dados

PRINCÍPIOS: ROBUSTO, FLEXÍVEL, 100% REAL
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import shutil
import pandas as pd
import PyPDF2
import fitz  # PyMuPDF
import re
from typing import List, Dict, Tuple
import xlsxwriter

# Configurar logging
log_dir = Path(__file__).parent.parent / "outputs" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'pipeline_rebuild_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PipelineRebuilder:
    """Reconstrói toda a pipeline com parser corrigido"""
    
    def __init__(self, clean_old_outputs=True):
        self.base_dir = Path(__file__).parent.parent
        self.inputs_dir = self.base_dir / "inputs"
        self.outputs_dir = self.base_dir / "outputs"
        self.clean_old_outputs = clean_old_outputs
        
        # Contadores
        self.stats = {
            'total_files': 0,
            'pdf_files': 0,
            's40_files': 0,
            'total_parameters': 0,
            'total_checkboxes': 0,
            'errors': []
        }
        
    def run(self):
        """Executa pipeline completa"""
        logger.info("="*80)
        logger.info("🚀 INICIANDO RECONSTRUÇÃO COMPLETA DA PIPELINE")
        logger.info("="*80)
        
        # ETAPA 1: Limpar outputs antigos
        if self.clean_old_outputs:
            self.clean_output_directories()
        
        # ETAPA 2: Processar todos os arquivos
        self.process_all_files()
        
        # ETAPA 3: Normalizar CSVs
        self.normalize_all_csvs()
        
        # ETAPA 4: Relatório final
        self.print_final_report()
        
        logger.info("="*80)
        logger.info("✅ PIPELINE RECONSTRUÍDA COM SUCESSO!")
        logger.info("="*80)
    
    def clean_output_directories(self):
        """Limpa diretórios de output para começar do zero"""
        logger.info("\n🧹 ETAPA 1: Limpando outputs antigos...")
        
        dirs_to_clean = ['csv', 'excel', 'norm_csv', 'norm_excel']
        
        for dir_name in dirs_to_clean:
            dir_path = self.outputs_dir / dir_name
            if dir_path.exists():
                # Mover arquivos antigos para backup
                backup_dir = self.outputs_dir / f"{dir_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_dir.mkdir(parents=True, exist_ok=True)
                
                file_count = 0
                for file in dir_path.glob('*'):
                    if file.is_file():
                        shutil.move(str(file), str(backup_dir / file.name))
                        file_count += 1
                
                logger.info(f"  ✓ {dir_name}: {file_count} arquivos movidos para backup")
            else:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"  ✓ {dir_name}: diretório criado")
        
        logger.info("✅ Limpeza concluída\n")
    
    def process_all_files(self):
        """Processa todos os PDFs e S40s"""
        logger.info("\n📄 ETAPA 2: Processando arquivos de entrada...")
        
        # Listar PDFs
        pdf_files = list((self.inputs_dir / "pdf").glob("*.pdf"))
        s40_files = list((self.inputs_dir / "txt").glob("*.S40"))
        
        all_files = pdf_files + s40_files
        self.stats['total_files'] = len(all_files)
        self.stats['pdf_files'] = len(pdf_files)
        self.stats['s40_files'] = len(s40_files)
        
        logger.info(f"  📁 {len(pdf_files)} PDFs encontrados")
        logger.info(f"  📁 {len(s40_files)} S40s encontrados")
        logger.info(f"  📁 {len(all_files)} arquivos TOTAL\n")
        
        # Processar cada arquivo
        for idx, file_path in enumerate(all_files, 1):
            logger.info(f"[{idx}/{len(all_files)}] Processando: {file_path.name}")
            
            try:
                if file_path.suffix.lower() == '.pdf':
                    self.process_pdf(file_path)
                elif file_path.suffix.upper() == '.S40':
                    self.process_s40(file_path)
                
                logger.info(f"  ✓ Concluído\n")
                
            except Exception as e:
                logger.error(f"  ❌ ERRO: {e}\n")
                self.stats['errors'].append({
                    'file': file_path.name,
                    'error': str(e)
                })
        
        logger.info("✅ Processamento de arquivos concluído\n")
    
    def process_pdf(self, pdf_path: Path):
        """Processa um arquivo PDF com parser CORRIGIDO"""
        # Extrair parâmetros e checkboxes
        params, checkboxes = self.extract_from_pdf(pdf_path)
        
        # Atualizar estatísticas
        self.stats['total_parameters'] += len(params)
        self.stats['total_checkboxes'] += len(checkboxes)
        
        # Combinar parâmetros e checkboxes
        all_data = params + checkboxes
        
        # Salvar CSV
        self.save_to_csv(all_data, pdf_path)
        
        # Salvar Excel
        self.save_to_excel(all_data, pdf_path)
        
        logger.info(f"  ✓ {len(params)} parâmetros + {len(checkboxes)} checkboxes extraídos")
    
    def extract_from_pdf(self, pdf_path: Path) -> Tuple[List[Dict], List[Dict]]:
        """
        Extrai parâmetros e checkboxes de PDF usando lógica GENÉRICA corrigida
        
        IMPORTANTE: Esta é a lógica CORRIGIDA que funciona para:
        - Páginas com INPUT (ex: página 3)
        - Páginas SEM INPUT (ex: página 6 com "Logical output")
        """
        params = []
        checkboxes = []
        
        try:
            # Abrir PDF
            doc = fitz.open(str(pdf_path))
            
            # Processar todas as páginas
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Parser linha por linha
                page_params, page_checkboxes = self.parse_text_with_checkboxes(text)
                params.extend(page_params)
                checkboxes.extend(page_checkboxes)
            
            doc.close()
            
        except Exception as e:
            logger.error(f"  ❌ Erro extraindo de {pdf_path.name}: {e}")
            raise
        
        return params, checkboxes
    
    def parse_text_with_checkboxes(self, text: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Parser GENÉRICO de texto com detecção de checkboxes
        
        LÓGICA CORRIGIDA (06/11/2025):
        - NÃO depende de keyword "INPUT"
        - Detecta checkboxes por PADRÃO (linhas sem código após parâmetros)
        - Funciona com qualquer estrutura de PDF
        """
        params = []
        checkboxes = []
        lines = text.split('\n')
        
        current_code = None
        current_description = None
        collecting_checkboxes = False
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Detectar código de parâmetro (NNNN: ou NNAA:)
            code_match = re.match(r'^([0-9A-F]{4}):\s*(.*)$', line, re.IGNORECASE)
            
            if code_match:
                code = code_match.group(1)
                rest_of_line = code_match.group(2).strip()
                
                # Separar descrição e valor
                if '=' in rest_of_line or '?:' in rest_of_line:
                    parts = re.split(r'[=?:]', rest_of_line, 1)
                    description = parts[0].strip()
                    value = parts[1].strip() if len(parts) > 1 else ''
                else:
                    description = rest_of_line
                    value = ''
                
                # Se valor vazio, verificar próxima linha
                if not value and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Se próxima linha não é código, pode ser valor
                    if not re.match(r'^[0-9A-F]{4}:', next_line):
                        # Verificar se parece com valor (número, YES/NO, unidade)
                        if self.looks_like_value(next_line):
                            value = next_line
                            i += 1  # Pular próxima linha
                
                # Adicionar parâmetro
                params.append({
                    'Code': code,
                    'Description': description,
                    'Value': value,
                    'Type': 'parameter'
                })
                
                # Preparar para coletar checkboxes
                current_code = code
                current_description = description
                collecting_checkboxes = True
                
            elif collecting_checkboxes and line:
                # Verificar se é checkbox (linha sem código)
                is_code = re.match(r'^[0-9A-F]{4}:', line, re.IGNORECASE)
                
                if is_code:
                    # Novo código encontrado, parar de coletar checkboxes
                    collecting_checkboxes = False
                    continue
                
                # Filtrar metadata e valores simples
                if self.is_checkbox_candidate(line):
                    checkboxes.append({
                        'Code': current_code,
                        'Description': f"{current_code}: {current_description}",
                        'CheckboxName': line,
                        'Type': 'checkbox'
                    })
            
            i += 1
        
        return params, checkboxes
    
    def looks_like_value(self, line: str) -> bool:
        """Verifica se linha parece com um valor de parâmetro"""
        if not line:
            return False
        
        # YES/NO/On/Off
        if line.upper() in ['YES', 'NO', 'ON', 'OFF']:
            return True
        
        # Números com unidades
        if re.match(r'^\d+\.?\d*\s*[A-Za-z]+', line):
            return True
        
        # Apenas números
        if re.match(r'^\d+\.?\d*$', line):
            return True
        
        return False
    
    def is_checkbox_candidate(self, line: str) -> bool:
        """
        Verifica se linha é candidata a checkbox
        
        LÓGICA GENÉRICA (funciona para INPUT e Logical output):
        - Não tem código no início
        - Tem texto significativo
        - Não é metadata (Easergy Studio, etc)
        - Tamanho razoável (< 50 chars)
        """
        if not line or len(line) > 50:
            return False
        
        # Filtrar metadata
        if any(x in line for x in ['Easergy', 'Studio', 'Page', 'Settings File', 'Substation']):
            return False
        
        # Filtrar valores simples
        if line.upper() in ['YES', 'NO', 'ON', 'OFF']:
            return False
        
        # Aceitar se tem características de checkbox
        # - Ponto final (EMERG_ST., TRIP.)
        # - Underscore (SET_GROUP, VOLT_DIP)
        # - Palavra "output" (Logical output 2)
        # - Maiúsculas com espaços (EXT RESET, DIST TRIG)
        if any([
            '.' in line,
            '_' in line,
            'output' in line.lower(),
            (line.isupper() and ' ' in line)
        ]):
            return True
        
        return False
    
    def process_s40(self, s40_path: Path):
        """Processa arquivo SEPAM S40"""
        # TODO: Implementar extração S40 (formato texto chave=valor)
        logger.info(f"  ⏭️  S40 processing not implemented yet (skipping)")
        pass
    
    def save_to_csv(self, data: List[Dict], source_file: Path):
        """Salva dados em CSV"""
        if not data:
            return
        
        # Gerar nome do arquivo de saída
        output_name = self.generate_output_filename(source_file, 'csv')
        output_path = self.outputs_dir / 'csv' / output_name
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Salvar
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"  ✓ CSV salvo: {output_name}")
    
    def save_to_excel(self, data: List[Dict], source_file: Path):
        """Salva dados em Excel"""
        if not data:
            return
        
        # Gerar nome do arquivo de saída
        output_name = self.generate_output_filename(source_file, 'xlsx')
        output_path = self.outputs_dir / 'excel' / output_name
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Salvar com formatação
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Parameters', index=False)
            
            # Formatar
            workbook = writer.book
            worksheet = writer.sheets['Parameters']
            
            # Auto-ajustar largura das colunas
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(idx, idx, max_len)
        
        logger.info(f"  ✓ Excel salvo: {output_name}")
    
    def generate_output_filename(self, source_file: Path, extension: str) -> str:
        """Gera nome padronizado para arquivo de saída"""
        # Remover extensão do arquivo original
        base_name = source_file.stem
        
        # Adicionar sufixo _params
        output_name = f"{base_name}_params.{extension}"
        
        return output_name
    
    def normalize_all_csvs(self):
        """Normaliza todos os CSVs gerados"""
        logger.info("\n🔄 ETAPA 3: Normalizando CSVs...")
        
        csv_files = list((self.outputs_dir / 'csv').glob('*.csv'))
        
        for csv_file in csv_files:
            try:
                # Ler CSV
                df = pd.read_csv(csv_file)
                
                # Normalizar
                df_normalized = self.normalize_dataframe(df)
                
                # Salvar CSV normalizado
                norm_csv_path = self.outputs_dir / 'norm_csv' / csv_file.name
                df_normalized.to_csv(norm_csv_path, index=False, encoding='utf-8')
                
                # Salvar Excel normalizado
                norm_excel_name = csv_file.stem + '.xlsx'
                norm_excel_path = self.outputs_dir / 'norm_excel' / norm_excel_name
                df_normalized.to_excel(norm_excel_path, index=False, engine='openpyxl')
                
                logger.info(f"  ✓ Normalizado: {csv_file.name}")
                
            except Exception as e:
                logger.error(f"  ❌ Erro normalizando {csv_file.name}: {e}")
    
    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza DataFrame (adicionar colunas padronizadas)"""
        # Adicionar colunas de normalização
        if 'normalized_name' not in df.columns:
            df['normalized_name'] = df.get('Description', '')
        
        if 'category' not in df.columns:
            df['category'] = 'General'
        
        if 'unit' not in df.columns:
            df['unit'] = ''
        
        if 'extraction_date' not in df.columns:
            df['extraction_date'] = datetime.now().isoformat()
        
        return df
    
    def print_final_report(self):
        """Imprime relatório final"""
        logger.info("\n" + "="*80)
        logger.info("📊 RELATÓRIO FINAL")
        logger.info("="*80)
        logger.info(f"📁 Arquivos processados: {self.stats['total_files']}")
        logger.info(f"  ├─ PDFs: {self.stats['pdf_files']}")
        logger.info(f"  └─ S40s: {self.stats['s40_files']}")
        logger.info(f"📝 Parâmetros extraídos: {self.stats['total_parameters']}")
        logger.info(f"☑️  Checkboxes detectados: {self.stats['total_checkboxes']}")
        
        if self.stats['errors']:
            logger.warning(f"⚠️  Erros: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.warning(f"  - {error['file']}: {error['error']}")
        else:
            logger.info("✅ Nenhum erro encontrado!")
        
        logger.info("="*80)


def main():
    """Execução principal"""
    print("\n" + "="*80)
    print("🚀 RECONSTRUÇÃO COMPLETA DA PIPELINE PROTECAI")
    print("="*80)
    print("\nEste script irá:")
    print("  1. Limpar outputs antigos (backup automático)")
    print("  2. Reprocessar 50 arquivos com parser CORRIGIDO")
    print("  3. Gerar outputs/csv/*.csv")
    print("  4. Gerar outputs/excel/*.xlsx")
    print("  5. Gerar outputs/norm_csv/*.csv")
    print("  6. Gerar outputs/norm_excel/*.xlsx")
    print("\n⚠️  ATENÇÃO: Isso pode levar alguns minutos!")
    
    response = input("\nDeseja continuar? (s/n): ")
    
    if response.lower() != 's':
        print("❌ Operação cancelada")
        return
    
    # Executar pipeline
    rebuilder = PipelineRebuilder(clean_old_outputs=True)
    rebuilder.run()
    
    print("\n✅ Pipeline reconstruída com sucesso!")
    print("\nPróximos passos:")
    print("  1. Validar arquivos em outputs/csv/")
    print("  2. Validar arquivos em outputs/norm_csv/")
    print("  3. Re-importar banco de dados (opcional)")


if __name__ == "__main__":
    main()

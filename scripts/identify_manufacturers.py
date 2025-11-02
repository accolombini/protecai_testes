#!/usr/bin/env python3
"""
🔍 IDENTIFICADOR DE FABRICANTES - Análise de Rodapés PDF
========================================================

Extrai fabricante dos PDFs através da análise de rodapé:
- "MiCOM S1 Agile" → GE (General Electric)
- "Easergy Studio" → Schneider Electric

Author: ProtecAI Team
Date: 2025-10-31
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import PyPDF2

class ManufacturerIdentifier:
    """Identifica fabricantes através de rodapés de PDF"""
    
    def __init__(self, pdf_dir: str):
        self.pdf_dir = Path(pdf_dir)
        self.results: List[Dict] = []
        
    def extract_footer_from_pdf(self, pdf_path: Path) -> str:
        """
        Extrai texto do rodapé (última linha) da primeira página do PDF
        
        Args:
            pdf_path: Caminho do arquivo PDF
            
        Returns:
            Texto do rodapé
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if len(pdf_reader.pages) == 0:
                    return ""
                
                # Extrair texto da primeira página
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()
                
                # Pegar as últimas 3 linhas (onde geralmente está o rodapé)
                lines = text.strip().split('\n')
                footer_lines = lines[-3:]
                footer = ' '.join(footer_lines)
                
                return footer
                
        except Exception as e:
            print(f"⚠️  Erro ao ler {pdf_path.name}: {e}")
            return ""
    
    def identify_manufacturer(self, footer_text: str) -> str:
        """
        Identifica fabricante pelo texto do rodapé
        
        Args:
            footer_text: Texto do rodapé extraído
            
        Returns:
            Nome do fabricante: "GE", "Schneider Electric", ou "Unknown"
        """
        footer_lower = footer_text.lower()
        
        # Padrões de identificação
        if 'micom s1 agile' in footer_lower or 'micom' in footer_lower:
            return "GE"
        elif 'easergy studio' in footer_lower or 'easergy' in footer_lower:
            return "Schneider Electric"
        elif 'schneider' in footer_lower:
            return "Schneider Electric"
        elif 'general electric' in footer_lower or 'ge grid' in footer_lower:
            return "GE"
        else:
            return "Unknown"
    
    def analyze_all_pdfs(self) -> Dict:
        """
        Analisa todos os PDFs no diretório
        
        Returns:
            Dicionário com estatísticas
        """
        print("=" * 70)
        print("       🔍 IDENTIFICAÇÃO DE FABRICANTES - ANÁLISE DE PDFs")
        print("=" * 70)
        print()
        
        pdf_files = sorted(self.pdf_dir.glob("*.pdf"))
        total_files = len(pdf_files)
        
        print(f"📁 Diretório: {self.pdf_dir}")
        print(f"📊 Total de PDFs encontrados: {total_files}")
        print()
        print("Analisando rodapés...")
        print("-" * 70)
        
        manufacturers_count = {
            "GE": 0,
            "Schneider Electric": 0,
            "Unknown": 0
        }
        
        for idx, pdf_file in enumerate(pdf_files, 1):
            # Extrair rodapé
            footer = self.extract_footer_from_pdf(pdf_file)
            
            # Identificar fabricante
            manufacturer = self.identify_manufacturer(footer)
            
            # Contar
            manufacturers_count[manufacturer] += 1
            
            # Registrar resultado
            result = {
                "file": pdf_file.name,
                "manufacturer": manufacturer,
                "footer_preview": footer[:100] + "..." if len(footer) > 100 else footer
            }
            self.results.append(result)
            
            # Exibir progresso
            icon = "🟢" if manufacturer != "Unknown" else "🔴"
            print(f"[{idx:2d}/{total_files}] {icon} {pdf_file.name[:50]:<50} → {manufacturer}")
        
        print("-" * 70)
        print()
        
        # Exibir estatísticas
        print("=" * 70)
        print("                    📊 ESTATÍSTICAS FINAIS")
        print("=" * 70)
        print()
        print(f"🏭 GE (General Electric):     {manufacturers_count['GE']:3d} PDFs  ({manufacturers_count['GE']/total_files*100:5.1f}%)")
        print(f"🏭 Schneider Electric:        {manufacturers_count['Schneider Electric']:3d} PDFs  ({manufacturers_count['Schneider Electric']/total_files*100:5.1f}%)")
        print(f"❓ Unknown (não identificado): {manufacturers_count['Unknown']:3d} PDFs  ({manufacturers_count['Unknown']/total_files*100:5.1f}%)")
        print()
        print(f"📊 Total processado:          {total_files:3d} PDFs")
        print()
        
        # Se houver Unknown, listar
        if manufacturers_count['Unknown'] > 0:
            print("⚠️  ARQUIVOS NÃO IDENTIFICADOS:")
            print("-" * 70)
            for result in self.results:
                if result['manufacturer'] == 'Unknown':
                    print(f"  • {result['file']}")
                    print(f"    Rodapé: {result['footer_preview']}")
                    print()
        
        print("=" * 70)
        
        return {
            "total": total_files,
            "counts": manufacturers_count,
            "details": self.results
        }
    
    def generate_mapping_file(self, output_file: str = "manufacturer_mapping.txt"):
        """Gera arquivo de mapeamento PDF → Fabricante"""
        output_path = Path(output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# MAPEAMENTO PDF → FABRICANTE\n")
            f.write("# Gerado automaticamente pela análise de rodapés\n")
            f.write(f"# Total: {len(self.results)} arquivos\n")
            f.write("#" + "=" * 68 + "\n\n")
            
            for result in self.results:
                f.write(f"{result['file']}\t{result['manufacturer']}\n")
        
        print(f"✅ Mapeamento salvo em: {output_path}")


def main():
    """Função principal"""
    # Diretório dos PDFs
    pdf_directory = "inputs/pdf"
    
    # Verificar se o diretório existe
    if not Path(pdf_directory).exists():
        print(f"❌ Erro: Diretório {pdf_directory} não encontrado!")
        print(f"   Executando de: {os.getcwd()}")
        return
    
    # Criar identificador
    identifier = ManufacturerIdentifier(pdf_directory)
    
    # Analisar todos os PDFs
    stats = identifier.analyze_all_pdfs()
    
    # Gerar arquivo de mapeamento
    identifier.generate_mapping_file("outputs/audit/manufacturer_mapping.txt")
    
    print()
    print("🎯 Análise concluída!")
    print()
    
    # Sugestão de próximo passo
    if stats['counts']['Unknown'] == 0:
        print("✅ TODOS os fabricantes foram identificados com sucesso!")
        print("   Próximo passo: Atualizar o código de processamento para usar esses dados.")
    else:
        print("⚠️  Alguns PDFs não foram identificados.")
        print("   Verifique manualmente os arquivos listados acima.")


if __name__ == "__main__":
    main()

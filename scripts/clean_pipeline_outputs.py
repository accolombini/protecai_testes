"""
🧹 LIMPEZA CONTROLADA DA PIPELINE
==================================

Remove arquivos de testes anteriores das pastas de output da pipeline,
preservando backups e mantendo estrutura de diretórios.

Autor: ProtecAI Team
Data: 06/11/2025
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class PipelineCleaner:
    """Limpa pastas da pipeline de forma controlada"""
    
    FOLDERS_TO_CLEAN = [
        'outputs/norm_csv',
        'outputs/norm_excel',
        'outputs/hybrid_csv',
        'outputs/sql',
        'outputs/universal_parser',
        'outputs/reports',
    ]
    
    BACKUP_FOLDER = 'outputs/pipeline_backup_{timestamp}'
    
    def __init__(self, project_root: str, create_backup: bool = True):
        """
        Inicializa cleaner
        
        Args:
            project_root: Raiz do projeto
            create_backup: Se True, cria backup antes de limpar
        """
        self.project_root = Path(project_root)
        self.create_backup = create_backup
        self.backup_path = None
        
        if create_backup:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.backup_path = self.project_root / self.BACKUP_FOLDER.format(timestamp=timestamp)
    
    def analyze(self) -> dict:
        """
        Analisa o que será limpo
        
        Returns:
            Dicionário com estatísticas
        """
        logger.info("\n" + "="*80)
        logger.info("🔍 ANALISANDO PASTAS DA PIPELINE")
        logger.info("="*80 + "\n")
        
        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_folder': {}
        }
        
        for folder in self.FOLDERS_TO_CLEAN:
            folder_path = self.project_root / folder
            
            if not folder_path.exists():
                logger.info(f"📁 {folder}: (não existe)")
                continue
            
            files = list(folder_path.glob('*'))
            files = [f for f in files if f.is_file()]
            
            folder_size = sum(f.stat().st_size for f in files)
            
            stats['by_folder'][folder] = {
                'count': len(files),
                'size': folder_size,
                'files': [f.name for f in files]
            }
            
            stats['total_files'] += len(files)
            stats['total_size'] += folder_size
            
            logger.info(f"📁 {folder}:")
            logger.info(f"   • Arquivos: {len(files)}")
            logger.info(f"   • Tamanho: {self._format_size(folder_size)}")
            
            if len(files) > 0:
                logger.info(f"   • Exemplos:")
                for f in files[:3]:
                    logger.info(f"     - {f.name} ({self._format_size(f.stat().st_size)})")
                if len(files) > 3:
                    logger.info(f"     ... e mais {len(files) - 3} arquivo(s)")
            logger.info("")
        
        logger.info("="*80)
        logger.info(f"📊 TOTAL: {stats['total_files']} arquivos, {self._format_size(stats['total_size'])}")
        logger.info("="*80 + "\n")
        
        return stats
    
    def clean(self, dry_run: bool = False) -> bool:
        """
        Executa limpeza
        
        Args:
            dry_run: Se True, apenas simula a limpeza
            
        Returns:
            True se sucesso
        """
        logger.info("\n" + "="*80)
        if dry_run:
            logger.info("🧪 SIMULAÇÃO DE LIMPEZA (DRY RUN)")
        else:
            logger.info("🧹 EXECUTANDO LIMPEZA")
        logger.info("="*80 + "\n")
        
        # Criar backup se necessário
        if self.create_backup and not dry_run:
            logger.info(f"💾 Criando backup em: {self.backup_path.name}")
            self.backup_path.mkdir(parents=True, exist_ok=True)
        
        cleaned_count = 0
        
        for folder in self.FOLDERS_TO_CLEAN:
            folder_path = self.project_root / folder
            
            if not folder_path.exists():
                continue
            
            files = list(folder_path.glob('*'))
            files = [f for f in files if f.is_file()]
            
            if len(files) == 0:
                continue
            
            logger.info(f"📁 {folder}:")
            
            for file in files:
                if dry_run:
                    logger.info(f"   🗑️  [SIMULAÇÃO] Removeria: {file.name}")
                else:
                    # Backup
                    if self.create_backup:
                        backup_folder = self.backup_path / folder
                        backup_folder.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file, backup_folder / file.name)
                    
                    # Remover
                    file.unlink()
                    logger.info(f"   ✅ Removido: {file.name}")
                
                cleaned_count += 1
            
            logger.info("")
        
        logger.info("="*80)
        if dry_run:
            logger.info(f"🧪 SIMULAÇÃO COMPLETA: {cleaned_count} arquivo(s) seriam removidos")
        else:
            logger.info(f"✅ LIMPEZA COMPLETA: {cleaned_count} arquivo(s) removidos")
            if self.create_backup:
                logger.info(f"💾 Backup salvo em: {self.backup_path}")
        logger.info("="*80 + "\n")
        
        return True
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Formata tamanho em bytes para string legível"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Limpa pastas da pipeline')
    parser.add_argument('--no-backup', action='store_true', help='Não criar backup')
    parser.add_argument('--dry-run', action='store_true', help='Apenas simular')
    parser.add_argument('--force', action='store_true', help='Não pedir confirmação')
    
    args = parser.parse_args()
    
    # Obter raiz do projeto
    project_root = Path(__file__).parent.parent
    
    # Criar cleaner
    cleaner = PipelineCleaner(
        project_root=str(project_root),
        create_backup=not args.no_backup
    )
    
    # Analisar
    stats = cleaner.analyze()
    
    if stats['total_files'] == 0:
        logger.info("✅ Nada para limpar!")
        return
    
    # Pedir confirmação (exceto se --force ou --dry-run)
    if not args.force and not args.dry_run:
        response = input(f"\n⚠️  Deseja continuar com a limpeza de {stats['total_files']} arquivo(s)? [s/N]: ")
        if response.lower() not in ['s', 'sim', 'yes', 'y']:
            logger.info("❌ Limpeza cancelada pelo usuário")
            return
    
    # Executar limpeza
    cleaner.clean(dry_run=args.dry_run)


if __name__ == '__main__':
    main()

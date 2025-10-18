#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Registry Manager - Sistema de controle de arquivos processados
==================================================================

Este módulo gerencia o registro de arquivos já processados para evitar reprocessamento
desnecessário. Usa hash SHA-256 dos arquivos e timestamps para controle.

Funcionalidades:
- Registra arquivos processados com hash, timestamp e metadados
- Verifica se arquivo já foi processado (baseado em hash)
- Detecta mudanças nos arquivos
- Suporta múltiplos formatos: PDF, TXT, XLSX, CSV
- Armazena registro em JSON para persistência

Autor: Sistema ProtecAI
Data: 2025-10-17
"""

from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class FileRegistryManager:
    """Gerenciador de registro de arquivos processados."""
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Inicializa o gerenciador de registro.
        
        Args:
            registry_path: Caminho para o arquivo de registro JSON.
                          Se None, usa inputs/registry/processed_files.json
        """
        # Determinar caminho do projeto
        # Este arquivo está em src/, então project_root é o parent do src/
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[1]  # src/ -> project_root/
            
        # Caminho padrão do registro
        if registry_path is None:
            registry_path = project_root / "inputs" / "registry" / "processed_files.json"
        
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Carregar registro existente
        self.registry: Dict[str, Dict[str, Any]] = self._load_registry()
        
        logger.info(f"FileRegistryManager inicializado: {self.registry_path}")
        logger.info(f"Arquivos registrados: {len(self.registry)}")
    
    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        """Carrega registro existente do arquivo JSON."""
        if not self.registry_path.exists():
            logger.info("Arquivo de registro não encontrado. Criando novo registro.")
            return {}
        
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            logger.info(f"Registro carregado: {len(registry)} arquivos")
            return registry
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Erro ao carregar registro: {e}. Criando novo registro.")
            return {}
    
    def _save_registry(self) -> None:
        """Salva registro no arquivo JSON."""
        try:
            # Criar backup se arquivo existir
            if self.registry_path.exists():
                backup_path = self.registry_path.with_suffix('.json.bak')
                self.registry_path.rename(backup_path)
            
            # Salvar registro
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug(f"Registro salvo: {len(self.registry)} arquivos")
            
        except IOError as e:
            logger.error(f"Erro ao salvar registro: {e}")
            raise
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calcula hash SHA-256 de um arquivo.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Hash SHA-256 em hexadecimal
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Ler arquivo em chunks para economizar memória
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except IOError as e:
            logger.error(f"Erro ao calcular hash de {file_path}: {e}")
            raise
    
    def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Obtém metadados de um arquivo.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Dicionário com metadados do arquivo
        """
        try:
            stat = file_path.stat()
            return {
                "size_bytes": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": file_path.suffix.lower(),
                "absolute_path": str(file_path.resolve())
            }
        except OSError as e:
            logger.error(f"Erro ao obter metadados de {file_path}: {e}")
            return {}
    
    def is_file_processed(self, file_path: Union[str, Path]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verifica se um arquivo já foi processado.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            Tupla (foi_processado, dados_registro)
            - foi_processado: True se arquivo já foi processado
            - dados_registro: Dados do registro se existir, None caso contrário
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"Arquivo não encontrado: {file_path}")
            return False, None
        
        # Calcular hash atual
        try:
            current_hash = self._calculate_file_hash(file_path)
        except Exception as e:
            logger.error(f"Erro ao verificar arquivo {file_path}: {e}")
            return False, None
        
        # Verificar se hash existe no registro
        file_key = str(file_path.resolve())
        
        if file_key in self.registry:
            registry_data = self.registry[file_key]
            stored_hash = registry_data.get("file_hash")
            
            if stored_hash == current_hash:
                logger.debug(f"Arquivo já processado (hash igual): {file_path.name}")
                return True, registry_data
            else:
                logger.info(f"Arquivo modificado (hash diferente): {file_path.name}")
                return False, registry_data
        
        logger.debug(f"Arquivo novo (não registrado): {file_path.name}")
        return False, None
    
    def register_file(self, file_path: Union[str, Path], 
                     processing_result: Dict[str, Any],
                     output_files: Optional[List[str]] = None) -> None:
        """
        Registra um arquivo como processado.
        
        Args:
            file_path: Caminho para o arquivo processado
            processing_result: Resultado do processamento (estatísticas, status, etc.)
            output_files: Lista de arquivos de saída gerados (opcional)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"Não é possível registrar arquivo inexistente: {file_path}")
            return
        
        try:
            # Calcular hash e metadados
            file_hash = self._calculate_file_hash(file_path)
            metadata = self._get_file_metadata(file_path)
            
            # Criar entrada no registro
            file_key = str(file_path.resolve())
            
            self.registry[file_key] = {
                "file_name": file_path.name,
                "file_hash": file_hash,
                "processed_at": datetime.now().isoformat(),
                "metadata": metadata,
                "processing_result": processing_result,
                "output_files": output_files or [],
                "registry_version": "1.0"
            }
            
            # Salvar registro
            self._save_registry()
            
            logger.info(f"Arquivo registrado: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Erro ao registrar arquivo {file_path}: {e}")
            raise
    
    def get_processed_files(self, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retorna lista de arquivos processados.
        
        Args:
            file_type: Filtrar por extensão (.pdf, .txt, .xlsx, .csv). Se None, retorna todos.
            
        Returns:
            Lista de dicionários com dados dos arquivos processados
        """
        processed_files = []
        
        for file_key, registry_data in self.registry.items():
            # Filtrar por tipo se especificado
            if file_type:
                file_extension = registry_data.get("metadata", {}).get("extension", "")
                if file_extension != file_type.lower():
                    continue
            
            processed_files.append({
                "file_path": file_key,
                "file_name": registry_data.get("file_name"),
                "processed_at": registry_data.get("processed_at"),
                "file_hash": registry_data.get("file_hash"),
                "processing_result": registry_data.get("processing_result", {}),
                "output_files": registry_data.get("output_files", [])
            })
        
        # Ordenar por data de processamento (mais recente primeiro)
        processed_files.sort(key=lambda x: x.get("processed_at", ""), reverse=True)
        
        return processed_files
    
    def remove_file_from_registry(self, file_path: Union[str, Path]) -> bool:
        """
        Remove um arquivo do registro.
        
        Args:
            file_path: Caminho para o arquivo
            
        Returns:
            True se arquivo foi removido, False se não estava registrado
        """
        file_key = str(Path(file_path).resolve())
        
        if file_key in self.registry:
            file_name = self.registry[file_key].get("file_name", "unknown")
            del self.registry[file_key]
            self._save_registry()
            
            logger.info(f"Arquivo removido do registro: {file_name}")
            return True
        
        logger.warning(f"Arquivo não estava registrado: {Path(file_path).name}")
        return False
    
    def cleanup_missing_files(self) -> int:
        """
        Remove do registro arquivos que não existem mais no sistema.
        
        Returns:
            Número de arquivos removidos do registro
        """
        missing_files = []
        
        for file_key in self.registry.keys():
            if not Path(file_key).exists():
                missing_files.append(file_key)
        
        # Remover arquivos ausentes
        for file_key in missing_files:
            file_name = self.registry[file_key].get("file_name", "unknown")
            del self.registry[file_key]
            logger.info(f"Arquivo ausente removido do registro: {file_name}")
        
        if missing_files:
            self._save_registry()
            logger.info(f"Limpeza concluída: {len(missing_files)} arquivos removidos")
        
        return len(missing_files)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do registro.
        
        Returns:
            Dicionário com estatísticas
        """
        if not self.registry:
            return {
                "total_files": 0,
                "by_extension": {},
                "oldest_processed": None,
                "newest_processed": None,
                "registry_path": str(self.registry_path)
            }
        
        # Contar por extensão
        by_extension = {}
        processed_dates = []
        
        for registry_data in self.registry.values():
            extension = registry_data.get("metadata", {}).get("extension", "unknown")
            by_extension[extension] = by_extension.get(extension, 0) + 1
            
            processed_at = registry_data.get("processed_at")
            if processed_at:
                processed_dates.append(processed_at)
        
        processed_dates.sort()
        
        return {
            "total_files": len(self.registry),
            "by_extension": by_extension,
            "oldest_processed": processed_dates[0] if processed_dates else None,
            "newest_processed": processed_dates[-1] if processed_dates else None,
            "registry_path": str(self.registry_path)
        }
    
    def export_registry(self, export_path: Union[str, Path]) -> None:
        """
        Exporta registro para arquivo JSON.
        
        Args:
            export_path: Caminho para arquivo de exportação
        """
        export_path = Path(export_path)
        
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Registro exportado para: {export_path}")
            
        except IOError as e:
            logger.error(f"Erro ao exportar registro: {e}")
            raise


# Função de conveniência para uso simples
def create_file_registry(registry_path: Optional[Path] = None) -> FileRegistryManager:
    """
    Função de conveniência para criar um FileRegistryManager.
    
    Args:
        registry_path: Caminho para arquivo de registro (opcional)
        
    Returns:
        Instância de FileRegistryManager
    """
    return FileRegistryManager(registry_path)


# Exemplo de uso
if __name__ == "__main__":
    # Configurar logging para exemplo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Criar gerenciador
    registry = FileRegistryManager()
    
    # Exemplo de uso básico
    print("=== EXEMPLO DE USO DO FILE REGISTRY MANAGER ===")
    
    # Estatísticas
    stats = registry.get_statistics()
    print(f"\nEstatísticas do registro:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\nArquivos processados por tipo:")
    for ext, count in stats.get("by_extension", {}).items():
        print(f"  {ext}: {count} arquivo(s)")
    
    # Listar arquivos processados
    processed = registry.get_processed_files()
    print(f"\nÚltimos arquivos processados:")
    for file_info in processed[:5]:  # Mostrar apenas os 5 mais recentes
        print(f"  - {file_info['file_name']} ({file_info['processed_at']})")
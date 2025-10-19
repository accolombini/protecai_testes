"""
Configurações da API ProtecAI
============================

Centralizador de configurações do sistema.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Configurações da aplicação"""
    
    # API Settings
    PROJECT_NAME: str = "ProtecAI API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "protecai"
    POSTGRES_PASSWORD: str = "protecai"
    POSTGRES_DB: str = "protecai_db"
    POSTGRES_PORT: int = 5432
    
    DATABASE_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # Security Settings
    SECRET_KEY: str = "protecai-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ETAP Integration Settings (Preparatório)
    ETAP_HOST: Optional[str] = None
    ETAP_PORT: Optional[int] = None
    ETAP_API_KEY: Optional[str] = None
    
    # ML Module Settings (Preparatório)
    ML_SERVICE_URL: Optional[str] = None
    ML_API_KEY: Optional[str] = None
    
    # File Upload Settings
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# Instância global das configurações
settings = Settings()
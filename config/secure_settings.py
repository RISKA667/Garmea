"""
Configuration sécurisée avec variables d'environnement
"""
import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    """Configuration sécurisée de l'application"""
    
    # Application
    app_name: str = "Garméa"
    debug: bool = False
    version: str = "2.0.0"
    
    # Sécurité
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Base de données
    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10
    
    # Cache Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_hours: int = 24
    
    # Sécurité réseau
    allowed_hosts: List[str] = ["*"]
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Fichiers
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "/tmp/garmea_uploads"
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_minutes: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/garmea.log"
    
    # Monitoring
    metrics_enabled: bool = True
    health_check_interval: int = 30
    
    @validator('jwt_secret_key')
    def jwt_secret_must_be_set(cls, v):
        if not v:
            raise ValueError('JWT_SECRET_KEY must be set')
        if len(v) < 32:
            raise ValueError('JWT_SECRET_KEY must be at least 32 characters')
        return v
    
    @validator('database_url')
    def database_url_must_be_set(cls, v):
        if not v:
            raise ValueError('DATABASE_URL must be set')
        return v
    
    @validator('cors_origins')
    def validate_cors_origins(cls, v):
        if not isinstance(v, list):
            return v.split(',') if isinstance(v, str) else [v]
        return v
    
    @validator('allowed_hosts')
    def validate_allowed_hosts(cls, v):
        if not isinstance(v, list):
            return v.split(',') if isinstance(v, str) else [v]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Factory pour la configuration (avec cache)"""
    return Settings()
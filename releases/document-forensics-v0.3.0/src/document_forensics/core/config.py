"""Configuration settings for the document forensics system."""

import os
from typing import Optional, List

try:
    from pydantic_settings import BaseSettings
    from pydantic import field_validator
    PYDANTIC_SETTINGS_AVAILABLE = True
except ImportError:
    # Fallback for when pydantic-settings is not available
    from pydantic import BaseModel as BaseSettings, field_validator
    PYDANTIC_SETTINGS_AVAILABLE = False


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "Document Forensics System"
    app_version: str = "0.1.0"
    debug: bool = False
    sql_debug: bool = False
    
    # Database settings
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/document_forensics"
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # File upload settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    upload_directory: str = "uploads"
    allowed_file_types: str = "application/pdf,image/jpeg,image/png,image/tiff,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain"
    
    @field_validator("allowed_file_types")
    @classmethod
    def parse_allowed_file_types(cls, v):
        """Parse comma-separated file types into a list."""
        if isinstance(v, str):
            return [ft.strip() for ft in v.split(',')]
        return v
    
    # AI/ML model settings
    models_directory: str = "models"
    cv_model_path: Optional[str] = None
    nlp_model_path: Optional[str] = None
    
    # Processing settings
    max_concurrent_jobs: int = 4
    job_timeout_minutes: int = 30
    
    # Logging settings
    log_level: str = "INFO"
    log_directory: str = "logs"
    
    # API settings
    API_BASE_URL: str = "http://localhost:8000/api/v1"
    api_rate_limit: str = "100/minute"
    cors_origins: str = "http://localhost:3000,http://localhost:8501"
    allowed_origins: str = "http://localhost:3000,http://localhost:8501"
    
    @field_validator("cors_origins", "allowed_origins")
    @classmethod
    def parse_origins(cls, v):
        """Parse comma-separated origins into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "sqlite:///")):
            raise ValueError("Database URL must start with postgresql:// or sqlite:///")
        return v
    
    @field_validator("upload_directory")
    @classmethod
    def create_upload_directory(cls, v):
        """Ensure upload directory exists."""
        os.makedirs(v, exist_ok=True)
        return v
    
    @field_validator("log_directory")
    @classmethod
    def create_log_directory(cls, v):
        """Ensure log directory exists."""
        os.makedirs(v, exist_ok=True)
        return v
    
    @field_validator("models_directory")
    @classmethod
    def create_models_directory(cls, v):
        """Ensure models directory exists."""
        os.makedirs(v, exist_ok=True)
        return v
    
    if PYDANTIC_SETTINGS_AVAILABLE:
        class Config:
            env_file = ".env"
            case_sensitive = False
            extra = "ignore"  # Ignore extra fields from .env


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
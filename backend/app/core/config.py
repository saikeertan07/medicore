import os
from typing import List, Literal, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MediCore AI"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Database selection
    ENVIRONMENT: Literal["development", "production", "testing"] = os.getenv("ENVIRONMENT", "development")
    DATABASE_ENGINE: Literal["postgresql", "sqlite"] = os.getenv("DATABASE_ENGINE", "sqlite")
    
    # PostgreSQL Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/medicore"
    )
    # SQLite fallback (strictly for development / local testing)
    SQLITE_URL: str = os.getenv("SQLITE_URL", "sqlite:///./medicore.db")
    
    # Security & Tokens
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))  # Short-lived (30m) with secure refresh rotation
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    HOSPITAL_TIMEZONE: str = os.getenv("HOSPITAL_TIMEZONE", "UTC")

    
    # AI Engine Configuration
    AI_PROVIDER: Literal["gemini", "mock"] = os.getenv("AI_PROVIDER", "gemini" if os.getenv("GEMINI_API_KEY") else "mock")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    
    # Storage & Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "png", "jpg", "jpeg", "doc", "docx"]
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

# Enforce security checks in production
if settings.ENVIRONMENT == "production":
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32 or "change_me" in settings.SECRET_KEY.lower() or "secret-key" in settings.SECRET_KEY.lower():
        raise RuntimeError(
            "FATAL: In production mode, a cryptographically strong SECRET_KEY of at least 32 characters "
            "must be explicitly set in the environment. Default, weak, or placeholder keys are strictly rejected."
        )
    if settings.DATABASE_ENGINE != "postgresql":
        raise RuntimeError(
            "FATAL: In production mode, DATABASE_ENGINE must be set to 'postgresql'. "
            "SQLite is strictly prohibited for production healthcare deployments."
        )
    if any(placeholder in settings.DATABASE_URL.lower() for placeholder in ["postgres:postgres", "medicore_secure_pass", "change_me", "password123"]):
        raise RuntimeError(
            "FATAL: In production mode, a strong non-default POSTGRES_PASSWORD must be configured in DATABASE_URL. "
            "Default, weak, or placeholder credentials are strictly rejected."
        )
elif not settings.SECRET_KEY:
    # Non-production (local development / testing only) fallback
    settings.SECRET_KEY = "dev_insecure_key_for_testing_only_not_for_production"


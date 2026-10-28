"""Application configuration module using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings validated at runtime."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core environment
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = Field(default=8000, ge=1, le=65535)

    # CORS origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Paths (Dynamically resolved relative to project root, no hardcoded absolute paths)
    PROJECT_ROOT: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
    )
    DATA_DIR_NAME: str = "data"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///data/recruit_lens.db"

    # Authentication & JWT
    JWT_SECRET_KEY: str = Field(
        default="recruitlens-dev-secret-key-change-in-production-123456789",
        description="Secret key for JWT signature",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, ge=5, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=30)

    # LLM Settings (Free Tier / Self-Hosted)
    GROQ_API_KEY: str = Field(default="", description="Optional Groq API key")
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-120b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    LLM_CACHE_ENABLED: bool = True
    LLM_MAX_RPM: int = Field(default=30, ge=1, le=100)
    LLM_MAX_TPM: int = Field(default=7000, ge=500, le=50000)
    LLM_REQUEST_TIMEOUT_SECONDS: float = Field(default=20.0, ge=1.0, le=120.0)
    LLM_MAX_RETRIES: int = Field(default=3, ge=0, le=5)

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    # Performance & Concurrency Limits
    MAX_BATCH_RESUMES: int = Field(default=200, ge=1, le=1000)
    MAX_UPLOAD_FILE_SIZE_MB: int = Field(default=10, ge=1, le=100)

    # Retrieval & Embeddings Configuration
    EMBEDDING_MODEL: Literal["minilm", "bge-small"] = "minilm"
    PRIMARY_RETRIEVAL_ENGINE: Literal["bm25", "hybrid", "dense"] = "bm25"

    # Storage Abstraction
    STORAGE_BACKEND: Literal["local", "supabase"] = "local"
    SUPABASE_URL: str = Field(default="", description="Supabase project URL")
    SUPABASE_KEY: str = Field(default="", description="Supabase anon/service-role API key")
    SUPABASE_STORAGE_BUCKET: str = "resumes"
    SUPABASE_DATABASE_URL: str = Field(
        default="", description="Optional Supabase Postgres connection string"
    )

    # Demo & Admin Credentials (read strictly from env)
    DEMO_RECRUITER_EMAIL: str = Field(default="recruiter@recruitlens.local")
    DEMO_RECRUITER_PASSWORD: str = Field(default="RecruiterDemoPass123!")

    # Security & Policies
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    EMAIL_DRY_RUN: bool = True
    DAILY_EMAIL_CAP: int = Field(default=50, ge=1, le=1000)
    DAILY_TOKEN_BUDGET: int = Field(default=50000, ge=1000, le=1000000)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        """Parse CORS origins if provided as comma-separated string."""
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                import json

                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def data_dir(self) -> Path:
        """Resolve absolute data directory dynamically from project root."""
        path = self.PROJECT_ROOT / self.DATA_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path


# Singleton settings instance
settings = Settings()

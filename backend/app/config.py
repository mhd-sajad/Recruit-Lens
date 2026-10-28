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

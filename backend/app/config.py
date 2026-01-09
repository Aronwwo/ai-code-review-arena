"""Application configuration and settings."""
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "AI Code Review Arena"
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./data/code_review.db"

    # Redis
    redis_url: str | None = "redis://localhost:6379/0"

    # Security
    jwt_secret_key: str = Field(
        default="dev_secret_key_change_in_production",
        description="Secret key for JWT encoding"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173"

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    max_file_size_mb: int = 10
    max_files_per_project: int = 100

    # LLM Providers
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    cloudflare_api_token: str | None = None
    cloudflare_account_id: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # Default LLM Configuration
    default_provider: Literal["groq", "gemini", "cloudflare", "ollama", "mock"] = "mock"
    default_model: str = "mixtral-8x7b-32768"

    # Agent Configuration
    max_conversation_turns: int = 5
    enable_agent_caching: bool = True
    cache_ttl_hours: int = 24

    # Logging
    log_level: str = "INFO"

    # Testing
    test_database_url: str = "sqlite:///./test.db"

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (replace postgresql+asyncpg with postgresql)."""
        return self.database_url.replace("+asyncpg", "")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cache_ttl_seconds(self) -> int:
        """Get cache TTL in seconds."""
        return self.cache_ttl_hours * 3600


# Global settings instance
settings = Settings()

"""Application configuration and settings.

Ten plik zarządza WSZYSTKIMI ustawieniami aplikacji. Ustawienia pochodzą z:
1. Plik .env (główne źródło - NIGDY nie commituj .env do Git!)
2. Zmienne środowiskowe (environment variables)
3. Wartości domyślne (fallback)

Pydantic Settings automatycznie waliduje typy i ładuje wartości.
"""
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Kolejność ładowania (od najważniejszego):
    1. Zmienne środowiskowe (export DATABASE_URL=...)
    2. Plik .env w głównym katalogu
    3. Wartości domyślne zdefiniowane poniżej

    Przykład użycia w kodzie:
        from app.config import settings
        print(settings.database_url)  # sqlite:///./data/code_review.db
    """

    # ==================== PYDANTIC CONFIG ====================
    model_config = SettingsConfigDict(
        env_file=".env",  # Ładuj z pliku .env
        env_file_encoding="utf-8",  # Kodowanie UTF-8
        case_sensitive=False,  # DATABASE_URL = database_url (nie ma znaczenia)
        extra="ignore"  # Ignoruj nieznane zmienne w .env
    )

    # ==================== APPLICATION ====================
    app_name: str = "AI Code Review Arena"
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = True  # Włącza verbose logging i stack traces

    # ==================== DATABASE ====================
    # SQLite dla development, PostgreSQL dla production
    database_url: str = "sqlite:///./data/code_review.db"
    # Przykłady:
    # - SQLite: "sqlite:///./data/code_review.db"
    # - PostgreSQL: "postgresql://user:pass@localhost/dbname"

    # ==================== REDIS ====================
    # Redis dla cache i rate limiting (opcjonalnie - fallback to in-memory)
    redis_url: str | None = "redis://localhost:6379/0"
    # None = użyj in-memory cache

    # ==================== SECURITY ====================
    jwt_secret_key: str = Field(
        default="dev_secret_key_change_in_production",  # ⚠️ ZMIEŃ W PRODUKCJI!
        description="Secret key for JWT encoding"
    )
    jwt_algorithm: str = "HS256"  # Algorytm podpisu JWT
    jwt_access_token_expire_minutes: int = 60  # Token wygasa po 1h

    # ==================== CORS ====================
    # Lista dozwolonych domen dla cross-origin requests (comma-separated)
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:5173"
    # Production: "https://yourdomain.com,https://www.yourdomain.com"

    def get_cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins.

        Input: "http://localhost:3000,http://localhost:5173"
        Output: ["http://localhost:3000", "http://localhost:5173"]
        """
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ==================== RATE LIMITING ====================
    rate_limit_enabled: bool = True  # Włącz rate limiting (60 req/min)
    rate_limit_per_minute: int = 60  # Maksymalnie 60 requestów na minutę per IP
    max_file_size_mb: int = 10  # Maksymalny rozmiar pliku: 10MB
    max_files_per_project: int = 100  # Maksymalnie 100 plików w projekcie

    # ==================== LLM PROVIDERS ====================
    # API keys dla zewnętrznych providerów AI (opcjonalne)
    groq_api_key: str | None = None  # Groq Cloud (llama-3.3-70b)
    gemini_api_key: str | None = None  # Google Gemini (gemini-1.5-flash)
    cloudflare_api_token: str | None = None  # Cloudflare Workers AI
    cloudflare_account_id: str | None = None
    ollama_base_url: str = "http://localhost:11434"  # Ollama lokalnie

    # ==================== DEFAULT LLM CONFIGURATION ====================
    # Domyślny provider i model używany jeśli user nie wybierze
    default_provider: Literal["groq", "gemini", "cloudflare", "ollama", "mock"] = "mock"
    default_model: str = "mixtral-8x7b-32768"
    # Provider "mock" - używa przykładowych odpowiedzi (bez wywołań API)

    # ==================== AGENT CONFIGURATION ====================
    max_conversation_turns: int = 5  # Maksymalnie 5 rund dyskusji w Council mode
    council_rounds: int = 2  # Liczba rund dyskusji w Council mode
    enable_agent_caching: bool = True  # Cache odpowiedzi agentów (oszczędność kosztów)
    cache_ttl_hours: int = 24  # Cache ważny przez 24h
    max_prompt_chars: int = 12000  # Maksymalna długość promptu przed przycięciem
    default_timeout_seconds: int = 300  # Domyślny timeout dla agentów (5 minut)
    default_max_tokens: int = 4096  # Domyślna liczba max tokenów w odpowiedzi

    # ==================== FILE VALIDATION ====================
    file_min_length: int = 10  # Minimalna długość pliku (znaki)
    file_line_uniqueness_threshold: float = 0.3  # Próg unikalności linii (30%)

    # ==================== LOGGING ====================
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # ==================== TESTING ====================
    test_database_url: str = "sqlite:///./test.db"  # Osobna baza dla testów

    # ==================== HELPER PROPERTIES ====================
    # @property = computed field (obliczany dynamicznie)

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL.

        Konwertuje async URL na sync (dla Alembic migrations).
        postgresql+asyncpg://... → postgresql://...
        """
        return self.database_url.replace("+asyncpg", "")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode.

        Returns:
            True jeśli environment == "production"
        """
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode.

        Returns:
            True jeśli environment == "development"
        """
        return self.environment == "development"

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes.

        Konwersja: 10 MB → 10 * 1024 * 1024 = 10485760 bytes

        Returns:
            int: Maksymalny rozmiar pliku w bajtach
        """
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cache_ttl_seconds(self) -> int:
        """Get cache TTL in seconds.

        Konwersja: 24 hours → 24 * 3600 = 86400 seconds

        Returns:
            int: Cache TTL w sekundach
        """
        return self.cache_ttl_hours * 3600


# ==================== GLOBAL SETTINGS INSTANCE ====================
# Ta instancja jest używana w całej aplikacji
# Import: from app.config import settings
settings = Settings()  # Automatycznie ładuje wartości z .env

# ==================== PRODUCTION SAFETY CHECKS ====================
# Sprawdzenie niebezpiecznych konfiguracji w produkcji
if settings.is_production and settings.log_level.upper() == 'DEBUG':
    import warnings
    warnings.warn(
        "⚠️  WARNING: DEBUG logging is enabled in PRODUCTION! "
        "This may expose sensitive data (passwords, tokens, API keys) in logs. "
        "Set LOG_LEVEL=INFO in production .env file.",
        stacklevel=2
    )

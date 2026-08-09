import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    DEMO_MODE: bool = Field(default=True)
    INLINE_PROCESSING: bool = Field(default=False)
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)

    # Database settings
    # For local/testing fallback, we default to a sqlite-like postgres format or generic placeholder
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/lossline"
    )
    DIRECT_DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/lossline"
    )

    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Intelligence pipeline (CONFIG_DEFAULT — not business facts)
    WINDOW_MINUTES: int = Field(default=30)
    WINDOW_SLIDE_MINUTES: int = Field(default=5)
    BASELINE_HISTORY_WINDOWS: int = Field(default=4)
    INCIDENT_DEDUP_MINUTES: int = Field(default=60)
    # M0 fixture baseline cancellation rate when history is sparse
    M0_FIXTURE_CANCELLATION_RATE: float = Field(default=0.07)
    M0_FIXTURE_ORDER_COUNT: float = Field(default=18.0)
    M0_FIXTURE_AVG_PREP_MINUTES: float = Field(default=12.0)
    M0_FIXTURE_AVG_HANDOFF_MINUTES: float = Field(default=3.0)
    ENABLE_SYNTHETIC_FIXTURE_BASELINES: bool = Field(default=False)
    CONFIG_VERSION: str = Field(default="config.v1")
    RECOMMENDATION_EXPIRY_MINUTES: int = Field(default=15)
    OUTCOME_MIN_EVENTS: int = Field(default=3)
    STREAM_MAX_RETRIES: int = Field(default=3)
    MAX_REQUEST_BYTES: int = Field(default=256 * 1024, gt=0)
    CORS_ORIGINS: str = Field(default="http://localhost:3000")
    INGEST_API_KEY: str | None = Field(default=None)
    MANAGER_API_KEY: str | None = Field(default=None)
    ADMIN_API_KEY: str | None = Field(default=None)
    ALLOW_GLOBAL_DEMO_RESET: bool = Field(default=False)
    WS_ALLOWED_ORIGINS: str = Field(default="http://localhost:3000")

    # (Optional) LLM & Tracing configurations — LangGraph deferred until
    # deterministic detection → correlate → recommend path is proven.
    LLM_API_KEY: str | None = Field(default=None)
    LLM_MODEL: str = Field(default="gpt-4.1-mini")
    LLM_BASE_URL: str = Field(default="https://api.openai.com/v1")
    LLM_TIMEOUT_SECONDS: float = Field(default=8.0, gt=0)
    LANGSMITH_API_KEY: str | None = Field(default=None)
    LANGCHAIN_TRACING_V2: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instantiate settings
settings = Settings()

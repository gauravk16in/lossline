import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
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

    # (Optional) LLM & Tracing configurations
    LLM_API_KEY: str | None = Field(default=None)
    LANGSMITH_API_KEY: str | None = Field(default=None)
    LANGCHAIN_TRACING_V2: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()

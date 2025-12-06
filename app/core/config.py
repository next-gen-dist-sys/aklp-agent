"""Application configuration."""

import os
import tomllib
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_openai_api_key() -> str:
    """Get OpenAI API key from ~/.aklp/config.toml or environment variable.

    Priority:
    1. ~/.aklp/config.toml (shared config file)
    2. OPENAI_API_KEY environment variable (fallback)

    Returns:
        str: API key if found, empty string otherwise.
    """
    # Try config file first
    config_file = Path.home() / ".aklp" / "config.toml"
    if config_file.exists():
        try:
            config = tomllib.loads(config_file.read_text())
            key = config.get("openai", {}).get("api_key")
            if key:
                return key
        except Exception:
            pass  # Fall through to environment variable

    # Fallback to environment variable
    return os.environ.get("OPENAI_API_KEY", "")


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "aklp-agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aklp_agent"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # OpenAI
    OPENAI_API_KEY: str = Field(default_factory=get_openai_api_key)
    OPENAI_MODEL: str = "gpt-5-mini"
    OPENAI_TIMEOUT: int = 60


settings = Settings()

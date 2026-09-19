from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from MEMORIA_* environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MEMORIA_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Memoria API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://memoria:memoria_dev_only@127.0.0.1:5432/memoria"


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""
FastAPI configuration.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings
    """
    es_scheme: str = "http"
    es_host: str = "localhost"
    es_port: int = 9200
    es_username: str | None = None
    es_password: str | None = None
    mongo_connection: str = "mongodb://localhost:27017"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings
    :return:
    """
    return Settings()

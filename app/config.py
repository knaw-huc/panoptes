"""
FastAPI configuration.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings
    """
    es_scheme: str
    es_host: str
    es_port: int = 9200
    mongo_connection: str

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings
    :return:
    """
    return Settings()

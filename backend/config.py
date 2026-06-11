from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/scentscience"
    anthropic_api_key: str = ""
    fragrantica_scrape_delay: float = 3.0
    model_version: str = "1.0.0"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    secret_key: str = "dev-secret-key"
    models_dir: str = "ml/models"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()

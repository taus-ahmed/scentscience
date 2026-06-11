from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", protected_namespaces=("settings_",))

    database_url: str = "postgresql://user:password@localhost:5432/scentscience"
    anthropic_api_key: str = ""
    fragrantica_scrape_delay: float = 3.0
    model_version: str = "1.0.0"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    secret_key: str = "dev-secret-key"
    models_dir: str = "ml/models"

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not url.startswith("postgresql+asyncpg://"):
            url = url.replace(url.split("://")[0], "postgresql+asyncpg", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()

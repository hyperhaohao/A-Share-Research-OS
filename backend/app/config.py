"""Application settings.

Backend protocol values are stable codes/enums (see AGENTS.md §15):
human-readable text is never used as a protocol value. Localizable
backend-generated text is resolved through message codes per requested
language.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASRO_", env_file=".env", extra="ignore")

    app_name: str = "A-Share Research OS"
    debug: bool = False
    # CORS origins for the frontend dev server / deployment. Empty list = same-origin only.
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Development default is file SQLite; production target is PostgreSQL (任务书 §5).
    database_url: str = "sqlite:///./asro_dev.db"
    auth_enabled: bool = False
    jwt_secret: str = "asro-dev-secret-change-in-production"
    jwt_expiry_hours: int = 24


@lru_cache
def get_settings() -> Settings:
    return Settings()


def app_version() -> str:
    return __version__

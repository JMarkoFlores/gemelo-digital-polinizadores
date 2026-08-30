from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    app_name: str = "Gemelos Digitales API"
    database_url: str = "postgresql+psycopg2://gemelos_user:gemelos_password@db:5432/gemelos_db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    admin_email: str = "admin@example.com"
    admin_password: str = "Admin12345!"
    client_email: str = "cliente@example.com"
    client_password: str = "Cliente12345!"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"
    model_dir: str = "/modelos_ia"
    model_filename: str = "modelo_optimizado.h5"
    model_metadata_filename: str = "modelo_optimizado_metadata.json"
    cache_ttl_seconds: int = 900
    cache_max_items: int = 64

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

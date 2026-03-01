from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    issuer: AnyHttpUrl = Field(..., alias="ISSUER")
    database_url: str = Field(..., alias="DATABASE_URL")
    app_secret: str = Field("dev-secret-change", alias="APP_SECRET")
    access_token_ttl_seconds: int = Field(3600, alias="ACCESS_TOKEN_TTL_SECONDS")
    id_token_ttl_seconds: int = Field(3600, alias="ID_TOKEN_TTL_SECONDS")
    auth_code_ttl_seconds: int = Field(300, alias="AUTH_CODE_TTL_SECONDS")
    secure_cookies: bool = Field(False, alias="SECURE_COOKIES")


@lru_cache
def get_settings() -> Settings:
    return Settings()

import json
from functools import lru_cache
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Investhome OS API", alias="API_APP_NAME")
    app_version: str = Field(default="0.1.0", alias="API_APP_VERSION")
    environment: str = Field(default="development", alias="API_ENVIRONMENT")
    debug: bool = Field(default=False, alias="API_DEBUG")
    enable_openapi: bool = Field(default=True, alias="API_ENABLE_OPENAPI")

    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")

    database_url: str = Field(
        default="postgresql+psycopg://investhome:investhome@localhost:5432/investhome",
        alias="DATABASE_URL",
    )

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:3000"],
        alias="API_CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return ["http://localhost:3000"]
        if isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return ["http://localhost:3000"]
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if not isinstance(parsed, list):
                    msg = "API_CORS_ORIGINS JSON value must be an array"
                    raise ValueError(msg)
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        msg = "API_CORS_ORIGINS must be a JSON array or comma-separated string"
        raise ValueError(msg)


@lru_cache
def get_settings() -> Settings:
    return Settings()

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

    jwt_secret: str = Field(
        default="dev-only-change-in-production-use-long-random-string",
        alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=480, alias="JWT_EXPIRE_MINUTES")
    auth_enabled: bool = Field(default=True, alias="API_AUTH_ENABLED")
    auth_cookie_name: str = Field(default="ih_session", alias="AUTH_COOKIE_NAME")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: str = Field(default="lax", alias="AUTH_COOKIE_SAMESITE")

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:3000"],
        alias="API_CORS_ORIGINS",
    )

    document_storage_root: str = Field(
        default="/var/lib/investhome/documents",
        alias="DOCUMENT_STORAGE_ROOT",
    )
    document_storage_provider: str = Field(default="local", alias="DOCUMENT_STORAGE_PROVIDER")
    document_max_upload_bytes: int = Field(
        default=52_428_800,
        alias="DOCUMENT_MAX_UPLOAD_BYTES",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    document_processing_sync: bool = Field(default=False, alias="DOCUMENT_PROCESSING_SYNC")
    document_processing_max_retries: int = Field(default=3, alias="DOCUMENT_PROCESSING_MAX_RETRIES")
    document_text_preview_chars: int = Field(default=2000, alias="DOCUMENT_TEXT_PREVIEW_CHARS")
    document_extracted_text_subdir: str = Field(
        default="extracted-text",
        alias="DOCUMENT_EXTRACTED_TEXT_SUBDIR",
    )

    ai_provider: str = Field(default="local", alias="AI_PROVIDER")
    ai_model: str = Field(default="local-heuristic-v1", alias="AI_MODEL")
    ai_api_key: str | None = Field(default=None, alias="AI_API_KEY")
    ai_allow_external_for_confidential: bool = Field(
        default=False,
        alias="AI_ALLOW_EXTERNAL_FOR_CONFIDENTIAL",
    )
    ai_allow_external_for_highly_confidential: bool = Field(
        default=False,
        alias="AI_ALLOW_EXTERNAL_FOR_HIGHLY_CONFIDENTIAL",
    )
    ocr_provider: str = Field(default="local", alias="OCR_PROVIDER")
    document_qa_history_retention_days: int = Field(
        default=90,
        alias="DOCUMENT_QA_HISTORY_RETENTION_DAYS",
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

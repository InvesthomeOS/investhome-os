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
    communication_credential_key: str | None = Field(
        default=None,
        alias="COMMUNICATION_CREDENTIAL_KEY",
        description="AES-256-GCM key for Email/WhatsApp tokens at rest. If unset, derived from JWT_SECRET via HKDF.",
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

    # Google Drive (Creative Studio asset scanner) — never hardcode secrets
    google_drive_client_id: str | None = Field(default=None, alias="GOOGLE_DRIVE_CLIENT_ID")
    google_drive_client_secret: str | None = Field(default=None, alias="GOOGLE_DRIVE_CLIENT_SECRET")
    google_drive_refresh_token: str | None = Field(default=None, alias="GOOGLE_DRIVE_REFRESH_TOKEN")
    google_drive_root_folder_id: str | None = Field(default=None, alias="GOOGLE_DRIVE_ROOT_FOLDER_ID")
    # Background incremental sync (safe local defaults: enabled, every 5 minutes)
    google_drive_sync_enabled: bool = Field(default=True, alias="GOOGLE_DRIVE_SYNC_ENABLED")
    google_drive_sync_interval_minutes: int = Field(
        default=5,
        alias="GOOGLE_DRIVE_SYNC_INTERVAL_MINUTES",
    )
    google_drive_sync_lock_ttl_minutes: int = Field(
        default=15,
        alias="GOOGLE_DRIVE_SYNC_LOCK_TTL_MINUTES",
    )
    google_drive_sync_max_retries: int = Field(default=3, alias="GOOGLE_DRIVE_SYNC_MAX_RETRIES")

    # Gmail mailbox OAuth reuses GOOGLE_DRIVE_CLIENT_ID / SECRET (Web client).
    # Do not reuse GOOGLE_DRIVE_REFRESH_TOKEN — that token is Drive-only.
    gmail_oauth_redirect_uri: str | None = Field(default=None, alias="GMAIL_OAUTH_REDIRECT_URI")
    gmail_sync_enabled: bool = Field(default=True, alias="GMAIL_SYNC_ENABLED")
    gmail_sync_interval_minutes: int = Field(default=5, alias="GMAIL_SYNC_INTERVAL_MINUTES")
    gmail_backfill_days: int = Field(default=30, alias="GMAIL_BACKFILL_DAYS")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    document_processing_sync: bool = Field(default=False, alias="DOCUMENT_PROCESSING_SYNC")
    document_processing_max_retries: int = Field(default=3, alias="DOCUMENT_PROCESSING_MAX_RETRIES")
    ai_index_processing_sync: bool = Field(default=False, alias="AI_INDEX_PROCESSING_SYNC")
    ai_index_max_download_bytes: int = Field(default=5_000_000, alias="AI_INDEX_MAX_DOWNLOAD_BYTES")

    # Semantic search / embeddings (local default — no external calls without keys)
    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="local-hash-v1", alias="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=64, alias="EMBEDDING_DIMENSIONS")
    embedding_api_key: str | None = Field(default=None, alias="EMBEDDING_API_KEY")
    embedding_base_url: str | None = Field(default=None, alias="EMBEDDING_BASE_URL")
    embedding_azure_endpoint: str | None = Field(default=None, alias="EMBEDDING_AZURE_ENDPOINT")
    embedding_azure_deployment: str | None = Field(default=None, alias="EMBEDDING_AZURE_DEPLOYMENT")
    embedding_azure_api_version: str = Field(
        default="2024-02-01",
        alias="EMBEDDING_AZURE_API_VERSION",
    )
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    vector_store_backend: str = Field(default="local", alias="VECTOR_STORE_BACKEND")
    ai_search_chunk_min_chars: int = Field(default=600, alias="AI_SEARCH_CHUNK_MIN_CHARS")
    ai_search_chunk_max_chars: int = Field(default=1200, alias="AI_SEARCH_CHUNK_MAX_CHARS")

    document_text_preview_chars: int = Field(default=2000, alias="DOCUMENT_TEXT_PREVIEW_CHARS")
    document_extracted_text_subdir: str = Field(
        default="extracted-text",
        alias="DOCUMENT_EXTRACTED_TEXT_SUBDIR",
    )

    ai_provider: str = Field(default="local", alias="AI_PROVIDER")
    ai_model: str = Field(default="local-heuristic-v1", alias="AI_MODEL")
    # Required when AI_PROVIDER is openai or azure_openai; never hardcode secrets.
    ai_api_key: str | None = Field(default=None, alias="AI_API_KEY")
    ai_base_url: str | None = Field(default=None, alias="AI_BASE_URL")
    ai_azure_endpoint: str | None = Field(default=None, alias="AI_AZURE_ENDPOINT")
    ai_azure_deployment: str | None = Field(default=None, alias="AI_AZURE_DEPLOYMENT")
    ai_azure_api_version: str = Field(default="2024-02-01", alias="AI_AZURE_API_VERSION")
    ai_assistant_retrieval_limit: int = Field(default=8, alias="AI_ASSISTANT_RETRIEVAL_LIMIT")
    ai_assistant_min_score: float = Field(default=0.12, alias="AI_ASSISTANT_MIN_SCORE")
    ai_assistant_max_prompt_chars: int = Field(
        default=12_000,
        alias="AI_ASSISTANT_MAX_PROMPT_CHARS",
    )
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

    # Ideogram External Design AI POC — never hardcode secrets.
    ideogram_api_key: str | None = Field(default=None, alias="IDEOGRAM_API_KEY")
    ideogram_enabled: bool = Field(default=True, alias="IDEOGRAM_ENABLED")
    ideogram_model: str = Field(default="V_4_0", alias="IDEOGRAM_MODEL")
    ideogram_default_quality: str = Field(default="QUALITY", alias="IDEOGRAM_DEFAULT_QUALITY")

    # GPT Image (OpenAI Images API) — SMB visual engine. Reuses AI_API_KEY.
    # Default model verified from official OpenAI docs (gpt-image-2, 2026-04-21).
    gpt_image_enabled: bool = Field(default=True, alias="GPT_IMAGE_ENABLED")
    gpt_image_model: str = Field(default="gpt-image-2", alias="GPT_IMAGE_MODEL")
    gpt_image_quality: str = Field(default="medium", alias="GPT_IMAGE_QUALITY")

    # Canva Connect OAuth 2.0 + PKCE — never hardcode secrets.
    canva_client_id: str | None = Field(default=None, alias="CANVA_CLIENT_ID")
    canva_client_secret: str | None = Field(default=None, alias="CANVA_CLIENT_SECRET")

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


_DEV_JWT_SECRET = "dev-only-change-in-production-use-long-random-string"


def validate_production_security(settings: Settings) -> None:
    """Fail closed on known-dangerous auth defaults when environment=production."""
    if settings.environment.lower() != "production":
        return
    problems: list[str] = []
    if not settings.auth_enabled:
        problems.append("API_AUTH_ENABLED must be true in production")
    if settings.jwt_secret == _DEV_JWT_SECRET or len(settings.jwt_secret.strip()) < 32:
        problems.append(
            "JWT_SECRET must be set to a unique secret (>=32 chars) in production"
        )
    dedicated = (settings.communication_credential_key or "").strip()
    if dedicated and len(dedicated) < 32:
        problems.append(
            "COMMUNICATION_CREDENTIAL_KEY must be at least 32 characters when set"
        )
    if not settings.auth_cookie_secure:
        problems.append("AUTH_COOKIE_SECURE must be true in production")
    if settings.debug:
        problems.append("API_DEBUG must be false in production")
    if settings.enable_openapi:
        problems.append("API_ENABLE_OPENAPI must be false in production")
    if problems:
        raise RuntimeError(
            "Refusing to start with insecure production configuration: "
            + "; ".join(problems)
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    validate_production_security(settings)
    return settings

import ipaddress
import json
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from investhome_api.config.cors import (
    DEFAULT_CORS_ORIGINS,
    production_cors_problems,
    sanitize_cors_origins,
)

# Published placeholders that must never be accepted at runtime.
_FORBIDDEN_JWT_SECRETS = frozenset(
    {
        "dev-only-change-in-production-use-long-random-string",
        "replace-with-long-random-secret-at-least-32-chars",
        "investhome-portal-demo-session-secret",
        "replace-with-long-random-portal-secret",
        "dev-only-portal-session-secret-change-me",
        "replace-with-32-char-encryption-key",
    }
)


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

    database_url: str = Field(alias="DATABASE_URL")

    jwt_secret: str = Field(alias="JWT_SECRET", min_length=32)
    communication_credential_key: str | None = Field(
        default=None,
        alias="COMMUNICATION_CREDENTIAL_KEY",
        description="Dedicated AES-256-GCM key for Email/WhatsApp tokens at rest. Required; never derived from JWT_SECRET.",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=480, alias="JWT_EXPIRE_MINUTES")
    session_absolute_timeout_minutes: int = Field(
        default=1440,
        alias="SESSION_ABSOLUTE_TIMEOUT_MINUTES",
        description="Absolute maximum browser session lifetime from original login (minutes).",
    )
    auth_enabled: bool = Field(default=True, alias="API_AUTH_ENABLED")
    auth_cookie_name: str = Field(default="ih_session", alias="AUTH_COOKIE_NAME")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: str = Field(default="lax", alias="AUTH_COOKIE_SAMESITE")
    auth_cookie_domain: str | None = Field(default=None, alias="AUTH_COOKIE_DOMAIN")

    cors_origins: Annotated[list[str] | None, NoDecode] = Field(
        default=None,
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
    document_malware_scan_enabled: bool = Field(
        default=False,
        alias="DOCUMENT_MALWARE_SCAN_ENABLED",
    )
    document_malware_scan_provider: str = Field(
        default="stub",
        alias="DOCUMENT_MALWARE_SCAN_PROVIDER",
    )
    document_malware_scan_fail_closed: bool = Field(
        default=True,
        alias="DOCUMENT_MALWARE_SCAN_FAIL_CLOSED",
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
    # Redirect URI is exact-match allowlisted (local HTTP in development; HTTPS in production).
    gmail_oauth_redirect_uri: str | None = Field(default=None, alias="GMAIL_OAUTH_REDIRECT_URI")
    gmail_sync_enabled: bool = Field(default=True, alias="GMAIL_SYNC_ENABLED")
    gmail_sync_interval_minutes: int = Field(default=5, alias="GMAIL_SYNC_INTERVAL_MINUTES")
    gmail_backfill_days: int = Field(default=30, alias="GMAIL_BACKFILL_DAYS")

    # Meta WhatsApp Cloud API inbound webhook. No usable defaults. Do not reuse JWT secrets.
    whatsapp_app_secret: str | None = Field(default=None, alias="WHATSAPP_APP_SECRET")
    whatsapp_verify_token: str | None = Field(default=None, alias="WHATSAPP_VERIFY_TOKEN")

    # Meta Page / Messenger inbound webhook. Separate from WhatsApp. No usable defaults.
    meta_app_secret: str | None = Field(default=None, alias="META_APP_SECRET")
    meta_verify_token: str | None = Field(default=None, alias="META_VERIFY_TOKEN")
    meta_page_id: str | None = Field(default=None, alias="META_PAGE_ID")
    # Page access token is server-side only. Required to send Messenger/Instagram DMs; fail closed if missing.
    meta_page_access_token: str | None = Field(default=None, alias="META_PAGE_ACCESS_TOKEN")
    # Optional Instagram Business account id used to filter inbound DMs. Not required for webhook startup.
    meta_instagram_account_id: str | None = Field(default=None, alias="META_INSTAGRAM_ACCOUNT_ID")

    redis_url: str = Field(alias="REDIS_URL")
    # Backup readiness reporting only. BACKUP_PROVIDER does not connect a live adapter
    # and cannot produce a verified/healthy status by itself.
    backup_provider: str = Field(default="none", alias="BACKUP_PROVIDER")
    backup_freshness_hours: int = Field(default=24, ge=1, alias="BACKUP_FRESHNESS_HOURS")
    # Security monitoring thresholds (signals only — does not block users).
    security_monitor_window_seconds: int = Field(default=900, ge=60, alias="SECURITY_MONITOR_WINDOW_SECONDS")
    security_monitor_failed_login_burst: int = Field(default=5, ge=2, alias="SECURITY_MONITOR_FAILED_LOGIN_BURST")
    security_monitor_failed_login_critical: int = Field(
        default=15, ge=3, alias="SECURITY_MONITOR_FAILED_LOGIN_CRITICAL"
    )
    security_monitor_multi_account: int = Field(default=3, ge=2, alias="SECURITY_MONITOR_MULTI_ACCOUNT")
    security_monitor_multi_account_critical: int = Field(
        default=8, ge=3, alias="SECURITY_MONITOR_MULTI_ACCOUNT_CRITICAL"
    )
    security_monitor_mfa_burst: int = Field(default=5, ge=2, alias="SECURITY_MONITOR_MFA_BURST")
    security_monitor_csrf_burst: int = Field(default=8, ge=2, alias="SECURITY_MONITOR_CSRF_BURST")
    security_monitor_webhook_burst: int = Field(default=5, ge=2, alias="SECURITY_MONITOR_WEBHOOK_BURST")
    security_monitor_document_denied_burst: int = Field(
        default=8, ge=2, alias="SECURITY_MONITOR_DOCUMENT_DENIED_BURST"
    )
    security_monitor_pepper: str | None = Field(default=None, alias="SECURITY_MONITOR_PEPPER")
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

    # IPs/CIDRs allowed to supply X-Forwarded-For / X-Real-IP.
    # Empty (default): ignore forwarded headers; use the TCP peer only.
    # Do not populate with CDN ranges until this API is actually behind that proxy.
    trusted_proxy_ips: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        alias="API_TRUSTED_PROXY_IPS",
    )
    mfa_totp_issuer: str = Field(default="InvestHomeOS", alias="MFA_TOTP_ISSUER")
    user_invite_ttl_hours: int = Field(default=168, ge=1, le=720, alias="USER_INVITE_TTL_HOURS")

    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, ge=1, le=65535, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="InvestHome OS", alias="SMTP_FROM_NAME")
    app_public_url: str | None = Field(default=None, alias="APP_PUBLIC_URL")

    # Public marketing form abuse protection (no production Turnstile keys yet).
    public_form_bot_verify: bool = Field(default=False, alias="PUBLIC_FORM_BOT_VERIFY")
    turnstile_secret_key: str | None = Field(default=None, alias="TURNSTILE_SECRET_KEY")
    turnstile_siteverify_url: str = Field(
        default="https://challenges.cloudflare.com/turnstile/v0/siteverify",
        alias="TURNSTILE_SITEVERIFY_URL",
    )
    public_form_burst_limit: int = Field(default=5, alias="PUBLIC_FORM_BURST_LIMIT")
    public_form_burst_window_seconds: int = Field(
        default=600,
        alias="PUBLIC_FORM_BURST_WINDOW_SECONDS",
    )
    public_form_daily_limit: int = Field(default=20, alias="PUBLIC_FORM_DAILY_LIMIT")
    public_form_daily_window_seconds: int = Field(
        default=86400,
        alias="PUBLIC_FORM_DAILY_WINDOW_SECONDS",
    )
    # WordPress server-to-server website form ingest. Never expose to browsers.
    website_form_ingest_secret: str | None = Field(
        default=None,
        alias="WEBSITE_FORM_INGEST_SECRET",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, list):
            return sanitize_cors_origins([str(origin) for origin in value])
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if stripped == "*":
                return []
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    msg = "API_CORS_ORIGINS JSON value is malformed"
                    raise ValueError(msg) from exc
                if not isinstance(parsed, list):
                    msg = "API_CORS_ORIGINS JSON value must be an array"
                    raise ValueError(msg)
                return sanitize_cors_origins([str(origin) for origin in parsed])
            return sanitize_cors_origins(stripped.split(","))
        msg = "API_CORS_ORIGINS must be a JSON array or comma-separated string"
        raise ValueError(msg)

    @field_validator("redis_url", mode="before")
    @classmethod
    def redis_url_required(cls, value: Any) -> str:
        if value is None or (isinstance(value, str) and not str(value).strip()):
            raise ValueError("REDIS_URL is required")
        return str(value).strip()

    @model_validator(mode="after")
    def apply_development_cors_default(self) -> "Settings":
        if self.cors_origins is not None:
            return self
        env = (self.environment or "").strip().lower()
        if env in {"production", "prod"}:
            self.cors_origins = []
            return self
        self.cors_origins = list(DEFAULT_CORS_ORIGINS)
        return self

    @field_validator("trusted_proxy_ips", mode="before")
    @classmethod
    def parse_trusted_proxy_ips(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if not isinstance(parsed, list):
                    msg = "API_TRUSTED_PROXY_IPS JSON value must be an array"
                    raise ValueError(msg)
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        msg = "API_TRUSTED_PROXY_IPS must be a JSON array or comma-separated string"
        raise ValueError(msg)

    @field_validator(
        "smtp_host",
        "smtp_username",
        "smtp_password",
        "smtp_from_email",
        "app_public_url",
        mode="before",
    )
    @classmethod
    def empty_optional_secret_to_none(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("smtp_from_name", mode="before")
    @classmethod
    def default_smtp_from_name(cls, value: Any) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "InvestHome OS"
        return str(value).strip()

    @field_validator("smtp_port", mode="before")
    @classmethod
    def default_smtp_port(cls, value: Any) -> Any:
        if value is None or (isinstance(value, str) and not value.strip()):
            return 587
        return value

    @field_validator("smtp_use_tls", mode="before")
    @classmethod
    def default_smtp_use_tls(cls, value: Any) -> Any:
        if value is None or (isinstance(value, str) and not value.strip()):
            return True
        return value

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_be_unique(cls, value: str) -> str:
        secret = (value or "").strip()
        if not secret:
            raise ValueError("JWT_SECRET is required")
        if len(secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        if secret in _FORBIDDEN_JWT_SECRETS:
            raise ValueError(
                "JWT_SECRET must not use a published default or placeholder value"
            )
        return secret


_LOCAL_DEV_ENVIRONMENTS = frozenset({"development", "dev", "local", "test"})
_STAGING_ENVIRONMENTS = frozenset({"staging", "stage", "preprod", "uat"})
_PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})


def _normalized_environment(settings: Settings) -> str:
    return (settings.environment or "").strip().lower()


def is_loopback_bind(host: str | None) -> bool:
    value = (host or "").strip().lower()
    if value in {"localhost", "::1"}:
        return True
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def validate_auth_bypass(settings: Settings) -> None:
    """Fail closed unless auth-disabled mode is explicit local loopback development."""
    if settings.auth_enabled:
        return
    env = _normalized_environment(settings)
    problems: list[str] = []
    if env in _PRODUCTION_ENVIRONMENTS:
        problems.append("API_AUTH_ENABLED must be true in production")
    if env in _STAGING_ENVIRONMENTS:
        problems.append("API_AUTH_ENABLED must be true in staging")
    if env not in _LOCAL_DEV_ENVIRONMENTS:
        problems.append(
            "API_AUTH_ENABLED=false is allowed only for explicit local development"
        )
    if not is_loopback_bind(settings.host):
        problems.append(
            "API_AUTH_ENABLED=false requires a loopback bind (127.0.0.1, ::1, or localhost)"
        )
    if problems:
        raise RuntimeError(
            "Refusing to start with insecure authentication bypass: " + "; ".join(problems)
        )


def validate_required_secrets(settings: Settings) -> None:
    """Fail closed in every environment when JWT_SECRET is missing or published."""
    secret = (settings.jwt_secret or "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET is required")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")
    if secret in _FORBIDDEN_JWT_SECRETS:
        raise RuntimeError(
            "JWT_SECRET must not use a published default or placeholder value"
        )


def redis_url_is_authenticated(url: str) -> bool:
    """True when REDIS_URL includes a non-empty password. Never log the URL."""
    parsed = urlparse((url or "").strip())
    password = parsed.password
    return bool(password)


def validate_production_security(settings: Settings) -> None:
    """Fail closed on known-dangerous auth defaults when environment=production."""
    validate_required_secrets(settings)
    env = _normalized_environment(settings)
    production_like = env in _PRODUCTION_ENVIRONMENTS
    if not production_like and settings.environment.lower() != "production":
        return
    problems: list[str] = []
    if production_like:
        if not (settings.redis_url or "").strip():
            problems.append("REDIS_URL is required in production")
        elif not redis_url_is_authenticated(settings.redis_url):
            problems.append("REDIS_URL must include a password in production")
        problems.extend(production_cors_problems(settings.cors_origins))
    if settings.environment.lower() != "production":
        if problems:
            raise RuntimeError(
                "Refusing to start with insecure production configuration: "
                + "; ".join(problems)
            )
        return
    if not settings.auth_enabled:
        problems.append("API_AUTH_ENABLED must be true in production")
    if len(settings.jwt_secret.strip()) < 32:
        problems.append("JWT_SECRET must be set to a unique secret (>=32 chars)")
    dedicated = (settings.communication_credential_key or "").strip()
    if not dedicated:
        problems.append("COMMUNICATION_CREDENTIAL_KEY is required in production")
    elif len(dedicated) < 32:
        problems.append("COMMUNICATION_CREDENTIAL_KEY must be at least 32 characters")
    elif dedicated == settings.jwt_secret.strip():
        problems.append("COMMUNICATION_CREDENTIAL_KEY must be distinct from JWT_SECRET")
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


def validate_communication_credential_key(settings: Settings) -> None:
    """Fail closed: communication credentials never derive from JWT_SECRET."""
    dedicated = (settings.communication_credential_key or "").strip()
    jwt = (settings.jwt_secret or "").strip()
    if dedicated and dedicated == jwt:
        raise RuntimeError("COMMUNICATION_CREDENTIAL_KEY must be distinct from JWT_SECRET")
    if dedicated and len(dedicated) < 32:
        raise RuntimeError("COMMUNICATION_CREDENTIAL_KEY must be at least 32 characters")
    env = _normalized_environment(settings)
    if env in _PRODUCTION_ENVIRONMENTS:
        if not dedicated:
            raise RuntimeError("COMMUNICATION_CREDENTIAL_KEY is required in production")
        return
    if not dedicated:
        raise RuntimeError("COMMUNICATION_CREDENTIAL_KEY is required")


def validate_whatsapp_webhook_secrets(settings: Settings) -> None:
    """Fail closed in production when Meta webhook secrets are missing."""
    env = _normalized_environment(settings)
    if env not in _PRODUCTION_ENVIRONMENTS:
        return
    if not (settings.whatsapp_app_secret or "").strip():
        raise RuntimeError("WHATSAPP_APP_SECRET is required in production")
    if not (settings.whatsapp_verify_token or "").strip():
        raise RuntimeError("WHATSAPP_VERIFY_TOKEN is required in production")


def validate_meta_webhook_secrets(settings: Settings) -> None:
    """Fail closed in production when Messenger webhook secrets are missing."""
    env = _normalized_environment(settings)
    if env not in _PRODUCTION_ENVIRONMENTS:
        return
    if not (settings.meta_app_secret or "").strip():
        raise RuntimeError("META_APP_SECRET is required in production")
    if not (settings.meta_verify_token or "").strip():
        raise RuntimeError("META_VERIFY_TOKEN is required in production")
    if not (settings.meta_page_id or "").strip():
        raise RuntimeError("META_PAGE_ID is required in production")


def _local_dotenv_candidates() -> list[Path]:
    cwd = Path.cwd().resolve()
    return [cwd / ".env", cwd.parent / ".env"]


def _persist_local_communication_credential_key() -> str | None:
    """Write a dedicated local key to .env without printing it. Never overwrites a set value."""
    generated = secrets.token_urlsafe(32)
    for path in _local_dotenv_candidates():
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        replaced = False
        new_lines: list[str] = []
        for line in lines:
            if line.startswith("COMMUNICATION_CREDENTIAL_KEY="):
                current = line.split("=", 1)[1].strip().strip('"').strip("'")
                if current:
                    return None
                new_lines.append(f"COMMUNICATION_CREDENTIAL_KEY={generated}")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            if new_lines and new_lines[-1] != "":
                new_lines.append("")
            new_lines.append(f"COMMUNICATION_CREDENTIAL_KEY={generated}")
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return generated
    return None


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    dedicated = (settings.communication_credential_key or "").strip()
    env = _normalized_environment(settings)
    if (
        not dedicated
        and env not in _PRODUCTION_ENVIRONMENTS
        and not os.environ.get("PYTEST_CURRENT_TEST")
    ):
        generated = _persist_local_communication_credential_key()
        if generated:
            os.environ["COMMUNICATION_CREDENTIAL_KEY"] = generated
            settings = Settings()
    validate_required_secrets(settings)
    validate_communication_credential_key(settings)
    validate_production_security(settings)
    validate_auth_bypass(settings)
    return settings

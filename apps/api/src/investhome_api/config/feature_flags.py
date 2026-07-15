"""Centralized feature flags (environment-driven, no code changes to toggle)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlags(BaseSettings):
    """Runtime feature toggles. Extend as new modules ship."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="FEATURE_",
    )

    company_foundation: bool = Field(default=True)
    document_intelligence: bool = Field(default=True)
    drawing_intelligence: bool = Field(default=True)
    universal_search: bool = Field(default=True)
    notification_center: bool = Field(default=True)
    activity_log: bool = Field(default=True)
    executive_dashboard: bool = Field(default=True)
    n8n_automation: bool = Field(default=False)
    external_ai: bool = Field(default=False)
    external_storage: bool = Field(default=False)


@lru_cache
def get_feature_flags() -> FeatureFlags:
    return FeatureFlags()


def is_feature_enabled(flag_name: str) -> bool:
    flags = get_feature_flags()
    return bool(getattr(flags, flag_name, False))

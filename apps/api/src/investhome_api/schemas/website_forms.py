"""Public website form (WordPress S2S) payload. No CRM read fields."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from investhome_api.services.crm.identity import is_valid_email, normalize_email

WEBSITE_FORM_MAX_BODY_BYTES = 32_768
WEBSITE_FORM_SOURCE_CODE = "website"
WEBSITE_FORM_SOURCE_LABEL = "Web Site Form"
WEBSITE_FORM_RATE_SLUG = "website-form-general"


def _optional_http_url(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an http or https URL")
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} must not include credentials")
    return text


class WebsiteFormSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=7, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    kvkk_accepted: Literal[True]
    occupation: str | None = Field(default=None, max_length=120)
    message: str | None = Field(default=None, max_length=5000)
    page_url: str | None = Field(default=None, max_length=2000)
    page_title: str | None = Field(default=None, max_length=255)
    project: str | None = Field(default=None, max_length=255)
    form_type: str | None = Field(default="general_contact", max_length=80)
    referrer: str | None = Field(default=None, max_length=2000)
    utm_source: str | None = Field(default=None, max_length=255)
    utm_medium: str | None = Field(default=None, max_length=255)
    utm_campaign: str | None = Field(default=None, max_length=255)
    utm_content: str | None = Field(default=None, max_length=255)
    utm_term: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, max_length=16)
    idempotency_key: str = Field(min_length=8, max_length=255)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("full_name is required")
        if any(ord(ch) < 32 for ch in cleaned):
            raise ValueError("full_name contains invalid characters")
        return cleaned

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        email = normalize_email(value)
        if not is_valid_email(email):
            raise ValueError("email is invalid")
        return email or value

    @field_validator("page_url")
    @classmethod
    def clean_page_url(cls, value: str | None) -> str | None:
        return _optional_http_url(value, field_name="page_url")

    @field_validator("referrer")
    @classmethod
    def clean_referrer(cls, value: str | None) -> str | None:
        return _optional_http_url(value, field_name="referrer")

    @field_validator("form_type", "occupation", "message", "page_title", "project", "language")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator(
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
    )
    @classmethod
    def empty_utm_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class WebsiteFormSubmitResponse(BaseModel):
    accepted: bool
    duplicate: bool = False
    matched_existing: bool
    inquiry_id: UUID
    request_id: str | None = None

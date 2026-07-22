"""Pydantic schemas for G15A Platform Core API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModuleUpdateRequest(BaseModel):
    enabled: bool | None = None
    env_enabled: bool | None = None
    kill_switch: bool | None = None
    depends_on: list[str] | None = None
    rename_code: str | None = None


class ModuleDepsPreviewRequest(BaseModel):
    depends_on: list[str] = Field(default_factory=list)


class FeatureFlagPlatformUpdateRequest(BaseModel):
    enabled: bool = True
    rollout_percent: int = Field(default=100, ge=0, le=100)
    target_roles: list[str] = Field(default_factory=list)
    target_companies: list[str] = Field(default_factory=list)
    target_users: list[str] = Field(default_factory=list)
    kill_switch: bool = False
    environment_scope: str = "all"
    notes: str | None = None


class EntitlementCheckRequest(BaseModel):
    capability: str
    role_codes: list[str] = Field(default_factory=list)
    external_type: str | None = None
    user_id: str | None = None
    company_id: str | None = None


class ApiClientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=list)


class ApiScopeCheckRequest(BaseModel):
    api_key: str
    required_scope: str


class WebhookCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    target_url: str = Field(min_length=8, max_length=1024)
    event_types: list[str] = Field(default_factory=list)


class WebhookEnqueueRequest(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    signing_secret: str | None = None


class WebhookVerifyRequest(BaseModel):
    secret: str
    payload: dict[str, Any]
    signature_header: str


class BrandingUpdateRequest(BaseModel):
    display_name_en: str | None = None
    display_name_tr: str | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    secondary_color: str | None = None
    support_email: str | None = None
    footer_en: str | None = None
    footer_tr: str | None = None
    custom_css: str | None = None


class ContractorAccessCheckRequest(BaseModel):
    contractor_user_id: str
    project_id: str
    assigned_project_ids: list[str] = Field(default_factory=list)


class ExternalAccessRecordRequest(BaseModel):
    action: str
    resource: str
    outcome: str = "allowed"
    external_type: str | None = None
    resource_id: str | None = None
    project_id: str | None = None
    detail: str | None = None


class MessageResponse(BaseModel):
    message: str
